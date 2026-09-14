"""
Adapter for H2O GPT Enterprise (h2ogpte) so evaluator_v04 can use any model
hosted on an h2ogpte instance — including Claude Opus via H2O's API.

Usage:
    from src.h2ogpte_model import H2OGPTEChatModel
    model = H2OGPTEChatModel(
        address="https://your-h2ogpte-instance.h2o.ai",
        api_key="your-api-key",
        model_name="claude-opus-5",   # whatever name h2ogpte uses
    )
    response = await model(messages)
    print(response.content[0]["text"])

Interface:
    Same duck-typed interface as AnthropicChatModel / OllamaChatModel:
    - __call__(messages, tools=None) → H2OGPTEResponse
    - response.content: list of {"type": "text", "text": "..."}

Note on tools:
    h2ogpte's answer_question does not support function/tool calling natively.
    If tools are passed they are silently ignored — the model will respond in text.
    For v0.3-style evaluation (no tool loop) this is fine.
    For v0.4 tool_gated / confused_deputy cases, wire up a separate adapter.

Message format accepted (OpenAI-style):
    [
        {"role": "system",    "content": "..."},
        {"role": "user",      "content": "..."},
        {"role": "assistant", "content": "..."},
        ...
    ]
h2ogpte wants: system_prompt (str) + chat_conversation (list of (human, assistant) tuples)
+ final question (str).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from h2ogpte import H2OGPTE


class H2OGPTEResponse:
    """Duck-typed to match _extract_text / _extract_tool_calls in evaluator_v04."""

    def __init__(self, text: str) -> None:
        self.content: list[dict] = [{"type": "text", "text": text}]


class H2OGPTEChatModel:
    """
    Async callable adapter for H2O GPT Enterprise.

    Parameters
    ----------
    address : str
        Base URL of the h2ogpte instance, e.g. "https://xxx.h2o.ai".
        Falls back to H2OGPTE_ADDRESS env var.
    api_key : str | None
        API key for authentication. Falls back to H2OGPTE_API_KEY env var.
    model_name : str
        The LLM identifier as h2ogpte names it, e.g. "claude-opus-5".
        Falls back to H2OGPTE_MODEL env var, then None (uses instance default).
    temperature : float
        Sampling temperature passed as llm_args.
    max_new_tokens : int
        Max output tokens passed as llm_args.
    verify_ssl : bool
        Set False to skip TLS verification (useful for self-signed certs or instances
        with missing intermediate certs). Defaults to False for h2ogpte.genai.h2o.ai.
    """

    def __init__(
        self,
        address: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.0,
        max_new_tokens: int = 1024,
        verify_ssl: bool = False,
    ) -> None:
        self.address = address or os.environ.get("H2OGPTE_ADDRESS", "")
        self.api_key = api_key or os.environ.get("H2OGPTE_API_KEY")
        self.model_name = model_name or os.environ.get("H2OGPTE_MODEL") or None
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        self.verify_ssl = verify_ssl

        if not self.address:
            raise ValueError(
                "h2ogpte address is required. Pass address= or set H2OGPTE_ADDRESS."
            )

        self._client = H2OGPTE(
            address=self.address,
            api_key=self.api_key,
            verify=self.verify_ssl,
            strict_version_check=False,
        )

    async def __call__(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> H2OGPTEResponse:
        system_prompt, chat_history, question = _convert_messages(messages)

        llm_args: dict = {
            "temperature": self.temperature,
            "max_new_tokens": self.max_new_tokens,
        }

        # answer_question is synchronous — run in thread pool so we don't block the event loop
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(
            None,
            lambda: self._client.answer_question(
                question=question,
                system_prompt=system_prompt,
                chat_conversation=chat_history,
                llm=self.model_name,
                llm_args=llm_args,
            ),
        )

        if answer.error:
            raise RuntimeError(f"h2ogpte error: {answer.error}")

        return H2OGPTEResponse(answer.content)


# ---------------------------------------------------------------------------
# Format converter
# ---------------------------------------------------------------------------

def _convert_messages(
    messages: list[dict],
) -> tuple[str, list[tuple[str, str]], str]:
    """
    Convert OpenAI-style messages → (system_prompt, chat_history, final_question).

    h2ogpte's answer_question takes:
      - system_prompt: str
      - chat_conversation: list of (human_msg, assistant_msg) tuples for prior turns
      - question: str (the current / final user message)

    Strategy:
      1. Extract system message (if present).
      2. Walk remaining messages in pairs: user → assistant builds history tuples.
      3. The last user message becomes `question`.
      4. If the last message is assistant (shouldn't happen in evaluation), append empty
         user string as question.
    """
    system_prompt = ""
    remaining: list[dict] = []

    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg.get("content") or ""
        else:
            remaining.append(msg)

    if not remaining:
        return system_prompt, [], ""

    # Separate the final user turn from the history
    if remaining[-1]["role"] == "user":
        history_msgs = remaining[:-1]
        question = remaining[-1].get("content") or ""
    else:
        # Last message is assistant — treat everything as history, question=""
        history_msgs = remaining
        question = ""

    # Build (human, assistant) tuples from alternating pairs
    chat_history: list[tuple[str, str]] = []
    i = 0
    while i < len(history_msgs) - 1:
        u = history_msgs[i]
        a = history_msgs[i + 1]
        if u["role"] == "user" and a["role"] == "assistant":
            chat_history.append((
                u.get("content") or "",
                a.get("content") or "",
            ))
            i += 2
        else:
            i += 1  # skip unexpected ordering

    return system_prompt, chat_history, question
