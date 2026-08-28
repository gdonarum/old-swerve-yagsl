"""Terminal UI helpers built on Rich, styled for DCS Corp."""

from __future__ import annotations

import difflib

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .theme import console as _theme_console


class UI:
    def __init__(self, console: Console | None = None):
        self.console = console or _theme_console()

    # -- generic ------------------------------------------------------------
    def print(self, *args, **kwargs) -> None:
        self.console.print(*args, **kwargs)

    def rule(self, label: str = "") -> None:
        self.console.rule(f"[dcs.muted]{label}[/dcs.muted]", style="dcs.rule")

    def info(self, msg: str) -> None:
        self.console.print(f"[dcs.muted]{msg}[/dcs.muted]")

    def ok(self, msg: str) -> None:
        self.console.print(f"[dcs.ok]✓[/dcs.ok] {msg}")

    def warn(self, msg: str) -> None:
        self.console.print(f"[dcs.warn]![/dcs.warn] {msg}")

    def error(self, msg: str) -> None:
        self.console.print(f"[dcs.err]✗ {msg}[/dcs.err]")

    # -- conversation -------------------------------------------------------
    def assistant_markdown(self, text: str) -> None:
        if text.strip():
            self.console.print(Markdown(text))

    def tool_call(self, name: str, summary: str) -> None:
        self.console.print(f"  [dcs.brand]⚙ {name}[/dcs.brand] [dcs.tool]{summary}[/dcs.tool]")

    def tool_result(self, text: str, ok: bool = True) -> None:
        style = "dcs.tool" if ok else "dcs.err"
        preview = text.strip().splitlines()
        shown = "\n".join(preview[:12])
        if len(preview) > 12:
            shown += f"\n… (+{len(preview) - 12} more lines)"
        if shown:
            self.console.print(Panel(Text(shown), border_style=style, expand=False, padding=(0, 1)))

    def diff(self, path: str, old: str, new: str, action: str) -> None:
        diff_lines = list(
            difflib.unified_diff(
                old.splitlines(),
                new.splitlines(),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )
        body = "\n".join(diff_lines) if diff_lines else "(no textual changes)"
        syntax = Syntax(body, "diff", theme="ansi_dark", word_wrap=True)
        self.console.print(
            Panel(syntax, title=f"[dcs.brand]{action}[/dcs.brand] [dcs.accent]{path}[/dcs.accent]",
                  border_style="dcs.rule", expand=False)
        )

    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
        t = Table(title=title, title_style="dcs.brand", border_style="dcs.rule", header_style="dcs.accent")
        for c in columns:
            t.add_column(c)
        for r in rows:
            t.add_row(*r)
        self.console.print(t)

    def panel(self, renderable, title: str = "", style: str = "dcs.rule") -> None:
        self.console.print(Panel(renderable, title=title, border_style=style, expand=False))
