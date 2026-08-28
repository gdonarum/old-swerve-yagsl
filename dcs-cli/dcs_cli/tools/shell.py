"""Shell execution tool with approval gating."""

from __future__ import annotations

import subprocess
from typing import Any

from .base import Tool, ToolContext, ToolError

DEFAULT_TIMEOUT = 120
MAX_OUTPUT = 30_000


class RunShellTool(Tool):
    name = "run_shell"
    description = (
        "Run a shell command in the workspace directory and return its stdout, "
        "stderr and exit code. Use for builds, tests, git, and inspection. "
        "Commands are subject to user approval."
    )
    mutating = True
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to run."},
            "timeout": {"type": "integer", "description": f"Timeout in seconds (default {DEFAULT_TIMEOUT})."},
        },
        "required": ["command"],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        command = args["command"]
        timeout = int(args.get("timeout", DEFAULT_TIMEOUT))
        if not ctx.approvals.confirm_shell(command):
            raise ToolError("User declined to run the command.")
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(ctx.workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise ToolError(f"Command timed out after {timeout}s.")
        out = proc.stdout or ""
        err = proc.stderr or ""
        combined = out
        if err:
            combined += ("\n[stderr]\n" + err) if combined else ("[stderr]\n" + err)
        if len(combined) > MAX_OUTPUT:
            combined = combined[:MAX_OUTPUT] + f"\n... (truncated, {len(combined)} bytes total)"
        return f"exit code: {proc.returncode}\n{combined}".rstrip()
