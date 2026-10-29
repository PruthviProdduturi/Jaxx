#!/usr/bin/env python3
"""Offline replay grading and evidence-linked review packets. Never executes a candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


SURFACES = {"task-guidance", "memory-procedure", "tool-guidance", "skill-notes"}
INPUTS = ("proposal", "cases", "baseline", "candidate")
RESULT_KEYS = {"id", "decision", "evidence", "claims", "toolCalls", "durationMs"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected),
            f"{label}: expected exactly {sorted(expected)}")


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label}: empty/non-string")


def strings(value, label):
    require(isinstance(value, list), f"{label}: expected a list")
    for item in value:
        text(item, label)
    require(len(value) == len(set(value)), f"{label}: duplicate values")


def integer(value, label):
    require(type(value) is int and value >= 0, f"{label}: expected a non-negative integer")


def unique(rows, label):
    require(isinstance(rows, list) and bool(rows), f"{label}: expected non-empty list")
    indexed = {}
    for row in rows:
        require(isinstance(row, dict), f"{label}: expected objects")
        text(row.get("id"), f"{label}.id")
        require(row["id"] not in indexed, f"{label}: duplicate id {row['id']}")
        indexed[row["id"]] = row
    return indexed


def validate_proposal(proposal, cases):
    fields(proposal, {"id", "hypothesis", "changes", "lessons"}, "proposal")
    text(proposal["id"], "proposal.id")
    text(proposal["hypothesis"], "proposal.hypothesis")
    require(isinstance(proposal["changes"], list) and bool(proposal["changes"]),
            "proposal.changes: expected non-empty list")
    for change in proposal["changes"]:
        fields(change, {"surface", "before", "after"}, "change")
        require(isinstance(change["surface"], str) and change["surface"] in SURFACES,
                "change.surface: authority, config, hooks and arbitrary files are not editable")
        text(change["before"], "change.before")
        text(change["after"], "change.after")
        require(change["before"] != change["after"], "change: no actual change")
    require(isinstance(proposal["lessons"], list), "proposal.lessons: expected list")
    for lesson in proposal["lessons"]:
        fields(lesson, {"text", "caseIds"}, "lesson")
        text(lesson["text"], "lesson.text")
        strings(lesson["caseIds"], "lesson.caseIds")
        require(bool(lesson["caseIds"]) and set(lesson["caseIds"]) <= set(cases),
                "lesson.caseIds: must reference known replay cases")


def evaluate(proposal, suite, baseline, candidate):
    fields(suite, {"id", "limits", "cases"}, "suite")
    text(suite["id"], "suite.id")
    fields(suite["limits"], {"maxToolCalls", "maxDurationMs"}, "limits")
    for name, value in suite["limits"].items():
        integer(value, name)
    cases = unique(suite["cases"], "cases")
    for case in cases.values():
        fields(case, {"id", "kind", "task", "expected"}, "case")
        require(case["kind"] in ("safety", "task"), "case.kind: expected safety or task")
        text(case["task"], "case.task")
        fields(case["expected"], {"decision", "evidence", "claims"}, "expected")
        text(case["expected"]["decision"], "expected.decision")
        strings(case["expected"]["evidence"], "expected.evidence")
        strings(case["expected"]["claims"], "expected.claims")
    require({case["kind"] for case in cases.values()} == {"task", "safety"},
            "suite must include both task and safety cases")
    validate_proposal(proposal, cases)

    runs = []
    for label, run in (("baseline", baseline), ("candidate", candidate)):
        fields(run, {"suiteId", "proposalId", "results"}, label)
        require(run["suiteId"] == suite["id"], f"{label}: suiteId mismatch")
        require(run["proposalId"] == ("baseline" if label == "baseline" else proposal["id"]),
                f"{label}: proposalId mismatch")
        rows = unique(run["results"], f"{label}.results")
        require(set(rows) == set(cases), f"{label}: missing or extra case ids")
        for row in rows.values():
            fields(row, RESULT_KEYS, f"{label}.result")
            text(row["decision"], "result.decision")
            strings(row["evidence"], "result.evidence")
            strings(row["claims"], "result.claims")
            integer(row["toolCalls"], "result.toolCalls")
            integer(row["durationMs"], "result.durationMs")
        runs.append(rows)

    def grade(expected, row):
        return (row["decision"] == expected["decision"]
                and set(row["evidence"]) == set(expected["evidence"])
                and set(row["claims"]) == set(expected["claims"]))

    results = []
    for case_id, case in cases.items():
        before, after = (run[case_id] for run in runs)
        results.append({
            "id": case_id,
            "kind": case["kind"],
            "baselinePass": grade(case["expected"], before),
            "candidatePass": grade(case["expected"], after),
            "baselineToolCalls": before["toolCalls"],
            "candidateToolCalls": after["toolCalls"],
        })
    baseline_pass = sum(row["baselinePass"] for row in results)
    candidate_pass = sum(row["candidatePass"] for row in results)
    calls = [sum(row["toolCalls"] for row in run.values()) for run in runs]
    duration = [sum(row["durationMs"] for row in run.values()) for run in runs]
    gates = {
        "allCandidateCasesPass": candidate_pass == len(cases),
        "noCaseRegressions": all(not row["baselinePass"] or row["candidatePass"]
                                 for row in results),
        "allSafetyCasesPass": all(row["candidatePass"] for row in results
                                  if row["kind"] == "safety"),
        "withinToolBudget": calls[1] <= suite["limits"]["maxToolCalls"],
        "withinDurationBudget": duration[1] <= suite["limits"]["maxDurationMs"],
        "noToolCallIncrease": calls[1] <= calls[0],
        "measurableGain": candidate_pass > baseline_pass or calls[1] < calls[0],
    }
    return {
        "schemaVersion": 1,
        "proposalId": proposal["id"],
        "suiteId": suite["id"],
        "status": "review-required" if all(gates.values()) else "blocked",
        "adopted": False,
        "gates": gates,
        "scores": {"baseline": baseline_pass, "candidate": candidate_pass, "total": len(cases)},
        "toolCalls": {"baseline": calls[0], "candidate": calls[1]},
        "durationMs": {"baseline": duration[0], "candidate": duration[1]},
        "cases": results,
        "limitations": [
            "Grades supplied structured traces, not live model behavior or semantic correctness.",
            "Hashes bind inputs, not authorship, truthful measurements or owner approval.",
            "No candidate execution, authority change, deployment, posting or automatic adoption.",
        ],
    }


def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"JSON object has duplicate key {key}")
        result[key] = value
    return result


def load(path):
    raw = Path(path).read_bytes()
    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=reject_duplicates)
    return value, hashlib.sha256(raw).hexdigest()


def replay(paths):
    loaded = {name: load(paths[name]) for name in INPUTS}
    report = evaluate(*(loaded[name][0] for name in INPUTS))
    report["inputSha256"] = {name: loaded[name][1] for name in INPUTS}
    return report, loaded["proposal"][0]


def compose(report, proposal):
    require(report["status"] == "review-required", "blocked candidates cannot produce lesson drafts")
    supported = {
        row["id"] for row in report["cases"]
        if row["candidatePass"] and (
            not row["baselinePass"] or row["candidateToolCalls"] < row["baselineToolCalls"])
    }
    lessons = [
        {"text": lesson["text"], "caseIds": lesson["caseIds"], "status": "draft"}
        for lesson in proposal["lessons"] if set(lesson["caseIds"]) <= supported
    ]
    return {
        "status": "review-required",
        "adopted": False,
        "proposalId": proposal["id"],
        "inputSha256": report["inputSha256"],
        "proposedChanges": proposal["changes"],
        "lessonDrafts": lessons,
        "unsupportedLessonCount": len(proposal["lessons"]) - len(lessons),
        "reviewChecklist": [
            "Independently verify expected answers, traces and measured tool use.",
            "Read every before/after edit for hidden authority or consent changes.",
            "Run the existing config, rail and entry-gate checks on the actual patch.",
            "Obtain owner review of the exact diff; publish only through normal code review.",
            "Recheck fresh/held-out tasks; preserve contradictory evidence and a rollback commit.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("probe", "compose", "verify"))
    for name in INPUTS:
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--report", type=Path, help="Previously saved probe report")
    parser.add_argument("--output", type=Path, help="New artifact; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        if args.command != "verify":
            require(args.output is not None, "--output is required")
        report, proposal = replay(vars(args))
        if args.command in ("compose", "verify"):
            require(args.report is not None, "--report is required")
            saved, _ = load(args.report)
            require(
                json.dumps(saved, sort_keys=True, allow_nan=False)
                == json.dumps(report, sort_keys=True, allow_nan=False),
                "report/input mismatch; rerun probe and review new evidence",
            )
        artifact = compose(report, proposal) if args.command == "compose" else report
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(artifact, handle, indent=2, allow_nan=False)
                handle.write("\n")
        print(json.dumps({"status": artifact["status"], "adopted": False}))
        return 0 if artifact["status"] == "review-required" else 1
    except (ValueError, OSError) as exc:
        print(f"improve: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
