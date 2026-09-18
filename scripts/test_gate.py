#!/usr/bin/env python3
"""Prove the entry gate blocks what the rails say it blocks.

Runs `hooks/jaxx_gate.py` as a real subprocess with real `preToolUse` payloads
on stdin, exactly the way the CLI invokes it -- so this tests the shipped
contract, not a mock of it.

    python scripts/test_gate.py
"""

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "hooks", "jaxx_gate.py")

OPEN_ROOM = {
    "id": "19:room-open",
    "name": "Datacenter Cooling",
    "mode": "autoreply",
    "entryGate": "open",
    "introduction": "Hi all -- I'm Jaxx, Pruthvi's assistant. He's asked me to keep an eye on this chat.",
    "introducedAt": "2026-09-01T10:00:00Z",
}


def config(**overrides):
    room = dict(OPEN_ROOM)
    room.update(overrides.pop("room", {}))
    cfg = {"chat": {"watch": [room], "readExclusions": []}}
    cfg["chat"].update(overrides)
    return cfg


def run(cfg, tool_name, tool_args, write_config=True):
    workdir = tempfile.mkdtemp(prefix="jaxx-gate-")
    if write_config:
        path = os.path.join(workdir, "agent.config.json")
        with open(path, "w", encoding="utf-8") as handle:
            if isinstance(cfg, str):
                handle.write(cfg)
            else:
                json.dump(cfg, handle)

    env = dict(os.environ)
    env["COPILOT_PROJECT_DIR"] = workdir
    payload = json.dumps({"toolName": tool_name, "toolArgs": tool_args})

    proc = subprocess.run(
        [sys.executable, GATE],
        input=payload, env=env, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return "CRASH", proc.stderr.strip()
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        return "BADJSON", proc.stdout
    return out.get("permissionDecision"), out.get("permissionDecisionReason", "")


SEND = "teams_send_message"
CASES = []


def case(name, expected, *args, **kwargs):
    CASES.append((name, expected, args, kwargs))


# --- must not get in the way of ordinary work --------------------------------
case("unrelated tool is untouched", "allow",
     config(), "glob", {"pattern": "*.md"})
case("no agent.config.json means not my business", "allow",
     config(), SEND, {"chatId": "19:room-open"}, write_config=False)
case("posting tool with no room id is a read", "allow",
     config(), "teams_list_messages", {"query": "cooling"})
case("broken config does not brick unrelated tools", "allow",
     "{ this is not json", "glob", {"pattern": "*.md"})
case("enforcement can be turned off deliberately", "allow",
     config(enforcement={"enabled": False}), SEND,
     {"chatId": "19:unknown", "content": "hello"})

# --- rail 3: every room starts closed ----------------------------------------
case("unknown room is denied", "deny",
     config(), SEND, {"chatId": "19:never-seen", "content": "hello"})
case("closed gate is denied", "deny",
     config(room={"entryGate": "closed"}), SEND,
     {"chatId": "19:room-open", "content": "hello"})
case("requested-but-not-granted gate is denied", "deny",
     config(room={"entryGate": "requested"}), SEND,
     {"chatId": "19:room-open", "content": "hello"})
case("revoked room is denied", "deny",
     config(readExclusions=[{"id": "19:room-open"}]), SEND,
     {"chatId": "19:room-open", "content": "hello"})

# --- the mode ladder: only autoreply posts -----------------------------------
case("notes-only posts nothing", "deny",
     config(room={"mode": "notes-only"}), SEND,
     {"chatId": "19:room-open", "content": "hello"})
case("draft posts nothing", "deny",
     config(room={"mode": "draft"}), SEND,
     {"chatId": "19:room-open", "content": "hello"})
case("autoreply may post", "allow",
     config(), SEND, {"chatId": "19:room-open", "content": "hello"})

# --- the introduction must be the first thing said ---------------------------
case("first post must be the introduction", "deny",
     config(room={"introducedAt": None}), SEND,
     {"chatId": "19:room-open", "content": "Sure, I can help with that."})
case("verbatim introduction is allowed", "allow",
     config(room={"introducedAt": None}), SEND,
     {"chatId": "19:room-open", "content": OPEN_ROOM["introduction"]})
case("introduction still matches through HTML", "allow",
     config(room={"introducedAt": None}), SEND,
     {"chatId": "19:room-open",
      "body": {"contentType": "html",
               "content": "<p>" + OPEN_ROOM["introduction"] + "</p>"}})
case("approved entry without approved wording posts nothing", "deny",
     config(room={"introducedAt": None, "introduction": None}), SEND,
     {"chatId": "19:room-open", "content": "hello"})

# --- an unverifiable gate is a closed one ------------------------------------
case("broken config denies an actual post", "deny",
     "{ this is not json", SEND,
     {"chatId": "19:room-open", "content": "hello"})
case("nested room id is still found", "deny",
     config(), SEND,
     {"params": {"conversationId": "19:never-seen"}, "content": "hello"})

# --- WorkIQ shape: the room is in a url and the body is a JSON string ---------
WORKIQ = "workiq-create_entity"


def workiq_args(room_id, content):
    return {"parentUrl": "/me/chats/%s/messages" % room_id,
            "jsonBody": json.dumps({"body": {"contentType": "html", "content": content}})}


case("workiq post to an unknown room is denied", "deny",
     config(), WORKIQ, workiq_args("19:never-seen", "hello"))
case("workiq post to an open room is allowed", "allow",
     config(), WORKIQ, workiq_args("19:room-open", "hello"))
case("workiq post to a closed room is denied", "deny",
     config(room={"entryGate": "closed"}), WORKIQ, workiq_args("19:room-open", "hello"))
case("workiq first post must be the introduction", "deny",
     config(room={"introducedAt": None}), WORKIQ, workiq_args("19:room-open", "hello"))
case("workiq verbatim introduction inside jsonBody is allowed", "allow",
     config(room={"introducedAt": None}), WORKIQ,
     workiq_args("19:room-open", "<p>" + OPEN_ROOM["introduction"] + "</p>"))
case("workiq edit in place is gated like a post", "deny",
     config(room={"entryGate": "closed"}), "workiq-update_entity",
     {"entityUrl": "/me/chats/19:room-open/messages/1789", "jsonBody": "{\"body\":{\"content\":\"x\"}}"})
case("workiq fetch is a read and passes", "allow",
     config(room={"entryGate": "closed"}), "workiq-fetch",
     {"entityUrls": ["/me/chats/19:room-open/messages"]})

# --- introduction stored as the schema's { text, approvedBy, approvedAt } -----
STRUCTURED = {"text": OPEN_ROOM["introduction"], "approvedBy": "owner", "approvedAt": "2026-09-01T09:00:00Z"}
case("structured introduction, verbatim, is allowed", "allow",
     config(room={"introducedAt": None, "introduction": STRUCTURED}), SEND,
     {"chatId": "19:room-open", "content": OPEN_ROOM["introduction"]})
case("structured introduction, other text, is denied", "deny",
     config(room={"introducedAt": None, "introduction": STRUCTURED}), SEND,
     {"chatId": "19:room-open", "content": "hello"})


def main():
    failures = 0
    for name, expected, args, kwargs in CASES:
        decision, reason = run(*args, **kwargs)
        ok = decision == expected
        if not ok:
            failures += 1
        print("%s  %-52s expected=%-5s got=%s" % (
            "PASS" if ok else "FAIL", name, expected, decision))
        if not ok and reason:
            print("      %s" % reason[:160])

    print("\n%d/%d passed" % (len(CASES) - failures, len(CASES)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
