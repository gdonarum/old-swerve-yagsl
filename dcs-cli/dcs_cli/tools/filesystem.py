"""Filesystem tools: read, write, edit, list."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import Tool, ToolContext, ToolError

MAX_READ_BYTES = 400_000


class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "Read a UTF-8 text file from the workspace and return its contents "
        "with 1-based line numbers. Use before editing a file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to the workspace root."},
            "start_line": {"type": "integer", "description": "1-based first line to return (optional)."},
            "end_line": {"type": "integer", "description": "1-based last line to return (optional)."},
        },
        "required": ["path"],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        p = self.resolve_path(ctx, args["path"])
        if not p.exists():
            raise ToolError(f"File not found: {args['path']}")
        if p.is_dir():
            raise ToolError(f"'{args['path']}' is a directory; use list_dir.")
        if p.stat().st_size > MAX_READ_BYTES:
            raise ToolError(f"File is too large (> {MAX_READ_BYTES} bytes) to read in full.")
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ToolError("File is not valid UTF-8 text.")
        lines = text.splitlines()
        start = max(1, int(args.get("start_line", 1)))
        end = int(args.get("end_line", len(lines)))
        end = min(end, len(lines))
        if not lines:
            return "(empty file)"
        width = len(str(end))
        out = [f"{i:>{width}}  {lines[i - 1]}" for i in range(start, end + 1)]
        return "\n".join(out)


class WriteFileTool(Tool):
    name = "write_file"
    description = (
        "Create a new file or completely overwrite an existing file with the "
        "given content. Parent directories are created automatically."
    )
    mutating = True
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to the workspace root."},
            "content": {"type": "string", "description": "Full file content to write."},
        },
        "required": ["path", "content"],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        p = self.resolve_path(ctx, args["path"])
        content = args["content"]
        existed = p.exists()
        old = p.read_text(encoding="utf-8") if existed and p.is_file() else ""
        action = "Overwrite" if existed else "Create"
        if not ctx.approvals.confirm_write(
            tool="write_file",
            path=str(p.relative_to(ctx.workspace)) if p.is_relative_to(ctx.workspace) else str(p),
            old=old,
            new=content,
            action=action,
        ):
            raise ToolError("User declined the write.")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        nlines = content.count("\n") + (0 if content.endswith("\n") or not content else 1)
        return f"{action}d {args['path']} ({nlines} lines)."


class EditFileTool(Tool):
    name = "edit_file"
    description = (
        "Replace an exact substring in a file with new text. The old_string "
        "must appear EXACTLY once in the file (include surrounding context to "
        "make it unique). Prefer this over write_file for small changes."
    )
    mutating = True
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to the workspace root."},
            "old_string": {"type": "string", "description": "Exact text to find (must be unique)."},
            "new_string": {"type": "string", "description": "Replacement text."},
            "replace_all": {
                "type": "boolean",
                "description": "Replace every occurrence instead of requiring uniqueness.",
            },
        },
        "required": ["path", "old_string", "new_string"],
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        p = self.resolve_path(ctx, args["path"])
        if not p.exists() or not p.is_file():
            raise ToolError(f"File not found: {args['path']}")
        old = p.read_text(encoding="utf-8")
        find = args["old_string"]
        repl = args["new_string"]
        replace_all = bool(args.get("replace_all", False))
        count = old.count(find)
        if count == 0:
            raise ToolError("old_string not found in file. Read the file and copy the text exactly.")
        if count > 1 and not replace_all:
            raise ToolError(
                f"old_string appears {count} times; it must be unique. "
                "Add surrounding context or set replace_all=true."
            )
        new = old.replace(find, repl) if replace_all else old.replace(find, repl, 1)
        rel = str(p.relative_to(ctx.workspace)) if p.is_relative_to(ctx.workspace) else str(p)
        if not ctx.approvals.confirm_write(
            tool="edit_file", path=rel, old=old, new=new, action="Edit"
        ):
            raise ToolError("User declined the edit.")
        p.write_text(new, encoding="utf-8")
        n = count if replace_all else 1
        return f"Edited {args['path']} ({n} replacement{'s' if n != 1 else ''})."


class ListDirTool(Tool):
    name = "list_dir"
    description = "List the entries of a directory in the workspace (non-recursive)."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path relative to workspace (default: root)."},
        },
    }

    def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        p = self.resolve_path(ctx, args.get("path", "."))
        if not p.exists():
            raise ToolError(f"Directory not found: {args.get('path', '.')}")
        if not p.is_dir():
            raise ToolError(f"'{args.get('path')}' is not a directory.")
        entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
        if not entries:
            return "(empty directory)"
        lines = []
        for e in entries:
            if e.name.startswith(".git"):
                continue
            marker = "/" if e.is_dir() else ""
            size = "" if e.is_dir() else f"  ({e.stat().st_size} bytes)"
            lines.append(f"{e.name}{marker}{size}")
        return "\n".join(lines)
