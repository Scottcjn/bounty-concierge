# SPDX-License-Identifier: MIT
"""Refresh the Open Bounties table in README.md from data/bounty_index.json.

The bounty_index_sync workflow writes ``data/bounty_index.json`` once a day,
but README.md's "Open Bounties" table is hand-curated and drifts out of
date. This module rewrites the table from the JSON between sentinel
markers so the README's headline numbers stay current without manual edits.

Sentinels used in README.md:

    <!-- BOUNTY-TABLE-START -->
    ...auto-generated content lives here...
    <!-- BOUNTY-TABLE-END -->

Run as a script::

    python -m concierge.readme_sync

Returns exit code 0 on success, 1 if sentinels are missing or the JSON
file cannot be read.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Iterable

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
INDEX_PATH = REPO_ROOT / "data" / "bounty_index.json"

START_MARKER = "<!-- BOUNTY-TABLE-START -->"
END_MARKER = "<!-- BOUNTY-TABLE-END -->"

# Cap to keep the README readable. Sorted by reward_rtc desc, then number.
DEFAULT_TOP_N = 10


def _format_int(n: float) -> str:
    """Render an RTC reward without trailing .0."""
    if n == int(n):
        return str(int(n))
    return f"{n:.1f}"


def render_table(bounties: Iterable[dict], top_n: int = DEFAULT_TOP_N) -> str:
    """Return a markdown table from a sequence of bounty dicts."""
    sorted_bounties = sorted(
        bounties,
        key=lambda b: (-(b.get("reward_rtc") or 0), b.get("number", 0)),
    )
    rows = sorted_bounties[:top_n]

    lines = [
        "| Repo | Issue | Title | RTC | Difficulty | Skills |",
        "|------|-------|-------|-----|------------|--------|",
    ]
    for b in rows:
        repo_short = (b.get("repo") or "").split("/")[-1]
        issue_num = b.get("number", "?")
        url = b.get("url") or f"https://github.com/{b.get('repo', '')}/issues/{issue_num}"
        title = (b.get("title") or "").strip().replace("|", "\\|")
        if len(title) > 60:
            title = title[:57] + "..."
        rtc = _format_int(b.get("reward_rtc") or 0)
        diff = b.get("difficulty") or "unknown"
        skills = ", ".join(b.get("skills") or []) or "-"
        lines.append(
            f"| {repo_short} | "
            f"[#{issue_num}]({url}) | "
            f"{title} | "
            f"{rtc} | {diff} | {skills} |"
        )
    return "\n".join(lines)


def build_section(top_n: int = DEFAULT_TOP_N) -> str:
    """Build the markdown that goes between the sentinels.

    Reads ``data/bounty_index.json`` and produces a header line plus the
    table. Raises FileNotFoundError if the JSON is missing.
    """
    payload = json.loads(INDEX_PATH.read_text())
    bounties = payload.get("bounties") or []
    updated = payload.get("updated_at", "unknown")
    table = render_table(bounties, top_n=top_n)
    header = (
        f"_Showing top {min(top_n, len(bounties))} open bounties, "
        f"sorted by RTC reward. Index rebuilt {updated}. For the live total, use the full bounty board link above._"
    )
    return f"{header}\n\n{table}"


def update_readme(readme_text: str, section: str) -> str:
    """Replace the contents between the sentinels with ``section``.

    Returns the updated text. Raises ValueError if either sentinel is
    missing.
    """
    pattern = re.compile(
        re.escape(START_MARKER) + r"(.*?)" + re.escape(END_MARKER),
        re.DOTALL,
    )
    match = pattern.search(readme_text)
    if not match:
        raise ValueError(
            f"README is missing the {START_MARKER} / {END_MARKER} sentinels. "
            "Add them around the Open Bounties table."
        )
    new_block = f"{START_MARKER}\n{section}\n{END_MARKER}"
    return pattern.sub(new_block, readme_text)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    top_n = DEFAULT_TOP_N
    if "--top" in argv:
        i = argv.index("--top")
        try:
            top_n = int(argv[i + 1])
        except (ValueError, IndexError):
            print("error: --top expects an integer", file=sys.stderr)
            return 2

    if not INDEX_PATH.exists():
        print(f"error: {INDEX_PATH} not found", file=sys.stderr)
        return 1

    try:
        section = build_section(top_n=top_n)
    except (OSError, ValueError) as exc:
        print(f"error: failed to build section: {exc}", file=sys.stderr)
        return 1

    try:
        original = README_PATH.read_text()
        updated = update_readme(original, section)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if updated != original:
        README_PATH.write_text(updated)
        print(f"updated {README_PATH}")
    else:
        print(f"{README_PATH} already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
