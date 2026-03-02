from concierge import bounty_index


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_parse_reward_from_issue_title():
    assert bounty_index.parse_reward("[major] Build bridge - 150 RTC", "") == 150.0
    assert bounty_index.parse_reward("Fix parser for 0.5 RTC payout", "") == 0.5
    assert bounty_index.parse_reward("Scale indexer - 1,000 RTC", "") == 1000.0


def test_parse_reward_falls_back_to_body_when_title_missing_amount():
    assert bounty_index.parse_reward("No amount in title", "Reward: 25 RTC") == 25.0


def test_parse_reward_returns_zero_when_no_rtc_amount_present():
    assert bounty_index.parse_reward("Improve docs", "No reward listed") == 0.0


def test_fetch_bounties_parses_title_reward_and_skips_pull_requests(monkeypatch):
    issues_payload = [
        {
            "number": 526,
            "title": "Implement matcher - 75 RTC",
            "body": "Need tests for matching",
            "html_url": "https://github.com/Scottcjn/rustchain-bounties/issues/526",
            "labels": [{"name": "bounty"}, {"name": "testing"}],
            "created_at": "2026-03-01T00:00:00Z",
        },
        {
            "number": 527,
            "title": "This is actually a PR - 200 RTC",
            "body": "Should be skipped",
            "html_url": "https://github.com/Scottcjn/rustchain-bounties/pull/527",
            "labels": [{"name": "bounty"}],
            "pull_request": {"url": "https://api.github.com/repos/x/pulls/527"},
            "created_at": "2026-03-01T00:00:00Z",
        },
    ]

    def fake_get(url, headers, params, timeout):
        assert url.endswith("/repos/Scottcjn/rustchain-bounties/issues")
        assert params["labels"] == "bounty"
        return DummyResponse(issues_payload)

    monkeypatch.setattr(bounty_index.requests, "get", fake_get)

    bounties = bounty_index.fetch_bounties(repos=["Scottcjn/rustchain-bounties"], token="")

    assert len(bounties) == 1
    assert bounties[0]["number"] == 526
    assert bounties[0]["reward_rtc"] == 75.0
