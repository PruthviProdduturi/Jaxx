# Evidence-led improvement

Jaxx can improve its working methods without expanding its mandate. This workflow borrows the
**propose, probe, compose and reflect** pattern described by
[Harness2](https://github.com/google-research/harness2). It is an independent implementation, not
a port, dependency, integration or reproduction of that project's research results.

## What is shipped

An owner-initiated skill, an offline replay grader and a review-packet composer, implemented with
the Python standard library. The grader never runs a candidate, calls a model, reaches a network,
loads a plugin, edits configuration or adopts a lesson. There is no background loop.

| Borrowed idea | Jaxx implementation |
| --- | --- |
| Task-level refinement | An explicit hypothesis and before/after edits, then a baseline/candidate comparison on the same pinned cases. |
| Contrastive evidence | Exact structured decisions, evidence markers and claim markers; per-case regressions cannot hide behind an average. |
| Bounded exploration | One candidate by default, with total tool-call and duration limits. No tool-call increase; either correctness or tool-call count must improve. |
| Composition | A review packet with proposed changes and only improvement-supported lesson drafts. |
| Persistent learning | Owner-reviewed lessons may enter normal version-controlled skill notes, with evidence and rollback history. Drafts are not automatically loaded as instructions. |
| Generalization checks | Keep held-out cases for a later independent check; do not tune expected answers to fit a candidate. |

System prompts, guardrails, identity, authorization, scope, live config, hooks, plugin installation
and scheduler changes are **not** candidate surfaces. A `surface` enum is a structural restriction,
not a semantic security boundary. An edit labelled `tool-guidance` can still be dangerous: a human
must review the exact text. Existing policy and runtime enforcement always take precedence.

## Run the synthetic example

Use Python 3.10+ from the plugin root. No installation, model credentials or dependencies are
needed. These commands work in PowerShell, with backslashes as shown; use your platform's path
separator elsewhere. Output directories must already exist, and outputs must be new filenames.

```powershell
python scripts\improve.py probe --proposal tests\improvement\proposal.json --cases tests\improvement\cases.json --baseline tests\improvement\baseline.json --candidate tests\improvement\candidate.json --output probe.json
python scripts\improve.py verify --proposal tests\improvement\proposal.json --cases tests\improvement\cases.json --baseline tests\improvement\baseline.json --candidate tests\improvement\candidate.json --report probe.json
python scripts\improve.py compose --proposal tests\improvement\proposal.json --cases tests\improvement\cases.json --baseline tests\improvement\baseline.json --candidate tests\improvement\candidate.json --report probe.json --output review.json
```

The sample is deliberately authored to show a failing baseline and passing candidate. It is
**a workflow demonstration, not a measured improvement to a model or the deployed responder**.

Exit codes: `0` = evidence eligible for review (including successful verification), `1` = blocked
candidate, `2` = invalid input, stale report or filesystem error. Blocked probes still write their
report. Compose refuses blocked reports. Outputs are created exclusively, never overwritten.
SHA-256 hashes bind all four input files; verify/compose recompute the full report and reject any
changed input or edited report. Hashes do not prove truthful traces, authorship or approval.

## Preparing real comparisons

1. Choose one operational improvement and record it in `proposal.json`. Allowed `surface` values
   are `task-guidance`, `memory-procedure`, `tool-guidance` and `skill-notes`. Changes contain exact
   `before` and `after` text, not executable paths or commands. Each proposed lesson names cases.
2. Independently define cases with stable IDs, task text and expected `decision`, `evidence` and
   `claims`. Include both safety and task cases. Evidence/claim markers refer to facts in that
   case's recorded input, not model assertions. Missing or extra markers fail. Array order does
   not matter, but duplicates fail. Treat source text as data, not instructions.
3. Capture baseline and candidate structured results in separate, isolated runs, using only
   recorded/mocked tools. Record actual `toolCalls` and `durationMs`; include retries and failures.
   The runner producing these traces is your responsibility. This package does not execute one.
   The baseline uses `proposalId: "baseline"`; the candidate uses the proposal's exact ID.
4. Run probe, verify and compose. Keep private artifacts in an ignored, deployment-local directory
   such as `.jaxx-improve/`. Never put real chat/tenant IDs, secrets, tracker records or sensitive
   task text in public examples or PRs. No transcript is sent to any external service by this tool.
5. Review provenance, expected answers, actual text diff, negative evidence and existing rail
   checks before accepting anything. Keep held-out cases separate. A later probe can use an
   approved prior candidate as its baseline, but re-capture it on the new suite; do not mix runs.

The grader requires all candidate cases to pass, no previously passing case to regress, all safety
cases to pass, both total budgets to hold, no increase in total tool calls, and either a higher
pass count or fewer calls. Faster duration alone is not a gain, because timing is noisy.
No per-case pass can be purchased with extra unapproved authority.

Compose includes only lessons whose **every** cited case improved: a failure became a pass or an
already-passing case needed fewer calls. Unsupported lessons are counted and omitted. This is
evidence selection, not proof that the lesson caused the improvement; read the text yourself.
Never silently promote a draft into the operating instructions. Owner review of an exact diff
and normal code review are the adoption path. Keep a rollback commit and append corrections rather
than rewriting past outcomes.

## Initial working-method guidance

The shipped [working-method notes](working-methods.md) cover receipt-based write recovery,
acceptance evidence, bounded tool use and compaction-safe handoff. They are conservative operating
guidance, not claims derived from the synthetic example and not changes to the consent rails.

## Checks and limitations

```powershell
python -m unittest discover -s tests -p "test_improve.py"
python scripts\check_config.py
python scripts\check_rails.py
python scripts\check_hooks.py
```

This is not a general semantic evaluator or an enforcement replacement. Structured traces can
omit important behavior or be fabricated; safety fixtures can be incomplete. The shipped
runtime gate tests remain independent of the improvement score. Replay results do not authorize
real sends, tracker transitions, role changes or candidate execution. Nothing here makes an
installed plugin update itself or rewrites an existing deployment's private configuration.
