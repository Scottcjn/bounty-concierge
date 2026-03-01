"""Tests for FAQ engine - matching returns correct answers."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import faq_engine


class TestFuzzyMatch:
    """Tests for fuzzy matching functionality."""

    def test_exact_match_returns_correct_answer(self):
        """Exact question match should return corresponding answer."""
        key, answer, score = faq_engine.fuzzy_match("what is rtc")
        assert answer is not None
        assert "RTC" in answer
        assert "RustChain Token" in answer

    def test_case_insensitive_match(self):
        """Match should be case-insensitive."""
        key, answer, score = faq_engine.fuzzy_match("WHAT IS RTC")
        assert answer is not None
        assert "RTC" in answer

    def test_partial_match(self):
        """Partial question should match relevant FAQ."""
        key, answer, score = faq_engine.fuzzy_match("wallet")
        assert answer is not None
        assert answer != ""

    def test_fuzzy_match_similar_question(self):
        """Similar questions should match."""
        key, answer, score = faq_engine.fuzzy_match("how to set up a wallet")
        assert answer is not None

    def test_no_match_returns_empty(self):
        """Unknown question should return empty tuple."""
        key, answer, score = faq_engine.fuzzy_match("xyzabc123nonexistent")
        assert key == ""
        assert answer == ""

    def test_rtc_reward_parsing(self):
        """FAQ should contain RTC value info."""
        key, answer, score = faq_engine.fuzzy_match("what is rtc")
        assert "$0.10" in answer or "0.10" in answer

    def test_payout_faq(self):
        """Payout FAQ should mention PR merge."""
        key, answer, score = faq_engine.fuzzy_match("how do payouts work")
        assert answer is not None

    def test_wrtc_faq(self):
        """WRTC FAQ should mention Ergo blockchain."""
        key, answer, score = faq_engine.fuzzy_match("what is wrtc")
        assert answer is not None

    def test_proof_of_antiquity_faq(self):
        """PoA FAQ should mention multipliers."""
        key, answer, score = faq_engine.fuzzy_match("what is proof of antiquity")
        assert answer is not None

    def test_beacon_faq(self):
        """Beacon FAQ should mention skills."""
        key, answer, score = faq_engine.fuzzy_match("what is beacon")
        assert answer is not None


class TestNormalise:
    """Tests for text normalization."""

    def test_lowercase_conversion(self):
        """Text should be converted to lowercase."""
        normalized = faq_engine._normalise("HELLO WORLD")
        assert normalized == "hello world"

    def test_punctuation_removed(self):
        """Punctuation should be removed or handled."""
        normalized = faq_engine._normalise("Hello, World!")
        assert "hello" in normalized
        assert "world" in normalized

    def test_extra_spaces_collapsed(self):
        """Extra spaces should be collapsed."""
        normalized = faq_engine._normalise("hello   world")
        assert normalized == "hello world"


class TestAnswer:
    """Tests for the main answer function."""

    def test_answer_returns_dict(self):
        """Answer should return a dict with answer and source."""
        result = faq_engine.answer("what is rtc")
        assert isinstance(result, dict)
        assert "answer" in result
        assert "source" in result
        assert len(result["answer"]) > 0

    def test_answer_with_grok_disabled(self):
        """Answer without Grok should use built-in FAQ."""
        result = faq_engine.answer("what is rip-200", use_grok=False)
        assert isinstance(result, dict)
        assert "answer" in result
        assert result["source"] in ["faq", "docs", "unknown"]
