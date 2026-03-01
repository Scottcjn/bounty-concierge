"""Tests for FAQ engine."""

import pytest
from unittest.mock import patch, MagicMock

from concierge.faq_engine import FAQ_ENTRIES


class TestFAQEntries:
    """Test FAQ entries data."""

    def test_faq_entries_not_empty(self):
        """Test FAQ_ENTRIES is not empty."""
        assert len(FAQ_ENTRIES) > 0

    def test_all_faq_entries_have_content(self):
        """Test all FAQ entries have non-empty content."""
        for key, value in FAQ_ENTRIES.items():
            assert key.strip() != ""
            assert value.strip() != ""
            assert len(value) > 10

    def test_rtc_faq_entry_exists(self):
        """Test RTC explanation FAQ exists."""
        assert "what is rtc" in FAQ_ENTRIES
        assert "RustChain Token" in FAQ_ENTRIES["what is rtc"]

    def test_wallet_setup_faq_exists(self):
        """Test wallet setup FAQ exists."""
        assert "how do i set up a wallet" in FAQ_ENTRIES

    def test_payout_faq_exists(self):
        """Test payout FAQ exists."""
        assert "how do payouts work" in FAQ_ENTRIES

    def test_poa_faq_exists(self):
        """Test Proof of Antiquity FAQ exists."""
        assert "what is proof of antiquity" in FAQ_ENTRIES
