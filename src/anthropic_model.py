"""
Thin async wrapper around the Anthropic Messages API.

Provides the same calling interface as OllamaChatModel so evaluator_v04
can target Claude models without changing the core evaluation logic.

Claude's tool-call format differs from OpenAI's:
  - Tool calls come back as content blocks: {"type": "tool_use", "id": ..., "name": ..., "input": {...}}
  - Tool results go back as a user message with content blocks:
      {"role": "user", "content": [{"type": "tool_result", "tool_use_id": ..., "content": "..."}]}

The adapter translates the evaluator's OpenAI-style tool_result messages into
Claude's format before each API call, and wraps the response in a duck-typed
object that _extract_text / _extract_tool_calls already understand.
"""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic


class AnthropicResponse:
    """Duck-typed to match what _extract_text / _extract_tool_calls expect."""

    def __init__(self, message: anthropic.types.Message) -> None:
        self._message = message
        # Convert Anthropic content blocks → internal content format
        self.content: list[dict] = []
        for block in message.content:
            if block.type == "text":
                self.content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                self.content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,  # already a dict
                })
        self.usage = None  # token tracking not wired yet


class AnthropicChatModel:
    """
    Async callable that mirrors OllamaChatModel's interface:

        response = await model(messages, tools=tool_schemas)

    Parameters
    ----------
    model_name : str
        E.g. "claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5-20251001"
    api_key : str | None
        If None, reads ANTHROPIC_API_KEY from environment.
    max_tokens : int
        Max output tokens per call (required by Anthropic API).
    """

    def __init__(
        self,
        model_name: str = "claude-opus-5",
        api_key: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> None:
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )

    async def __call__(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> AnthropicResponse:
        system_prompt, claude_messages = _convert_messages(messages)
        claude_tools = _convert_tools(tools) if tools else anthropic.NOT_GIVEN

        response = await self._client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt or anthropic.NOT_GIVEN,
            messages=claude_messages,
            tools=claude_tools,
        )
        return AnthropicResponse(response)


# ---------------------------------------------------------------------------
# Format converters
# ---------------------------------------------------------------------------

def _convert_messages(
    messages: list[dict],
) -> tuple[str, list[dict]]:
    """
    Split out the system message and convert the rest to Anthropic format.

    OpenAI-style tool results:
        {"role": "tool", "tool_call_id": "...", "content": "..."}

    Anthropic-style tool results (inside a user message):
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]}

    OpenAI-style assistant tool calls:
        {"role": "assistant", "content": None, "tool_calls": [{"id": ..., "function": {"name": ..., "arguments": ...}}]}

    Anthropic-style assistant tool calls:
        {"role": "assistant", "content": [{"type": "tool_use", "id": ..., "name": ..., "input": {...}}]}
    """
    system_prompt = ""
    out: list[dict] = []

    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg["role"]

        if role == "system":
            system_prompt = msg.get("content") or ""
            i += 1
            continue

        if role == "tool":
            # Collect consecutive tool results into one user message
            tool_results: list[dict] = []
            while i < len(messages) and messages[i]["role"] == "tool":
                tr = messages[i]
                content_str = tr.get("content", "")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tr.get("tool_call_id", ""),
                    "content": content_str,
                })
                i += 1
            out.append({"role": "user", "content": tool_results})
            continue

        if role == "assistant":
            content_str = msg.get("content") or ""
            tool_calls = msg.get("tool_calls", [])

            if tool_calls:
                # Convert OpenAI-style tool calls to Claude content blocks
                blocks: list[dict] = []
                if content_str:
                    blocks.append({"type": "text", "text": content_str})
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", fn.get("name", "call")),
                        "name": fn.get("name", ""),
                        "input": args,
                    })
                out.append({"role": "assistant", "content": blocks})
            else:
                out.append({"role": "assistant", "content": content_str or " "})
            i += 1
            continue

        if role == "user":
            content = msg.get("content", "")
            out.append({"role": "user", "content": content or " "})
            i += 1
            continue

        # Unknown role — skip
        i += 1

    # Anthropic requires alternating user/assistant. Merge consecutive same-role messages.
    out = _merge_consecutive(out)

    return system_prompt, out


def _merge_consecutive(messages: list[dict]) -> list[dict]:
    """Merge consecutive messages with the same role into one."""
    if not messages:
        return messages
    merged = [messages[0]]
    for msg in messages[1:]:
        if msg["role"] == merged[-1]["role"]:
            # Combine content
            prev = merged[-1]
            prev_content = prev["content"]
            curr_content = msg["content"]
            if isinstance(prev_content, list) and isinstance(curr_content, list):
                prev["content"] = prev_content + curr_content
            elif isinstance(prev_content, str) and isinstance(curr_content, str):
                prev["content"] = (prev_content + "\n" + curr_content).strip()
            elif isinstance(prev_content, list):
                prev["content"] = prev_content + [{"type": "text", "text": str(curr_content)}]
            else:
                prev["content"] = [{"type": "text", "text": str(prev_content)}] + (
                    curr_content if isinstance(curr_content, list)
                    else [{"type": "text", "text": str(curr_content)}]
                )
        else:
            merged.append(msg)
    return merged


def _convert_tools(tools: list[dict]) -> list[dict]:
    """Convert OpenAI-style tool schemas to Anthropic format."""
    out = []
    for t in tools:
        fn = t.get("function", t)
        out.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return out
