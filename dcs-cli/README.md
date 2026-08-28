# DCS Coding CLI

An internal, terminal-based **agentic coding assistant** for DCS Corp — a
Claude‑Code‑style CLI, written in Python, that reads, writes, and refactors
code, runs builds and tests, and investigates repositories. It is backed
**exclusively by DCS‑approved LiteLLM endpoints** that are baked into the
tool, so it cannot be pointed at an arbitrary external model.

```
        ██
        ██
    ██████   ██████   ██████
   ██   ██  ██       ██
   ██   ██  ██        █████
   ██   ██  ██            ██
    ██████   ██████   ██████
                          corp

  Coding CLI — internal agentic coding assistant
```

At launch the splash renders the DCS Corp wordmark in the brand palette —
a teal block `dcs` over a grey `corp`.

## Why "locked endpoints"?

The set of reachable model endpoints ships **inside the package**
(`dcs_cli/endpoints.toml`). Users may choose *which* approved endpoint and
*which* approved model to use, but they cannot introduce a new `base_url` or an
unapproved model at runtime. Endpoint governance is a **release‑time** decision.
API keys are never stored in the tool — each endpoint reads its key from a
designated environment variable.

## Install

```bash
cd dcs-cli
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

This installs the `dcs` (and `dcs-cli`) command.

## Configure

1. Point the bundled registry at your real LiteLLM proxy by editing
   `dcs_cli/endpoints.toml` (the `base_url` values) and cutting a release.
2. Export your API key for the endpoint you'll use:

   ```bash
   export DCS_LLM_API_KEY="sk-...your DCS LiteLLM key..."
   ```

3. (Optional) Drop a user config at `~/.config/dcs-cli/config.toml`
   (see `config.example.toml`).

Inspect what's approved:

```bash
dcs --list-endpoints
dcs --list-models -e dcs-litellm-prod
```

## Use

Interactive REPL:

```bash
dcs                      # start in the current directory
dcs -C /path/to/repo     # set the workspace
dcs -m dcs-claude-sonnet # pick an approved model
dcs --mode plan          # read-only planning session
```

One‑shot (non‑interactive):

```bash
dcs -p "Explain what src/main.py does and suggest one improvement."
```

### Slash commands

| Command | Description |
| --- | --- |
| `/help` | Show help |
| `/tools` | List available tools |
| `/model [name]` | Show or switch the active approved model |
| `/models` | List approved models on the current endpoint |
| `/endpoint [id]` / `/endpoints` | Show/switch/list approved endpoints |
| `/mode [suggest\|auto\|full-auto\|plan]` | Approval mode |
| `/cost` | Token usage and estimated cost |
| `/save [name]` / `/load <name>` | Persist / restore a conversation |
| `/reset` · `/clear` · `/cwd` · `/exit` | Session controls |

## Tools the agent can use

`read_file`, `write_file`, `edit_file`, `list_dir`, `glob`, `grep`,
`run_shell`. All paths are confined to the workspace root. Mutating actions
(writes, edits, shell) are gated by the **approval mode**:

- **suggest** (default) — confirm every mutating action, showing a diff first
- **auto** — auto‑approve file writes/edits, still confirm shell commands
- **full-auto** — auto‑approve everything
- **plan** — read‑only; refuse all mutating actions

## Extending with plugins

Add custom tools (e.g. an internal ticket lookup) by dropping `*.py` files in
a plugin directory and setting `plugin_dir` in your config. See
`plugins.example/jira_lookup.py` for the pattern.

## Architecture

```
dcs_cli/
├── endpoints.toml     # LOCKED approved-endpoint registry (bundled)
├── endpoints.py       # registry loader
├── config.py          # runtime config (flags > env > file > registry)
├── llm.py             # OpenAI-compatible client -> LiteLLM (streaming + tools)
├── agent.py           # the agentic model<->tools loop
├── session.py         # message history + save/load
├── approvals.py       # approval gating for mutating actions
├── prompts.py         # system prompt (+ project DCS.md/AGENTS.md)
├── cost.py            # token/cost tracking
├── ui.py / theme.py   # DCS-themed Rich terminal UI
├── repl.py            # interactive REPL + slash commands
├── cli.py             # argparse entry point
└── tools/             # read/write/edit/list/glob/grep/shell + plugin loader
```

## Test

```bash
pip install -e '.[dev]'
pytest
```

The test suite covers the tool layer, workspace sandboxing, approval/plan‑mode
gating, and endpoint governance — no network or API key required.
