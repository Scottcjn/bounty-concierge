# SPDX-License-Identifier: MIT
"""Regression tests for concierge/discord_bridge SQL-injection hardening.

These tests cover three defensive properties added to the SSH-backed SQL
helpers:

1. `get_discord_balance` rejects malformed `user_id` values before
   touching the network.
2. `list_discord_holders` rejects out-of-range / non-numeric
   `min_balance` values before touching the network.
3. `debit_discord_balance` rejects malformed `user_id` and non-positive
   or non-numeric `amount` values before touching the network.

The actual SSH calls are mocked -- we never want the unit tests to attempt
to contact the Sophiacord NAS. The point is to prove that the validation
guards *do* fire (and short-circuit) before any subprocess is spawned.
"""
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import discord_bridge


VALID_SNOWFLAKE = "123456789012345678"  # 18 digits, fits 17-20 window
INVALID_SNOWFLAKE_INJECTION = "1' OR '1'='1"
INVALID_SNOWFLAKE_TOO_SHORT = "123"
INVALID_SNOWFLAKE_TOO_LONG = "1" * 25


class TestDiscordUserIdValidation(unittest.TestCase):
    """The helper regex must accept only 17-20 digit snowflakes."""

    def test_valid_17_digit(self):
        self.assertTrue(discord_bridge._DISCORD_USER_ID_RE.match("1" * 17))

    def test_valid_20_digit(self):
        self.assertTrue(discord_bridge._DISCORD_USER_ID_RE.match("1" * 20))

    def test_invalid_short(self):
        self.assertFalse(discord_bridge._DISCORD_USER_ID_RE.match("123"))

    def test_invalid_long(self):
        self.assertFalse(discord_bridge._DISCORD_USER_ID_RE.match("1" * 25))

    def test_invalid_sql_injection(self):
        self.assertFalse(
            discord_bridge._DISCORD_USER_ID_RE.match("1' OR '1'='1")
        )

    def test_invalid_unicode(self):
        self.assertFalse(discord_bridge._DISCORD_USER_ID_RE.match("\u4e2d\u6587"))


class TestGetDiscordBalanceValidation(unittest.TestCase):
    """`get_discord_balance` must short-circuit on invalid user_id."""

    def test_rejects_sql_injection(self):
        result = discord_bridge.get_discord_balance(INVALID_SNOWFLAKE_INJECTION)
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Invalid Discord user id", result["error"])

    def test_rejects_too_short(self):
        result = discord_bridge.get_discord_balance(INVALID_SNOWFLAKE_TOO_SHORT)
        self.assertIn("error", result)

    def test_rejects_too_long(self):
        result = discord_bridge.get_discord_balance(INVALID_SNOWFLAKE_TOO_LONG)
        self.assertIn("error", result)

    def test_rejects_none(self):
        result = discord_bridge.get_discord_balance(None)
        self.assertIn("error", result)

    def test_rejects_empty_string(self):
        result = discord_bridge.get_discord_balance("")
        self.assertIn("error", result)

    @patch("concierge.discord_bridge._ssh_run_script")
    def test_valid_id_calls_ssh_with_safe_sql(self, mock_run):
        # Valid ids proceed to the network layer; we stub the SSH call to
        # verify that the SQL we send contains a '?' placeholder and *no*
        # interpolated user_id value.
        mock_run.return_value = (
            '[{"user_id": "123456789012345678", "balance": 1.0, '
            '"total_earned": 1.0, "total_spent": 0.0}]',
            "",
            0,
        )
        result = discord_bridge.get_discord_balance(VALID_SNOWFLAKE)
        # Result is the single matching row.
        self.assertIsInstance(result, dict)
        self.assertEqual(result["balance"], 1.0)
        mock_run.assert_called_once()
        script_sent = mock_run.call_args.kwargs.get("extra_stdin", "")
        # Look in the script (positional arg) and the extra_stdin channel.
        all_sent = mock_run.call_args.args[0] + script_sent
        self.assertIn("WHERE user_id = ?", all_sent)
        self.assertNotIn(VALID_SNOWFLAKE, mock_run.call_args.args[0])


class TestListDiscordHoldersValidation(unittest.TestCase):
    """`list_discord_holders` must short-circuit on bad min_balance."""

    def test_rejects_string_with_sql_injection(self):
        result = discord_bridge.list_discord_holders("0; DROP TABLE balances")
        self.assertIn("error", result)

    def test_rejects_negative(self):
        result = discord_bridge.list_discord_holders(-1)
        self.assertIn("error", result)

    def test_rejects_huge(self):
        result = discord_bridge.list_discord_holders(10**12)
        self.assertIn("error", result)

    def test_rejects_none(self):
        result = discord_bridge.list_discord_holders(None)
        self.assertIn("error", result)

    @patch("concierge.discord_bridge._ssh_run_script")
    def test_valid_numeric_proceeds(self, mock_run):
        mock_run.return_value = ("[]", "", 0)
        result = discord_bridge.list_discord_holders(0.5)
        self.assertEqual(result, [])
        script_sent = mock_run.call_args.args[0]
        self.assertIn("balance >= ?", script_sent)
        # The numeric value must travel through stdin as JSON, not inline.
        self.assertNotIn("0.5", script_sent)


class TestDebitDiscordBalanceValidation(unittest.TestCase):
    """`debit_discord_balance` must short-circuit on bad inputs."""

    def test_rejects_sql_injection_user_id(self):
        result = discord_bridge.debit_discord_balance(
            INVALID_SNOWFLAKE_INJECTION, 1.0
        )
        self.assertIn("error", result)

    def test_rejects_string_amount(self):
        result = discord_bridge.debit_discord_balance(
            VALID_SNOWFLAKE, "1.0; DROP TABLE balances"
        )
        self.assertIn("error", result)

    def test_rejects_zero_amount(self):
        result = discord_bridge.debit_discord_balance(VALID_SNOWFLAKE, 0)
        self.assertIn("error", result)

    def test_rejects_negative_amount(self):
        result = discord_bridge.debit_discord_balance(VALID_SNOWFLAKE, -1.0)
        self.assertIn("error", result)

    def test_rejects_huge_amount(self):
        result = discord_bridge.debit_discord_balance(
            VALID_SNOWFLAKE, 10**12
        )
        self.assertIn("error", result)

    def test_rejects_none_inputs(self):
        result = discord_bridge.debit_discord_balance(None, None)
        self.assertIn("error", result)

    @patch("concierge.discord_bridge._ssh_run_script")
    def test_valid_inputs_pass_params_via_stdin(self, mock_run):
        mock_run.return_value = ("OK", "", 0)
        result = discord_bridge.debit_discord_balance(VALID_SNOWFLAKE, 0.5)
        self.assertTrue(result)
        mock_run.assert_called_once()
        script_sent = mock_run.call_args.args[0]
        extra_stdin = mock_run.call_args.kwargs.get("extra_stdin", "")
        self.assertIn("params = json.loads", script_sent)
        self.assertIn("UPDATE balances SET balance = balance - ?", script_sent)
        # The user id travels via the params JSON in extra_stdin, not the SQL.
        self.assertIn(VALID_SNOWFLAKE, extra_stdin)
        self.assertNotIn(VALID_SNOWFLAKE, script_sent)


class TestSshRunScriptExtraStdin(unittest.TestCase):
    """`_ssh_run_script` must prepend extra_stdin before the script."""

    @patch("concierge.discord_bridge.config")
    @patch("concierge.discord_bridge.subprocess.run")
    def test_extra_stdin_prepended(self, mock_run, mock_config):
        # Make the password guard pass.
        mock_config.DISCORD_NAS_PASSWORD = "x"
        mock_config.DISCORD_NAS_USER = "u"
        mock_config.DISCORD_NAS_HOST = "h"
        mock_run.return_value = type("R", (), {
            "stdout": "out", "stderr": "", "returncode": 0
        })()
        discord_bridge._ssh_run_script("PRINT\n", extra_stdin="DATA\n")
        self.assertTrue(mock_run.called)
        kwargs = mock_run.call_args.kwargs
        self.assertEqual(kwargs["input"], "DATA\nPRINT\n")

    @patch("concierge.discord_bridge.config")
    @patch("concierge.discord_bridge.subprocess.run")
    def test_no_extra_stdin_works(self, mock_run, mock_config):
        mock_config.DISCORD_NAS_PASSWORD = "x"
        mock_config.DISCORD_NAS_USER = "u"
        mock_config.DISCORD_NAS_HOST = "h"
        mock_run.return_value = type("R", (), {
            "stdout": "out", "stderr": "", "returncode": 0
        })()
        discord_bridge._ssh_run_script("PRINT\n")
        self.assertTrue(mock_run.called)
        kwargs = mock_run.call_args.kwargs
        self.assertEqual(kwargs["input"], "PRINT\n")


if __name__ == "__main__":
    unittest.main()
