#!/usr/bin/env python3
"""
Generate a PyPI-safe version of the README.

Converts GitHub-style admonitions ([!NOTE], [!TIP], [!WARNING], [!IMPORTANT], [!CAUTION])
into emoji blockquotes that render cleanly on PyPI, e.g.:

> 📝 **Note**
>
> Content...
"""

from pathlib import Path
import re
import sys

# Paths (adjust if needed)
SRC = Path(__file__).resolve().parents[1] / "README.md"
DST = SRC.with_name("README-pypi.md")

ADMO_MAP = {
    "NOTE": ("📝", "Note"),
    "TIP": ("💡", "Tip"),
    "WARNING": ("⚠️", "Warning"),
    "IMPORTANT": ("❗", "Important"),
    "CAUTION": ("⚠️", "Caution"),
}

# Regexes (note: use raw strings r'...' and do NOT double-escape backslashes)
RE_ADMO_START = re.compile(r'^\s*>\s*\[!([A-Za-z]+)\]\s*$')  # e.g. "> [!NOTE]"
RE_IS_QUOTED  = re.compile(r'^\s*>')                        # any line starting with ">"

def convert(text: str) -> str:
    lines = text.splitlines()
    out = []
    i = 0

    while i < len(lines):
        line = lines[i]
        m = RE_ADMO_START.match(line)
        if m:
            kind = m.group(1).upper()
            emoji, title = ADMO_MAP.get(kind, ("📝", kind.title()))

            # Collect subsequent quoted lines (content), stripping one leading ">"
            i += 1
            content_lines = []
            while i < len(lines) and RE_IS_QUOTED.match(lines[i]):
                ln = lines[i]
                # Strip exactly one leading quote marker and one optional space
                ln = re.sub(r'^\s*>\s?', '', ln)
                content_lines.append(ln)
                i += 1

            # Emit PyPI-friendly block
            out.append(f"> {emoji} **{title}**")
            out.append(">")
            if content_lines:
                for c in content_lines:
                    out.append(f"> {c}")
            else:
                out.append("> ")
            out.append("")  # blank line after the block
            continue

        # Not an admonition start; pass through
        out.append(line)
        i += 1

    return "\n".join(out) + "\n"


if __name__ == "__main__":
    if not SRC.exists():
        print(f"ERROR: README not found at {SRC}", file=sys.stderr)
        sys.exit(1)
    text = SRC.read_text(encoding="utf-8")
    DST.write_text(convert(text), encoding="utf-8")
    print(f"Wrote {DST}")
