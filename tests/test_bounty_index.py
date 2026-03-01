"""Tests for bounty index and RTC parsing."""

import pytest
from unittest.mock import patch, MagicMock

from concierge.bounty_index import parse_reward, estimate_difficulty, tag_skills


class TestParseReward:
    """Test RTC amount parsing from issue titles and bodies."""

    def test_parse_rtc_from_title_simple(self):
        """Test parsing simple RTC amount from title."""
        title = "[Bounty: 10 RTC] Add new feature"
        result = parse_reward(title, "")
        assert result == 10.0

    def test_parse_rtc_from_body(self):
        """Test parsing RTC from body when not in title."""
        title = "Feature request"
        body = "Reward: 50 RTC for completion"
        result = parse_reward(title, body)
        assert result == 50.0

    def test_parse_rtc_no_match_returns_zero(self):
        """Test title and body without RTC returns 0."""
        result = parse_reward("Just a regular issue", "No reward here")
        assert result == 0.0

    def test_parse_rtc_case_insensitive(self):
        """Test RTC parsing is case insensitive."""
        result1 = parse_reward("[Bounty: 20 rtc] Task", "")
        result2 = parse_reward("[Bounty: 20 RTC] Task", "")
        assert result1 == result2 == 20.0

    def test_parse_rtc_decimal(self):
        """Test parsing decimal RTC amount."""
        result = parse_reward("[Bounty: 15.5 RTC] Task", "")
        assert result == 15.5

    def test_parse_rtc_with_comma(self):
        """Test parsing RTC with comma formatting."""
        result = parse_reward("[Bounty: 1,000 RTC] Large task", "")
        assert result == 1000.0


class TestEstimateDifficulty:
    """Test difficulty estimation."""

    def test_difficulty_micro(self):
        """Test micro difficulty for small rewards."""
        result = estimate_difficulty("Some task", [], 5)
        assert result == "micro"

    def test_difficulty_standard(self):
        """Test standard difficulty."""
        result = estimate_difficulty("Task", [], 25)
        assert result == "standard"

    def test_difficulty_major(self):
        """Test major difficulty."""
        result = estimate_difficulty("Big task", [], 100)
        assert result == "major"

    def test_difficulty_critical(self):
        """Test critical difficulty."""
        result = estimate_difficulty("Huge task", [], 250)
        assert result == "critical"

    def test_difficulty_label_overrides_reward(self):
        """Test difficulty label overrides reward calculation."""
        result = estimate_difficulty("Task", ["critical"], 5)
        assert result == "critical"


class TestTagSkills:
    """Test skill tagging."""

    def test_tag_python(self):
        """Test Python skill detection."""
        result = tag_skills("Fix Python script", "")
        assert "python" in result

    def test_tag_rust(self):
        """Test Rust skill detection."""
        result = tag_skills("Rust implementation needed", "")
        assert "rust" in result

    def test_tag_docker(self):
        """Test Docker skill detection."""
        result = tag_skills("Add Dockerfile", "")
        assert "docker" in result

    def test_tag_multiple_skills(self):
        """Test multiple skill detection."""
        result = tag_skills("Python and Docker project", "")
        assert "python" in result
        assert "docker" in result

    def test_no_skills_returns_empty(self):
        """Test no matching skills returns empty list."""
        result = tag_skills("Just some text", "")
        assert result == []
