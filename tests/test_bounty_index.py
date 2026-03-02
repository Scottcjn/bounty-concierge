import sys
import types
import unittest

sys.modules.setdefault(
    "requests",
    types.SimpleNamespace(RequestException=Exception),
)

from concierge.bounty_index import estimate_difficulty, parse_reward, tag_skills


class TestBountyIndex(unittest.TestCase):
    def test_parse_reward_extracts_first_rtc_amount(self):
        title = "[Bounty] Build dashboard - 40 RTC"
        body = "Bonus possible: 10 RTC"
        self.assertEqual(parse_reward(title, body), 40.0)

    def test_parse_reward_handles_thousands_separator(self):
        self.assertEqual(parse_reward("Earn 1,000 RTC", ""), 1000.0)

    def test_estimate_difficulty_respects_label_override(self):
        tier = estimate_difficulty("Any", ["micro"], 999)
        self.assertEqual(tier, "micro")

    def test_tag_skills_matches_keywords(self):
        skills = tag_skills("Write documentation for Docker setup", "Update README and docs")
        self.assertIn("documentation", skills)
        self.assertIn("docker", skills)


if __name__ == "__main__":
    unittest.main()
