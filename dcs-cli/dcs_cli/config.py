"""Runtime configuration.

Configuration precedence (highest wins):
    CLI flags  >  environment variables  >  user config file  >  registry defaults

The user can choose *which* approved endpoint and *which* approved model to
use, plus non-security preferences (approval mode, theme, plugin dir). The
user can NOT introduce a new base_url or an unapproved model — that is
governed exclusively by the locked bundled registry (``endpoints.toml``).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .endpoints import Endpoint, Registry, load_registry

CONFIG_ENV = "DCS_CLI_CONFIG"
DEFAULT_CONFIG_PATHS = [
    Path.home() / ".config" / "dcs-cli" / "config.toml",
    Path.home() / ".dcs-cli.toml",
]

# Approval modes for tools that mutate state (write/edit/shell).
MODE_SUGGEST = "suggest"   # ask before every mutating action
MODE_AUTO = "auto"         # auto-approve edits/writes, still confirm shell
MODE_FULL_AUTO = "full-auto"  # auto-approve everything (use with care)
MODE_PLAN = "plan"         # read-only: refuse all mutating actions
APPROVAL_MODES = [MODE_SUGGEST, MODE_AUTO, MODE_FULL_AUTO, MODE_PLAN]


@dataclass
class Config:
    registry: Registry
    endpoint_id: str
    model: str
    approval_mode: str = MODE_SUGGEST
    workspace: Path = field(default_factory=Path.cwd)
    plugin_dir: Path | None = None
    session_dir: Path = field(default_factory=lambda: Path.home() / ".dcs-cli" / "sessions")
    max_tool_iterations: int = 50
    stream: bool = True

    @property
    def endpoint(self) -> Endpoint:
        ep = self.registry.get(self.endpoint_id)
        if ep is None:
            raise SystemExit(f"Endpoint '{self.endpoint_id}' is not an approved DCS endpoint.")
        return ep

    def validate(self) -> None:
        ep = self.endpoint
        if not ep.allows_model(self.model):
            allowed = ", ".join(m.name for m in ep.models)
            raise SystemExit(
                f"Model '{self.model}' is not approved on endpoint '{ep.id}'.\n"
                f"Approved models: {allowed}"
            )
        if self.approval_mode not in APPROVAL_MODES:
            raise SystemExit(f"Unknown approval mode '{self.approval_mode}'.")


def _find_config_file(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.exists() else None
    env = os.environ.get(CONFIG_ENV)
    if env:
        p = Path(env).expanduser()
        return p if p.exists() else None
    for candidate in DEFAULT_CONFIG_PATHS:
        if candidate.exists():
            return candidate
    return None


def _load_file(path: Path | None) -> dict:
    if not path:
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def load_config(
    *,
    endpoint_id: str | None = None,
    model: str | None = None,
    approval_mode: str | None = None,
    config_path: str | None = None,
    workspace: str | None = None,
) -> Config:
    """Assemble the effective runtime config, honoring the locked registry."""
    registry = load_registry()
    file_cfg = _load_file(_find_config_file(config_path))

    # --- endpoint selection ---
    chosen_endpoint = (
        endpoint_id
        or os.environ.get("DCS_LLM_ENDPOINT")
        or file_cfg.get("endpoint")
        or registry.default_endpoint
    )
    ep = registry.get(chosen_endpoint)
    if ep is None:
        approved = ", ".join(e.id for e in registry.endpoints)
        raise SystemExit(
            f"Endpoint '{chosen_endpoint}' is not an approved DCS endpoint.\n"
            f"Approved endpoints: {approved}"
        )

    # --- model selection (must be approved on the endpoint) ---
    chosen_model = (
        model
        or os.environ.get("DCS_LLM_MODEL")
        or file_cfg.get("model")
        or ep.default_model
    )

    chosen_mode = (
        approval_mode
        or os.environ.get("DCS_CLI_APPROVAL_MODE")
        or file_cfg.get("approval_mode")
        or MODE_SUGGEST
    )

    plugin_dir_raw = os.environ.get("DCS_CLI_PLUGIN_DIR") or file_cfg.get("plugin_dir")
    plugin_dir = Path(plugin_dir_raw).expanduser() if plugin_dir_raw else None

    ws = Path(workspace).expanduser().resolve() if workspace else Path.cwd()

    cfg = Config(
        registry=registry,
        endpoint_id=ep.id,
        model=chosen_model,
        approval_mode=chosen_mode,
        workspace=ws,
        plugin_dir=plugin_dir,
        max_tool_iterations=int(file_cfg.get("max_tool_iterations", 50)),
        stream=bool(file_cfg.get("stream", True)),
    )
    cfg.validate()
    return cfg
