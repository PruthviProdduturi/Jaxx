---
name: jaxx-health
description: 'Run a read-only Jaxx deployment health check. Verifies package discovery, configuration safety, owner identity, MCP reach, room gates, private reporting, scheduler visibility, responder runtime, and the latest cycle without changing, posting, installing, or repairing anything. WHEN "Jaxx health", "is Jaxx running", "check Jaxx", "verify Jaxx setup", "responder health", or "are the Jaxx rails enforced".'
license: MIT
---

# Jaxx health

Run the complete read-only health procedure in
[`commands/jaxx-health.md`](../../commands/jaxx-health.md).

Read that file before checking anything and follow every section in order. Do not repair,
authenticate, install, schedule, edit, post, or otherwise mutate the deployment. Lead with the
overall state, show the health table and room table, and finish with concrete blockers ordered
critical to degraded.

This skill exists because GitHub Copilot CLI plugins discover `skills/*/SKILL.md`, while Claude
Code also exposes the command wrapper. The health behavior and result criteria remain defined in
the command file so both clients run the same check.
