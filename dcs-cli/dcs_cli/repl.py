"""Interactive REPL with slash commands."""

from __future__ import annotations

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.markdown import Markdown

from .agent import Agent
from .approvals import ApprovalManager
from .config import APPROVAL_MODES, Config
from .cost import Usage
from .llm import LLMClient
from .prompts import build_system_prompt
from .session import Session
from .theme import banner
from .tools import ToolContext, build_default_registry
from .ui import UI

SLASH = [
    "/help", "/tools", "/model", "/models", "/endpoint", "/endpoints",
    "/mode", "/cost", "/clear", "/reset", "/save", "/load", "/cwd", "/exit", "/quit",
]

HELP_TEXT = """\
### DCS Coding CLI — commands

- **/help** — show this help
- **/tools** — list available tools
- **/model [name]** — show or switch the active (approved) model
- **/models** — list approved models on the current endpoint
- **/endpoint [id]** — show or switch the active approved endpoint
- **/endpoints** — list all approved DCS endpoints
- **/mode [suggest|auto|full-auto|plan]** — show or set the approval mode
- **/cost** — show token usage and estimated cost this session
- **/clear** — clear the screen
- **/reset** — start a fresh conversation (keep settings)
- **/save [name]** — save the conversation
- **/load <name>** — load a saved conversation
- **/cwd** — show the workspace directory
- **/exit**, **/quit** — leave

Type anything else to talk to the assistant. It can read, edit, search your
code and run commands (with your approval).
"""


class Repl:
    def __init__(self, config: Config):
        self.config = config
        self.ui = UI()
        self.usage = Usage()
        self.approvals = ApprovalManager(self.ui, config.approval_mode)
        self.registry = build_default_registry(config.plugin_dir)
        self.client = LLMClient(config.endpoint, config.model)
        self.ctx = ToolContext(
            workspace=config.workspace, approvals=self.approvals, ui=self.ui
        )
        self.session = Session(build_system_prompt(config.workspace))
        self.agent = Agent(
            self.client, self.registry, self.session, self.ctx, self.ui, self.usage,
            stream=config.stream, max_iterations=config.max_tool_iterations,
        )
        hist_path = Path.home() / ".dcs-cli" / "history"
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        self.prompt = PromptSession(
            history=FileHistory(str(hist_path)),
            completer=WordCompleter(SLASH, sentence=True),
        )

    # -- lifecycle ----------------------------------------------------------
    def run(self) -> int:
        self.ui.print(banner())
        self._status_line()
        self.ui.info("Type /help for commands, /exit to quit.\n")
        while True:
            try:
                line = self.prompt.prompt("dcs › ").strip()
            except (EOFError, KeyboardInterrupt):
                self.ui.print()
                self.ui.info("Goodbye.")
                return 0
            if not line:
                continue
            if line.startswith("/"):
                if self._handle_command(line):
                    return 0
                continue
            try:
                self.agent.run_turn(line)
            except KeyboardInterrupt:
                self.ui.warn("Interrupted.")
            except Exception as e:  # noqa: BLE001
                self.ui.error(f"Error: {e}")
            self.ui.print()

    # -- helpers ------------------------------------------------------------
    def _status_line(self) -> None:
        ep = self.config.endpoint
        self.ui.print(
            f"[dcs.muted]endpoint[/dcs.muted] [dcs.accent]{ep.id}[/dcs.accent]  "
            f"[dcs.muted]model[/dcs.muted] [dcs.accent]{self.client.model}[/dcs.accent]  "
            f"[dcs.muted]mode[/dcs.muted] [dcs.accent]{self.approvals.mode}[/dcs.accent]  "
            f"[dcs.muted]cwd[/dcs.muted] [dcs.accent]{self.config.workspace}[/dcs.accent]"
        )

    # -- slash commands (returns True to exit) ------------------------------
    def _handle_command(self, line: str) -> bool:
        parts = line.split()
        cmd, args = parts[0], parts[1:]
        handler = {
            "/help": self._cmd_help,
            "/tools": self._cmd_tools,
            "/model": self._cmd_model,
            "/models": self._cmd_models,
            "/endpoint": self._cmd_endpoint,
            "/endpoints": self._cmd_endpoints,
            "/mode": self._cmd_mode,
            "/cost": self._cmd_cost,
            "/clear": self._cmd_clear,
            "/reset": self._cmd_reset,
            "/save": self._cmd_save,
            "/load": self._cmd_load,
            "/cwd": self._cmd_cwd,
        }.get(cmd)
        if cmd in ("/exit", "/quit"):
            self.ui.info("Goodbye.")
            return True
        if handler is None:
            self.ui.warn(f"Unknown command: {cmd}. Try /help.")
            return False
        handler(args)
        return False

    def _cmd_help(self, args):
        self.ui.console.print(Markdown(HELP_TEXT))

    def _cmd_tools(self, args):
        rows = [[t.name, "yes" if t.mutating else "no", t.description.split(". ")[0]]
                for t in self.registry.all()]
        self.ui.table("Tools", ["name", "mutating", "description"], rows)

    def _cmd_models(self, args):
        ep = self.config.endpoint
        rows = [[m.name, m.label, str(m.context), f"${m.prompt_per_1k}/{m.completion_per_1k}"]
                for m in ep.models]
        self.ui.table(f"Approved models — {ep.id}", ["name", "label", "context", "$/1k in·out"], rows)

    def _cmd_model(self, args):
        if not args:
            self.ui.info(f"Active model: {self.client.model}")
            return
        target = args[0]
        ep = self.config.endpoint
        if not ep.allows_model(target):
            self.ui.error(f"'{target}' is not approved on endpoint '{ep.id}'. See /models.")
            return
        self.client.set_model(target)
        self.config.model = target
        self.ui.ok(f"Switched model to {target}.")

    def _cmd_endpoints(self, args):
        rows = [[e.id, e.label, e.base_url, e.default_model]
                for e in self.config.registry.endpoints]
        self.ui.table("Approved DCS endpoints", ["id", "label", "base_url", "default model"], rows)

    def _cmd_endpoint(self, args):
        if not args:
            self.ui.info(f"Active endpoint: {self.config.endpoint.id} ({self.config.endpoint.base_url})")
            return
        target = args[0]
        ep = self.config.registry.get(target)
        if ep is None:
            self.ui.error(f"'{target}' is not an approved DCS endpoint. See /endpoints.")
            return
        try:
            new_client = LLMClient(ep, ep.default_model)
        except SystemExit as e:
            self.ui.error(str(e))
            return
        self.client = new_client
        self.agent.client = new_client
        self.config.endpoint_id = ep.id
        self.config.model = ep.default_model
        self.ui.ok(f"Switched to endpoint {ep.id} (model {ep.default_model}).")

    def _cmd_mode(self, args):
        if not args:
            self.ui.info(f"Approval mode: {self.approvals.mode}. Options: {', '.join(APPROVAL_MODES)}")
            return
        target = args[0]
        if target not in APPROVAL_MODES:
            self.ui.error(f"Unknown mode '{target}'. Options: {', '.join(APPROVAL_MODES)}")
            return
        self.approvals.set_mode(target)
        self.ui.ok(f"Approval mode set to {target}.")

    def _cmd_cost(self, args):
        ep = self.config.endpoint
        spec = ep.model(self.client.model)
        cost = self.usage.cost(spec)
        self.ui.table(
            "Session usage",
            ["requests", "prompt tokens", "completion tokens", "total", "est. cost"],
            [[
                str(self.usage.requests),
                str(self.usage.prompt_tokens),
                str(self.usage.completion_tokens),
                str(self.usage.total_tokens),
                f"${cost:.4f}",
            ]],
        )

    def _cmd_clear(self, args):
        self.ui.console.clear()
        self._status_line()

    def _cmd_reset(self, args):
        self.session.reset()
        self.usage = Usage()
        self.agent.usage = self.usage
        self.ui.ok("Started a fresh conversation.")

    def _cmd_save(self, args):
        name = args[0] if args else "last"
        if not name.endswith(".json"):
            name += ".json"
        path = self.config.session_dir / name
        self.session.save(path)
        self.ui.ok(f"Saved conversation to {path}")

    def _cmd_load(self, args):
        if not args:
            self.ui.error("Usage: /load <name>")
            return
        name = args[0]
        if not name.endswith(".json"):
            name += ".json"
        path = self.config.session_dir / name
        if not path.exists():
            self.ui.error(f"No saved session at {path}")
            return
        self.session.load(path)
        self.ui.ok(f"Loaded conversation from {path} ({self.session.user_turns()} user turns).")

    def _cmd_cwd(self, args):
        self.ui.info(f"Workspace: {self.config.workspace}")
