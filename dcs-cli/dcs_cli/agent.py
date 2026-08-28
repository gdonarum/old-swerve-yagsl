"""The agentic loop: model <-> tools until the task is done."""

from __future__ import annotations

import json

from .cost import Usage
from .llm import LLMClient
from .session import Session
from .tools import ToolContext, ToolError, ToolRegistry
from .ui import UI


def _summarize_args(name: str, args: dict) -> str:
    if "path" in args:
        return str(args["path"])
    if "command" in args:
        cmd = str(args["command"])
        return cmd if len(cmd) <= 80 else cmd[:80] + "…"
    if "pattern" in args:
        return str(args["pattern"])
    return ""


class Agent:
    def __init__(
        self,
        client: LLMClient,
        registry: ToolRegistry,
        session: Session,
        ctx: ToolContext,
        ui: UI,
        usage: Usage,
        *,
        stream: bool = True,
        max_iterations: int = 50,
    ):
        self.client = client
        self.registry = registry
        self.session = session
        self.ctx = ctx
        self.ui = ui
        self.usage = usage
        self.stream = stream
        self.max_iterations = max_iterations

    def run_turn(self, user_input: str) -> None:
        self.session.add_user(user_input)
        tools = self.registry.openai_schemas()

        for _ in range(self.max_iterations):
            streamed_any = {"v": False}

            def on_text(chunk: str) -> None:
                if not streamed_any["v"]:
                    self.ui.console.print("[dcs.assistant]", end="")
                    streamed_any["v"] = True
                self.ui.console.print(chunk, end="", style="dcs.assistant")

            resp = self.client.complete(
                self.session.messages,
                tools,
                stream=self.stream,
                on_text=on_text if self.stream else None,
            )
            if streamed_any["v"]:
                self.ui.console.print()  # newline after streamed text
            elif resp.content.strip() and not self.stream:
                self.ui.assistant_markdown(resp.content)

            self.usage.add(resp.prompt_tokens, resp.completion_tokens)
            self.session.add_assistant(resp.content, resp.tool_calls or None)

            if not resp.tool_calls:
                return

            for call in resp.tool_calls:
                self._run_tool(call)

        self.ui.warn(f"Reached the tool-iteration limit ({self.max_iterations}).")

    # -- tool execution -----------------------------------------------------
    def _run_tool(self, call: dict) -> None:
        name = call["function"]["name"]
        raw_args = call["function"]["arguments"] or "{}"
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            self.session.add_tool_result(call["id"], name, "Error: arguments were not valid JSON.")
            self.ui.error(f"{name}: invalid JSON arguments")
            return

        tool = self.registry.get(name)
        if tool is None:
            self.session.add_tool_result(call["id"], name, f"Error: unknown tool '{name}'.")
            self.ui.error(f"Unknown tool requested: {name}")
            return

        self.ui.tool_call(name, _summarize_args(name, args))
        try:
            output = tool.run(args, self.ctx)
            self.session.add_tool_result(call["id"], name, output)
            self.ui.tool_result(output, ok=True)
        except ToolError as e:
            msg = f"Error: {e}"
            self.session.add_tool_result(call["id"], name, msg)
            self.ui.tool_result(msg, ok=False)
        except Exception as e:  # noqa: BLE001 - report unexpected errors to the model
            msg = f"Error: unexpected failure in {name}: {e}"
            self.session.add_tool_result(call["id"], name, msg)
            self.ui.error(msg)
