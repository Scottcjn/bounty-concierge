"""Tests for RustChain payout tracking helpers."""

import pathlib
import sys

import pytest
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import payout_tracker


class DummyResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.raised = False

    def raise_for_status(self):
        self.raised = True
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self.payload


def test_check_pending_accepts_list_response(monkeypatch):
    calls = []
    response = DummyResponse([{"amount_rtc": 2, "memo": "review bounty"}])

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return response

    monkeypatch.setattr(requests, "get", fake_get)

    pending = payout_tracker.check_pending(
        "miner-1",
        node_url="https://node.example/",
    )

    assert pending == [{"amount_rtc": 2, "memo": "review bounty"}]
    assert calls == [
        (
            "https://node.example/wallet/pending",
            {"params": {"miner_id": "miner-1"}, "timeout": 15, "verify": False},
        )
    ]
    assert response.raised is True


def test_check_pending_extracts_pending_key_from_object(monkeypatch):
    response = DummyResponse({"pending": [{"amount_rtc": 5}]})
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)

    assert payout_tracker.check_pending("miner-2", "https://node.example") == [
        {"amount_rtc": 5}
    ]


@pytest.mark.parametrize("status_code", [404, 500])
def test_check_pending_returns_empty_for_404_and_request_errors(monkeypatch, status_code):
    response = DummyResponse({"error": "nope"}, status_code=status_code)

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)

    assert payout_tracker.check_pending("miner-3", "https://node.example") == []


def test_check_history_extracts_history_key_from_object(monkeypatch):
    response = DummyResponse({"history": [{"amount_rtc": 1, "from": "a", "to": "b"}]})
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)

    assert payout_tracker.check_history("miner-4", "https://node.example") == [
        {"amount_rtc": 1, "from": "a", "to": "b"}
    ]


def test_check_history_returns_empty_on_connection_error(monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.ConnectionError("node unavailable")

    monkeypatch.setattr(requests, "get", fake_get)

    assert payout_tracker.check_history("miner-5", "https://node.example") == []


def test_format_payout_status_shows_empty_sections():
    output = payout_tracker.format_payout_status([], [])

    assert "-- Pending Transfers --" in output
    assert "-- Recent History --" in output
    assert output.count("  (none)") == 2


def test_format_payout_status_includes_pending_and_history_details():
    output = payout_tracker.format_payout_status(
        pending=[
            {
                "amount_rtc": 2.5,
                "memo": "unit-test bounty",
                "created_at": "2026-05-11T13:00:00Z",
            }
        ],
        history=[
            {
                "amount_rtc": 1,
                "from": "treasury",
                "to": "miner-1",
                "timestamp": "2026-05-11T14:00:00Z",
            }
        ],
    )

    assert "2.5 RTC  memo: unit-test bounty  (2026-05-11T13:00:00Z)" in output
    assert "1 RTC  treasury -> miner-1  (2026-05-11T14:00:00Z)" in output


def test_format_payout_status_uses_placeholders_for_missing_history_fields():
    output = payout_tracker.format_payout_status([], [{"amount_rtc": 3}])

    assert "3 RTC  ? -> ?" in output
