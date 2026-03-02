import sys
import types
import unittest

sys.modules.setdefault(
    "requests",
    types.SimpleNamespace(RequestException=Exception),
)

from concierge.faq_engine import fuzzy_match


class TestFaqEngine(unittest.TestCase):
    def test_fuzzy_match_returns_expected_answer(self):
        entries = {
            "what is rtc": "RTC is RustChain token",
            "how do payouts work": "Payouts occur after merge",
        }

        key, answer, score = fuzzy_match("Can you explain what rtc is?", entries)

        self.assertEqual(key, "what is rtc")
        self.assertEqual(answer, "RTC is RustChain token")
        self.assertGreater(score, 0.5)

    def test_fuzzy_match_handles_empty_question(self):
        key, answer, score = fuzzy_match("   ", {"what is rtc": "x"})
        self.assertEqual((key, answer, score), ("", "", 0.0))


if __name__ == "__main__":
    unittest.main()
