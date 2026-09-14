"""Wallet balance process status must not depend on its output format."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from concierge.cli import main


class WalletBalanceExitTests(unittest.TestCase):
    def invoke(self, response, json_output):
        argv = ["concierge", "wallet", "balance", "example-wallet"]
        if json_output:
            argv.append("--json")
        stdout, stderr = io.StringIO(), io.StringIO()
        status = 0
        with patch("sys.argv", argv), patch(
            "concierge.cli.get_balance", return_value=response
        ) as fetch, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                main()
            except SystemExit as exc:
                status = exc.code
        fetch.assert_called_once_with("example-wallet")
        return status, stdout.getvalue(), stderr.getvalue()

    def test_failed_requests_exit_nonzero_in_both_formats(self):
        for error in ("Request to node timed out (10s)", "miner not found"):
            for json_output in (False, True):
                with self.subTest(error=error, json_output=json_output):
                    payload = {"error": error}
                    status, stdout, stderr = self.invoke(payload, json_output)
                    self.assertEqual(status, 1)
                    if json_output:
                        self.assertEqual(json.loads(stdout), payload)
                        self.assertEqual(stderr, "")
                    else:
                        self.assertEqual(stdout, "")
                        self.assertEqual(stderr, f"Error: {error}\n")

    def test_successful_requests_keep_zero_exit_and_original_output(self):
        for payload, formatted in (
            ({"miner_id": "example-wallet", "balance_rtc": 0.0}, "0.000000"),
            ({"miner_id": "example-wallet", "balance_rtc": 12.5}, "12.500000"),
            ({"miner_id": "example-wallet", "amount_i64": 12500000}, "12.500000"),
        ):
            for json_output in (False, True):
                with self.subTest(payload=payload, json_output=json_output):
                    status, stdout, stderr = self.invoke(payload, json_output)
                    self.assertEqual(status, 0)
                    self.assertEqual(stderr, "")
                    if json_output:
                        self.assertEqual(json.loads(stdout), payload)
                    else:
                        self.assertEqual(
                            stdout, f"Wallet:  example-wallet\nBalance: {formatted} RTC\n"
                        )


if __name__ == "__main__":
    unittest.main()
