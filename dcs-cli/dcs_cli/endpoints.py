"""Locked, DCS-approved LiteLLM endpoint registry.

The registry is bundled with the package (``endpoints.toml``). Because the
approved endpoints ship inside the distribution, an operator cannot make the
CLI talk to an arbitrary external model at runtime — only the endpoints and
models declared here are reachable. API keys are supplied via the environment
variable named by each endpoint (never stored in the registry).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from importlib import resources


@dataclass(frozen=True)
class ModelSpec:
    name: str
    label: str
    prompt_per_1k: float = 0.0
    completion_per_1k: float = 0.0
    context: int = 128000


@dataclass(frozen=True)
class Endpoint:
    id: str
    label: str
    base_url: str
    api_key_env: str
    default_model: str
    models: list[ModelSpec] = field(default_factory=list)

    def model(self, name: str) -> ModelSpec | None:
        for m in self.models:
            if m.name == name:
                return m
        return None

    def allows_model(self, name: str) -> bool:
        return self.model(name) is not None

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env)


@dataclass(frozen=True)
class Registry:
    locked: bool
    default_endpoint: str
    endpoints: list[Endpoint]

    def get(self, endpoint_id: str) -> Endpoint | None:
        for e in self.endpoints:
            if e.id == endpoint_id:
                return e
        return None

    @property
    def default(self) -> Endpoint:
        ep = self.get(self.default_endpoint)
        if ep is None:
            if not self.endpoints:
                raise RuntimeError("No approved endpoints are configured.")
            return self.endpoints[0]
        return ep


def _parse(data: dict) -> Registry:
    endpoints: list[Endpoint] = []
    for raw in data.get("endpoints", []):
        models = [
            ModelSpec(
                name=m["name"],
                label=m.get("label", m["name"]),
                prompt_per_1k=float(m.get("prompt_per_1k", 0.0)),
                completion_per_1k=float(m.get("completion_per_1k", 0.0)),
                context=int(m.get("context", 128000)),
            )
            for m in raw.get("models", [])
        ]
        endpoints.append(
            Endpoint(
                id=raw["id"],
                label=raw.get("label", raw["id"]),
                base_url=raw["base_url"],
                api_key_env=raw["api_key_env"],
                default_model=raw.get("default_model", models[0].name if models else ""),
                models=models,
            )
        )
    return Registry(
        locked=bool(data.get("locked", True)),
        default_endpoint=data.get("default_endpoint", endpoints[0].id if endpoints else ""),
        endpoints=endpoints,
    )


_cache: Registry | None = None


def load_registry() -> Registry:
    """Load the bundled endpoint registry (cached)."""
    global _cache
    if _cache is None:
        with resources.files("dcs_cli").joinpath("endpoints.toml").open("rb") as fh:
            _cache = _parse(tomllib.load(fh))
    return _cache
