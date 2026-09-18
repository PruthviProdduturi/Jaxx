---
description: First-run setup for Jaxx. Detects what reach you have, discovers your identity, writes agent.config.json, bootstraps the memory files, and tells you plainly what is still missing. Safe to re-run.
---

# Jaxx setup

Bootstrap a Jaxx deployment in the current repo. **Idempotent** — re-running it re-detects and
repairs rather than overwriting answers the user already gave.

The goal is that someone who has just installed the plugin ends this command with a working,
**inert** Jaxx and an honest list of what they still need.

## Step 1 — detect reach, before asking anything

Do not ask the user what tools they have. Find out.

| Check | How | If missing |
| --- | --- | --- |
| Azure DevOps | is an ADO MCP tool available (work item read/write)? | note it; offer step 5 |
| Teams / Graph | is a tool available that can `GET /me` and `/chats`? | note it; `jaxx-responder` will be spec-only |
| Repo | `git rev-parse --show-toplevel` | offer to `git init`, or continue without |

Report the result as a short table **before** asking any questions, so the user knows what they're
configuring against.

## Step 2 — discover identity, don't interrogate

If Teams/Graph reach exists, fetch the owner rather than asking for a GUID nobody knows by heart:

```
GET /me?$select=id,displayName,userPrincipalName,givenName
```

Use that for `owner.id`, `owner.displayName`, `owner.upn`, `owner.firstName`. Confirm it back in one
line: *"Setting you as sole owner: Ada Lovelace (ada@example.com) — correct?"*

If there is no Graph reach, ask for display name and UPN only, and leave `owner.id` as
`<OWNER_DIRECTORY_OBJECT_ID>` with a clear note that **sender-id authority cannot be enforced until
it is filled in**. That is a real safety gap, not a cosmetic one — say so.

## Step 3 — keep the identity fixed, then ask what cannot be detected

The agent name is **Jaxx**. Do not ask for a name and do not offer aliases or per-deployment
renaming. `agent.name` remains `Jaxx` and `configAuthority.nameLocked` remains `true`.

One form, three questions, sensible defaults:

| Field | Default | Note |
| --- | --- | --- |
| Tagline | `Your AI Assistant` | Per-chat presentation may vary; the name Jaxx never does |
| ADO org / project | detected from `git remote` if it's an ADO remote | skip entirely if no ADO reach |
| Tracker area path | blank | optional |

## Step 3b — discover chats, don't demand ids

Nobody knows their own chat ids. **List them.** If Graph reach exists:

```
GET /me/chats?$expand=members&$select=id,topic,chatType&$top=50
```

Show them as a numbered table — name, type, member count, last activity — and ask two separate
questions, because they are two separate permissions:

1. **"Which of these may I read?"** — offer *all of them* as a legitimate default. Reading is how
   the summary gets useful, and it is the owner's own credential seeing what they can already see.
   Sets `chat.readScope` to `"all"` or `"watched"`.
2. **"Which may I ever post in?"** — default **none**. Only the chosen ones go into `chat.watch`,
   each at `mode: "notes-only"` and `entryGate: "closed"`.

Make the distinction explicit in the asking, because it is the whole design:

> *"I can read broadly and report back to you privately. Speaking is separate — I post nowhere
> until you name the room and approve an introduction for it."*

## Step 3c — where private reports go

Ask where summaries should land. Offer, in order:

1. **This session** (default) — nothing leaves the machine.
2. **A 1:1 chat** with the agent's identity — pick from the list above, **1:1 only**.

Verify a candidate really has two members before writing it to `chat.reportTo`. A cross-chat summary
is more sensitive than any single message inside it; landing one in a group chat would be a worse
leak than anything the responder could say. If it can't be verified, fall back to the session and
say why.

Do **not** ask about watched chats beyond the above. A new deployment posts nowhere by design — and
the user does not need to come back here to add rooms. Say so: **they can summon the agent into
any group chat or 1:1 they're in, just by naming it there** (*"Jaxx, take notes here"*). That gets
picked up on the next `/jaxx-check`, added to `chat.watch` at `notes-only`, and the agent still
posts nothing in that room until they promote it.


## Step 4 — write the config

Copy `agent.config.template.json` from the plugin root to `agent.config.json` in the repo, then
fill in the answers. Preserve every `$comment_*` key verbatim — they are the rationale, and they are
what stops a later edit from quietly undoing a rail.

**Hard defaults for a new deployment. Never deviate, never "helpfully" pre-fill:**

```
chat.mode           = "notes-only"
chat.watch          = []            // posts nowhere
chat.readScope      = per step 3b   // "all" is fine; reading != speaking
chat.reportTo       = per step 3c   // 1:1 chat id, or null for session-only
chat.allowFrom      = []            // answers nobody
chat.writeActions.enabled = false
configAuthority     = all rails ON
```

A fresh Jaxx **posts nowhere**. It may read as widely as the user allowed and summarise that back to
them privately, but it does not speak in any room until they add it to `watch` and walk it through
`notes-only` → `draft` → `autoreply`. Explain that this split is deliberate.

Add `agent.config.json` to `.gitignore` if the repo has a remote — it holds directory ids.

Validate the completed file against `agent.config.schema.json`. If validation fails, report the
exact paths and leave Jaxx inert; do not weaken the schema or remove a safety field to make it pass.

## Step 5 — offer ADO reach (only if missing and wanted)

If no ADO MCP server is configured, offer to add one to the user's own MCP config using the org they
just gave:

```json
{ "mcpServers": { "azure-devops": {
    "type": "local", "command": "npx",
    "args": ["-y", "@azure-devops/mcp", "<THEIR_ORG>"] } } }
```

Ask before editing their config file, show the diff, and tell them it takes effect on restart.
See [`mcp.example.json`](../mcp.example.json).

## Step 6 — bootstrap memory

Create any of these that don't exist, from [`../assets/`](../assets/):

```
ACTIVE.md  BACKLOG.md  ARCHIVE.md  streams/.gitkeep  reference/sessions.md
```

Never overwrite an existing one. If `ACTIVE.md` already has content, leave it and say so.

## Step 6b — offer the entry gate

Ask whether to install it. Don't install without asking — nothing in Jaxx switches itself on.

```
python scripts/install_gate.py
```

Say what it is in one line: a `preToolUse` hook that **denies** any posting tool call into a room
the config doesn't say is open — unknown room, gate not `open`, mode below `autoreply`, or an
introduction still owed. It is the difference between the rails being instructions and being
enforced, and it matters most later, when a long session has compacted and the reasoning behind
them is gone.

Two things to tell them plainly, and don't skip the second:

- It installs to `~/.copilot/hooks/`, not with the plugin, because plugin-contributed hooks do not
  fire on the current CLI. `--remove` uninstalls it. It needs Python 3 on `PATH`.
- It cannot enforce authority-is-the-sender, containment, or never-answering-another-agent — those
  turn on what a message means. Those remain the reader's job.

If they decline, note it in the step 7 report as `⚠️` rather than dropping it silently.

## Step 7 — report, honestly

Close with a status table and **name the gaps without softening them**:

```
✅ Config written        agent.config.json (inert: watching nothing)
✅ Memory bootstrapped   ACTIVE / BACKLOG / ARCHIVE
✅ Azure DevOps          connected, org <ORG>
✅ Entry gate            installed — posts into unopened rooms are blocked
❌ Teams                 no Graph-capable MCP server
                         → jaxx-responder is a specification until you supply one
⚠️  Owner id             not set — sender-id authority is NOT enforceable yet
```

Then give three next steps, no more:

1. `/jaxx-health` — verify identity, reach, gates and runtime
2. `/jaxx-standup` — read your work back (needs ADO)
3. Add a chat to `chat.watch` at `notes-only`, then `/jaxx-check`

**Never finish by claiming Jaxx is watching anything.** It is not, and a user who believes otherwise
is the worst possible outcome of this command.
