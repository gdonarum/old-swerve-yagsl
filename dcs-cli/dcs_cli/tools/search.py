"""Search tools: glob and grep (pure-Python, no external deps)."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

from .base import Tool, ToolContext, ToolError

_IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist", ".gradle"}
MAX_MATCHES = 200


def _walk(root: Path):
    for p in root.rglob("*"):
        if any(part in _IGNORE_DIRS for part in p.parts):
            continue
        yield p


class GlobTool(Tool):
    name = "glob"
    description = (
        "Find files by glob pattern (e.g. '**/*.py', 'src/**/*.java'). "
        "Returns matching paths relative to the workspace."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern, e.g. '**/*.py'."},
        },
        "required": ["pattern"],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        pattern = args["pattern"]
        root = ctx.workspace
        matches = []
        for p in root.glob(pattern):
            if any(part in _IGNORE_DIRS for part in p.relative_to(root).parts):
                continue
            if p.is_file():
                matches.append(str(p.relative_to(root)))
        matches.sort()
        if not matches:
            return "(no files matched)"
        truncated = matches[:MAX_MATCHES]
        out = "\n".join(truncated)
        if len(matches) > MAX_MATCHES:
            out += f"\n... ({len(matches) - MAX_MATCHES} more)"
        return out


class GrepTool(Tool):
    name = "grep"
    description = (
        "Search file contents for a regular expression and return matching "
        "lines as 'path:line: text'. Optionally restrict to files matching a "
        "glob include pattern."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Python regular expression."},
            "include": {"type": "string", "description": "Optional glob to filter files, e.g. '*.py'."},
            "ignore_case": {"type": "boolean", "description": "Case-insensitive match."},
        },
        "required": ["pattern"],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        try:
            flags = re.IGNORECASE if args.get("ignore_case") else 0
            rx = re.compile(args["pattern"], flags)
        except re.error as e:
            raise ToolError(f"Invalid regex: {e}")
        include = args.get("include")
        root = ctx.workspace
        results: list[str] = []
        for p in _walk(root):
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if include and not fnmatch.fnmatch(p.name, include):
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    snippet = line.strip()
                    if len(snippet) > 240:
                        snippet = snippet[:240] + "…"
                    results.append(f"{rel}:{i}: {snippet}")
                    if len(results) >= MAX_MATCHES:
                        results.append(f"... (stopped at {MAX_MATCHES} matches)")
                        return "\n".join(results)
        return "\n".join(results) if results else "(no matches)"
