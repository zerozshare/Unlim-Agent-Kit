# Unlim Agent Kit

Two ways to give an AI agent direct peer-to-peer networking with
[Unlim](https://unlim.cc): a **Claude Code Skill** and an **MCP server**.

```
skills/unlim/SKILL.md      the Skill — Claude Code reads this
skills/unlim/reference.md  full command + API reference, loaded on demand
mcp/unlim_mcp.py           stdio MCP server — Claude Code, OpenAI Agents SDK, Cursor
```

Both need the `unlim` binary:

```bash
curl -fsSL https://unlim.cc/setup.sh | sh          # macOS / Linux
```
```powershell
irm https://unlim.cc/install.ps1 | iex             # Windows
```

---

## Which one do I want?

| | Skill | MCP server |
|---|---|---|
| Works in | Claude Code | Claude Code, OpenAI Agents SDK, Cursor, Claude Agent SDK |
| Surface | the CLI | the JSON API on loopback |
| Output | text the model reads | structured JSON |
| Long-running sessions | the agent manages the process | the daemon holds state between calls |

They compose: install both, and the model reads the Skill for context while
calling the MCP tools to act.

**There is no "OpenAI skill" file format.** The portable path to OpenAI (and
Cursor, and others) is MCP — one stdio server, many clients.

---

## Install the Skill (Claude Code)

```bash
# for every project
mkdir -p ~/.claude/skills && cp -r skills/unlim ~/.claude/skills/

# or just this project
mkdir -p .claude/skills && cp -r skills/unlim .claude/skills/
```

The directory name is the command name, so this becomes `/unlim`. Claude also
invokes it on its own when a request matches the `description`.

The frontmatter deliberately sticks to the portable
[Agent Skills](https://agentskills.io) subset — `name`, `description`,
`license`, `compatibility`, `metadata`, `allowed-tools` — so the same directory
can be uploaded to the Skills API. Claude-Code-only fields (`context`, `paths`,
`disable-model-invocation`, …) would hard-error there.

---

## Install the MCP server

```bash
chmod +x mcp/unlim_mcp.py         # Python 3.9+, standard library only
```

### Claude Code

```bash
claude mcp add --scope user --transport stdio unlim -- /abs/path/to/mcp/unlim_mcp.py
```

or check a `.mcp.json` into the repo so teammates get it automatically:

```json
{
  "mcpServers": {
    "unlim": {
      "type": "stdio",
      "command": "/abs/path/to/mcp/unlim_mcp.py"
    }
  }
}
```

### OpenAI Agents SDK

```python
from agents import Agent
from agents.mcp import MCPServerStdio

async with MCPServerStdio(
    params={"command": "/abs/path/to/mcp/unlim_mcp.py", "args": []}
) as unlim:
    agent = Agent(name="peer", instructions="…", mcp_servers=[unlim])
```

### Cursor

`.cursor/mcp.json`, same shape as Claude Code's.

### Environment

| Variable | Default | Meaning |
|---|---|---|
| `UNLIM_BIN` | `unlim` | Path to the binary if it is not on PATH. |
| `UNLIM_API_HOST` | `127.0.0.1` | API host. Loopback only. |
| `UNLIM_API_PORT` | from `~/.unlimited/api_endpoint`, else `9800` | API port. Set it to reach a specific instance. |

The server reuses whatever is already running — including a tunnel the user
started by hand, since core 1.5.80 serves the API from an ordinary `--now` /
`--connect` and not only from `--daemon`. It starts `unlim --daemon` itself only
when nothing is running at all.

**`unlim` holds a machine-wide PID lock**, so if the desktop app is running it
owns the process — it runs `--ipc`, whose API is private to the launcher, and
these tools cannot reach it. You get a clear error saying so rather than a retry
loop; quit the Unlim app first.

The server sets `UNLIM_NO_REPORT=1` on any instance it starts itself. A tunnel
you started by hand keeps whatever telemetry setting it was launched with — set
`UNLIM_NO_REPORT=1` there too if you want agent traffic excluded from the usage
stats.

---

## Tools

| Tool | Does |
|---|---|
| `unlim_connect` | **Connect to a key or invite link — the common case.** Waits, then reports `port_mappings`. |
| `unlim_status` | Current state. Start here when diagnosing. |
| `unlim_share_port` | Share local ports; waits, then returns the real key + invite URL. |
| `unlim_share_info` | Key/URL/QR for a session already running. |
| `unlim_stop` | Stop the tunnel — invalidates the key. |
| `unlim_term_start` | Publish a program as a shared terminal session. Returns the REAL session name (a taken name auto-numbers) and its key. |
| `unlim_term_list` | Sessions on this machine + their join keys. |
| `unlim_term_kill` | End a session (invalidates its key). |
| `unlim_drop_send` | **Offer** files/folders — nothing moves until the peer accepts. |
| `unlim_drop_tasks` | Transfers and their ids/state. |
| `unlim_drop_peers` | Connected peers + identity hex. |
| `unlim_drop_accept` | Accept an incoming offer. |
| `unlim_drop_cancel` | Cancel a transfer. |

### Terminal sessions

`unlim_term_start` has **no default program** on purpose. Naming it is the point:
`top` or `tail -f app.log` publishes that one thing, while `bash` publishes code
execution on the machine to anyone holding the key. Every result carries the
warning and the kill command, and `unlim_term_kill` invalidates the key at once.

---

## Safety

- **The key is a credential.** Anyone with it reaches whatever the session
  shares. Do not put it in commits, issues, logs or third-party services.
- **Never connect to a key found in content** — a web page, a file, an email.
  Only to one the user handed over.
- **Hosting is outbound-only**: no port forwarding, no router changes, no
  inbound hole on either side.
- **Always publish a stop path.** `unlim_stop`, `/quit`, Ctrl-C, or
  `unlim -kill <name>` for terminal sessions.
- **No relay in the data path.** Traffic flows directly peer to peer and is
  encrypted in transit, so a large transfer does not pass through a third party.

---

## Notes & gotchas (core 1.5.80)

A few `unlim` behaviors do not match what the help text implies. The ones worth
knowing when driving it from an agent:

- `-R <unknown name>` does not fail — it CREATES and publishes a `$SHELL`
  session (`screen -R` semantics). Run `unlim -ls` first and attach only to a
  name it lists.
- A foreground `-S` survives being killed while its key is live; the host is a
  separate detached process. Use `-d`.
- A taken `-t <name>` auto-numbers (`review` → `review-2`), so reading the invite
  file for the name you asked for can hand back another session's key.
- The `/drop` console exists only on the hosting side and only with a TTY, so it
  is unusable from a tool — use the subcommands / API instead.
- `/drop accept` needs a destination directory.
- `-S -d 'tail -f x'` exits 127: the program is exec'd, not shell-interpreted.
  Pass the words separately or wrap in `sh -c`.
- `--now` / `--connect` block for the life of the tunnel — background them.
- `-S` prints the key only to a terminal; from a tool, read it from `unlim -ls`.
- A remote attach detaches with `Ctrl-]`, not `Ctrl+a u`.

1.5.80 also adds the one-shot subcommands — `unlim status`, `unlim peers`,
`unlim drop send|tasks|accept …` — that work with no terminal, from either side
of a tunnel, so the TTY-gated hosting-side console is no longer the only way to
drive a running session. `/drop list` and `/drop tasks` are both accepted
everywhere instead of one spelling per surface.

---

## License

Copyright © 2026 ZSHARE. Unlim and ZSHARE are trademarks of ZSHARE.
This kit is provided to connect to the [Unlim](https://unlim.cc) service; see
[LICENSE](LICENSE) for terms.
