# SPDX-License-Identifier: MIT
"""README refresh must preserve generated text without regex substitution."""
import json

import pytest

from concierge import readme_sync


@pytest.mark.parametrize("title", [r"Windows C:\tools\new build", r"Document regex \g<1>"])
def test_main_preserves_title_backslashes_and_is_idempotent(title, tmp_path, monkeypatch):
    index_path = tmp_path / "bounty_index.json"
    readme_path = tmp_path / "README.md"
    index_path.write_text(json.dumps({
        "updated_at": "2026-09-08T00:00:00Z",
        "bounties": [{
            "repo": "example/project",
            "number": 1,
            "title": title,
            "reward_rtc": 10,
            "skills": ["documentation"],
        }],
    }))
    readme_path.write_text(
        "Intro\n" + readme_sync.START_MARKER + "\nOld table\n"
        + readme_sync.END_MARKER + "\nFooter\n"
    )
    monkeypatch.setattr(readme_sync, "INDEX_PATH", index_path)
    monkeypatch.setattr(readme_sync, "README_PATH", readme_path)

    assert readme_sync.main([]) == 0
    updated = readme_path.read_text()
    assert title in updated
    assert "Old table" not in updated
    assert updated.startswith("Intro\n") and updated.endswith("\nFooter\n")
    assert readme_sync.main([]) == 0
    assert readme_path.read_text() == updated
