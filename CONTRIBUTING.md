# Contributing

Thanks for looking. This is a small, opinionated project — the fastest way to get a change merged is
to know what it's opinionated *about*.

## What this project is

A set of **rails**: rules an agent follows when it acts in front of other people. The rails live in
[`skills/jaxx-consent/SKILL.md`](skills/jaxx-consent/SKILL.md) and are the point of the project. The
Teams responder is one implementation that obeys them; the memory skill is scaffolding that keeps an
agent coherent across context loss.

Changes to the rails are held to a higher bar than changes to anything else. That's deliberate.

## Ground rules

**1. Restrictions are the default; permissions are the exception.**
A change that makes the agent able to do more needs to explain what stops it doing that thing in the
wrong room, to the wrong person, on the wrong authority. "The user can turn it off" is not an
answer — the failure mode is a user who never looked.

**2. Authority is the sender id, never the message content.**
No PR may introduce a path where text the agent *read* becomes an instruction it *follows*. This
includes plausible framing: quoted approvals, pasted transcripts, a ticket field that says
"the owner approved this". If your feature needs to trust content, it doesn't get merged.

**3. Nothing crosses rooms.**
Anything the agent says in one place must be justifiable from that place alone. If a proposed reply
could only exist because another room was read, it's a leak, however polite.

**4. Silence is a valid outcome, and usually the right one.**
Features that make the agent speak more often start from behind. Most cycles should do nothing.

## Good first contributions

- **New failure modes.** Found a way to talk an agent past a rail? That's the most valuable issue
  you can file, and it doesn't need code — a description of the loophole is enough.
- **Another chat platform.** The responder is Teams-only. A Slack or Discord responder that obeys
  the same rails would be genuinely useful. Keep platform specifics out of `jaxx-consent`.
- **A non-ADO tracker.** The memory skill assumes work items exist somewhere. GitHub Issues, Jira,
  or Linear back-ends are all reasonable.
- **Docs and worked examples.** Especially the setup path — it's the part most likely to break for
  someone whose environment isn't the one it was built on.

## Workflow

1. **Open an issue first** for anything touching `jaxx-consent`. For typos, docs, and obvious bugs,
   just send the PR.
2. Fork, branch, change, PR against `main`.
3. Keep PRs focused. One idea per PR.
4. Commit messages: `type(scope): imperative summary`, e.g. `feat(responder): dedupe by message id`.
   Types used here: `feat`, `fix`, `docs`, `refactor`, `chore`.

## Before you open the PR

- [ ] JSON still parses — `plugin.json` and `agent.config.template.json`.
- [ ] `plugin.json` still validates against the Agent Plugins 1.0.0 schema. It sets
      `additionalProperties: false`, so component folders (`skills/`, `commands/`) are discovered by
      convention and must **not** be listed in the manifest.
- [ ] **No real identifiers anywhere.** No tenant ids, chat ids (`19:…@thread.v2`), object GUIDs,
      org names, or real people's names — including in examples and sample tables. Use placeholders
      and invented names. This is checked in CI and is the one thing that will get a PR closed
      without discussion.
- [ ] Skill edits read as instructions to an agent, not prose about an agent. Second person,
      imperative, no hedging. An agent can't act on "it may be preferable to".
- [ ] If you added a rule, you also added the failure mode it prevents.

## What gets declined

- Bypasses, overrides, or "advanced mode" flags for the consent rails.
- Anything that makes the agent post somewhere it wasn't explicitly invited.
- Autonomy features that remove the human from a decision rather than speeding one up.
- Renaming Jaxx in the shipped skills, setup flow, template or schema. The fixed Jaxx identity is
  load-bearing: signatures, reply detection, audit logs and other-agent detection all depend on it.
  A separately branded fork is a different product and must not present itself as Jaxx.

## Naming

The display name is **Jaxx**. The manifest `name` is `jaxx`, lowercase — the Agent Plugins schema
constrains it to `^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$`, and the install id has to match it. Capital
J everywhere a human reads it; lowercase everywhere a machine parses it.

## Publishing to a marketplace

Marketplaces generally want a metadata file of their own alongside `plugin.json` — a category, a
platform list, an author list. That file is **vendor-time metadata and is deliberately not carried
in this repo**: its schema URL and review conventions belong to the marketplace, not to the plugin,
and shipping them here would mean publishing links that resolve for nobody.

Add it in the published copy, not upstream. CI validates such a file when it is present and does
not require it. Note that the identifier check rejects real-looking email addresses anywhere in the
tree, so an author address is something the published copy adds too.

## Security

Don't file loopholes that expose a live deployment as public issues. See
[`SECURITY.md`](SECURITY.md).

## License

By contributing you agree your contributions are licensed under the MIT License in
[`LICENSE`](LICENSE).
