"""Tests for skill-based bounty matching."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import skill_matcher


class TestNormaliseTags:
    """Tests for skill tag configuration normalization."""

    def test_structured_entries_include_skill_aliases_and_labels(self):
        raw = {
            "python": {
                "aliases": ["py", "PY"],
                "bounty_labels": ["backend", "python"],
            }
        }

        result = skill_matcher._normalise_tags(raw)

        assert result["python"] == ["python", "py", "backend"]

    def test_list_entries_are_preserved(self):
        raw = {"docs": ["readme", "guide"]}

        result = skill_matcher._normalise_tags(raw)

        assert result == {"docs": ["readme", "guide"]}

    def test_unexpected_entry_type_falls_back_to_skill_name(self):
        raw = {"testing": "pytest"}

        result = skill_matcher._normalise_tags(raw)

        assert result == {"testing": ["testing"]}


class TestBountyText:
    """Tests for searchable bounty text construction."""

    def test_combines_title_body_labels_and_difficulty_lowercase(self):
        bounty = {
            "title": "Write Pytest Tests",
            "body": "Cover Python helpers",
            "labels": ["Testing", "Backend"],
            "difficulty": "Easy",
        }

        text = skill_matcher._bounty_text(bounty)

        assert "write pytest tests" in text
        assert "cover python helpers" in text
        assert "testing backend" in text
        assert "easy" in text

    def test_missing_fields_produce_empty_text(self):
        assert skill_matcher._bounty_text({}).strip() == ""


class TestMatchSkills:
    """Tests for skill match scoring."""

    def test_empty_skills_score_zero(self):
        bounty = {"title": "Python pytest task"}

        assert skill_matcher.match_skills(bounty, []) == 0.0

    def test_empty_bounty_text_scores_zero(self):
        assert skill_matcher.match_skills({}, ["python"]) == 0.0

    def test_known_skill_matches_loaded_keywords(self):
        bounty = {"title": "Add python backend tests"}

        assert skill_matcher.match_skills(bounty, ["python"]) == 1.0

    def test_unknown_skill_uses_skill_name_as_keyword(self):
        bounty = {"body": "Needs wasm packaging documentation"}

        assert skill_matcher.match_skills(bounty, ["wasm"]) == 1.0

    def test_multiple_skills_return_fractional_score(self):
        bounty = {"title": "Add pytest coverage", "labels": ["testing"]}

        assert skill_matcher.match_skills(bounty, ["testing", "frontend"]) == 0.5


class TestRecommend:
    """Tests for ranked bounty recommendations."""

    def test_recommend_sorts_by_match_score_and_respects_limit(self):
        bounties = [
            {"id": 1, "title": "Write docs guide"},
            {"id": 2, "title": "Add python pytest coverage"},
            {"id": 3, "title": "Frontend CSS polish"},
        ]

        result = skill_matcher.recommend(bounties, ["python", "testing"], limit=2)

        assert [item["id"] for item in result] == [2, 1]
        assert result[0]["match_score"] == 1.0
        assert result[1]["match_score"] == 0.0

    def test_recommend_copies_bounties_instead_of_mutating_input(self):
        bounties = [{"id": 1, "title": "Python task"}]

        result = skill_matcher.recommend(bounties, ["python"])

        assert result[0] is not bounties[0]
        assert "match_score" in result[0]
        assert "match_score" not in bounties[0]

    def test_zero_limit_returns_empty_list(self):
        bounties = [{"id": 1, "title": "Python task"}]

        assert skill_matcher.recommend(bounties, ["python"], limit=0) == []
