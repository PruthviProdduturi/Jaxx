#!/usr/bin/env python3
"""Jaxx entry-gate enforcement.

A `preToolUse` hook. It turns the positional rails in `jaxx-consent` -- the ones
that depend on recorded config state rather than judgement -- into something that
blocks, rather than something the model is asked to remember.

It enforces exactly four things, and deliberately nothing else:

  1. A room the agent posts in must be listed in `chat.watch`.
  2. That room's `entryGate` must be `open`.
  3. Its `mode` must be `autoreply`; `notes-only` and `draft` post nothing.
  4. While `introducedAt` is null, the approved `introduction` is the only text
     that may go out.

Everything else in the rails -- authority is the sender, containment across
rooms, never reply to another agent -- needs judgement about content, and a
regex would only give the comforting illusion of enforcing it. Those stay in
the skill, where they are honest about needing a reader.

Failure policy. `preToolUse` command hooks are fail-closed: a crash or a
non-zero exit denies the tool call. That makes a buggy hook capable of bricking
the agent entirely, so the two halves are treated differently:

  * Deciding whether this call is even a post -- guarded, and any failure
    allows. A malformed payload on an unrelated tool must never block work.
  * Deciding whether a post is permitted -- once we know it IS a post, any
    failure denies. Every room starts closed, so "I could not tell" resolves
    to no.
"""

import json
import os
import re
import sys

ROOM_ID_KEYS = (
    "chatid", "chat_id", "channelid", "channel_id", "conversationid",
    "conversation_id", "roomid", "room_id", "threadid", "thread_id", "to",
)

BODY_KEYS = (
    "content", "body", "message", "text", "html", "messagebody",
)

DEFAULT_POST_TOOL_PATTERN = (
    r".*(send|post|reply|create).*(message|chat|mail|post|comment).*"
    r"|.*(message|chat|mail).*(send|post|create|reply).*"
)

POSTABLE_MODE = "autoreply"


def emit(decision, reason=None):
    out = {"permissionDecision": decision}
    if reason:
        out["permissionDecisionReason"] = reason
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


def allow():
    emit("allow")


def deny(reason):
    emit("deny", "Blocked by the Jaxx entry gate. " + reason)


def walk(obj):
    """Yield every (lowercased key, value) pair anywhere in a nested payload."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield str(key).lower(), value
            for pair in walk(value):
                yield pair
    elif isinstance(obj, list):
        for item in obj:
            for pair in walk(item):
                yield pair


def first_match(payload, keys):
    for key, value in walk(payload):
        if key in keys and isinstance(value, str) and value.strip():
            return value.strip()
    return None


def normalise(text):
    """Compare introduction wording without being defeated by HTML wrapping."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def load_config():
    """Return (state, config) where state is 'absent', 'broken' or 'ok'.

    Absent and broken are very different answers. No config means Jaxx was
    never set up here and the hook should stay out of the way. A config that
    exists but will not parse is the file that defines the rails being
    unreadable -- that must never resolve to 'post freely'.
    """
    root = os.environ.get("COPILOT_PROJECT_DIR") or os.getcwd()
    path = os.path.join(root, "agent.config.json")
    if not os.path.isfile(path):
        return "absent", None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return "ok", json.load(handle)
    except Exception:
        return "broken", None


def main():
    # --- Guarded half: is this a post at all? Any failure here allows. ------
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        tool_name = payload.get("toolName") or payload.get("tool_name") or ""
        tool_args = payload.get("toolArgs")
        if tool_args is None:
            tool_args = payload.get("tool_input")
        if tool_args is None:
            tool_args = {}

        state, config = load_config()
        if state == "absent":
            allow()  # Jaxx is not configured here; not this hook's business.

        chat = (config or {}).get("chat") or {}
        enforcement = chat.get("enforcement") or {}

        if state == "ok" and enforcement.get("enabled") is False:
            allow()

        pattern = enforcement.get("postToolPattern") or DEFAULT_POST_TOOL_PATTERN
        if not re.fullmatch(pattern, tool_name, re.IGNORECASE):
            allow()

        # A posting-shaped tool carrying no room id is a read or a search.
        room_id = first_match(tool_args, ROOM_ID_KEYS)
        if not room_id:
            allow()
    except SystemExit:
        raise
    except Exception:
        allow()

    # --- Committed half: this IS a post. Any failure here denies. -----------
    try:
        if state == "broken":
            deny(
                "agent.config.json exists but could not be parsed, so no entry "
                "gate could be read. The file that defines the rails being "
                "unreadable is not permission to post."
            )

        watch = chat.get("watch") or []
        exclusions = chat.get("readExclusions") or []

        for item in exclusions:
            excluded = item.get("id") if isinstance(item, dict) else item
            if excluded and str(excluded) == room_id:
                deny(
                    "Room %s is in chat.readExclusions. Entry there was revoked, "
                    "and only the owner can restore it." % room_id
                )

        room = None
        for item in watch:
            if isinstance(item, dict) and str(item.get("id") or "") == room_id:
                room = item
                break

        if room is None:
            deny(
                "Room %s is not in chat.watch. Every room starts closed, so a "
                "room with no recorded entry decision is one the agent has "
                "never been let into." % room_id
            )

        name = room.get("name") or room_id

        if (room.get("entryGate") or "closed") != "open":
            deny(
                "The entry gate for %s is closed. Only the owner opens a gate, "
                "and until then nothing is posted there -- not an introduction, "
                "not an acknowledgement, not a refusal." % name
            )

        mode = room.get("mode") or "notes-only"
        if mode != POSTABLE_MODE:
            deny(
                "%s is at mode '%s', which posts nothing. 'notes-only' reads and "
                "records; 'draft' composes and shows the owner. Only 'autoreply' "
                "may post, and promotion is the owner's decision." % (name, mode)
            )

        if not room.get("introducedAt"):
            approved = room.get("introduction")
            if not approved:
                deny(
                    "Entry to %s was approved but the introduction wording was "
                    "not. Post nothing and ask the owner for the exact text."
                    % name
                )
            outgoing = first_match(tool_args, BODY_KEYS)
            if not outgoing or normalise(outgoing) != normalise(approved):
                deny(
                    "The first post in %s must be the approved introduction, "
                    "verbatim. Send chat.watch[].introduction unchanged, then "
                    "record introducedAt." % name
                )
    except SystemExit:
        raise
    except Exception as exc:
        deny(
            "The gate could not be verified (%s: %s), and an unverified room is "
            "a closed one." % (type(exc).__name__, exc)
        )

    allow()


if __name__ == "__main__":
    main()
