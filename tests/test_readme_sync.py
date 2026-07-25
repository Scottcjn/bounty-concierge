# SPDX-License-Identifier: MIT
"""Tests for README auto-sync from bounty_index.json."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import concierge.readme_sync as rs


SAMPLE_BOUNTIES = [
    {
        "repo": "Scottcjn/rustchain-bounties",
        "number": 504,
        "title": "Prometheus Metrics Exporter + Grafana",
        "url": "https://github.com/Scottcjn/rustchain-bounties/issues/504",
        "reward_rtc": 40.0,
        "difficulty": "standard",
        "skills": ["ci/cd", "documentation"],
    },
    {
        "repo": "Scottcjn/Rustchain",
        "number": 123,
        "title": "Very | tricky | pipes | in | titles",
        "url": "https://github.com/Scottcjn/Rustchain/issues/123",
        "reward_rtc": 12.5,
        "difficulty": "standard",
        "skills": [],
    },
    {
        "repo": "Scottcjn/bounty-concierge",
        "number": 39,
        "title": "Very long title that absolutely must be truncated at sixty characters now",
        "url": "https://github.com/Scottcjn/bounty-concierge/issues/39",
        "reward_rtc": 0.0,
        "difficulty": "micro",
        "skills": ["documentation"],
    },
]


def test_render_table_sorts_by_reward_then_number():
    table = rs.render_table(SAMPLE_BOUNTIES, top_n=10)
    rows = [l for l in table.splitlines() if l.startswith("|") and not l.startswith("|-") and "Issue" not in l and "Repo" not in l]
    # Highest reward first (40 > 12.5 > 0)
    assert "Prometheus" in rows[0]
    assert "Very \| tricky" in rows[1]  # pipes escaped in markdown
    # Pipes in titles get escaped
    assert "\\|" in rows[1]
    # Long titles truncated to 60 chars + ellipsis
    assert "..." in rows[2]
    # Zero rewards render as integer "0", not "0.0"
    assert "| 0 | micro |" in rows[2]


def test_render_table_caps_to_top_n():
    table = rs.render_table(SAMPLE_BOUNTIES, top_n=2)
    rows = [l for l in table.splitlines() if l.startswith("|") and not l.startswith("|-") and "Issue" not in l and "Repo" not in l]
    assert len(rows) == 2


def test_update_readme_replaces_between_sentinels():
    original = (
        "Header\n\n"
        + rs.START_MARKER + "\nOLD CONTENT\n" + rs.END_MARKER + "\n\nFooter"
    )
    new = rs.update_readme(original, "NEW SECTION")
    assert "OLD CONTENT" not in new
    assert "NEW SECTION" in new
    assert "Header" in new and "Footer" in new


def test_update_readme_raises_when_sentinels_missing():
    bad = "No sentinels here."
    try:
        rs.update_readme(bad, "anything")
    except ValueError as e:
        assert "missing" in str(e).lower()
        return
    assert False, "expected ValueError"


def test_build_section_reads_real_index_file():
    """Smoke check: build_section must read the on-disk JSON without raising."""
    index_path = rs.INDEX_PATH
    if not index_path.exists():
        # CI may not have the workflow run yet — synthesize a tiny index.
        tmp = index_path.parent
        tmp.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps({
            "updated_at": "2026-07-25T00:00:00+00:00",
            "total_count": len(SAMPLE_BOUNTIES),
            "bounties": SAMPLE_BOUNTIES,
        }))
    section = rs.build_section(top_n=3)
    assert "open bounties" in section
    # At least one row with a number link present
    assert "[#" in section and "](https://" in section  # markdown issue link


def test_main_dry_run_path(tmp_path, monkeypatch):
    """Running main with a tiny synthesized index should not raise."""
    fake_index = tmp_path / "data" / "bounty_index.json"
    fake_index.parent.mkdir(parents=True)
    fake_index.write_text(json.dumps({
        "updated_at": "2026-07-25T00:00:00+00:00",
        "total_count": 1,
        "bounties": [SAMPLE_BOUNTIES[0]],
    }))
    fake_readme = tmp_path / "README.md"
    fake_readme.write_text(
        "intro\n\n" + rs.START_MARKER + "\nold\n" + rs.END_MARKER + "\noutro"
    )
    monkeypatch.setattr(rs, "INDEX_PATH", fake_index)
    monkeypatch.setattr(rs, "README_PATH", fake_readme)
    rc = rs.main([])
    assert rc == 0
    updated = fake_readme.read_text()
    assert "Prometheus" in updated
    assert "old" not in updated
