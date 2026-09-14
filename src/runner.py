from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class ExecutionTrace:
    case_id: str
    responses: list[ModelResponse]
    tool_calls: list[ToolCall]
    turns: int


class ModelAdapter:
    def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> ModelResponse:
        raise NotImplementedError


def run_case(
    case: dict,
    model: ModelAdapter,
) -> ExecutionTrace:

    messages = list(case["attack"]["conversation"])

    responses = []
    tool_calls = []

    max_turns = case["attack"]["budget"]["max_turns"]

    for _ in range(max_turns):

        response = model.generate(
            messages=messages,
            tools=case.get("tools", []),
        )

        responses.append(response)

        tool_calls.extend(response.tool_calls)

        messages.append({
            "role": "assistant",
            "content": response.text,
        })

        # Tool execution is deliberately handled outside
        # the model adapter so that unauthorized attempts
        # can be measured independently.

        if not response.tool_calls:
            break

        break

    return ExecutionTrace(
        case_id=case["id"],
        responses=responses,
        tool_calls=tool_calls,
        turns=len(responses),
    )

