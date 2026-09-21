# SPDX-License-Identifier: MIT
"""Tests for wallet_helper — wallet name validation, balance checks, transfers.

All network calls are mocked to keep tests offline and fast.
"""
import pathlib
import sys
import unittest
from unittest.mock import patch, MagicMock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import wallet_helper
from concierge import cli


# ---------------------------------------------------------------------------
# validate_wallet_name
# ---------------------------------------------------------------------------

class TestValidateWalletName(unittest.TestCase):
    """Wallet name validation rules."""

    def test_valid_simple_name(self):
        ok, msg = wallet_helper.validate_wallet_name("alice")
        self.assertTrue(ok)

    def test_valid_with_hyphens(self):
        ok, msg = wallet_helper.validate_wallet_name("my-cool-wallet")
        self.assertTrue(ok)

    def test_valid_with_digits(self):
        ok, msg = wallet_helper.validate_wallet_name("wallet42")
        self.assertTrue(ok)

    def test_valid_min_length(self):
        ok, msg = wallet_helper.validate_wallet_name("abc")
        self.assertTrue(ok)

    def test_valid_max_length(self):
        ok, msg = wallet_helper.validate_wallet_name("a" * 64)
        self.assertTrue(ok)

    def test_empty_name(self):
        ok, msg = wallet_helper.validate_wallet_name("")
        self.assertFalse(ok)
        self.assertIn("empty", msg.lower())

    def test_none_name(self):
        ok, msg = wallet_helper.validate_wallet_name(None)
        self.assertFalse(ok)

    def test_too_short(self):
        ok, msg = wallet_helper.validate_wallet_name("ab")
        self.assertFalse(ok)
        self.assertIn("3", msg)

    def test_too_long(self):
        ok, msg = wallet_helper.validate_wallet_name("a" * 65)
        self.assertFalse(ok)
        self.assertIn("64", msg)

    def test_uppercase_rejected(self):
        ok, msg = wallet_helper.validate_wallet_name("Alice")
        self.assertFalse(ok)
        self.assertIn("lowercase", msg.lower())

    def test_starts_with_hyphen(self):
        ok, msg = wallet_helper.validate_wallet_name("-wallet")
        self.assertFalse(ok)

    def test_ends_with_hyphen(self):
        ok, msg = wallet_helper.validate_wallet_name("wallet-")
        self.assertFalse(ok)

    def test_special_chars_rejected(self):
        ok, msg = wallet_helper.validate_wallet_name("wal!et")
        self.assertFalse(ok)

    def test_spaces_rejected(self):
        ok, msg = wallet_helper.validate_wallet_name("my wallet")
        self.assertFalse(ok)

    def test_underscore_rejected(self):
        ok, msg = wallet_helper.validate_wallet_name("my_wallet")
        self.assertFalse(ok)


# ---------------------------------------------------------------------------
# check_wallet_exists (mocked network)
# ---------------------------------------------------------------------------

class TestCheckWalletExists(unittest.TestCase):

    @patch("concierge.wallet_helper._get")
    def test_wallet_exists(self, mock_get):
        mock_get.return_value = {"miner_id": "alice", "balance_rtc": 42.0}
        self.assertTrue(wallet_helper.check_wallet_exists("alice"))

    @patch("concierge.wallet_helper._get")
    def test_wallet_not_found(self, mock_get):
        mock_get.return_value = {"error": "miner not found"}
        self.assertFalse(wallet_helper.check_wallet_exists("nonexistent"))

    @patch("concierge.wallet_helper._get")
    def test_wallet_zero_balance_exists(self, mock_get):
        mock_get.return_value = {"miner_id": "bob", "balance_rtc": 0.0}
        self.assertTrue(wallet_helper.check_wallet_exists("bob"))

    @patch("concierge.wallet_helper._get")
    def test_connection_error(self, mock_get):
        mock_get.return_value = {"error": "Could not connect to node"}
        self.assertFalse(wallet_helper.check_wallet_exists("alice"))


# ---------------------------------------------------------------------------
# get_balance (mocked network)
# ---------------------------------------------------------------------------

class TestGetBalance(unittest.TestCase):

    @patch("concierge.wallet_helper._get")
    def test_returns_balance(self, mock_get):
        mock_get.return_value = {"miner_id": "alice", "balance_rtc": 100.5}
        result = wallet_helper.get_balance("alice")
        self.assertEqual(result["balance_rtc"], 100.5)
        mock_get.assert_called_once_with("/balance", params={"miner_id": "alice"})

    @patch("concierge.wallet_helper._get")
    def test_returns_error(self, mock_get):
        mock_get.return_value = {"error": "miner not found"}
        result = wallet_helper.get_balance("unknown")
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# get_pending_transfers (mocked network)
# ---------------------------------------------------------------------------

class TestGetPendingTransfers(unittest.TestCase):

    @patch("concierge.wallet_helper._get")
    def test_returns_list(self, mock_get):
        mock_get.return_value = [{"id": 1, "amount_rtc": 10}]
        result = wallet_helper.get_pending_transfers("alice")
        self.assertEqual(len(result), 1)

    @patch("concierge.wallet_helper._get")
    def test_returns_dict_with_pending(self, mock_get):
        mock_get.return_value = {"pending": [{"id": 1}]}
        result = wallet_helper.get_pending_transfers("alice")
        self.assertEqual(len(result), 1)

    @patch("concierge.wallet_helper._get")
    def test_error_returns_empty_list(self, mock_get):
        mock_get.return_value = {"error": "timeout"}
        result = wallet_helper.get_pending_transfers("alice")
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# register_wallet_guide
# ---------------------------------------------------------------------------

class TestRegisterWalletGuide(unittest.TestCase):

    def test_valid_name_returns_instructions(self):
        guide = wallet_helper.register_wallet_guide("my-wallet")
        self.assertIn("my-wallet", guide)
        self.assertIn("Option 1", guide)
        self.assertIn("Option 2", guide)

    def test_invalid_name_returns_error(self):
        guide = wallet_helper.register_wallet_guide("A!")
        self.assertIn("Invalid", guide)


# ---------------------------------------------------------------------------
# transfer_rtc (mocked network)
# ---------------------------------------------------------------------------

class TestTransferRTC(unittest.TestCase):

    def test_no_admin_key_returns_error(self):
        with patch.dict("os.environ", {}, clear=True):
            result = wallet_helper.transfer_rtc("alice", "bob", 10.0)
            self.assertIn("error", result)
            self.assertIn("RC_ADMIN_KEY", result["error"])

    @patch("concierge.wallet_helper._post")
    def test_transfer_success(self, mock_post):
        mock_post.return_value = {"status": "pending", "pending_id": "abc123"}
        result = wallet_helper.transfer_rtc("alice", "bob", 10.0, admin_key="secret")
        self.assertEqual(result["status"], "pending")
        mock_post.assert_called_once()

    @patch("concierge.wallet_helper._post")
    def test_transfer_with_env_key(self, mock_post):
        mock_post.return_value = {"status": "pending", "pending_id": "x"}
        with patch.dict("os.environ", {"RC_ADMIN_KEY": "envkey"}):
            result = wallet_helper.transfer_rtc("alice", "bob", 5.0)
            self.assertEqual(result["status"], "pending")


# ---------------------------------------------------------------------------
# _classify_wallet
# ---------------------------------------------------------------------------

class TestClassifyWallet(unittest.TestCase):

    def test_founder_wallet(self):
        self.assertEqual(wallet_helper._classify_wallet("founder_community"), "founder")

    def test_platform_wallet(self):
        self.assertEqual(wallet_helper._classify_wallet("bottube_platform"), "platform")

    def test_redteam_wallet(self):
        self.assertEqual(wallet_helper._classify_wallet("exploit-test-1"), "redteam")

    def test_auto_hash_wallet(self):
        self.assertEqual(wallet_helper._classify_wallet("a" * 35 + "RTC"), "auto-hash")

    def test_named_wallet(self):
        self.assertEqual(wallet_helper._classify_wallet("alice"), "named")


# ---------------------------------------------------------------------------
# Legacy aliases
# ---------------------------------------------------------------------------

class TestLegacyAliases(unittest.TestCase):

    @patch("concierge.wallet_helper._get")
    def test_check_balance_alias(self, mock_get):
        mock_get.return_value = {"balance_rtc": 50}
        result = wallet_helper.check_balance("alice")
        self.assertEqual(result["balance_rtc"], 50)

    def test_registration_instructions_alias(self):
        result = wallet_helper.registration_instructions("my-wallet")
        self.assertIn("my-wallet", result)


# ---------------------------------------------------------------------------
# CLI wallet balance exit code tests
# ---------------------------------------------------------------------------

class TestWalletBalanceCLI(unittest.TestCase):

    @patch("concierge.cli.get_balance")
    def test_json_error_exits_nonzero(self, mock_get_balance):
        mock_get_balance.return_value = {"error": "Request to node timed out (10s)"}
        argv = ["concierge", "wallet", "balance", "example-wallet", "--json"]
        with patch("sys.argv", argv), patch("sys.stdout"):
            with self.assertRaises(SystemExit) as cm:
                cli.main()
            self.assertEqual(cm.exception.code, 1)

    @patch("concierge.cli.get_balance")
    def test_text_error_exits_nonzero(self, mock_get_balance):
        mock_get_balance.return_value = {"error": "Request to node timed out (10s)"}
        argv = ["concierge", "wallet", "balance", "example-wallet"]
        with patch("sys.argv", argv), patch("sys.stderr"):
            with self.assertRaises(SystemExit) as cm:
                cli.main()
            self.assertEqual(cm.exception.code, 1)

    @patch("concierge.cli.get_balance")
    def test_json_success_exits_zero(self, mock_get_balance):
        mock_get_balance.return_value = {"miner_id": "example-wallet", "balance_rtc": 15.5}
        argv = ["concierge", "wallet", "balance", "example-wallet", "--json"]
        with patch("sys.argv", argv), patch("sys.stdout"):
            cli.main()

    @patch("concierge.cli.get_balance")
    def test_text_success_exits_zero(self, mock_get_balance):
        mock_get_balance.return_value = {"miner_id": "example-wallet", "balance_rtc": 15.5}
        argv = ["concierge", "wallet", "balance", "example-wallet"]
        with patch("sys.argv", argv), patch("sys.stdout"):
            cli.main()


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# Canonical RTC addresses (RTC + exactly 40 lowercase hex)
# ---------------------------------------------------------------------------

CANON = "RTC" + "0123456789abcdef" * 2 + "01234567"  # 43 chars


class TestRtcAddressValidation(unittest.TestCase):

    def test_canonical_address_is_accepted_as_wallet(self):
        self.assertEqual(len(CANON), 43)
        valid, msg = wallet_helper.validate_wallet_name(CANON)
        self.assertTrue(valid, msg)
        self.assertTrue(wallet_helper.is_rtc_address(CANON))

    def test_truncated_address_rejected(self):
        # 32-char and 42-char variants have stranded real payouts.
        for bad in (CANON[:-1], "RTC64aa3fc417e75224e1574acae906f"):
            valid, msg = wallet_helper.validate_wallet_name(bad)
            self.assertFalse(valid, bad)
            self.assertIn("exactly 43", msg)

    def test_extended_address_rejected(self):
        valid, msg = wallet_helper.validate_wallet_name(CANON + "a")
        self.assertFalse(valid)
        self.assertIn("exactly 43", msg)

    def test_uppercase_hex_rejected(self):
        valid, msg = wallet_helper.validate_wallet_name("RTC" + "A" * 40)
        self.assertFalse(valid)
        self.assertIn("lowercase", msg)

    def test_non_hex_rejected(self):
        valid, msg = wallet_helper.validate_wallet_name("RTC" + "g" * 40)
        self.assertFalse(valid)
        self.assertIn("hex", msg)

    def test_lowercased_address_is_not_silently_a_name(self):
        # Before: "rtc" + hex passed as a plain *name*, a different identity
        # from the address the contributor meant.
        valid, msg = wallet_helper.validate_wallet_name(CANON.lower())
        self.assertFalse(valid)
        self.assertIn("'RTC'", msg)

    def test_solana_lookalike_rejected(self):
        valid, _ = wallet_helper.validate_wallet_name("RTC29WwMjwcaFeTTQqKaMNmFUFLYz3f")
        self.assertFalse(valid)

    def test_agent_style_rtc_prefix_rejected(self):
        valid, _ = wallet_helper.validate_wallet_name("RTC-agent-antigravity-9944")
        self.assertFalse(valid)

    def test_whitespace_padding_rejected(self):
        for bad in (" " + CANON, CANON + "\n"):
            self.assertFalse(wallet_helper.validate_wallet_name(bad)[0])

    def test_short_rtc_names_still_names(self):
        self.assertTrue(wallet_helper.validate_wallet_name("rtcfan")[0])

    def test_validate_rtc_address_empty(self):
        self.assertFalse(wallet_helper.validate_rtc_address("")[0])
        self.assertFalse(wallet_helper.validate_rtc_address(None)[0])


class TestClassifyAddress(unittest.TestCase):

    def test_canonical_address(self):
        self.assertEqual(wallet_helper._classify_wallet(CANON), "address")

    def test_malformed_address(self):
        for bad in (CANON[:-1], CANON + "a", "RTC" + "A" * 40,
                    "RTC-agent-antigravity-9944"):
            self.assertEqual(wallet_helper._classify_wallet(bad), "malformed-address", bad)
