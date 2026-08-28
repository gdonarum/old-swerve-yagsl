"""Approval gating for mutating tool actions."""

from __future__ import annotations

from prompt_toolkit import prompt as pt_prompt

from .config import MODE_AUTO, MODE_FULL_AUTO, MODE_PLAN, MODE_SUGGEST
from .ui import UI


class PlanModeViolation(Exception):
    """Raised when a mutating action is attempted in read-only plan mode."""


class ApprovalManager:
    """Decides whether a mutating tool action may proceed.

    Modes:
      suggest    - confirm every mutating action (default)
      auto       - auto-approve file writes/edits, confirm shell commands
      full-auto  - auto-approve everything
      plan       - read-only: reject all mutating actions
    """

    def __init__(self, ui: UI, mode: str = MODE_SUGGEST):
        self.ui = ui
        self.mode = mode
        # Remember blanket "always allow" choices for this session.
        self._always_writes = False
        self._always_shell = False

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    # -- writes / edits -----------------------------------------------------
    def confirm_write(self, *, tool: str, path: str, old: str, new: str, action: str) -> bool:
        if self.mode == MODE_PLAN:
            self.ui.warn(f"Plan mode: refusing to {action.lower()} {path}.")
            return False
        self.ui.diff(path, old, new, action)
        if self.mode in (MODE_AUTO, MODE_FULL_AUTO) or self._always_writes:
            self.ui.info(f"[auto] {action} {path}")
            return True
        return self._ask(f"{action} {path}?", scope="writes")

    # -- shell --------------------------------------------------------------
    def confirm_shell(self, command: str) -> bool:
        if self.mode == MODE_PLAN:
            self.ui.warn(f"Plan mode: refusing to run: {command}")
            return False
        self.ui.panel(command, title="[dcs.brand]run_shell[/dcs.brand]", style="dcs.warn")
        if self.mode == MODE_FULL_AUTO or self._always_shell:
            self.ui.info("[auto] running command")
            return True
        return self._ask("Run this command?", scope="shell")

    # -- prompt -------------------------------------------------------------
    def _ask(self, question: str, scope: str) -> bool:
        try:
            answer = pt_prompt(
                f"  {question} [y]es / [n]o / [a]lways: "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if answer in ("y", "yes"):
            return True
        if answer in ("a", "always"):
            if scope == "writes":
                self._always_writes = True
            else:
                self._always_shell = True
            return True
        return False
