import pytest
import requests

from concierge import wallet_helper


@pytest.mark.parametrize(
    "name",
    [
        "abc",
        "wallet-123",
        "a1b2c3",
        "z" * 64,
    ],
)
def test_validate_wallet_name_accepts_valid_names(name):
    is_valid, message = wallet_helper.validate_wallet_name(name)
    assert is_valid is True
    assert message == "Valid wallet name."


@pytest.mark.parametrize(
    "name,error_fragment",
    [
        ("", "cannot be empty"),
        ("ab", "at least 3 characters"),
        ("A-wallet", "must be lowercase"),
        ("-startbad", "may only contain"),
        ("endbad-", "may only contain"),
        ("has_underscore", "may only contain"),
        ("x" * 65, "64 characters or fewer"),
    ],
)
def test_validate_wallet_name_rejects_invalid_names(name, error_fragment):
    is_valid, message = wallet_helper.validate_wallet_name(name)
    assert is_valid is False
    assert error_fragment in message


def test_check_wallet_exists_uses_api_result(monkeypatch):
    monkeypatch.setattr(wallet_helper, "_get", lambda *args, **kwargs: {"balance_rtc": 0})
    assert wallet_helper.check_wallet_exists("wallet-a") is True

    monkeypatch.setattr(
        wallet_helper,
        "_get",
        lambda *args, **kwargs: {"error": "Could not connect"},
    )
    assert wallet_helper.check_wallet_exists("wallet-a") is False


def test_get_returns_timeout_error_when_request_times_out(monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(wallet_helper.requests, "get", fake_get)
    result = wallet_helper._get("/balance", params={"miner_id": "wallet-a"})

    assert result == {"error": "Request to node timed out (10s)"}
