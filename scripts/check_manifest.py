"""Validate the plugin manifest.

Two things get checked:

1. plugin.json against the Agent Plugins 1.0.0 manifest schema. That schema sets
   additionalProperties:false, so declaring components here (skills, commands,
   hooks, agents) is invalid — they are discovered by folder convention. The
   allowed keys and the name pattern are mirrored below so this runs offline.

2. agency.json, if present. It is vendor-time metadata, added when this plugin is
   copied into a marketplace, and is deliberately absent from this repo. When it
   does exist, engines must stay consistent with where the manifest lives:
   engines ["copilot"] means one manifest, at the plugin root, and no
   Claude-shaped folder.
"""

import json
import os
import re
import sys

MANIFEST = "plugin.json"
SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"

ALLOWED = {
    "$schema", "name", "version", "description", "author",
    "homepage", "repository", "license", "keywords", "extensions",
}
# Lowercase only. A capitalised display name belongs in the README, not here.
NAME_PATTERN = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
CONVENTION_DIRS = ("skills", "commands", "agents", "hooks")

problems = []

if not os.path.exists(MANIFEST):
    print(f"Missing {MANIFEST} at the plugin root")
    sys.exit(1)

manifest = json.load(open(MANIFEST, encoding="utf-8"))

if manifest.get("$schema") != SCHEMA_ID:
    problems.append(f"plugin.json $schema must be exactly {SCHEMA_ID}")

for key in sorted(set(manifest) - ALLOWED):
    problems.append(
        f"plugin.json key '{key}' is not in the Agent Plugins schema "
        "(additionalProperties is false; components are discovered by folder)"
    )

# Marketplace validation requires these three on top of the schema.
for field in ("version", "description", "author"):
    if not manifest.get(field):
        problems.append(f"plugin.json is missing required field: {field}")

name = manifest.get("name", "")
if not NAME_PATTERN.match(name):
    problems.append(f"plugin.json name {name!r} must match {NAME_PATTERN.pattern}")

if set(manifest.get("author", {})) - {"name", "email", "url"}:
    problems.append("plugin.json author allows only name, email and url")

for directory in CONVENTION_DIRS:
    if os.path.isdir(directory) and not os.listdir(directory):
        problems.append(f"{directory}/ exists but is empty")

# agency.json is optional here by design: it is added when the plugin is vendored
# into a marketplace, not carried in this repo. Validate it only if it is present.
if os.path.exists("agency.json"):
    agency = json.load(open("agency.json", encoding="utf-8"))
    if not agency.get("category"):
        problems.append("agency.json is missing 'category'")
    if not agency.get("authors"):
        problems.append("agency.json is missing 'authors'")
    if agency.get("engines") == ["copilot"]:
        for stray in (".claude-plugin/plugin.json", ".github/plugin/plugin.json"):
            if os.path.exists(stray):
                problems.append(
                    f"engines is ['copilot'] but {stray} also exists — "
                    "ship exactly one manifest, at the plugin root"
                )

if problems:
    print("Manifest problems:")
    print("\n".join(f"  - {p}" for p in problems))
    sys.exit(1)

print(f"Manifest OK (plugin name: {name})")
