"""Fail when a local Markdown or HTML link points to a missing packaged file."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)")
HTML_LINK = re.compile(r"(?:href|src)=[\"']([^\"']+)[\"']", re.IGNORECASE)
FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]+`")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)


def references(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".md":
        text = INLINE_CODE.sub("", FENCED_CODE.sub("", text))
        return MARKDOWN_LINK.findall(text)
    return HTML_LINK.findall(text)


missing: list[tuple[Path, str]] = []
for document in [*ROOT.rglob("*.md"), *ROOT.rglob("*.html")]:
    for reference in references(document):
        target_text = unquote(reference.split("#", 1)[0].strip("<>"))
        if not target_text or EXTERNAL.match(target_text):
            continue
        target = (
            ROOT / target_text.lstrip("/")
            if target_text.startswith("/")
            else document.parent / target_text
        )
        if not target.resolve().exists():
            missing.append((document.relative_to(ROOT), reference))

if missing:
    for document, reference in missing:
        print(f"{document}: missing local target {reference}")
    sys.exit(1)

print("Documentation links OK")
