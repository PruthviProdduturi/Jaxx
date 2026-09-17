---
description: Start here. What Jaxx is, what it can currently reach, and the one next step. Safe to run at any time — reads state, changes nothing, posts nothing.
---

# Jaxx

The front door. Someone who has just installed the plugin and typed `/jaxx` should leave this
command knowing three things: **what it is, what it can currently do, and the single next step.**

**This command is read-only.** It never writes config, never posts, never enables anything. It is
safe to run on a strange repo, and safe to run repeatedly.

## Step 1 — work out which of three states you are in

Check, in this order, and stop at the first match:

| State | Test | Go to |
| --- | --- | --- |
| **Fresh** | no `agent.config.json` in the repo | Step 2 |
| **Inert** | config exists, `chat.watch` is empty | Step 3 |
| **Live** | config exists, `chat.watch` is non-empty | Step 4 |

Do not ask the user which one they are. Look.

## Step 2 — Fresh: the welcome

This is the only time the full pitch is warranted. Keep it to roughly this length — someone who
just installed a plugin wants orientation, not a manual.

> **Jaxx** — an assistant that acts in your name, and can't overstep it.
>
> Three parts:
>
> - **Consent rails** — a mandate the agent cannot widen on its own. It reads where you allow, and
>   speaks only where you have separately approved. Those are two different permissions.
> - **A chat responder** that obeys those rails, rather than a bot that posts and apologises later.
> - **Repo-as-memory** — the durable record lives in files, so it survives a session being
>   compacted or thrown away.
>
> Right now I am **inert**. No config, watching nothing, posting nowhere.
>
> **Next:** `/jaxx-setup` — detects what you have, asks four questions, and writes a config that
> still posts nowhere. Nothing goes live in that command either.

Then stop. **Do not offer to run setup for them, and do not start setting up.** A plugin that
begins configuring itself on first contact is exactly the behaviour these rails exist to prevent.
Let them type it.

## Step 3 — Inert: configured, watching nothing

Report state as a table, then the next step. No pitch — they have already seen it.

```
Owner        Ada Lovelace (ada@example.com)
Reading      all chats
Posting in   nothing
Reports to   your 1:1 with Jaxx
Azure DevOps connected — contoso/Platform
```

Then **one** next step, chosen by what is actually missing:

- `owner.id` still a placeholder → say plainly that sender-id authority is **not enforceable** until
  it is filled in, and that this is a real gap, not cosmetic. That outranks everything else.
- No Graph reach → `jaxx-responder` is a specification, not a running thing. Say so.
- Otherwise → `/jaxx-check` to run a read-only cycle and see what it would have told you.

## Step 4 — Live: watching something

Lead with the rooms and their gates, because that is the part with consequences:

```
Chat              Mode         Entry gate   Introduced
Platform team     notes-only   open         2026-09-08
Ada / Grace       draft        open         2026-09-02
```

Any room at `open` with no introduction recorded is **not** a room the agent may talk in — the
approved introduction is the only message permitted there until it has gone out. Say that
explicitly rather than showing a blank cell; a blank reads like "fine".

Then: `/jaxx-check` to run a cycle now.

## Always close with the honest line

Whatever the state, the last line says what the agent is currently able to say out loud:

- Fresh or inert → **"Posting nowhere."**
- Live → name the rooms it could post in, and the mode of each.

**Never close by implying it is watching or answering anything it isn't.** A user who believes the
agent is covering their chats when it is inert is the worst outcome of this command — worse than
them never running it.

## What not to do here

- Don't write files. `/jaxx-setup` owns that.
- Don't read chats. `/jaxx-check` owns that.
- Don't post anything, anywhere, for any reason.
- Don't pad the fresh-install welcome with the full rail list. Send them to
  [`jaxx-consent`](../skills/jaxx-consent/SKILL.md) if they want it.
