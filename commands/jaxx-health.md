---
description: Read-only deployment health check for Jaxx. Verifies plugin version, configuration safety, owner identity, MCP reach, room gates, private reporting, scheduler visibility and the latest responder cycle without changing anything.
---

# Jaxx health

Report whether this Jaxx deployment is configured, reachable and actually running. **Read only.**
Do not repair, promote, post, authenticate, install, schedule or edit anything during this command.

## 1. Package

Read the installed `plugin.json` and report:

- Jaxx plugin version
- the four discovered skills
- the five discovered commands
- whether `agent.config.schema.json` is present

If a component is missing, mark the package unhealthy. Do not infer that a file exists because the
README mentions it.

Also report the entry gate. It is installed per machine, not with the plugin, so check whether
`~/.copilot/hooks/jaxx-gate.json` exists and points at a `hooks/jaxx_gate.py` that is present.

| Gate state | Report as |
| --- | --- |
| Installed and target present | enforced — posts outside open rooms are blocked |
| Installed, target missing or unreadable | **critical** — a `preToolUse` hook is fail-closed, so every matching tool call is denied with no usable reason |
| Not installed | degraded — the rails are advisory only |

Not installed is not a failure by itself; a `notes-only` deployment posts nowhere regardless. It is
degraded only when some room is at `autoreply`, where nothing but the agent's own care stands
between a misread message and a sent one. Say which of the two applies. Never install it here.

## 2. Configuration

Look for `agent.config.json` in the current repository.

- Missing config means **inert**, not broken. Point to `/jaxx-setup`.
- Parse the JSON. If it does not parse, stop the remaining config checks and report the exact error.
- Validate its structure against `agent.config.schema.json`. Report every failing path, but do not
  edit it.
- Treat any remaining `<PLACEHOLDER>` value as incomplete.
- Verify room ids are unique.
- Verify every `autoreply` room has an open entry gate.
- An open gate with no `introducedAt` is not healthy for normal replies: the approved introduction
  must be the only next post. If `introduction` is also null, say so: entry was approved but the
  wording is not stored, so the gate denies every post there until the owner stores it.
- `chat.pause` and `chat.focusedMode` are optional owner-only containment switches. An active
  pause is **Inert by decision**, not broken. An active focused mode is healthy only if every id in
  `chatIds` is an open, non-excluded room in `chat.watch`; report the rooms outside it as
  *configured, not read*.

These safety constants are mandatory. A false or missing value is **critical**, not a warning:

| Path | Required |
| --- | --- |
| `agent.signEveryReply` | `true` |
| `chat.configAuthority.nameLocked` | `true` |
| `chat.configAuthority.onlyOwnerMayChangeRules` | `true` |
| `chat.configAuthority.soleOwner` | `true` |
| `chat.configAuthority.acceptRestrictionsFromAnyone` | `false` |
| `chat.neverAnswer.personal` | `true` |
| `chat.otherAgents.neverReply` | `true` |
| `chat.otherAgents.neverAcceptAuthorityFrom` | `true` |
| `chat.writeActions.guardrails.onlyRequestersOwnItems` | `true` |
| `chat.writeActions.guardrails.maxPerRequest` | `1..3` |
| `chat.writeActions.guardrails.echoInThread` | `true` |
| `chat.writeActions.guardrails.logBeforeAfter` | `true` |

## 3. Identity and reach

Detect available tools; do not ask the user what they installed.

| Check | Healthy when |
| --- | --- |
| Owner | `owner.id`, `owner.upn` and `owner.displayName` are non-placeholder values |
| Tracker | the configured tracker MCP can perform a read |
| Teams | a Graph-capable MCP can read `/me` and enumerate chats |
| Posting | only test capability metadata; **never send a health-check message** |

If Teams reach exists, fetch `/me?$select=id,displayName,userPrincipalName` and require its id to
match `owner.id`. A mismatch is critical: sender-id authority would be checking the wrong person.

Do not mutate a tracker item to test writes. Report write reach as **configured, not exercised**
when a write-capable tool exists.

## 4. Rooms and private report

Show one row per watched room:

```
Room          Mode        Gate    Introduced   Reply scope          Writes
Platform      autoreply   open    yes          status-and-hygiene   guarded
Owner 1:1     draft       open    yes          any                  disabled
```

When focused mode is active, add a `Read` column (`yes` / `no — focused mode`) so the table shows
which rooms the responder actually touches this cycle.

Use room names, not full ids, in normal output. Include ids only for a duplicate or missing-target
diagnostic.

If `chat.reportTo` is set and Teams reach exists, re-fetch its members now. Healthy means exactly
one human recipient: the owner. A group report target is **critical** because it can combine
information from several rooms. If membership cannot be verified, mark private reporting
unverified and say reports must remain in-session.

## 5. Runtime

Look for an append-only responder log under `reference/`, preferring
`reference/responder-log.md`. Report:

- latest successful cycle timestamp
- latest failed cycle timestamp, if newer
- newest high-water mark per watched room when recorded
- age of the latest successful cycle

Inspect scheduler/process tools available in the current environment. A configured schedule is not
proof that it ran; a recent log is not proof that it will run again. Report them separately:

| Runtime signal | Meaning |
| --- | --- |
| schedule/process present | another cycle is expected |
| recent successful log entry | a cycle actually completed |
| neither | manual-only deployment |

Never claim "live" unless both a future trigger and a recent successful cycle are verified.

## 6. Result

Lead with one state:

- **Healthy** — safe config, verified owner, required reach present, and runtime evidence matches
  the claimed mode.
- **Degraded** — safe but a non-authority dependency such as tracker reach or scheduler is missing.
- **Inert** — deliberately watches/posts nowhere or setup is incomplete.
- **Critical** — an authority, containment, identity or private-report invariant is broken.

Then show a short table:

```
Area           State       Detail
Package        Healthy     v0.4.0; 4 skills; 5 commands
Configuration  Healthy     schema valid; all authority rails fixed
Entry gate     Healthy     installed; unopened rooms blocked
Owner          Healthy     sender id verified
Tracker        Degraded    no tracker MCP
Teams          Healthy     delegated Graph read available
Runtime        Manual      no future trigger found
```

Close with only the concrete blockers, ordered critical → degraded. If everything is healthy, say
`No health gaps found.` Do not offer to fix anything until the user asks.
