"""Token usage and cost tracking."""

from __future__ import annotations

from dataclasses import dataclass

from .endpoints import ModelSpec


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    requests: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, prompt: int, completion: int) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.requests += 1

    def cost(self, model: ModelSpec | None) -> float:
        if model is None:
            return 0.0
        return (
            self.prompt_tokens / 1000 * model.prompt_per_1k
            + self.completion_tokens / 1000 * model.completion_per_1k
        )
