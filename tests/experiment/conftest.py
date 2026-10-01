"""Shared helper: a scripted stand-in for the model (Inspect mockllm, no network)."""

from __future__ import annotations

import pytest
from inspect_ai.model import ModelOutput, ModelUsage, get_model


@pytest.fixture
def scripted_model():
    """Factory: a model that issues the given tool calls in order.

    `seen` receives, per model call, the messages and tool definitions exactly
    as the model would get them.
    """

    def make(calls: list[tuple[str, dict]], seen: list | None = None):
        remaining = iter(calls)

        def respond(input, tools, tool_choice, config):
            if seen is not None:
                seen.append(
                    {
                        "messages": [(m.role, m.text) for m in input],
                        "tools": [t.model_dump() for t in tools],
                    }
                )
            name, arguments = next(remaining)
            output = ModelOutput.for_tool_call("mockllm/model", name, arguments)
            # Explicit usage; without it mockllm downloads a tokenizer to count.
            output.usage = ModelUsage(input_tokens=3, output_tokens=2, total_tokens=5)
            return output

        return get_model("mockllm/model", custom_outputs=respond)

    return make
