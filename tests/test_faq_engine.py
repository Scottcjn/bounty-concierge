import requests

from concierge import faq_engine


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fuzzy_match_returns_expected_answer():
    entries = {
        "what is rtc": "RTC is the native token.",
        "how do payouts work": "Payouts happen after merge.",
    }
    key, answer, score = faq_engine.fuzzy_match("What is RTC???", entries=entries)

    assert key == "what is rtc"
    assert answer == "RTC is the native token."
    assert score == 1.0


def test_answer_prefers_faq_match():
    result = faq_engine.answer("what is rtc")

    assert result["source"] == "faq"
    assert result["confidence"] >= 0.3
    assert "native token" in result["answer"].lower()


def test_ask_grok_success_with_mocked_api(monkeypatch):
    def fake_post(url, headers, json, timeout):
        assert url == "https://api.x.ai/v1/chat/completions"
        assert headers["Authorization"] == "Bearer test-key"
        assert json["model"] == "grok-3-mini"
        return DummyResponse(
            {"choices": [{"message": {"content": "Mocked Grok answer"}}]}
        )

    monkeypatch.setattr(faq_engine, "GROK_API_KEY", "test-key")
    monkeypatch.setattr(faq_engine.requests, "post", fake_post)

    result = faq_engine.ask_grok("What is PoA?")
    assert result == "Mocked Grok answer"


def test_ask_grok_handles_request_exception(monkeypatch):
    def fake_post(*args, **kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr(faq_engine, "GROK_API_KEY", "test-key")
    monkeypatch.setattr(faq_engine.requests, "post", fake_post)

    result = faq_engine.ask_grok("What is PoA?")
    assert result.startswith("[error] Grok API request failed:")
