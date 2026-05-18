"""Unit tests for bounty skill matching and recommendation ranking."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import skill_matcher


class TestNormaliseTags:
    def test_flat_list_entries_are_preserved(self):
        raw = {"python": ["pytest", "flask"]}

        assert skill_matcher._normalise_tags(raw) == {"python": ["pytest", "flask"]}

    def test_structured_entries_include_skill_aliases_and_labels(self):
        raw = {
            "python": {
                "aliases": ["py", "python"],
                "bounty_labels": ["backend", "pytest", "py"],
            }
        }

        result = skill_matcher._normalise_tags(raw)

        assert result["python"] == ["python", "py", "backend", "pytest"]

    def test_invalid_entry_falls_back_to_skill_name(self):
        assert skill_matcher._normalise_tags({"rust": "cargo"}) == {"rust": ["rust"]}


class TestMatchSkills:
    def test_empty_skills_return_zero_score(self):
        bounty = {"title": "Python tests", "body": "pytest needed"}

        assert skill_matcher.match_skills(bounty, []) == 0.0

    def test_empty_bounty_text_returns_zero_score(self):
        assert skill_matcher.match_skills({}, ["python"]) == 0.0

    def test_known_skill_matches_title_body_labels_and_difficulty(self):
        bounty = {
            "title": "Write unit coverage",
            "body": "Use pytest for API helpers",
            "labels": ["testing"],
            "difficulty": "standard",
        }

        assert skill_matcher.match_skills(bounty, ["python", "testing"]) == 1.0

    def test_unknown_skill_uses_skill_name_as_keyword(self):
        bounty = {"title": "Need cobol parser", "body": "", "labels": [], "difficulty": ""}

        assert skill_matcher.match_skills(bounty, ["cobol"]) == 1.0

    def test_partial_match_scores_fraction_of_requested_skills(self):
        bounty = {"title": "Docker deployment", "body": "", "labels": [], "difficulty": ""}

        assert skill_matcher.match_skills(bounty, ["docker", "security"]) == 0.5


class TestRecommend:
    def test_recommend_adds_match_score_without_mutating_originals(self):
        bounties = [
            {"title": "Python API", "body": "", "labels": [], "difficulty": ""},
            {"title": "Write docs", "body": "", "labels": [], "difficulty": ""},
        ]

        result = skill_matcher.recommend(bounties, ["python"], limit=2)

        assert result[0]["match_score"] == 1.0
        assert result[0]["title"] == "Python API"
        assert "match_score" not in bounties[0]

    def test_recommend_sorts_by_score_descending_and_applies_limit(self):
        bounties = [
            {"title": "General issue", "body": "", "labels": [], "difficulty": ""},
            {"title": "Python security tests", "body": "pytest audit", "labels": [], "difficulty": ""},
            {"title": "Docker task", "body": "", "labels": [], "difficulty": ""},
        ]

        result = skill_matcher.recommend(bounties, ["python", "security"], limit=2)

        assert [item["title"] for item in result] == [
            "Python security tests",
            "General issue",
        ]
        assert len(result) == 2

    def test_recommend_with_zero_limit_returns_empty_list(self):
        result = skill_matcher.recommend(
            [{"title": "Python", "body": "", "labels": [], "difficulty": ""}],
            ["python"],
            limit=0,
        )

        assert result == []
