"""Example DCS Coding CLI plugin.

Drop this file into your configured plugin directory (see config.example.toml)
to add a custom tool. This one is a stub that shows the pattern; wire it to
your real internal system as needed.
"""

from dcs_cli.tools.base import FunctionTool, ToolContext


def _lookup(args: dict, ctx: ToolContext) -> str:
    ticket = args.get("ticket", "").strip()
    if not ticket:
        return "Error: no ticket id provided."
    # Replace with a real call to your internal tracker.
    return f"(stub) Ticket {ticket}: details would be fetched from the DCS tracker here."


TOOLS = [
    FunctionTool(
        name="dcs_ticket_lookup",
        description="Look up a DCS internal ticket by id and return its summary.",
        parameters={
            "type": "object",
            "properties": {
                "ticket": {"type": "string", "description": "Ticket id, e.g. DCS-1234."},
            },
            "required": ["ticket"],
        },
        runner=_lookup,
        mutating=False,
    )
]
