"""Every skill must have a heading and actual content."""

import pathlib
import sys

bad = []
skills = list(pathlib.Path("skills").glob("*/SKILL.md"))

if not skills:
    print("No skills found under skills/*/SKILL.md")
    sys.exit(1)

for skill in skills:
    text = skill.read_text(encoding="utf-8")
    body = text.lstrip()
    if body.startswith("---"):
        _, _, body = body.partition("---")[2].partition("---")
        body = body.lstrip()
    if len(text) < 200 or not body.startswith("#"):
        bad.append(str(skill))

if bad:
    print("Skills missing a heading or too short: " + ", ".join(bad))
    sys.exit(1)

print(f"{len(skills)} skills OK")
