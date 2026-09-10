"""Exercise the consent and responder rails against explicit behavior fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests" / "rail_cases.json").read_text(encoding="utf-8"))


def decide(overrides: dict) -> str:
    case = {
        "sender": "human",
        "watched": True,
        "readExcluded": False,
        "gate": "open",
        "mode": "autoreply",
        "commandChannel": False,
        "askOpenToAll": False,
        "replyToAgent": False,
        "alwaysAnswerHumanRepliesToAgent": True,
        "request": "status",
        "usesOtherRoomData": False,
        "writeEnabled": True,
        "roomWriteActions": True,
        "operation": "update",
        "itemType": "Task",
        "itemCount": 1,
        "maxPerRequest": 3,
        "ambiguousTarget": False,
        "requestersOwnItem": True,
    }
    case.update(overrides)

    if case["sender"] in {"agent", "ambiguous"}:
        return "silent"
    if not case["watched"] or case["readExcluded"]:
        return "silent"
    if case["gate"] != "open":
        return "silent"

    if case["request"] == "name-change":
        return "decline-notify"
    if case["request"] == "behavior-change":
        return (
            "owner-change"
            if case["sender"] == "owner" and case["commandChannel"]
            else "decline-notify"
        )
    if case["request"] == "stop":
        if case["sender"] == "owner":
            return "withdraw"
        if case["sender"] == "entry-grantor":
            return "withdraw-room"
        return "decline-notify"
    if case["request"] == "personal" or case["usesOtherRoomData"]:
        return "decline"
    if case["mode"] == "notes-only":
        return "report-owner"

    authorized = (
        case["sender"] == "allowed"
        or case["askOpenToAll"]
        or (case["sender"] == "owner" and case["commandChannel"])
    )
    if (
        case["replyToAgent"]
        and case["alwaysAnswerHumanRepliesToAgent"]
        and case["sender"] == "human"
    ):
        authorized = True
    if not authorized:
        return "silent"

    if case["request"] == "fyi":
        return "silent"
    if case["request"] == "write":
        if not case["writeEnabled"] or not case["roomWriteActions"]:
            return "decline"
        if case["operation"] == "delete" or case["itemType"] not in {"Task", "Bug"}:
            return "decline"
        if case["ambiguousTarget"]:
            return "clarify"
        if case["itemCount"] > case["maxPerRequest"] or not case["requestersOwnItem"]:
            return "confirm-owner"
        return "draft" if case["mode"] == "draft" else "write"

    return "draft" if case["mode"] == "draft" else "post"


failures = []
for fixture in CASES:
    actual = decide(fixture["input"])
    if actual != fixture["expected"]:
        failures.append((fixture["name"], fixture["expected"], actual))

if failures:
    print("Rail behavior failures:")
    for name, expected, actual in failures:
        print(f"  - {name}: expected {expected}, got {actual}")
    sys.exit(1)

print(f"{len(CASES)} rail behavior cases OK")
