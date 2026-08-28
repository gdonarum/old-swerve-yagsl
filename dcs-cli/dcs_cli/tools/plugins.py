"""Plugin loader for user-supplied tools (MCP-style extensibility).

A plugin is a ``.py`` file in the configured plugin directory. It exposes its
tools in one of two ways:

    # option A: a module-level list of Tool instances
    TOOLS = [MyTool()]

    # option B: a factory function
    def get_tools():
        return [MyTool()]

Each tool must subclass ``dcs_cli.tools.base.Tool`` (or ``FunctionTool``).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .base import Tool


def load_plugins(plugin_dir: Path) -> list[Tool]:
    tools: list[Tool] = []
    if not plugin_dir or not plugin_dir.exists():
        return tools
    for path in sorted(plugin_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        mod_name = f"dcs_cli_plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:  # noqa: BLE001 - a bad plugin must not crash the CLI
            print(f"[dcs-cli] Failed to load plugin {path.name}: {e}", file=sys.stderr)
            continue
        found = getattr(module, "TOOLS", None)
        if found is None and hasattr(module, "get_tools"):
            try:
                found = module.get_tools()
            except Exception as e:  # noqa: BLE001
                print(f"[dcs-cli] Plugin {path.name} get_tools() failed: {e}", file=sys.stderr)
                continue
        for t in found or []:
            if isinstance(t, Tool):
                tools.append(t)
    return tools
