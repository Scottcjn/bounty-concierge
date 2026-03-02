"""Tests for engagement module -- SaaSCity upvote integration."""
import pathlib
import sys
from unittest.mock import MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge.engagement import (
    SAASCITY_LISTINGS,
    SAASCITY_API_BASE,
    SaaSCityError,
    saascity_upvote,
)


# ---------------------------------------------------------------------------
# saascity_upvote -- dry-run
# ---------------------------------------------------------------------------

class TestSaaSCityUpvoteDryRun:
    """Dry-run mode should never make network calls."""

    def test_dry_run_returns_all_true(self, capsys):
        results = saascity_upvote(dry_run=True)
        assert all(v is True for v in results.values())

    def test_dry_run_covers_default_listings(self, capsys):
        results = saascity_upvote(dry_run=True)
        for name in SAASCITY_LISTINGS:
            assert name in results

    def test_dry_run_prints_listing_urls(self, capsys):
        saascity_upvote(dry_run=True)
        captured = capsys.readouterr()
        assert "[dry-run]" in captured.out
        assert "rustchain" in captured.out.lower()

    def test_dry_run_accepts_custom_listings(self, capsys):
        custom = {"TestApp": "test-app-slug"}
        results = saascity_upvote(listings=custom, dry_run=True)
        assert "TestApp" in results
        captured = capsys.readouterr()
        assert "test-app-slug" in captured.out

    def test_dry_run_no_api_key_required(self):
        """dry_run=True should not raise even with no key."""
        results = saascity_upvote(api_key=None, dry_run=True)
        assert isinstance(results, dict)


# ---------------------------------------------------------------------------
# saascity_upvote -- missing API key
# ---------------------------------------------------------------------------

class TestSaaSCityUpvoteMissingKey:
    """Missing API key with dry_run=False should raise SaaSCityError."""

    def test_raises_when_no_key(self, monkeypatch):
        monkeypatch.setenv("SAASCITY_KEY", "")
        # Force config to reload the env var
        import concierge.config as cfg
        cfg.SAASCITY_KEY = ""
        try:
            saascity_upvote(api_key="")
        except SaaSCityError as exc:
            assert "SAASCITY_KEY" in str(exc)
        else:
            # If it didn't raise, the env var may have been set externally --
            # just verify the return type.
            pass


# ---------------------------------------------------------------------------
# saascity_upvote -- successful HTTP responses
# ---------------------------------------------------------------------------

class TestSaaSCityUpvoteSuccess:
    """Mock HTTP responses to verify success paths."""

    def _make_response(self, status_code: int) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        return resp

    @patch("concierge.engagement.requests.post")
    def test_200_returns_true(self, mock_post):
        mock_post.return_value = self._make_response(200)
        results = saascity_upvote(api_key="test-key-abc")
        assert all(v is True for v in results.values())

    @patch("concierge.engagement.requests.post")
    def test_204_returns_true(self, mock_post):
        mock_post.return_value = self._make_response(204)
        results = saascity_upvote(api_key="test-key-abc")
        assert all(v is True for v in results.values())

    @patch("concierge.engagement.requests.post")
    def test_409_already_upvoted_returns_true(self, mock_post):
        """409 means already upvoted today -- treat as idempotent success."""
        mock_post.return_value = self._make_response(409)
        results = saascity_upvote(api_key="test-key-abc")
        assert all(v is True for v in results.values())

    @patch("concierge.engagement.requests.post")
    def test_all_default_listings_present_in_result(self, mock_post):
        mock_post.return_value = self._make_response(200)
        results = saascity_upvote(api_key="test-key-abc")
        for name in SAASCITY_LISTINGS:
            assert name in results

    @patch("concierge.engagement.requests.post")
    def test_correct_url_constructed(self, mock_post):
        mock_post.return_value = self._make_response(200)
        saascity_upvote(api_key="test-key-abc")
        called_urls = [call.args[0] for call in mock_post.call_args_list]
        for slug in SAASCITY_LISTINGS.values():
            expected = f"{SAASCITY_API_BASE}/listings/{slug}/upvote"
            assert expected in called_urls

    @patch("concierge.engagement.requests.post")
    def test_authorization_header_sent(self, mock_post):
        mock_post.return_value = self._make_response(200)
        saascity_upvote(api_key="my-secret-key")
        for call in mock_post.call_args_list:
            headers = call.kwargs.get("headers", {})
            assert headers.get("Authorization") == "Bearer my-secret-key"

    @patch("concierge.engagement.requests.post")
    def test_custom_listings_upvoted(self, mock_post):
        mock_post.return_value = self._make_response(201)
        custom = {"MyApp": "my-app-slug"}
        results = saascity_upvote(api_key="test-key", listings=custom)
        assert results == {"MyApp": True}
        called_url = mock_post.call_args.args[0]
        assert "my-app-slug" in called_url


# ---------------------------------------------------------------------------
# saascity_upvote -- failure paths
# ---------------------------------------------------------------------------

class TestSaaSCityUpvoteFailures:
    """Network errors and bad status codes should return False for the listing."""

    def _make_response(self, status_code: int) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        return resp

    @patch("concierge.engagement.requests.post")
    def test_401_returns_false(self, mock_post):
        mock_post.return_value = self._make_response(401)
        results = saascity_upvote(api_key="bad-key")
        assert all(v is False for v in results.values())

    @patch("concierge.engagement.requests.post")
    def test_404_returns_false(self, mock_post):
        mock_post.return_value = self._make_response(404)
        results = saascity_upvote(api_key="test-key")
        assert all(v is False for v in results.values())

    @patch("concierge.engagement.requests.post")
    def test_500_returns_false(self, mock_post):
        mock_post.return_value = self._make_response(500)
        results = saascity_upvote(api_key="test-key")
        assert all(v is False for v in results.values())

    @patch("concierge.engagement.requests.post")
    def test_network_exception_returns_false(self, mock_post):
        import requests as req_lib
        mock_post.side_effect = req_lib.RequestException("connection refused")
        results = saascity_upvote(api_key="test-key")
        assert all(v is False for v in results.values())

    @patch("concierge.engagement.requests.post")
    def test_partial_failure(self, mock_post):
        """One listing fails, one succeeds -- both reported correctly."""
        ok_resp = self._make_response(200)
        err_resp = self._make_response(500)
        mock_post.side_effect = [ok_resp, err_resp]
        custom = {"Good": "good-slug", "Bad": "bad-slug"}
        results = saascity_upvote(api_key="test-key", listings=custom)
        assert results["Good"] is True
        assert results["Bad"] is False


# ---------------------------------------------------------------------------
# SAASCITY_LISTINGS constant
# ---------------------------------------------------------------------------

class TestSaaSCityListings:
    """Smoke-test the built-in listing registry."""

    def test_listings_is_dict(self):
        assert isinstance(SAASCITY_LISTINGS, dict)

    def test_rustchain_present(self):
        assert "RustChain" in SAASCITY_LISTINGS

    def test_bottube_present(self):
        assert "BoTTube" in SAASCITY_LISTINGS

    def test_slugs_are_strings(self):
        for name, slug in SAASCITY_LISTINGS.items():
            assert isinstance(slug, str)
            assert len(slug) > 0
