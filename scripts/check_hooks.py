#!/usr/bin/env python3
"""Check the entry gate is wired correctly.

A `preToolUse` hook is fail-closed: if it crashes, the tool call is denied.
So a gate with a syntax error does not fail quietly in the corner -- it blocks
every posting tool with no usable reason attached. That makes these checks
worth running in CI rather than discovering at post time.
"""

import ast
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "hooks", "jaxx_gate.py")
TEMPLATE = os.path.join(ROOT, "agent.config.template.json")

failures = []


def check(label, ok, detail=""):
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else " -- " + detail))
    if not ok:
        failures.append(label)


# The gate must exist and parse. A SyntaxError here denies every post.
if not os.path.isfile(GATE):
    check("hooks/jaxx_gate.py exists", False, "missing")
else:
    try:
        with open(GATE, "r", encoding="utf-8") as handle:
            ast.parse(handle.read())
        check("hooks/jaxx_gate.py parses", True)
    except SyntaxError as exc:
        check("hooks/jaxx_gate.py parses", False, str(exc))

# The template must describe the settings the gate reads, or the gate silently
# falls back to defaults the owner never saw.
with open(TEMPLATE, "r", encoding="utf-8") as handle:
    chat = json.load(handle).get("chat", {})

enforcement = chat.get("enforcement")
check("chat.enforcement is present", isinstance(enforcement, dict))
if isinstance(enforcement, dict):
    check("chat.enforcement.enabled is a bool",
          isinstance(enforcement.get("enabled"), bool))
    check("chat.enforcement.postToolPattern is present",
          "postToolPattern" in enforcement)
check("chat.enforcement is explained",
      isinstance(chat.get("$comment_enforcement"), str))

# The behaviour itself. If these ever stop holding, the gate is decorative.
if os.path.isfile(GATE):
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "test_gate.py")],
        capture_output=True, text=True)
    check("entry gate test suite passes", proc.returncode == 0,
          proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "")

if failures:
    print("\n%d check(s) failed" % len(failures))
    sys.exit(1)
print("\nEntry gate wiring OK")
