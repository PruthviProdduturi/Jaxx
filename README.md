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

## What the plugin does and does not give you

A plugin ships **instructions**. It carries no credentials and no API access. Reach comes from MCP
servers; behaviour comes from the skills. Both halves are required.

| Capability | Comes from | Shipped here |
| --- | --- | --- |
| Create / update Azure DevOps work items | `@azure-devops/mcp` | ✅ see [`mcp.example.json`](mcp.example.json) — `/jaxx-setup` wires it up |
| Read and post Microsoft Teams messages | a server holding delegated Graph `Chat.Read` / `Chat.ReadWrite` | ❌ **you must bring this** |
| Knowing *how* to behave when doing either | `jaxx-consent`, `jaxx-responder` | ✅ |
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

```
/plugin install jaxx
/jaxx-setup
```

`/jaxx-setup` does the rest: it detects which MCP servers you actually have, discovers your own
identity rather than asking you for a GUID, writes `agent.config.json` from the template,
bootstraps the memory files, and then **tells you plainly what is still missing**.

It is idempotent — re-run it any time.

### The three commands

| Command | Does |
| --- | --- |
| `/jaxx-setup` | First run. Detect, configure, bootstrap, report gaps. Safe to repeat. |
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

`0.1.0` — extracted from a working private deployment. **The responder is Microsoft Teams only**,
via Microsoft Graph; there is no Slack or Discord path and none is planned. The `jaxx-consent` rails
are platform-independent and are the part worth taking on their own.

MIT licensed. Not affiliated with or endorsed by any employer.
