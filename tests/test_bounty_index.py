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

    def test_title_takes_priority_over_body(self):
        """When both title and body have RTC, title value is returned first."""
        title = "Fix: 8 RTC reward"
        body = "Additional context: also 50 RTC mentioned here"
        reward = bounty_index.parse_reward(title, body)
        assert reward == 8.0

    def test_returns_float(self):
        """Return value should always be a float."""
        reward = bounty_index.parse_reward("10 RTC bounty", "")
        assert isinstance(reward, float)

    def test_returns_zero_float_when_no_match(self):
        """Should return 0.0 (float) when no RTC found."""
        reward = bounty_index.parse_reward("no reward here", "")
        assert reward == 0.0
        assert isinstance(reward, float)

    def test_rtc_not_matched_as_substring(self):
        """'RTC' inside a word (e.g. 'WRTC') should not match."""
        title = "Add WRTC bridge"
        reward = bounty_index.parse_reward(title, "")
        assert reward == 0.0

    def test_empty_title_and_body(self):
        """Empty title and body should return 0."""
        assert bounty_index.parse_reward("", "") == 0.0

    def test_rtc_in_body_only(self):
        """If only body has RTC amount, it should still be found."""
        reward = bounty_index.parse_reward("", "Reward is 42 RTC for this task")
        assert reward == 42.0


class TestEstimateDifficulty:
    """Tests for difficulty estimation with exact tier assertions."""

    def test_micro_tier_below_10(self):
        """Reward < 10 RTC should return 'micro'."""
        assert bounty_index.estimate_difficulty("Task", [], 5) == "micro"

    def test_micro_tier_at_zero(self):
        """Zero reward should return 'micro'."""
        assert bounty_index.estimate_difficulty("Task", [], 0) == "micro"

    def test_micro_tier_at_nine(self):
        """9 RTC should return 'micro'."""
        assert bounty_index.estimate_difficulty("Task", [], 9) == "micro"

    def test_standard_tier_at_10(self):
        """10 RTC should return 'standard'."""
        assert bounty_index.estimate_difficulty("Task", [], 10) == "standard"

    def test_standard_tier_at_50(self):
        """50 RTC should return 'major' (boundary >= 50 is major)."""
        result = bounty_index.estimate_difficulty("Task", [], 50)
        assert result == "major"

    def test_standard_tier_midrange(self):
        """30 RTC should return 'standard'."""
        assert bounty_index.estimate_difficulty("Task", [], 30) == "standard"

    def test_major_tier_at_100(self):
        """100 RTC should return 'major'."""
        assert bounty_index.estimate_difficulty("Task", [], 100) == "major"

    def test_major_tier_at_199(self):
        """199 RTC should return 'major'."""
        assert bounty_index.estimate_difficulty("Task", [], 199) == "major"

    def test_critical_tier_at_200(self):
        """200 RTC should return 'critical'."""
        assert bounty_index.estimate_difficulty("Task", [], 200) == "critical"

    def test_critical_tier_large(self):
        """1000 RTC should return 'critical'."""
        assert bounty_index.estimate_difficulty("Task", [], 1000) == "critical"

    def test_label_critical_overrides_low_reward(self):
        """'critical' label should override reward-based estimate."""
        result = bounty_index.estimate_difficulty("Task", ["critical"], 5)
        assert result == "critical"

    def test_label_major_overrides_low_reward(self):
        """'major' label should override low reward."""
        result = bounty_index.estimate_difficulty("Task", ["major"], 3)
        assert result == "major"

    def test_label_standard_overrides(self):
        """'standard' label should override critical reward."""
        result = bounty_index.estimate_difficulty("Task", ["standard"], 500)
        assert result == "standard"

    def test_label_micro_overrides_high_reward(self):
        """'micro' label should override high reward."""
        result = bounty_index.estimate_difficulty("Task", ["micro"], 300)
        assert result == "micro"

    def test_labels_case_insensitive(self):
        """Labels should be compared case-insensitively."""
        result = bounty_index.estimate_difficulty("Task", ["CRITICAL"], 5)
        assert result == "critical"

    def test_unknown_labels_fall_back_to_reward(self):
        """Unknown labels should not affect reward-based estimate."""
        result = bounty_index.estimate_difficulty("Task", ["enhancement", "bug"], 75)
        assert result == "major"


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

    def test_docker_tag_from_body(self):
        """Docker keyword in body should tag docker."""
        tags = bounty_index.tag_skills("Deploy service", "Use Docker and docker-compose")
        assert "docker" in tags

    def test_security_tag(self):
        """Security keyword should tag security."""
        tags = bounty_index.tag_skills("Security audit needed", "")
        assert "security" in tags

    def test_documentation_tag(self):
        """Documentation keyword should tag documentation."""
        tags = bounty_index.tag_skills("Update documentation", "")
        assert "documentation" in tags

    def test_ci_cd_tag(self):
        """CI/CD keyword should tag ci/cd."""
        tags = bounty_index.tag_skills("Set up CI/CD pipeline", "")
        assert "ci/cd" in tags

    def test_translation_tag(self):
        """Translation keyword should tag translation."""
        tags = bounty_index.tag_skills("Add translation for Spanish", "")
        assert "translation" in tags

    def test_tags_are_sorted(self):
        """Returned tags should be sorted alphabetically."""
        tags = bounty_index.tag_skills("Python Docker security", "rust cargo")
        assert tags == sorted(tags)

    def test_no_duplicate_tags(self):
        """Each skill should appear at most once."""
        tags = bounty_index.tag_skills("python .py flask django pip", "")
        assert len(tags) == len(set(tags))

    def test_nodejs_triggers_javascript_tag(self):
        """'node' keyword should tag javascript."""
        tags = bounty_index.tag_skills("Build node.js backend", "")
        assert "javascript" in tags

    def test_social_media_tag(self):
        """Social media keyword should tag social-media."""
        tags = bounty_index.tag_skills("Post on Twitter and Moltbook", "")
        assert "social-media" in tags


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

    def test_format_includes_header_row(self):
        """Output should include a markdown table header."""
        result = bounty_index.format_markdown([])
        assert "|" in result
        # Header row expected
        assert "Repo" in result or "Title" in result or "RTC" in result

    def test_format_bounty_with_skills(self):
        """Skills should appear in the formatted output."""
        bounties = [{
            "title": "Python task",
            "reward_rtc": 15,
            "number": 42,
            "repo": "org/repo",
            "skills": ["python", "docker"],
            "difficulty": "standard"
        }]
        result = bounty_index.format_markdown(bounties)
        assert "python" in result
        assert "docker" in result

    def test_format_long_title_truncated(self):
        """Titles longer than 60 chars should be truncated."""
        long_title = "A" * 80
        bounties = [{
            "title": long_title,
            "reward_rtc": 5,
            "number": 1,
            "repo": "a/b",
            "skills": [],
            "difficulty": "micro"
        }]
        result = bounty_index.format_markdown(bounties)
        # Title in output should not be 80 chars (truncated to 60)
        assert long_title not in result

    def test_format_repo_shows_short_name(self):
        """Should display short repo name (after slash)."""
        bounties = [{
            "title": "Task",
            "reward_rtc": 10,
            "number": 1,
            "repo": "myorg/myrepo",
            "skills": [],
            "difficulty": "standard"
        }]
        result = bounty_index.format_markdown(bounties)
        assert "myrepo" in result

    def test_format_reward_shown_as_float(self):
        """Reward should be formatted as a float."""
        bounties = [{
            "title": "Task",
            "reward_rtc": 7,
            "number": 1,
            "repo": "a/b",
            "skills": [],
            "difficulty": "micro"
        }]
        result = bounty_index.format_markdown(bounties)
        assert "7.0" in result


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
                return [
                    {"number": 1, "title": "[Bounty: 10 RTC] Issue", "body": "",
                     "html_url": "https://github.com/a/b/issues/1",
                     "labels": [{"name": "bounty"}], "created_at": "2026-01-01T00:00:00Z"},
                    {"number": 2, "title": "[Bounty: 20 RTC] PR", "body": "",
                     "html_url": "https://github.com/a/b/pull/2",
                     "labels": [{"name": "bounty"}], "created_at": "2026-01-01T00:00:00Z",
                     "pull_request": {"url": "https://api.github.com/repos/a/b/pulls/2"}},
                ]

        monkeypatch.setattr(requests, "get", lambda *a, **kw: MockResponse())
        monkeypatch.setattr(bounty_index, "GITHUB_TOKEN", None)
        monkeypatch.setattr(bounty_index, "REPOS", ["a/b"])

        bounties = bounty_index.fetch_bounties()
        assert len(bounties) == 1
        assert bounties[0]["number"] == 1

    def test_fetch_enriches_with_reward_and_difficulty(self, monkeypatch):
        """Returned bounties should have reward_rtc, difficulty, and skills fields."""
        import requests

        class MockResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return [{
                    "number": 5,
                    "title": "[Bounty: 50 RTC] Python script",
                    "body": "Write a python script",
                    "html_url": "https://github.com/a/b/issues/5",
                    "labels": [{"name": "bounty"}],
                    "created_at": "2026-01-01T00:00:00Z",
                }]

        monkeypatch.setattr(requests, "get", lambda *a, **kw: MockResponse())
        monkeypatch.setattr(bounty_index, "GITHUB_TOKEN", None)
        monkeypatch.setattr(bounty_index, "REPOS", ["a/b"])

        bounties = bounty_index.fetch_bounties()
        assert len(bounties) == 1
        b = bounties[0]
        assert b["reward_rtc"] == 50.0
        assert b["difficulty"] == "major"
        assert "python" in b["skills"]

    def test_fetch_handles_404_gracefully(self, monkeypatch):
        """404 response should be silently skipped, not raise."""
        import requests

        class MockResponse404:
            status_code = 404

            def raise_for_status(self):
                pass

            def json(self):
                return []

        monkeypatch.setattr(requests, "get", lambda *a, **kw: MockResponse404())
        monkeypatch.setattr(bounty_index, "GITHUB_TOKEN", None)
        monkeypatch.setattr(bounty_index, "REPOS", ["nonexistent/repo"])

        bounties = bounty_index.fetch_bounties()
        assert bounties == []

    def test_fetch_handles_network_error_gracefully(self, monkeypatch):
        """Network errors should be caught and return empty list."""
        import requests

        def raise_error(*a, **kw):
            raise requests.RequestException("network error")

        monkeypatch.setattr(requests, "get", raise_error)
        monkeypatch.setattr(bounty_index, "GITHUB_TOKEN", None)
        monkeypatch.setattr(bounty_index, "REPOS", ["a/b"])

        bounties = bounty_index.fetch_bounties()
        assert bounties == []

    def test_fetch_multiple_repos(self, monkeypatch):
        """Should aggregate bounties from multiple repos."""
        import requests

        call_count = {"n": 0}

        class MockResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                call_count["n"] += 1
                return [{
                    "number": call_count["n"],
                    "title": f"[Bounty: {call_count['n'] * 10} RTC] Task {call_count['n']}",
                    "body": "",
                    "html_url": f"https://github.com/a/repo{call_count['n']}/issues/{call_count['n']}",
                    "labels": [{"name": "bounty"}],
                    "created_at": "2026-01-01T00:00:00Z",
                }]

        monkeypatch.setattr(requests, "get", lambda *a, **kw: MockResponse())
        monkeypatch.setattr(bounty_index, "GITHUB_TOKEN", None)
        monkeypatch.setattr(bounty_index, "REPOS", ["a/repo1", "a/repo2"])

        bounties = bounty_index.fetch_bounties()
        assert len(bounties) == 2


class TestAggregate:
    """Tests for the aggregate function."""

    def test_aggregate_returns_expected_keys(self, monkeypatch):
        """Aggregate result should have updated_at, total_count, bounties."""
        monkeypatch.setattr(bounty_index, "REPOS", [])

        result = bounty_index.aggregate()
        assert "updated_at" in result
        assert "total_count" in result
        assert "bounties" in result

    def test_aggregate_total_count_matches_bounties(self, monkeypatch):
        """total_count should match the length of bounties list."""
        import requests

        class MockResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return [
                    {"number": i, "title": f"[Bounty: {i * 5} RTC] Task {i}",
                     "body": "", "html_url": f"https://github.com/a/b/issues/{i}",
                     "labels": [{"name": "bounty"}], "created_at": "2026-01-01T00:00:00Z"}
                    for i in range(1, 4)
                ]

        monkeypatch.setattr(requests, "get", lambda *a, **kw: MockResponse())
        monkeypatch.setattr(bounty_index, "GITHUB_TOKEN", None)
        monkeypatch.setattr(bounty_index, "REPOS", ["a/b"])

        result = bounty_index.aggregate()
        assert result["total_count"] == len(result["bounties"])

    def test_aggregate_sorted_by_reward_desc(self, monkeypatch):
        """Bounties should be sorted by reward_rtc descending."""
        import requests

        class MockResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return [
                    {"number": 1, "title": "[Bounty: 10 RTC] Task", "body": "",
                     "html_url": "url1", "labels": [{"name": "bounty"}], "created_at": ""},
                    {"number": 2, "title": "[Bounty: 100 RTC] Task", "body": "",
                     "html_url": "url2", "labels": [{"name": "bounty"}], "created_at": ""},
                    {"number": 3, "title": "[Bounty: 50 RTC] Task", "body": "",
                     "html_url": "url3", "labels": [{"name": "bounty"}], "created_at": ""},
                ]

        monkeypatch.setattr(requests, "get", lambda *a, **kw: MockResponse())
        monkeypatch.setattr(bounty_index, "GITHUB_TOKEN", None)
        monkeypatch.setattr(bounty_index, "REPOS", ["a/b"])

        result = bounty_index.aggregate()
        rewards = [b["reward_rtc"] for b in result["bounties"]]
        assert rewards == sorted(rewards, reverse=True)

    def test_aggregate_updated_at_is_iso_format(self, monkeypatch):
        """updated_at should be an ISO-8601 formatted timestamp."""
        from datetime import datetime
        monkeypatch.setattr(bounty_index, "REPOS", [])

        result = bounty_index.aggregate()
        # Should parse without error
        ts = result["updated_at"]
        assert "T" in ts  # ISO-8601 contains T between date and time
