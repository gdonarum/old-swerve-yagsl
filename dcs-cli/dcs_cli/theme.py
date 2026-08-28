"""DCS Corp visual theming for the CLI."""

from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

# DCS Corp brand-ish palette. Deep navy + steel blue + signal orange accent.
DCS_THEME = Theme(
    {
        "dcs.brand": "bold #E8871E",       # signal orange
        "dcs.accent": "#3B82C4",           # steel blue
        "dcs.muted": "#8A94A6",            # slate grey
        "dcs.ok": "bold #4CAF50",
        "dcs.warn": "bold #E8A11E",
        "dcs.err": "bold #E5484D",
        "dcs.user": "bold #3B82C4",
        "dcs.assistant": "#D6DEEB",
        "dcs.tool": "#8A94A6",
        "dcs.rule": "#2A3B54",
    }
)

BANNER = r"""
[dcs.accent]      ____   ____ ____  [/dcs.accent]
[dcs.accent]     |  _ \ / ___/ ___| [/dcs.accent]   [dcs.brand]DCS Coding CLI[/dcs.brand]
[dcs.accent]     | | | | |   \___ \ [/dcs.accent]   [dcs.muted]Internal agentic coding assistant[/dcs.muted]
[dcs.accent]     | |_| | |___ ___) |[/dcs.accent]
[dcs.accent]     |____/ \____|____/ [/dcs.accent]   [dcs.muted]Powered by approved LiteLLM endpoints[/dcs.muted]
"""

_console: Console | None = None


def console() -> Console:
    global _console
    if _console is None:
        _console = Console(theme=DCS_THEME, highlight=False)
    return _console


def banner() -> str:
    return BANNER
