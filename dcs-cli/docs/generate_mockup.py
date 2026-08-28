"""Regenerate the DCS Coding CLI mockup (docs/mockup.svg and docs/mockup.png).

Renders a representative session through the *real* CLI theme so the mockup
always matches the shipped colors. The transcript is illustrative — the tool
is not driven against a live LiteLLM endpoint here.

Usage:
    python docs/generate_mockup.py

Produces docs/mockup.svg always; also docs/mockup.png if a Chromium binary is
found (Playwright's bundled Chromium, or `chromium`/`google-chrome` on PATH).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

# Import the shipped theme so the mockup matches the real CLI exactly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dcs_cli import __version__  # noqa: E402
from dcs_cli.theme import BANNER, DCS_THEME  # noqa: E402

DOCS = Path(__file__).resolve().parent
SVG_PATH = DOCS / "mockup.svg"
PNG_PATH = DOCS / "mockup.png"


def build_svg() -> tuple[int, int]:
    c = Console(record=True, theme=DCS_THEME, highlight=False, width=88)

    c.print(BANNER.format(version=__version__))
    c.print(
        "[dcs.muted]endpoint[/dcs.muted] [dcs.accent]dcs-litellm-prod[/dcs.accent]  "
        "[dcs.muted]model[/dcs.muted] [dcs.accent]dcs-gpt-4o[/dcs.accent]  "
        "[dcs.muted]mode[/dcs.muted] [dcs.accent]suggest[/dcs.accent]  "
        "[dcs.muted]cwd[/dcs.muted] [dcs.accent]~/robot/old-swerve-yagsl[/dcs.accent]"
    )
    c.print("[dcs.muted]Type /help for commands, /exit to quit.[/dcs.muted]\n")

    c.print("[dcs.user]dcs ›[/dcs.user] add a deadband to the drive joystick input in RobotContainer")
    c.print("[dcs.assistant]I'll find where the joystick drive input is wired up and add a "
            "deadband.[/dcs.assistant]")

    c.print("  [dcs.brand]⚙ grep[/dcs.brand] [dcs.tool]getLeftY|getRightX[/dcs.tool]")
    c.print(Panel(Text("src/main/java/frc/robot/RobotContainer.java:54:  () -> -driver.getLeftY(),\n"
                       "src/main/java/frc/robot/RobotContainer.java:55:  () -> -driver.getRightX(),"),
                  border_style="dcs.tool", expand=False, padding=(0, 1)))

    c.print("  [dcs.brand]⚙ edit_file[/dcs.brand] [dcs.tool]src/main/java/frc/robot/RobotContainer.java[/dcs.tool]")
    diff = """\
--- a/src/main/java/frc/robot/RobotContainer.java
+++ b/src/main/java/frc/robot/RobotContainer.java
@@ -52,8 +52,8 @@
   drivebase.setDefaultCommand(
     drivebase.driveCommand(
-      () -> -driver.getLeftY(),
-      () -> -driver.getRightX(),
+      () -> MathUtil.applyDeadband(-driver.getLeftY(), 0.08),
+      () -> MathUtil.applyDeadband(-driver.getRightX(), 0.08),
       () -> -driver.getRightX()));
"""
    c.print(Panel(Syntax(diff, "diff", theme="ansi_dark", word_wrap=True),
                  title="[dcs.brand]Edit[/dcs.brand] [dcs.accent]RobotContainer.java[/dcs.accent]",
                  border_style="dcs.rule", expand=False))
    c.print("  [dcs.muted]Edit RobotContainer.java? [/dcs.muted][dcs.accent]y[/dcs.accent]")
    c.print(Panel(Text("Edited src/main/java/frc/robot/RobotContainer.java (2 replacements)."),
                  border_style="dcs.tool", expand=False, padding=(0, 1)))

    c.print("  [dcs.brand]⚙ run_shell[/dcs.brand] [dcs.tool]./gradlew compileJava[/dcs.tool]")
    c.print(Panel(Text("exit code: 0\nBUILD SUCCESSFUL in 6s"),
                  border_style="dcs.tool", expand=False, padding=(0, 1)))

    c.print("[dcs.assistant]Done. I wrapped both translation axes in "
            "[/dcs.assistant][dcs.accent]MathUtil.applyDeadband(..., 0.08)[/dcs.accent]"
            "[dcs.assistant] so small stick drift near center is ignored, and "
            "verified it compiles cleanly.[/dcs.assistant]\n")

    c.print("[dcs.user]dcs ›[/dcs.user] /cost")
    t = Table(title="Session usage", title_style="dcs.brand",
              border_style="dcs.rule", header_style="dcs.accent")
    for col in ["requests", "prompt tokens", "completion tokens", "total", "est. cost"]:
        t.add_column(col)
    t.add_row("3", "4,182", "611", "4,793", "$0.0301")
    c.print(t)
    c.print("\n")  # trailing pad so Rich allocates height for the full table

    c.save_svg(str(SVG_PATH), title="DCS Coding CLI")

    # Recover the viewBox dimensions Rich chose, for exact PNG sizing.
    head = SVG_PATH.read_text(encoding="utf-8")[:400]
    import re
    m = re.search(r'viewBox="0 0 ([0-9.]+) ([0-9.]+)"', head)
    w, h = (int(float(m.group(1))), int(float(m.group(2))) + 1) if m else (1092, 1441)
    return w, h


def find_chromium() -> str | None:
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        p = shutil.which(name)
        if p:
            return p
    # Playwright's bundled Chromium.
    for cand in Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"):
        return str(cand)
    return None


def build_png(w: int, h: int) -> bool:
    chrome = find_chromium()
    if not chrome:
        print("No Chromium found; skipping PNG. SVG written to", SVG_PATH)
        return False
    html = DOCS / "_mockup.html"
    html.write_text(
        f'<!doctype html><html><head><meta charset="utf-8">'
        f'<style>html,body{{margin:0;padding:0;background:#0d1117}}'
        f'img{{display:block;width:{w}px;height:{h}px}}</style></head>'
        f'<body><img src="file://{SVG_PATH}"></body></html>',
        encoding="utf-8",
    )
    subprocess.run(
        [chrome, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
         "--force-device-scale-factor=2", f"--window-size={w},{h}",
         f"--screenshot={PNG_PATH}", f"file://{html}"],
        check=True, capture_output=True,
    )
    html.unlink(missing_ok=True)
    print("Wrote", PNG_PATH)
    return True


if __name__ == "__main__":
    w, h = build_svg()
    print("Wrote", SVG_PATH, f"({w}x{h})")
    build_png(w, h)
