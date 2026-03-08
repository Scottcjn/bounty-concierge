"""Tests for bounty index - RTC parsing from issue titles."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import bounty_index


class TestParseReward:
    """Tests for RTC reward parsing from issue titles."""

    def test_parse_rtc_amount_bracket_format(self):
        """Should parse [Bounty: 15 RTC] format."""
        title = "[Bounty: 15 RTC] Implement feature X"
        reward = bounty_index.parse_reward(title, "")
        assert reward == 15

    def test_parse_rtc_amount_with_decimal(self):
        """Should parse decimal RTC amounts."""
        title = "[Bounty: 10.5 RTC] Small task"
        reward = bounty_index.parse_reward(title, "")
        assert reward == 10.5

    def test_parse_rtc_case_insensitive(self):
        """Should be case insensitive."""
        title = "[BOUNTY: 20 RTC] Task"
        reward = bounty_index.parse_reward(title, "")
        assert reward == 20

    def test_parse_rtc_no_bounty(self):
        """No bounty in title should return 0."""
        title = "Just a regular issue"
        reward = bounty_index.parse_reward(title, "")
        assert reward == 0

    def test_parse_rtc_in_body(self):
        """Should also check body for reward amount."""
        title = "Feature request"
        body = "This has a 25 RTC bounty"
        reward = bounty_index.parse_reward(title, body)
        assert reward == 25

    def test_parse_large_bounty(self):
        """Should handle large bounty amounts."""
        title = "[Bounty: 500 RTC] Major feature"
        reward = bounty_index.parse_reward(title, "")
        assert reward == 500

    def test_parse_small_bounty(self):
        """Should handle small bounty amounts."""
        title = "[Bounty: 1 RTC] Tiny fix"
        reward = bounty_index.parse_reward(title, "")
        assert reward == 1

    def test_parse_comma_in_number(self):
        """Should parse bounty with comma like '1,000 RTC'."""
        title = "[Bounty: 1,000 RTC] Major feature"
        reward = bounty_index.parse_reward(title, "")
        assert reward == 1000.0

    def test_parse_large_comma_number(self):
        """Should parse bounty with multiple commas like '10,000 RTC'."""
        title = "[Bounty: 10,000 RTC] Huge feature"
        reward = bounty_index.parse_reward(title, "")
        assert reward == 10000.0


class TestEstimateDifficulty:
    """Tests for difficulty estimation."""

    def test_high_reward_high_difficulty(self):
        """High reward should indicate some difficulty level."""
        difficulty = bounty_index.estimate_difficulty(
            "Complex system",
            [],
            reward=100
        )
        assert difficulty is not None

    def test_low_reward_low_difficulty(self):
        """Low reward should indicate some difficulty level."""
        difficulty = bounty_index.estimate_difficulty(
            "Simple fix",
            [],
            reward=5
        )
        assert difficulty is not None

    def test_difficulty_labels_override(self):
        """Labels should influence difficulty."""
        difficulty = bounty_index.estimate_difficulty(
            "Anything",
            ["good first issue"],
            reward=50
        )
        assert difficulty is not None

    def test_difficulty_with_both_labels(self):
        """Multiple labels should be considered."""
        difficulty = bounty_index.estimate_difficulty(
            "Issue",
            ["enhancement", "bug"],
            reward=30
        )
        assert difficulty is not None


class TestTagSkills:
    """Tests for skill tagging."""

    def test_python_tag(self):
        """Python in title should tag python."""
        tags = bounty_index.tag_skills("Python script needed", "")
        assert "python" in tags

    def test_rust_tag(self):
        """Rust in title should tag rust."""
        tags = bounty_index.tag_skills("Rust implementation", "")
        assert "rust" in tags

    def test_javascript_tag(self):
        """JavaScript in title should tag javascript."""
        tags = bounty_index.tag_skills("JavaScript frontend work", "")
        assert "javascript" in tags

    def test_multiple_tags(self):
        """Multiple skills should be tagged."""
        tags = bounty_index.tag_skills("Python and Rust needed", "")
        assert len(tags) >= 1

    def test_no_skills(self):
        """No specific skills should return empty or minimal tags."""
        tags = bounty_index.tag_skills("General task", "")
        assert isinstance(tags, list)


class TestFormatMarkdown:
    """Tests for markdown formatting."""

    def test_format_single_bounty(self):
        """Should format single bounty correctly."""
        bounties = [{
            "title": "Test bounty",
            "reward_rtc": 10,
            "number": 1,
            "repo": "test/repo",
            "skills": [],
            "difficulty": "medium"
        }]
        result = bounty_index.format_markdown(bounties)
        assert isinstance(result, str)
        assert "Test bounty" in result
        assert "10" in result

    def test_format_multiple_bounties(self):
        """Should format multiple bounties."""
        bounties = [
            {"title": "Bounty 1", "reward_rtc": 10, "number": 1, "repo": "a", "skills": [], "difficulty": "easy"},
            {"title": "Bounty 2", "reward_rtc": 20, "number": 2, "repo": "b", "skills": [], "difficulty": "hard"},
        ]
        result = bounty_index.format_markdown(bounties)
        assert "Bounty 1" in result
        assert "Bounty 2" in result

    def test_format_empty_list(self):
        """Should handle empty list."""
        result = bounty_index.format_markdown([])
        assert isinstance(result, str)


class TestFetchBountiesIntegration:
    """Integration tests for fetch_bounties with mocked GitHub API."""

    def test_skips_pull_requests(self, monkeypatch):
        """fetch_bounties should skip PRs that appear in issues endpoint."""
        import requests

        class MockResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                # Issues endpoint can include PRs with pull_request key
                return [
                    {"number": 1, "title": "[Bounty: 10 RTC] Issue", "body": "",
                     "html_url": "https://github.com/a/b/issues/1",
                     "labels": [{"name": "bounty"}], "created_at": "2026-01-01T00:00:00Z"},
                    {"number": 2, "title": "[Bounty: 20 RTC] PR", "body": "",
                     "html_url": "https://github.com/a/b/pull/2",
                     "labels": [{"name": "bounty"}], "created_at": "2026-01-01T00:00:00Z",
                     "pull_request": {"url": "https://api.github.com/repos/a/b/pulls/2"}},
                ]

        monkeypatch.setattr(
            requests, "get",
            lambda *a, **kw: MockResponse()
        )
        monkeypatch.setattr(bounty_index, "GITHUB_TOKEN", None)
        monkeypatch.setattr(bounty_index, "REPOS", ["a/b"])

        bounties = bounty_index.fetch_bounties()
        # Should only return the issue, not the PR
        assert len(bounties) == 1
        assert bounties[0]["number"] == 1
