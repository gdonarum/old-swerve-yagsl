"""Conversation session: message history + persistence."""

from __future__ import annotations

import json
import time
from pathlib import Path


class Session:
    """Holds the running message list and knows how to save/load itself."""

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # -- mutation -----------------------------------------------------------
    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str, tool_calls: list[dict] | None = None) -> None:
        msg: dict = {"role": "assistant", "content": content or ""}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, name: str, content: str) -> None:
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": name,
                "content": content,
            }
        )

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def user_turns(self) -> int:
        return sum(1 for m in self.messages if m["role"] == "user")

    # -- persistence --------------------------------------------------------
    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"saved_at": time.time(), "messages": self.messages}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def load(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        msgs = data.get("messages", [])
        if msgs and msgs[0].get("role") == "system":
            # Keep the current system prompt (environment may have changed).
            self.messages = [{"role": "system", "content": self.system_prompt}] + msgs[1:]
        else:
            self.messages = [{"role": "system", "content": self.system_prompt}] + msgs
