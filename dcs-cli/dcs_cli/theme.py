"""DCS Corp visual theming for the CLI."""

from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

# DCS Corp brand palette, sampled from the corporate logo: teal "dcs" wordmark
# over a grey "corp". Teal is the primary brand color; grey is secondary text.
DCS_THEME = Theme(
    {
        "dcs.brand": "bold #16A5C0",       # DCS logo teal
        "dcs.accent": "#4FB9CE",           # lighter teal (values, highlights)
        "dcs.corp": "#9AA4B0",             # logo "corp" grey
        "dcs.muted": "#8A94A6",            # slate grey
        "dcs.ok": "bold #4CAF50",
        "dcs.warn": "bold #E8A11E",
        "dcs.err": "bold #E5484D",
        "dcs.user": "bold #4FB9CE",
        "dcs.assistant": "#D6DEEB",
        "dcs.tool": "#8A94A6",
        "dcs.rule": "#2A3B54",
    }
)

# Splash wordmark: the DCS Corp logo as ASCII — teal block "dcs" over grey
# "corp", matching the corporate mark.
BANNER = """\

        [dcs.brand]██[/dcs.brand]
        [dcs.brand]██[/dcs.brand]
    [dcs.brand]██████   ██████   ██████[/dcs.brand]
   [dcs.brand]██   ██  ██       ██[/dcs.brand]
   [dcs.brand]██   ██  ██        █████[/dcs.brand]
   [dcs.brand]██   ██  ██            ██[/dcs.brand]
    [dcs.brand]██████   ██████   ██████[/dcs.brand]
                          [dcs.corp]corp[/dcs.corp]

  [dcs.brand]Coding CLI[/dcs.brand] [dcs.muted]v{version} — internal agentic coding assistant[/dcs.muted]
"""

_console: Console | None = None


def console() -> Console:
    global _console
    if _console is None:
        _console = Console(theme=DCS_THEME, highlight=False)
    return _console


def banner() -> str:
    from . import __version__

    return BANNER.format(version=__version__)
