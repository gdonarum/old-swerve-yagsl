"""Tool registry."""

from __future__ import annotations

from pathlib import Path

from .base import Tool, ToolContext, ToolError
from .filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from .plugins import load_plugins
from .search import GlobTool, GrepTool
from .shell import RunShellTool


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._tools: dict[str, Tool] = {}
        for t in tools:
            self.add(t)

    def add(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("Tool is missing a name.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def openai_schemas(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]


def build_default_registry(plugin_dir: Path | None = None) -> ToolRegistry:
    tools: list[Tool] = [
        ReadFileTool(),
        WriteFileTool(),
        EditFileTool(),
        ListDirTool(),
        GlobTool(),
        GrepTool(),
        RunShellTool(),
    ]
    if plugin_dir:
        tools.extend(load_plugins(plugin_dir))
    return ToolRegistry(tools)


__all__ = [
    "Tool",
    "ToolContext",
    "ToolError",
    "ToolRegistry",
    "build_default_registry",
]
