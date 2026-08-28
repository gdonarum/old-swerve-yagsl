"""LiteLLM client wrapper.

LiteLLM proxies expose an OpenAI-compatible API, so we use the ``openai`` SDK
pointed at the *locked* approved endpoint. The base_url comes from the bundled
registry — it cannot be overridden at runtime — and the API key comes from the
endpoint's designated environment variable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from openai import OpenAI

from .endpoints import Endpoint


@dataclass
class StreamedResponse:
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str | None = None


class LLMClient:
    def __init__(self, endpoint: Endpoint, model: str, timeout: float = 600.0):
        self.endpoint = endpoint
        self.model = model
        api_key = endpoint.api_key
        if not api_key:
            raise SystemExit(
                f"No API key found. Set the environment variable "
                f"'{endpoint.api_key_env}' with your DCS LiteLLM key."
            )
        self._client = OpenAI(
            base_url=endpoint.base_url,
            api_key=api_key,
            timeout=timeout,
        )

    def set_model(self, model: str) -> None:
        self.model = model

    def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        *,
        stream: bool = True,
        on_text: Any = None,
    ) -> StreamedResponse:
        """Run one chat completion turn, returning accumulated text + tool calls.

        ``on_text`` (if provided) is called with each incremental text chunk so
        the REPL can render streaming output.
        """
        if stream:
            return self._complete_streaming(messages, tools, on_text)
        return self._complete_blocking(messages, tools)

    # -- streaming ----------------------------------------------------------
    def _complete_streaming(self, messages, tools, on_text) -> StreamedResponse:
        kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        result = StreamedResponse()
        tool_acc: dict[int, dict] = {}
        stream = self._client.chat.completions.create(**kwargs)
        for chunk in stream:
            if chunk.usage:
                result.prompt_tokens = chunk.usage.prompt_tokens or 0
                result.completion_tokens = chunk.usage.completion_tokens or 0
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if choice.finish_reason:
                result.finish_reason = choice.finish_reason
            if delta is None:
                continue
            if delta.content:
                result.content += delta.content
                if on_text:
                    on_text(delta.content)
            for tc in delta.tool_calls or []:
                slot = tool_acc.setdefault(
                    tc.index, {"id": None, "name": "", "arguments": ""}
                )
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    slot["arguments"] += tc.function.arguments

        result.tool_calls = [
            {
                "id": tool_acc[i]["id"] or f"call_{i}",
                "type": "function",
                "function": {
                    "name": tool_acc[i]["name"],
                    "arguments": tool_acc[i]["arguments"] or "{}",
                },
            }
            for i in sorted(tool_acc)
        ]
        return result

    # -- blocking -----------------------------------------------------------
    def _complete_blocking(self, messages, tools) -> StreamedResponse:
        kwargs: dict[str, Any] = dict(model=self.model, messages=messages)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        result = StreamedResponse(
            content=msg.content or "",
            finish_reason=choice.finish_reason,
        )
        if resp.usage:
            result.prompt_tokens = resp.usage.prompt_tokens or 0
            result.completion_tokens = resp.usage.completion_tokens or 0
        for tc in msg.tool_calls or []:
            result.tool_calls.append(
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
            )
        return result
