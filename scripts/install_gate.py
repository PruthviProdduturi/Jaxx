#!/usr/bin/env python3
"""Install the Jaxx entry gate as a hook.

Copilot CLI loads hooks from `~/.copilot/hooks/*.json`. Plugin-contributed
hooks are described in the CLI docs but do not fire on the builds tested
(1.0.86), so the gate is installed deliberately by the owner rather than
switched on by installing the plugin. That is the right shape for Jaxx anyway:
nothing about this agent self-activates.

    python scripts/install_gate.py            # install or refresh
    python scripts/install_gate.py --remove   # take it back off
    python scripts/install_gate.py --print    # show what would be written
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "hooks", "jaxx_gate.py")

# Broad on purpose. A false positive costs one subprocess that returns allow;
# a false negative is a post that skipped the gate entirely. `entity` is here
# because WorkIQ posts through create_entity/update_entity on a chat url --
# a tool name with none of the other words in it.
MATCHER = r".*(chat|message|mail|post|send|teams|graph|slack|reply|comment|entity).*"


def hooks_dir():
    home = os.environ.get("COPILOT_HOME") or os.path.join(
        os.path.expanduser("~"), ".copilot")
    return os.path.join(home, "hooks")


def payload():
    return {
        "version": 1,
        "hooks": {
            "preToolUse": [
                {
                    "type": "command",
                    "matcher": MATCHER,
                    # exec/args runs the interpreter directly. A `command`
                    # string is copied into `powershell` on Windows, where a
                    # leading quoted path parses as a string literal rather
                    # than a command -- and because preToolUse is fail-closed,
                    # that misparse denies every matching tool with no reason
                    # attached.
                    "exec": sys.executable,
                    "args": [GATE],
                    "timeoutSec": 20,
                }
            ]
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--print", dest="show", action="store_true")
    args = parser.parse_args()

    target = os.path.join(hooks_dir(), "jaxx-gate.json")

    if args.show:
        print(json.dumps(payload(), indent=2))
        return 0

    if args.remove:
        if os.path.isfile(target):
            os.remove(target)
            print("Entry gate removed: %s" % target)
        else:
            print("Entry gate was not installed.")
        return 0

    if not os.path.isfile(GATE):
        print("Cannot find %s" % GATE, file=sys.stderr)
        return 1

    os.makedirs(hooks_dir(), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(payload(), handle, indent=2)

    print("Entry gate installed: %s" % target)
    print("Enforcing: %s" % GATE)
    print()
    print("It denies a post when the room is not in chat.watch, the entryGate")
    print("is not open, the mode is not autoreply, or the approved")
    print("introduction has not been sent yet. Everything else is allowed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
