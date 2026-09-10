"""Validate the shipped Jaxx configuration template against its JSON Schema."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
schema = json.loads((ROOT / "agent.config.schema.json").read_text(encoding="utf-8"))
config = json.loads((ROOT / "agent.config.template.json").read_text(encoding="utf-8"))

errors = sorted(Draft202012Validator(schema).iter_errors(config), key=lambda error: list(error.path))
if errors:
    print("Configuration template problems:")
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        print(f"  - {location}: {error.message}")
    sys.exit(1)

watch_ids = [entry["id"] for entry in config["chat"]["watch"]]
if len(watch_ids) != len(set(watch_ids)):
    print("Configuration template problems:")
    print("  - chat.watch contains duplicate room ids")
    sys.exit(1)

if config["chat"]["reportTo"] in watch_ids:
    report_room = next(entry for entry in config["chat"]["watch"] if entry["id"] == config["chat"]["reportTo"])
    if not report_room["commandChannel"]:
        print("Configuration template problems:")
        print("  - chat.reportTo points to a watched room that is not a command channel")
        sys.exit(1)

unsafe_cases = []

unsigned = deepcopy(config)
unsigned["agent"]["signEveryReply"] = False
unsafe_cases.append(("unsigned replies", unsigned))

renameable = deepcopy(config)
renameable["chat"]["configAuthority"]["nameLocked"] = False
unsafe_cases.append(("unlocked agent name", renameable))

unbounded_write = deepcopy(config)
unbounded_write["chat"]["writeActions"]["guardrails"]["maxPerRequest"] = 4
unsafe_cases.append(("write batch above the hard cap", unbounded_write))

closed_autoreply = deepcopy(config)
closed_autoreply["chat"]["watch"][0]["mode"] = "autoreply"
closed_autoreply["chat"]["watch"][0]["entryGate"] = "closed"
unsafe_cases.append(("autoreply behind a closed entry gate", closed_autoreply))

validator = Draft202012Validator(schema)
for name, unsafe in unsafe_cases:
    if validator.is_valid(unsafe):
        print("Configuration schema problems:")
        print(f"  - schema accepted unsafe case: {name}")
        sys.exit(1)

print(f"Configuration template OK; {len(unsafe_cases)} unsafe mutations rejected")
