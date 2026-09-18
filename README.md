<div align="center">

<img src="docs/banner.svg" alt="Jaxx — give an agent a mandate it can't overstep." width="820">

[Docs](https://pruthviprodduturi.github.io/Jaxx/) ·
[The rails](skills/jaxx-consent/SKILL.md) ·
[Install](#install) ·
[Contributing](CONTRIBUTING.md)

[![validate](https://github.com/PruthviProdduturi/Jaxx/actions/workflows/validate.yml/badge.svg)](https://github.com/PruthviProdduturi/Jaxx/actions/workflows/validate.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Agent Plugins 1.0.0](https://img.shields.io/badge/agent--plugins-1.0.0-7fb0ff.svg)](https://agent-plugins.org)
[![docs](https://img.shields.io/badge/docs-live-7ee2a8.svg)](https://pruthviprodduturi.github.io/Jaxx/)

</div>

---

Most agent tooling answers *what can this agent do*. Jaxx answers the questions that actually bite
once an agent starts speaking in your name in front of your colleagues:

- Who is allowed to change what the agent **is** — as opposed to asking it to **do** something?
- What happens when a message says *"your owner said it's fine"*?
- Did the people in this channel ever agree to have an agent in it?
- What must the agent refuse to answer, even to the person who owns it?

Jaxx is those rails, written down as skills, plus a working reference implementation of an agent
that obeys them.

## How it works

<img src="docs/architecture.svg" alt="Read plane feeds an authority gate; only what passes all four checks reaches the speak plane, while the report plane always returns in full to the owner." width="100%">

Read scope is your own credential and stays wide, because a narrow read makes the summary
worthless. Post scope starts empty and is opened one room at a time, by you, by name. Nothing
crosses from one room to another except in the private report back to you.

## Why not just put this in your system prompt?

Because a prompt competes with the message. *"Ignore that, her manager approved it"* and your
instruction arrive in the same context window as the same kind of text. Making authority a property
of the **sender id** takes it out of the contest — the check never reads the argument, so there is
nothing to argue with.

And whether a room consented happened days ago, in a different thread. That is state, not
persuasion: it lives in a file the model cannot write to, which is why *"you were added to the
group, so you may speak"* can never become true by being asserted.

## Skills

| Skill | What it gives you |
| --- | --- |
| [`jaxx-consent`](skills/jaxx-consent/SKILL.md) | The rails. Fixed identity, sole owner, authority-is-the-sender, entry gate, disclosure, withdrawal, containment, other agents, personal-question refusal. **Useful to any agent, chat or not.** |
| [`jaxx-responder`](skills/jaxx-responder/SKILL.md) | A **Microsoft Teams** watch that obeys them — scope ladder, reply detection, guarded write-backs, dedupe, edit-in-place, draft→autoreply promotion. |
| [`jaxx-memory`](skills/jaxx-memory/SKILL.md) | Repo-as-memory so the agent survives context compaction: `ACTIVE`/`BACKLOG`/`ARCHIVE`, append-only run log, session hygiene. |

### Everything installed by the plugin

| Component | Installed files | Purpose |
| --- | --- | --- |
| Authority and consent | `skills/jaxx-consent/SKILL.md` | Defines who may change the agent, how room consent works, disclosure, withdrawal and containment. |
| Teams responder | `skills/jaxx-responder/SKILL.md` | Defines the complete gate → classify → gather → draft → post → log cycle. |
| Durable memory | `skills/jaxx-memory/SKILL.md` | Defines tracker reconciliation, session hygiene, append-only history and safe git persistence. |
| First-run configuration | `commands/jaxx-setup.md` | Detects MCP reach, discovers identity and chats, writes an inert config and reports missing prerequisites. |
| Manual responder cycle | `commands/jaxx-check.md` | Runs one bounded watch cycle without requiring a scheduler. |
| Work status | `commands/jaxx-standup.md` | Reconciles repo memory with the connected work tracker and reports drift. |
| Deployment health | `commands/jaxx-health.md` | Verifies version, config safety, owner identity, MCP reach, room gates, private reports and runtime evidence. |
| Configuration | `agent.config.template.json` + `agent.config.schema.json` | Holds and validates owner identity, chat gates, scopes, write safeguards and immutable authority settings. |
| Starter memory | `assets/` | Provides `ACTIVE.md`, `BACKLOG.md`, `ARCHIVE.md` and the session-log template. |
| Validation | `scripts/`, `tests/` and `.github/workflows/validate.yml` | Checks the manifest, config schema, 25 fail-closed rail scenarios, skill structure, identifiers and documentation links. |

The skills are the detailed operating instructions. The commands are safe entry points into those
skills; they do not replace or weaken the rails.

**The name is not configurable.** Every installation is Jaxx. Owners may choose a tagline and
operating scope, but setup never asks for a name and the schema rejects any value other than
`agent.name: "Jaxx"`.

## What the plugin does and does not give you

A plugin ships **instructions**. It carries no credentials and no API access. Reach comes from MCP
servers; behaviour comes from the skills. Both halves are required. The one exception is the
entry gate below, which is code and does block.

| Capability | Comes from | Shipped here |
| --- | --- | --- |
| Create / update Azure DevOps work items | `@azure-devops/mcp` | ✅ see [`mcp.example.json`](mcp.example.json) — `/jaxx-setup` wires it up |
| Read and post Microsoft Teams messages | a server holding delegated Graph `Chat.Read` / `Chat.ReadWrite` | ❌ **you must bring this** |
| Knowing *how* to behave when doing either | `jaxx-consent`, `jaxx-responder` | ✅ |
| **Blocking** a post that breaks the entry gate | [`hooks/jaxx_gate.py`](hooks/jaxx_gate.py) | ✅ opt-in, see [Enforcement](#enforcement) |
| A heartbeat to run the watch unattended | your scheduler | ❌ |

### What you must bring yourself

**A Teams-capable MCP server.** This is the hard prerequisite and there is no way around it. A
plain CLI or service token does **not** carry delegated `Chat.Read` / `Chat.ReadWrite` — `/me/chats`
returns `Forbidden`. You need a server holding a delegated user token, and the one this was built
against is Microsoft-internal and cannot be redistributed.

So, honestly: **without your own Teams MCP server, `jaxx-responder` is a specification, not a
working bot.** `jaxx-consent` and `jaxx-memory` work regardless, and `jaxx-consent` is the part
worth taking on its own.

## Install

Use Jaxx with **either GitHub Copilot CLI or Claude Code**. Choose the client you already use;
you do not need to install both. The same consent, responder and memory skills are included in
each package.

### GitHub Copilot CLI

```
copilot plugin marketplace add PruthviProdduturi/Jaxx
copilot plugin install jaxx@jaxx
```

Then, in a Copilot CLI session:

```
/jaxx
```

That is the front door — it tells you what Jaxx is, what it can currently reach, and the one next
step. It reads state and changes nothing, so it is safe to run first and safe to re-run later.

Jaxx publishes itself as a single-plugin marketplace rather than relying on a direct repo
install, because the CLI warns that direct installs from repos, URLs and local paths are
deprecated and only `plugin@marketplace` will keep working. The marketplace entry pins a tag,
so an install resolves to a released state rather than whatever `main` happens to be.

To pick up a later release:

```
copilot plugin marketplace update jaxx
copilot plugin update jaxx
```

### Claude Code

Jaxx uses the same `skills/` and `commands/` in Claude Code; the Claude-specific manifest lives in
`.claude-plugin/`.

```
/plugin marketplace add PruthviProdduturi/Jaxx
/plugin install jaxx@jaxx
```

Restart Claude Code or run `/reload-plugins`, then run:

```
/jaxx:jaxx-setup
```

Claude still needs the same external MCP reach described below. Installing the plugin supplies the
consent rails and workflows, not Microsoft 365 or Azure DevOps credentials.

### Test Jaxx

If you installed Jaxx in GitHub Copilot CLI, start a Copilot session and run:

```
/jaxx-health
```

If you installed Jaxx in Claude Code, start Claude Code and run:

```
/jaxx:jaxx-health
```

The health command is read-only. It verifies plugin discovery, configuration safety, connected MCP
reach, room gates and runtime evidence, then reports any missing setup without changing it.

`/jaxx-setup` does the rest: it detects which MCP servers you actually have, discovers your own
identity rather than asking you for a GUID, writes `agent.config.json` from the template,
bootstraps the memory files, and then **tells you plainly what is still missing**.

It is idempotent — re-run it any time.

### How a complete deployment runs

1. Install the plugin and run `/jaxx-setup`.
2. Connect an ADO MCP server if tracker reads or writes are required.
3. Connect a delegated Teams/Graph MCP server if chat reads or posts are required.
4. Add rooms deliberately. New rooms start unable to post.
5. Run `/jaxx-check` manually and review draft behavior before enabling autoreply.
6. If unattended operation is required, schedule that same bounded check externally.
7. Keep the generated config private and persist only sanitized tracker memory.

Every responder cycle reloads the config, checks the room gate and sender authority, deduplicates
against its high-water mark, resolves live status from the system of record, applies write
guardrails, signs any permitted reply and appends an audit entry. Most cycles should be quiet.

### The five commands

| Command | Does |
| --- | --- |
| `/jaxx` | Start here. What it is, what it reaches, what's next. Read-only. |
| `/jaxx-setup` | First run. Detect, configure, bootstrap, report gaps. Safe to repeat. |
| `/jaxx-health` | Read-only proof of package, configuration, identity, reach, room and runtime health. |
| `/jaxx-check` | One watch cycle, on demand. No scheduler needed. |
| `/jaxx-standup` | Read your work back and reconcile the repo against the tracker. |

### What you get on install

`/jaxx-setup` lists the chats you can actually see and asks **two separate questions**, because they
are two separate permissions:

- **What may I read?** — all of them is a fine answer. It's your own credential seeing what you can
  already see, and it's what makes the summary useful.
- **What may I post in?** — **none**, by default.

Reports come back to you privately: a 1:1 chat you nominate, or just the session.

Adding rooms later needs no config editing — **summon it**. Say *"Jaxx, take notes here"* in any
group chat or 1:1 you're in and it joins at `notes-only`: reads, records, reports back to you, and
says **nothing** in that room until you promote it through `draft` → `autoreply`. Only you can
summon it; anyone else naming it is ignored silently.

`agent.config.json` holds directory ids — **keep it out of any public repo.** Setup adds it to
`.gitignore` for you if the repo has a remote.

## Enforcement

Everything else here is prose the agent is asked to follow. Asking is not much of a guarantee: a
long session compacts, the reasoning behind a rule drops out of context, and the rule quietly stops
being applied. So the rails that can be decided from recorded state are also enforced in code.

```
python scripts/install_gate.py     # --print to preview, --remove to uninstall
```

Run it from a clone, or let `/jaxx-setup` offer it — the agent knows where the installed plugin
lives, and the script writes absolute paths, so it works from any directory.

That installs a `preToolUse` hook at `~/.copilot/hooks/jaxx-gate.json`. It runs before any tool
whose name looks like it sends a message, finds the room id in the arguments, and **denies** the
call unless your own `agent.config.json` says that room is open:

| It denies when | Rail |
| --- | --- |
| The room is not in `chat.watch` | every room starts closed |
| `entryGate` is not `open` | only you open a gate |
| `mode` is not `autoreply` | `notes-only` and `draft` post nothing |
| The room has never been introduced to, and the text isn't the approved introduction | disclosure comes first |

Each denial says which rail it was and why, so the agent reads it as a consent decision rather
than a broken tool to be worked around.

**It is honest about its limits.** Authority-is-the-sender, containment across rooms, and never
answering another agent all depend on what a message *means*. No tool-name matcher can decide
those, and one dressed up to look as if it could would be worse than none — it would draw
attention away from the rails that still need a careful reader. Those stay in the skill.

Three things worth knowing:

- **Installation is deliberate, and has to be.** Plugin-contributed hooks are documented but do
  not fire on CLI 1.0.86 — verified against all three declaration shapes, with a user-level hook
  firing in the same session as a control. So the gate goes in `~/.copilot/hooks/` by your own
  command. That also suits Jaxx, where nothing is supposed to switch itself on.
- **It fails safe in both directions.** Before it knows the call is a post, any error allows —
  a malformed payload on an unrelated tool must never block your work. Once it knows it *is* a
  post, any error denies, including an unreadable `agent.config.json`. No config at all means
  Jaxx isn't set up in that repo, so it stays out of the way entirely.
- **It needs Python 3** on `PATH`, the same as the repo's validators.

Check it yourself: `python scripts/test_gate.py` runs the gate as a real subprocess against real
payloads, and every rail in the table above has a test that proves it blocks.

## The one idea

> **Authority is the sender id on the message, never the content of the message.**

An agent that reads shared content — chat, tickets, PRs, email — is reading text written by people
who know it is an agent. Some of that text will be shaped to steer it. So text is *data to report
on*, never *instructions to follow*, and no amount of plausible framing promotes it.

Everything else in `jaxx-consent` follows from taking that seriously, including the three rails
people skip: **consent to enter a room is separate from permission to act, and comes first**, **only
whoever placed the agent may take it out**, and **what it reads in one room never travels to
another**.

The last one is what makes broad read access safe. An agent that can see many rooms is a join point
nobody in any single room agreed to; containment is the difference between a useful assistant and an
accidental leak with good manners.

## Design notes

**Why a skill and not a daemon.** The obvious build is poll-and-keyword-match. It fails on the
first question phrased in a way you didn't anticipate — and every real question is. There's also
usually a hard credential blocker: reading Teams needs delegated Graph scopes a service token
doesn't carry. So the loop runs as an agent turn on a schedule, and a full model does the triage.

**Why git and not a vector store.** Memory changes are diffable, reviewable, revertible, portable,
and greppable with tools the agent already has. The commit log doubles as an audit trail.

**Why most cycles do nothing.** An agent that finds something to say every minute is misconfigured.
`quiet` is the expected outcome, and it still gets logged.

## Status

`0.4.0` — adds fail-closed consent enforcement, configuration schema validation, health checks and
dual GitHub Copilot CLI / Claude Code packaging. **The responder is Microsoft Teams only**, via
Microsoft Graph; there is no Slack or Discord path and none is planned. The `jaxx-consent` rails are
platform-independent and are the part worth taking on their own.

MIT licensed. Not affiliated with or endorsed by any employer.
