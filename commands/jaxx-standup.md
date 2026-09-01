---
description: Read your work back — what is in flight, what moved, what is stale, and what needs a decision. Reconciles the repo memory files against the tracker and reports the deltas.
---

# Jaxx standup

What you'd say in standup, assembled from the tracker and the repo memory. Read-only by default.

## Run

1. **Read the memory first** — `ACTIVE.md` and any relevant `streams/*.md`. This is the cheap half
   and it frames everything else.
2. **Query the tracker** for items assigned to the owner that are active or changed recently.
3. **Reconcile.** The interesting output is the *delta*, not the list:

| Delta | Meaning |
| --- | --- |
| In tracker, not in `ACTIVE.md` | untracked work — offer to add it |
| In `ACTIVE.md`, closed in tracker | finished — offer to move to `ARCHIVE.md` |
| In `ACTIVE.md`, no id | **never let work exist only in markdown** — offer to create the item |
| Unchanged for >2 weeks | flag as stalled |
| Not verified this session | mark `(stale)` — never invent status |

## Report

Three short sections, tables not prose:

- **In flight** — what's actually moving
- **Needs you** — approvals, reviews, blocked items, unanswered questions
- **Drifted** — the deltas above

Dates as `YYYY-MM-DD`. Every item and PR as a real link.

Keep it to what someone could actually say out loud in two minutes. If the honest answer is
"nothing moved", say that — a padded standup is worse than a short one.

## Then offer, don't do

Offer to write the reconciliation back (update `ACTIVE.md`, archive the closed rows, create the
missing items). Wait for a yes. If the user accepts, follow
[`jaxx-memory`](../skills/jaxx-memory/SKILL.md) — including the session-end commit.
