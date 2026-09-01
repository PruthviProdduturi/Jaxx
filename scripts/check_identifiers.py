"""Fail if anything that looks like a real identifier is committed.

This repo is documentation for a pattern, not a deployment. Tenant ids, chat ids,
object GUIDs, corporate addresses and local paths have no business here — in prose,
in examples, or in sample tables. Use placeholders and invented names.
"""

import pathlib
import re
import sys

PATTERNS = {
    "Teams chat id": re.compile(r"19:[0-9a-zA-Z_\-]{10,}@"),
    "Teams meeting id": re.compile(r"19:meeting_"),
    "bare GUID": re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I
    ),
    "absolute local path": re.compile(r"\b[A-Z]:\\(?:Users|Repos)\\", re.I),
    "real-looking email": re.compile(r"[\w.\-]+@[\w\-]+\.(?:com|net|org)\b"),
    # Vendor-time metadata for a private marketplace must not ride along here: the
    # URLs resolve for nobody outside it, and the comments around them tend to
    # describe that marketplace's internal review process. Matched structurally, so
    # this file does not itself name the thing it is keeping out.
    "private schema host": re.compile(
        r"raw\.githubusercontent\.com/[^/\s\"]+/\.github-private|\.github-private\b"
    ),
}

# Placeholders, null GUIDs and well-known public hosts are fine.
ALLOW = re.compile(
    r"00000000-0000-0000-0000-000000000000"
    r"|<[A-Za-z_]+>"
    r"|\{\{[^}]+\}\}"
    r"|example\.(?:com|org|net)"
    r"|contoso\."
    r"|adaptivecards\.io"
    r"|schemas?\."
    r"|noreply\.github\.com"
    r"|users\.noreply\.",
    re.I,
)

SUFFIXES = {".md", ".json", ".yml", ".yaml", ".html", ".txt", ".py"}

# ALLOW exists to silence placeholder noise, but it matches whole lines — a line
# mentioning "schema." was skipping every check, which is how a private $schema URL
# got through review. These labels are never waived.
NEVER_WAIVED = {"private schema host"}

failures = []
for path in sorted(pathlib.Path(".").rglob("*")):
    if not path.is_file() or ".git/" in path.as_posix():
        continue
    if path.suffix.lower() not in SUFFIXES:
        continue
    if path.name == "check_identifiers.py":
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for lineno, line in enumerate(text.splitlines(), 1):
        waived = ALLOW.search(line)
        for label, pattern in PATTERNS.items():
            if waived and label not in NEVER_WAIVED:
                continue
            if pattern.search(line):
                failures.append(f"{path}:{lineno}  [{label}]  {line.strip()[:120]}")

if failures:
    print("Possible real identifiers found. Replace them with placeholders:\n")
    print("\n".join(failures))
    sys.exit(1)

print("No real identifiers found")
