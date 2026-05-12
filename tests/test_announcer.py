"""Unit tests for cross-platform bounty announcements."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import announcer


def _bounty(title="Build thing", rtc=5, url="https://example.test/1", difficulty="micro"):
    return {
        "title": title,
        "rtc": rtc,
        "url": url,
        "difficulty": difficulty,
    }


class TestFormatAnnouncement:
    def test_empty_bounty_list_returns_empty_platform_strings(self):
        assert announcer.format_announcement([]) == {
            "short": "",
            "medium": "",
            "long": "",
        }

    def test_short_announcement_uses_top_bounty_and_stays_under_280_chars(self):
        result = announcer.format_announcement(
            [
                _bounty(title="A" * 400, rtc=10, url="https://example.test/long"),
                _bounty(title="Second bounty", rtc=20),
            ]
        )

        assert len(result["short"]) <= 280
        assert result["short"].endswith("...")
        assert "Second bounty" not in result["short"]

    def test_medium_announcement_lists_first_five_and_extra_count(self):
        bounties = [_bounty(title=f"Bounty {i}", rtc=i) for i in range(1, 8)]

        result = announcer.format_announcement(bounties)

        assert "Bounty 1" in result["medium"]
        assert "Bounty 5" in result["medium"]
        assert "Bounty 6" not in result["medium"]
        assert "+2 more" in result["medium"]

    def test_medium_announcement_omits_extra_count_for_five_or_fewer(self):
        result = announcer.format_announcement([_bounty(title=f"Bounty {i}") for i in range(5)])

        assert "+0 more" not in result["medium"]
        assert "more at" not in result["medium"]

    def test_long_announcement_contains_markdown_table_with_difficulty(self):
        result = announcer.format_announcement(
            [
                _bounty(title="Python tests", rtc=2, url="https://example.test/2", difficulty="standard")
            ]
        )

        assert "| Title | RTC | Difficulty | Link |" in result["long"]
        assert "| Python tests | 2 | standard | [link](https://example.test/2) |" in result["long"]
        assert "1 RTC = $0.10 USD" in result["long"]

    def test_missing_optional_fields_use_placeholders(self):
        result = announcer.format_announcement([{"title": "No metadata"}])

        assert "(? RTC)" in result["short"]
        assert "No metadata | ? RTC |" in result["medium"]
        assert "| No metadata | ? | -- | [link]() |" in result["long"]


class TestPostAnnouncement:
    def test_unknown_platform_returns_structured_error(self):
        result = announcer.post_announcement("unknown", "content", {})

        assert result == {
            "ok": False,
            "url": "",
            "error": "Unknown platform: unknown",
        }

    def test_dispatches_to_registered_handler(self, monkeypatch):
        calls = []

        def handler(content, cfg):
            calls.append((content, cfg))
            return {"ok": True, "url": "https://posted.example", "error": ""}

        monkeypatch.setitem(announcer._PLATFORM_HANDLERS, "unit-test", handler)

        result = announcer.post_announcement("unit-test", "hello", {"channel": "test"})

        assert result["ok"] is True
        assert result["url"] == "https://posted.example"
        assert calls == [("hello", {"channel": "test"})]

    def test_handler_exception_is_returned_as_error(self, monkeypatch):
        def handler(_content, _cfg):
            raise RuntimeError("boom")

        monkeypatch.setitem(announcer._PLATFORM_HANDLERS, "broken", handler)

        result = announcer.post_announcement("broken", "hello", {})

        assert result["ok"] is False
        assert result["url"] == ""
        assert "boom" in result["error"]

    def test_stub_platforms_are_not_reported_as_success(self):
        result = announcer.post_announcement("twitter", "hello", {})

        assert result["ok"] is False
        assert "not yet implemented" in result["error"]
