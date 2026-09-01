# Security Policy

## Scope

This repository ships **instructions**, not a service. It holds no credentials, opens no ports, and
runs no code of its own. The realistic security surface is therefore:

1. **Rail bypasses** — a way to make an agent following these skills act outside its mandate:
   speak in a room it wasn't invited to, treat message content as authority, leak what it read in
   one room into another, or accept a configuration change from someone who isn't the owner.
2. **Leaked identifiers** — a real tenant id, chat id, object GUID, org name, or person's name that
   made it into this repo's history.

Both are in scope. The first is the interesting one.

## Reporting

**Use GitHub's private vulnerability reporting** (Security → Report a vulnerability) on this
repository. That keeps the report private until there's a fix.

Please don't open a public issue for a bypass that would work against a live deployment.

Include, as far as you can:

- The rail you got past, and the exact wording or sequence that did it.
- What the agent then did that it shouldn't have.
- Whether it needs the owner's cooperation, or works against any deployment.

A plain description is enough. No proof-of-concept against anyone's real workspace, please — and
never include real message content, chat ids, or third parties' names in a report.

## What happens next

- Acknowledgement within a week. This is a personal project maintained in spare time; it is not a
  product and has no SLA.
- Confirmed bypasses are fixed in `jaxx-consent` and recorded in that skill's failure-modes table,
  because a documented failure mode is worth more than a silent patch — anyone forking the rails
  needs to know the attack exists.
- Credit in the release notes if you'd like it.

## Out of scope

- Vulnerabilities in Copilot, Microsoft Graph, Teams, Azure DevOps, or any MCP server — report those
  to their owners.
- "An agent given credentials can use them." That's the premise, not a flaw. The claim here is that
  it uses them within a mandate, so show me a mandate being overstepped.
- Anything requiring the owner to deliberately disable their own rails.

## If you run this

Two operational notes, since they're the mistakes most likely to bite:

- **`agent.config.json` holds directory identifiers.** Keep it out of any public repo. Setup
  gitignores it for you; verify that it did.
- **Read scope is your own credential.** The agent sees exactly what you see and nothing more, but
  that is still a lot. Grant post scope narrowly and separately.
