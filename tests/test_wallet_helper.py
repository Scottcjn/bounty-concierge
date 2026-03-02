import sys
import types
import unittest

sys.modules.setdefault(
    "requests",
    types.SimpleNamespace(
        RequestException=Exception,
        ConnectionError=Exception,
        Timeout=Exception,
    ),
)

from concierge.wallet_helper import validate_wallet_name


class TestWalletHelper(unittest.TestCase):
    def test_validate_wallet_name_accepts_valid_name(self):
        ok, msg = validate_wallet_name("wallet-123")
        self.assertTrue(ok)
        self.assertEqual(msg, "Valid wallet name.")

    def test_validate_wallet_name_rejects_uppercase(self):
        ok, msg = validate_wallet_name("Wallet-123")
        self.assertFalse(ok)
        self.assertIn("lowercase", msg)

    def test_validate_wallet_name_rejects_invalid_chars(self):
        ok, msg = validate_wallet_name("wallet_name")
        self.assertFalse(ok)
        self.assertIn("letters, digits, and hyphens", msg)

    def test_validate_wallet_name_rejects_short(self):
        ok, msg = validate_wallet_name("ab")
        self.assertFalse(ok)
        self.assertIn("at least 3", msg)


if __name__ == "__main__":
    unittest.main()
