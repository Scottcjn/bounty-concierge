"""Unit tests for PoW miner helper functions."""

import pathlib
import sys
from unittest.mock import MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import pow_miners


class TestResolvePoolEndpoint:
    def test_resolves_known_pool_alias(self):
        result = pow_miners.resolve_pool_endpoint("wooly")

        assert result["verified"] is True
        assert result["pool"] == "woolypooly"
        assert result["endpoint"] == pow_miners.POOL_ENDPOINTS["woolypooly"]
        assert result["source"] == "known-pool"

    def test_accepts_explicit_pool_url_for_custom_pool(self):
        result = pow_miners.resolve_pool_endpoint(
            "lab-pool",
            "stratum+tcp://example.org:1234",
        )

        assert result == {
            "verified": True,
            "pool": "lab-pool",
            "endpoint": "stratum+tcp://example.org:1234",
            "source": "explicit-url",
        }

    def test_unknown_pool_returns_actionable_error(self):
        result = pow_miners.resolve_pool_endpoint("unknown")

        assert result["verified"] is False
        assert "Unknown pool" in result["error"]


class TestVerifyPoolAccount:
    def test_missing_address_fails_before_pool_lookup(self):
        result = pow_miners.verify_pool_account("", "woolypooly")

        assert result == {
            "verified": False,
            "error": "Address is required for pool verification",
        }

    def test_known_pool_and_address_are_verified(self):
        result = pow_miners.verify_pool_account("RTCabc", "hero")

        assert result["verified"] is True
        assert result["address"] == "RTCabc"
        assert result["pool"] == "herominers"
        assert result["proof"] == "pool-config-validated"


class TestMinerCommands:
    def test_build_bzminer_command_uses_warthog_algorithm(self):
        command = pow_miners.build_bzminer_command(
            wallet="RTCwallet",
            pool_url="stratum+tcp://pool:3140",
            miner_path="/opt/bzminer",
        )

        assert command == [
            "/opt/bzminer",
            "-a",
            "warthog",
            "-w",
            "RTCwallet",
            "-p",
            "stratum+tcp://pool:3140",
        ]

    def test_build_bzminer_command_requires_wallet_and_pool(self):
        try:
            pow_miners.build_bzminer_command("", "stratum+tcp://pool")
        except ValueError as exc:
            assert "wallet" in str(exc)
        else:
            raise AssertionError("missing wallet should raise")

        try:
            pow_miners.build_bzminer_command("RTCwallet", "")
        except ValueError as exc:
            assert "pool_url" in str(exc)
        else:
            raise AssertionError("missing pool_url should raise")

    def test_build_janusminer_command_converts_port_to_string(self):
        command = pow_miners.build_janusminer_command(
            "RTCwallet",
            miner_path="janus",
            host="10.0.0.5",
            port=4444,
        )

        assert command == ["janus", "-a", "RTCwallet", "-h", "10.0.0.5", "-p", "4444"]


class TestNodeRpc:
    def _response(self, ok=True, status_code=200, payload=None):
        resp = MagicMock()
        resp.ok = ok
        resp.status_code = status_code
        resp.json.return_value = payload if payload is not None else {"ok": True}
        resp.text = "not json"
        return resp

    def test_missing_address_returns_validation_error(self):
        result = pow_miners.query_node_rpc("")

        assert result == {
            "verified": False,
            "error": "Address is required for node proof",
        }

    @patch("concierge.pow_miners.requests.get")
    def test_all_rpc_endpoints_ok_marks_verified(self, mock_get):
        mock_get.return_value = self._response(payload={"height": 1})

        result = pow_miners.query_node_rpc("RTCabc", base_url="http://node")

        assert result["verified"] is True
        assert set(result["results"]) == {"chain_head", "mine_eligibility", "balance"}
        assert mock_get.call_count == 3

    @patch("concierge.pow_miners.requests.get")
    def test_rpc_error_marks_unverified(self, mock_get):
        mock_get.side_effect = [
            self._response(payload={"height": 1}),
            self._response(ok=False, status_code=500, payload={"error": "boom"}),
            self._response(payload={"balance": 0}),
        ]

        result = pow_miners.query_node_rpc("RTCabc", base_url="http://node")

        assert result["verified"] is False
        assert "mine_eligibility: HTTP 500" in result["errors"]


class TestCalculateBonusMultiplier:
    def test_no_verifications_returns_base_multiplier(self):
        result = pow_miners.calculate_bonus_multiplier(False, False, False, False)

        assert result == {"base": 1.0, "total_multiplier": 1.0, "factors": []}

    def test_combines_all_verified_factors(self):
        result = pow_miners.calculate_bonus_multiplier(True, True, True, True)

        expected = round(1.5 * 1.15 * 1.3 * 1.5, 6)
        assert result["total_multiplier"] == expected
        assert [factor["name"] for factor in result["factors"]] == [
            "managed_pow_subprocess",
            "external_miner_detected",
            "pool_account_verified",
            "node_rpc_verified",
        ]
