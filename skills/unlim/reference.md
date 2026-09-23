# Unlim — full reference

Everything here was checked against the real binary. If a flag is not listed,
assume it does not exist rather than guessing — `unlim --help` is the authority.

## Commands

| Command | What it does |
|---|---|
| `unlim --now <ports>` | Host: share local ports. Prints the key + QR. |
| `unlim --connect <key>` | Client: connect to a key or invite URL. |
| `unlim <key>` | Same as `--connect`. |
| `unlim -S [-t <name>] [-d] <program>` | Start a shared terminal session. `-t` names it, `-d` detaches. Both go AFTER `-S`. |
| `unlim -ls` | List background sessions. |
| `unlim -R [name\|key]` | Attach to a live session, or join a remote one by key. **If the name is not live — or no name is given and none exist — it CREATES and publishes a new $SHELL session** (`screen -R` semantics). Run `unlim -ls` first. |
| `unlim -kill <name>` | End a session. `--all` ends every one. |
| `unlim --profile create\|load` | Create or load a port profile. |
| `unlim --version` / `-v` | Version. |
| `unlim --help [command]` / `-h` | Help. |

## Subcommands (act on a RUNNING instance)

These do **not** start anything. They find the running instance and talk to its
local API, which routes into the same dispatcher as the console and the TUI —
so the three surfaces cannot disagree.

| Command | What it does |
|---|---|
| `unlim status` | Mode, peer count, whitelist, and the forwarded port mappings. |
| `unlim peers` | Connected peers. (`players` is the same thing.) |
| `unlim share` | Key, invite URL and QR for the running session. |
| `unlim apps` | Installed applications. |
| `unlim drop <verb> …` | File transfer — see below. |
| `unlim kick\|ban\|pardon <id>` | Peer control. |
| `unlim whitelist on\|off\|add\|remove\|list` | Allow-list. |
| `unlim maxplayers <n>` | Peer cap. `0` = unlimited. |
| `unlim name <idkey\|nickname> <name>` | Label a device. |
| `unlim myid` / `unlim myname [name]` | This device's ID / label. |
| `unlim lang en\|ja` | Interface language. |
| `unlim stop` | End the tunnel; the process stays up. |
| `unlim quit` | End the tunnel and exit the process. |
| `unlim commands` | List all of the above. |

`--json` gives structured output. `status`, `peers`, `share`, `apps` and every
`drop` verb return real JSON; the rest return the display lines.

**Exit codes** — branch on these instead of parsing text:

| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | The instance answered and refused (unknown command, bad id, …). |
| 2 | The command line was wrong. |
| 3 | No running instance — **or several**: the message then lists them; pick one with `--instance <pid\|:port>` or `UNLIM_API_PORT`. |
| 4 | An instance is recorded but did not answer. |

### drop

```
unlim drop send <path...> [--peer <hex>]   offer files/folders (relative paths are resolved here)
unlim drop tasks                           transfers, ids and state   (`list` also accepted)
unlim drop peers                           connected peers + identity hex
unlim drop accept <id> <dir>               <dir> is REQUIRED
unlim drop decline|cancel <id> [reason]
unlim drop remove <id>
unlim drop clear
```

`send` only **offers**; the task sits in `pending` until the peer accepts.
A path that does not exist is rejected before the offer goes out.

## Options

| Option | Meaning |
|---|---|
| `--no-tui` | Plain console instead of the full-screen UI. **Use this for anything an agent runs.** |
| `--host <host>` | Local bind address (default `127.0.0.1`). |
| `--port <port>` | Pin the local forward port (default `8989`). Only meaningful with an explicit single port. |
| `--max-peers <n>` | Cap concurrent peers. `0` = unlimited. |
| `--lang <en\|ja>` | UI language. Saved permanently. |
| `--log` | Debug logging. Noisy; diagnosis only. |
| `--public` | Publish the room to the public directory. |
| `--vip-key <k>` | Request a custom key. It is still the credential that grants access — make it unguessable; a short or memorable value is brute-forceable. |
| `--daemon` | Headless: serve the JSON API and nothing else. |
| `--no-api` | Do NOT serve the local API alongside this run. Subcommands then cannot reach it. |
| `--allow-multiple` | Deprecated no-op — since 1.5.82 concurrent instances need no flag. |

`-S` takes its own arguments *after* it: `-t <name>`, `-d`/`--detach`,
`--share`/`--local`/`--no-share`, then `--` and the program. Putting them before
`-S` hands them to the flag parser, which rejects them.

## Install

```bash
curl -fsSL https://unlim.cc/setup.sh | sh          # macOS / Linux
```
```powershell
irm https://unlim.cc/install.ps1 | iex             # Windows
```

Chain the real command after it so the user pastes once:
`curl -fsSL https://unlim.cc/setup.sh | sh && unlim --connect <key> --no-tui`

### Port syntax

```
3000                        one TCP port
25565/tcp                   explicit protocol
19132/udp                   UDP
'25565/tcp,19132/udp'       several, comma-separated
'19132/udp@500KB'           with a bandwidth cap
```

Quote the list — the comma and `@` are shell-significant.

## Console commands

**Only on the HOSTING side, and only from a real terminal.** The console exists
solely in `unlim --now --no-tui` and only when stdin is a TTY. There is no
console on the `--connect` side, and piped input is ignored.

None of that matters any more: every verb below is also a subcommand
(`unlim status`, `unlim drop send …`), which works with no terminal, from either
side, from any other shell. Use those.

```
/status            current state
/players           connected peers
/drop send <path>   offer a file or folder
/drop list          transfers
/drop tasks         same — both spellings work everywhere
/drop peers         connected peers + identity hex
/drop accept <id> <dir>   accept an offer INTO a directory (dir required)
/drop decline <id>  refuse one
/drop cancel <id>   cancel
/drop remove <id>   forget a finished/failed transfer
/drop clear         forget every finished/failed transfer
/whitelist ...     restrict who may connect
/kick, /ban, /pardon
/connect <key>     connect from inside a running session
/quit              stop
```

## Local HTTP API

The daemon can serve a JSON API on loopback. **Two modes exist and only one is
for you.**

| Mode | Port | Auth | For |
|---|---|---|---|
| any ordinary run, and `--daemon` | **`127.0.0.1:9800`**, or a free port if that is taken | `Authorization: Bearer <token>` | anything outside the desktop app |
| `unlim --ipc` | dynamic, announced on stdout | private to the launcher that spawned it | the desktop launcher only |

Use `--daemon`. `--ipc` is a private interface for the desktop app with no
compatibility promise; third-party callers cannot use it.

The bearer token is the contents of `~/.unlimited/api_token` (mode 0600). It
rotates weekly, so read it per run rather than caching it.

An ordinary `unlim --now …` / `unlim --connect …` serves this too — `--daemon`
is only needed for a headless instance with no tunnel of its own. `--no-api`
opts out.

The port actually bound is recorded in `~/.unlimited/api_endpoint` (mode 0600):

```json
{"host":"127.0.0.1","port":9800,"pid":4711,"version":"1.5.80"}
```

Read that rather than assuming 9800 — 9800 may be taken, in which case the
instance binds elsewhere and says so on stderr. `UNLIM_API_PORT` overrides.
Since 1.5.82 several instances can run at once: each one registers
`~/.unlimited/instances/<pid>.json` (`unlim instances` lists the live ones),
while the single `api_endpoint` record is claimed by whoever got port 9800 —
or by a sole instance on a fallback port.

```bash
unlim --now 3000 --no-tui &
TOK=$(cat ~/.unlimited/api_token)
PORT=$(python3 -c "import json;print(json.load(open('$HOME/.unlimited/api_endpoint'))['port'])")
curl -s -H "Authorization: Bearer $TOK" http://127.0.0.1:$PORT/api/status
```

The token is generated on first serve. If it cannot be established at all the
API **refuses to start** rather than serving unauthenticated.

Every response is `{"ok":true,"data":…}` or `{"ok":false,"error":"…"}`.
A request with no token gets `401`; from a non-loopback address, `403`.

**Several instances are fine (1.5.82+).** There is no single-instance lock —
a second `unlim` starts alongside the first and registers itself. When more
than one is live a plain `unlim <verb>` refuses to guess (exit 3, with the
list); select with `--instance <pid|:port>` or `UNLIM_API_PORT`. The desktop
app's core is the exception that looks like nothing: it runs `--ipc`, whose
API is private to the launcher, so it never registers and never claims
`api_endpoint` — to these tools it is simply invisible, and starting a daemon
next to it works.

**Starting is asynchronous.** `/api/now` and `/api/connect` return
`{"ok":true,"data":["..."]}` immediately; `mode` goes `starting` → `server` /
`client` a few seconds later, and only then does `/api/share` return a key
(`409 not connected` before that). Poll `/api/status`.

### Endpoints

| Method | Path | Body / notes |
|---|---|---|
| GET | `/api/status` | Current state. |
| GET | `/api/version` | Version. |
| POST | `/api/now` | `{"port_list":"3000/tcp","public":false}` → start hosting. |
| POST | `/api/connect` | `{"key":"zshareunlim-…"}` → connect. |
| POST | `/api/stop` | Stop the tunnel. |
| GET | `/api/share` | Key, invite URL and QR for the running session. |
| GET | `/api/players` | Connected peers. |
| POST | `/api/kick`, `/api/ban`, `/api/pardon` | Peer control. |
| GET/POST | `/api/whitelist` | Allow-list management. |
| POST | `/api/maxplayers` | Peer cap. |
| GET | `/api/apps` | Installed applications. |
| POST | `/api/apps/unlimdrop/{verb}` | File transfer — verbs below. |
| GET | `/api/apps/events` | Server-sent events stream. |
| GET/POST | `/api/auth/...` | Access-code gate: `status`, `enable`, `disable`, `setup`, `setup/confirm`, `code`, `exempt`, `revoke`, `reset`. |
| POST | `/api/quit` | Stop the tunnel and exit the process. |
| POST | `/api/command` | `{"cmd":"drop","args":["tasks"]}` → the console/TUI dispatcher. Returns display lines. An unknown verb is a 400, not an ok-with-prose. |

### UnlimDrop verbs

Exactly these. The app endpoint's verb is `tasks`; `list` is accepted at the
console and by `unlim drop list`, both of which map it to `tasks` for you.

| Verb | Body | Notes |
|---|---|---|
| `tasks` | `{}` | All transfers with their ids and state. |
| `peers` | `{}` | Connected peers + identity hex. |
| `send` | `{"paths":["/abs/path"],"peer":"<hex>"}` | **`paths` is an ARRAY.** `peer` is optional when exactly one peer is connected. |
| `accept` | `{"id":"…","dest":"/dir"}` | |
| `decline` | `{"id":"…","reason":"…"}` | |
| `cancel` | `{"id":"…","reason":"…"}` | |
| `remove` | `{"id":"…"}` | Forget a finished/failed transfer. |
| `clear` | `{}` | Drop all finished/failed entries. |

`send`, `accept`, `decline`, `cancel`, `clear` and `remove` are **local-only** —
they are refused for a remote caller.

## Behaviour worth knowing

**Connecting waits.** A client whose host is not in the room yet keeps waiting
for up to ten minutes, logging every 30 s, then fails with "could not connect —
check the key". This is deliberate: a host starting a minute late is the single
largest cause of failed connections. Ctrl-C interrupts it immediately.

**"Applications only" is success.** `connected (no forwarded ports —
Applications only)` means the host shared no ports. File transfer and the
terminal still work.

**Transfers resume.** Interrupting a transfer is safe; both sides keep their
durable state and continue from where they stopped. Files already delivered are
not re-sent. Do not clear state to "fix" a stalled transfer.

**Same file name, different content.** A file whose name and size match one
already in the destination is still received — it is not silently discarded.
The receiver only skips a file it has genuinely delivered for that transfer.

**Access codes.** A host can require a 6-digit TOTP code. A client that is
refused reports the reason (`EUNL-401`) rather than hanging.

## Failure modes

| Symptom | Meaning |
|---|---|
| `could not connect — check the key and that the host is running` | The wait window expired with no host. The key may be fine — the host may simply never have started. |
| `access denied by host` | The host's whitelist or ban list refused this peer. Not a network fault. |
| `no ports received from host` | The host advertised no ports (app-only). |
| `binary crashed` / non-zero exit | Report it; do not retry in a loop. |

## Privacy and telemetry

The core reports an anonymous NAT-traversal outcome (NAT type, failure bucket,
version) to the signaling server so the maintainers can see where traversal
fails. It carries no addresses, no keys and no identity.

Set `UNLIM_NO_REPORT=1` to opt a run out entirely — nothing is sent and nothing
is queued. **Automated runs, CI and test harnesses should set it**, so machine
so test and CI traffic is excluded from the usage stats.
