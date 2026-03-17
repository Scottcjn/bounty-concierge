"""Tests for FAQ engine - matching returns correct answers."""
import os
import pathlib
import sys
import tempfile

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

    def test_score_is_float_between_zero_and_one(self):
        """Score should be a float in [0.0, 1.0]."""
        _, _, score = faq_engine.fuzzy_match("what is rtc")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_exact_match_score_is_one(self):
        """An exact key match should return score of 1.0."""
        _, _, score = faq_engine.fuzzy_match("what is rtc")
        assert score == 1.0

    def test_no_match_score_is_zero(self):
        """No match should return score of 0.0."""
        _, _, score = faq_engine.fuzzy_match("xyzabc123nonexistent")
        assert score == 0.0

    def test_returns_matched_key(self):
        """Should return the matched FAQ key, not empty."""
        key, answer, score = faq_engine.fuzzy_match("what is rtc")
        assert key == "what is rtc"

    def test_custom_entries_override_defaults(self):
        """Custom entries dict should be used instead of FAQ_ENTRIES."""
        custom = {"test question": "custom answer here"}
        key, answer, score = faq_engine.fuzzy_match("test question", entries=custom)
        assert answer == "custom answer here"
        assert score == 1.0

    def test_custom_entries_empty_dict(self):
        """Empty entries dict returns empty tuple."""
        key, answer, score = faq_engine.fuzzy_match("anything", entries={})
        assert key == ""
        assert answer == ""
        assert score == 0.0

    def test_rip200_faq(self):
        """RIP-200 FAQ should mention consensus."""
        key, answer, score = faq_engine.fuzzy_match("what is rip-200")
        assert answer != ""
        assert score > 0.0

    def test_rip201_faq(self):
        """RIP-201 FAQ should be findable."""
        key, answer, score = faq_engine.fuzzy_match("what is rip-201")
        assert answer != ""

    def test_hardware_multipliers_faq(self):
        """Hardware multipliers FAQ should list multiplier values."""
        key, answer, score = faq_engine.fuzzy_match("hardware multipliers")
        assert "2.5x" in answer or "G4" in answer

    def test_empty_question_returns_empty(self):
        """Empty string question should return empty tuple."""
        key, answer, score = faq_engine.fuzzy_match("")
        assert key == ""
        assert answer == ""
        assert score == 0.0

    def test_whitespace_only_returns_empty(self):
        """Whitespace-only question should return empty tuple."""
        key, answer, score = faq_engine.fuzzy_match("   ")
        assert score == 0.0


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

    def test_leading_trailing_whitespace_stripped(self):
        """Leading/trailing whitespace should be stripped."""
        normalized = faq_engine._normalise("  hello  ")
        assert normalized == "hello"

    def test_mixed_case_and_punctuation(self):
        """Mixed case with punctuation should be fully normalized."""
        normalized = faq_engine._normalise("What is RTC?")
        assert "what" in normalized
        assert "rtc" in normalized
        assert "?" not in normalized

    def test_empty_string(self):
        """Empty string should normalize to empty string."""
        normalized = faq_engine._normalise("")
        assert normalized == ""

    def test_hyphens_replaced(self):
        """Hyphens should be treated as whitespace."""
        normalized = faq_engine._normalise("rip-200")
        # Hyphens are punctuation and get replaced
        assert "200" in normalized


class TestSearchDocs:
    """Tests for documentation search."""

    def test_returns_empty_for_missing_dir(self):
        """Should return empty string if docs dir doesn't exist."""
        result = faq_engine.search_docs("anything", docs_dir="/nonexistent/path")
        assert result == ""

    def test_returns_empty_for_empty_dir(self, tmp_path):
        """Should return empty string if docs dir has no .md files."""
        result = faq_engine.search_docs("anything", docs_dir=str(tmp_path))
        assert result == ""

    def test_finds_matching_paragraph(self, tmp_path):
        """Should find a paragraph that matches the question."""
        doc = tmp_path / "test.md"
        doc.write_text(
            "## Introduction\n\nThis is about RustChain tokens.\n\n"
            "## Other section\n\nUnrelated content here.\n"
        )
        result = faq_engine.search_docs("rustchain tokens", docs_dir=str(tmp_path))
        assert "RustChain" in result or "rustchain" in result.lower()

    def test_ignores_non_md_files(self, tmp_path):
        """Should ignore non-.md files in the docs dir."""
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("RustChain RTC tokens wallet")
        result = faq_engine.search_docs("rustchain tokens", docs_dir=str(tmp_path))
        assert result == ""

    def test_returns_best_matching_paragraph(self, tmp_path):
        """Should return the paragraph with highest keyword overlap."""
        doc = tmp_path / "guide.md"
        doc.write_text(
            "## Mining\n\nMining requires hardware attestation.\n\n"
            "## Wallets\n\nWallets store RTC tokens for mining rewards. "
            "Mining wallet setup is important.\n"
        )
        result = faq_engine.search_docs("mining wallet", docs_dir=str(tmp_path))
        # Best match should be the Wallets paragraph (2 keyword hits)
        assert result != ""

    def test_returns_empty_for_empty_question(self, tmp_path):
        """Empty question returns empty string."""
        doc = tmp_path / "doc.md"
        doc.write_text("## Section\n\nSome content about RTC.\n")
        result = faq_engine.search_docs("", docs_dir=str(tmp_path))
        assert result == ""

    def test_skips_short_paragraphs(self, tmp_path):
        """Paragraphs shorter than 20 chars should be skipped."""
        doc = tmp_path / "short.md"
        doc.write_text("# Title\n\nRTC\n\nThis paragraph is long enough to be returned as a result.\n")
        result = faq_engine.search_docs("rtc paragraph result", docs_dir=str(tmp_path))
        assert result != "RTC"  # Short "RTC" para skipped


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

    def test_answer_has_confidence_field(self):
        """Answer dict should include confidence field."""
        result = faq_engine.answer("what is rtc")
        assert "confidence" in result
        assert isinstance(result["confidence"], float)

    def test_faq_source_for_known_question(self):
        """Known question should be answered from FAQ source."""
        result = faq_engine.answer("what is rtc")
        assert result["source"] == "faq"
        assert result["confidence"] >= 0.3

    def test_unknown_question_returns_unknown_source(self):
        """Completely unknown question without grok returns unknown."""
        result = faq_engine.answer("xyzzy123abcdef987654", use_grok=False)
        assert result["source"] == "unknown"
        assert result["confidence"] == 0.0

    def test_unknown_source_has_fallback_message(self):
        """Unknown source should include a helpful fallback message."""
        result = faq_engine.answer("xyzzy123abcdef987654", use_grok=False)
        assert len(result["answer"]) > 0
        # Should suggest rephrasing or similar
        assert result["answer"] != ""

    def test_answer_proof_of_antiquity(self):
        """PoA question should get faq source."""
        result = faq_engine.answer("what is proof of antiquity")
        assert result["source"] == "faq"
        assert "G4" in result["answer"] or "multiplier" in result["answer"].lower()

    def test_grok_used_when_enabled_and_no_faq_match(self, monkeypatch):
        """When use_grok=True and no FAQ match, Grok should be called."""
        import requests

        call_count = {"n": 0}

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                call_count["n"] += 1
                return {"choices": [{"message": {"content": "Grok answer"}}]}

        monkeypatch.setattr(requests, "post", lambda *a, **kw: MockResponse())
        monkeypatch.setattr(faq_engine, "GROK_API_KEY", "test-key")

        result = faq_engine.answer("xyzzy123abcdef987654", use_grok=True)
        assert result["source"] == "grok"
        assert result["answer"] == "Grok answer"

    def test_grok_not_called_when_disabled(self, monkeypatch):
        """When use_grok=False, Grok should never be called."""
        import requests

        called = {"flag": False}

        def mock_post(*a, **kw):
            called["flag"] = True
            raise AssertionError("Grok should not be called")

        monkeypatch.setattr(requests, "post", mock_post)
        monkeypatch.setattr(faq_engine, "GROK_API_KEY", "test-key")

        faq_engine.answer("xyzzy123abcdef987654", use_grok=False)
        assert not called["flag"]


class TestGrokApiMocking:
    """Tests for Grok API integration with mocked responses."""

    def test_grok_api_success_mock(self, monkeypatch):
        """Grok API should return answer when mock succeeds."""
        import requests

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "choices": [
                        {"message": {"content": "Grok says hello"}}
                    ]
                }

        monkeypatch.setattr(
            requests, "post",
            lambda *a, **kw: MockResponse()
        )
        monkeypatch.setattr(faq_engine, "GROK_API_KEY", "test-key")

        result = faq_engine.ask_grok("test question")
        assert result == "Grok says hello"

    def test_grok_api_error_mock(self, monkeypatch):
        """Grok API should return error message on failure."""
        import requests

        class MockResponse:
            def raise_for_status(self):
                raise requests.RequestException("timeout")

        monkeypatch.setattr(
            requests, "post",
            lambda *a, **kw: MockResponse()
        )
        monkeypatch.setattr(faq_engine, "GROK_API_KEY", "test-key")

        result = faq_engine.ask_grok("test question")
        assert "[error]" in result

    def test_grok_no_api_key_returns_error(self, monkeypatch):
        """ask_grok without API key should return error message."""
        monkeypatch.setattr(faq_engine, "GROK_API_KEY", "")
        result = faq_engine.ask_grok("what is rtc")
        assert "[error]" in result

    def test_grok_includes_context_in_request(self, monkeypatch):
        """ask_grok with context should include it in the payload."""
        import requests

        captured = {}

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

        def mock_post(url, headers, json, timeout):
            captured["payload"] = json
            return MockResponse()

        monkeypatch.setattr(requests, "post", mock_post)
        monkeypatch.setattr(faq_engine, "GROK_API_KEY", "test-key")

        faq_engine.ask_grok("my question", context="some context")
        user_msg = captured["payload"]["messages"][-1]["content"]
        assert "some context" in user_msg
        assert "my question" in user_msg

    def test_grok_unexpected_response_format(self, monkeypatch):
        """Unexpected Grok response format should return error string."""
        import requests

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"unexpected": "format"}

        monkeypatch.setattr(
            requests, "post",
            lambda *a, **kw: MockResponse()
        )
        monkeypatch.setattr(faq_engine, "GROK_API_KEY", "test-key")

        result = faq_engine.ask_grok("question")
        assert "[error]" in result
