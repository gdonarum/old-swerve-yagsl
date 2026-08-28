"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import APPROVAL_MODES, load_config
from .cost import Usage
from .endpoints import load_registry
from .theme import console


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dcs",
        description="DCS Coding CLI — internal agentic coding assistant (LiteLLM-backed).",
    )
    p.add_argument("--version", action="version", version=f"dcs-cli {__version__}")
    p.add_argument("-e", "--endpoint", help="Approved endpoint id to use.")
    p.add_argument("-m", "--model", help="Approved model to use.")
    p.add_argument(
        "--mode", choices=APPROVAL_MODES,
        help="Approval mode for mutating actions.",
    )
    p.add_argument("-C", "--workspace", help="Workspace directory (default: cwd).")
    p.add_argument("--config", help="Path to a config TOML file.")
    p.add_argument(
        "-p", "--prompt",
        help="Run a single prompt non-interactively, print the result, and exit.",
    )
    p.add_argument(
        "--list-endpoints", action="store_true",
        help="List approved DCS endpoints and exit.",
    )
    p.add_argument(
        "--list-models", action="store_true",
        help="List approved models for the selected endpoint and exit.",
    )
    return p


def _list_endpoints() -> int:
    reg = load_registry()
    c = console()
    c.print("[dcs.brand]Approved DCS endpoints[/dcs.brand]")
    for e in reg.endpoints:
        default = " [dcs.muted](default)[/dcs.muted]" if e.id == reg.default_endpoint else ""
        c.print(f"  [dcs.accent]{e.id}[/dcs.accent]{default} — {e.label}")
        c.print(f"      [dcs.muted]{e.base_url}  (key env: {e.api_key_env})[/dcs.muted]")
    return 0


def _list_models(endpoint_id: str | None) -> int:
    reg = load_registry()
    ep = reg.get(endpoint_id) if endpoint_id else reg.default
    if ep is None:
        console().print(f"[dcs.err]Unknown endpoint '{endpoint_id}'.[/dcs.err]")
        return 2
    c = console()
    c.print(f"[dcs.brand]Approved models on '{ep.id}'[/dcs.brand]")
    for m in ep.models:
        d = " [dcs.muted](default)[/dcs.muted]" if m.name == ep.default_model else ""
        c.print(f"  [dcs.accent]{m.name}[/dcs.accent]{d} — {m.label}  [dcs.muted]ctx {m.context}[/dcs.muted]")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.list_endpoints:
        return _list_endpoints()
    if args.list_models:
        return _list_models(args.endpoint)

    try:
        config = load_config(
            endpoint_id=args.endpoint,
            model=args.model,
            approval_mode=args.mode,
            config_path=args.config,
            workspace=args.workspace,
        )
    except SystemExit as e:
        console().print(f"[dcs.err]{e}[/dcs.err]")
        return 2

    # Non-interactive one-shot mode.
    if args.prompt:
        return _run_once(config, args.prompt)

    # Interactive REPL.
    from .repl import Repl

    try:
        return Repl(config).run()
    except SystemExit as e:
        console().print(f"[dcs.err]{e}[/dcs.err]")
        return 2


def _run_once(config, prompt: str) -> int:
    from .agent import Agent
    from .approvals import ApprovalManager
    from .llm import LLMClient
    from .prompts import build_system_prompt
    from .session import Session
    from .tools import ToolContext, build_default_registry
    from .ui import UI

    ui = UI()
    usage = Usage()
    approvals = ApprovalManager(ui, config.approval_mode)
    registry = build_default_registry(config.plugin_dir)
    try:
        client = LLMClient(config.endpoint, config.model)
    except SystemExit as e:
        ui.error(str(e))
        return 2
    ctx = ToolContext(workspace=config.workspace, approvals=approvals, ui=ui)
    session = Session(build_system_prompt(config.workspace))
    agent = Agent(
        client, registry, session, ctx, ui, usage,
        stream=config.stream, max_iterations=config.max_tool_iterations,
    )
    try:
        agent.run_turn(prompt)
    except KeyboardInterrupt:
        ui.warn("Interrupted.")
        return 130
    except Exception as e:  # noqa: BLE001
        ui.error(f"Error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
