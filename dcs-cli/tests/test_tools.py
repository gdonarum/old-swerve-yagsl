"""Tests for the tool layer, registry, and endpoint governance.

These tests do not require network access or an API key.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dcs_cli.approvals import ApprovalManager
from dcs_cli.config import MODE_FULL_AUTO, MODE_PLAN
from dcs_cli.endpoints import load_registry
from dcs_cli.tools import ToolContext, ToolError, build_default_registry
from dcs_cli.tools.filesystem import EditFileTool, ReadFileTool, WriteFileTool
from dcs_cli.tools.search import GlobTool, GrepTool


class DummyUI:
    def diff(self, *a, **k): ...
    def panel(self, *a, **k): ...
    def info(self, *a, **k): ...
    def warn(self, *a, **k): ...
    def error(self, *a, **k): ...


def make_ctx(tmp_path, mode=MODE_FULL_AUTO) -> ToolContext:
    ui = DummyUI()
    return ToolContext(workspace=tmp_path, approvals=ApprovalManager(ui, mode), ui=ui)


def test_write_read_edit_roundtrip(tmp_path):
    ctx = make_ctx(tmp_path)
    WriteFileTool().run({"path": "a.txt", "content": "hello\nworld\n"}, ctx)
    assert (tmp_path / "a.txt").read_text() == "hello\nworld\n"

    out = ReadFileTool().run({"path": "a.txt"}, ctx)
    assert "1  hello" in out and "2  world" in out

    EditFileTool().run({"path": "a.txt", "old_string": "world", "new_string": "DCS"}, ctx)
    assert "DCS" in (tmp_path / "a.txt").read_text()


def test_edit_requires_unique_match(tmp_path):
    ctx = make_ctx(tmp_path)
    WriteFileTool().run({"path": "b.txt", "content": "x\nx\n"}, ctx)
    with pytest.raises(ToolError):
        EditFileTool().run({"path": "b.txt", "old_string": "x", "new_string": "y"}, ctx)
    # replace_all makes it succeed
    EditFileTool().run(
        {"path": "b.txt", "old_string": "x", "new_string": "y", "replace_all": True}, ctx
    )
    assert (tmp_path / "b.txt").read_text() == "y\ny\n"


def test_path_escape_is_blocked(tmp_path):
    ctx = make_ctx(tmp_path)
    with pytest.raises(ToolError):
        ReadFileTool().run({"path": "../secret.txt"}, ctx)


def test_plan_mode_blocks_writes(tmp_path):
    ctx = make_ctx(tmp_path, mode=MODE_PLAN)
    with pytest.raises(ToolError):
        WriteFileTool().run({"path": "c.txt", "content": "nope"}, ctx)
    assert not (tmp_path / "c.txt").exists()


def test_glob_and_grep(tmp_path):
    ctx = make_ctx(tmp_path)
    WriteFileTool().run({"path": "src/main.py", "content": "def hello():\n    return 1\n"}, ctx)
    WriteFileTool().run({"path": "src/util.py", "content": "def world():\n    return 2\n"}, ctx)

    globbed = GlobTool().run({"pattern": "src/**/*.py"}, ctx)
    assert "src/main.py" in globbed and "src/util.py" in globbed

    grepped = GrepTool().run({"pattern": r"def \w+", "include": "*.py"}, ctx)
    assert "main.py" in grepped and "hello" in grepped


def test_registry_builds_expected_tools():
    reg = build_default_registry()
    for name in ["read_file", "write_file", "edit_file", "list_dir", "glob", "grep", "run_shell"]:
        assert reg.get(name) is not None
    schemas = reg.openai_schemas()
    assert all(s["type"] == "function" for s in schemas)


def test_endpoint_registry_is_locked_and_governs_models():
    reg = load_registry()
    assert reg.locked is True
    ep = reg.default
    assert ep.allows_model(ep.default_model)
    assert not ep.allows_model("gpt-4-turbo-from-openai-dot-com")
