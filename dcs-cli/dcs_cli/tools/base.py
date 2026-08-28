"""Tool framework: base class, context, and result types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..approvals import ApprovalManager
    from ..ui import UI


@dataclass
class ToolContext:
    """Shared state handed to every tool invocation."""

    workspace: Path
    approvals: "ApprovalManager"
    ui: "UI"


class ToolError(Exception):
    """Raised by a tool to signal a recoverable error back to the model."""


class Tool:
    """Base class for a tool the model can call.

    Subclasses set ``name``, ``description`` and ``parameters`` (a JSON Schema
    object) and implement :meth:`run`.
    """

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {"type": "object", "properties": {}}
    # If True, the tool may modify the filesystem/system and is subject to
    # approval gating.
    mutating: bool = False

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:  # pragma: no cover
        raise NotImplementedError

    # -- helpers -------------------------------------------------------------
    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def resolve_path(self, ctx: ToolContext, path: str) -> Path:
        """Resolve ``path`` inside the workspace and forbid escaping it."""
        p = Path(path)
        if not p.is_absolute():
            p = ctx.workspace / p
        p = p.resolve()
        try:
            p.relative_to(ctx.workspace.resolve())
        except ValueError:
            raise ToolError(
                f"Path '{path}' is outside the workspace "
                f"({ctx.workspace}). Access denied."
            )
        return p


# Simple decorator-based registration for lightweight/plugin tools.
FunctionRunner = Callable[[dict[str, Any], ToolContext], str]


class FunctionTool(Tool):
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        runner: FunctionRunner,
        mutating: bool = False,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self._runner = runner
        self.mutating = mutating

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        return self._runner(args, ctx)
