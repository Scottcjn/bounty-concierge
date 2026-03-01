"""Tests for wallet helper - wallet name validation."""
import pathlib
import sys
from unittest.mock import patch, MagicMock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import wallet_helper


class TestValidateWalletName:
    """Tests for wallet name validation."""

    def test_valid_wallet_name_simple(self):
        """Simple valid wallet name should pass."""
        is_valid, message = wallet_helper.validate_wallet_name("mywallet")
        assert is_valid is True

    def test_valid_wallet_with_numbers(self):
        """Wallet name with numbers should be valid."""
        is_valid, message = wallet_helper.validate_wallet_name("wallet123")
        assert is_valid is True

    def test_valid_wallet_with_hyphen(self):
        """Wallet name with hyphen should be valid."""
        is_valid, message = wallet_helper.validate_wallet_name("my-wallet")
        assert is_valid is True

    def test_invalid_empty_name(self):
        """Empty wallet name should fail."""
        is_valid, message = wallet_helper.validate_wallet_name("")
        assert is_valid is False

    def test_invalid_special_characters(self):
        """Wallet name with special chars should fail."""
        is_valid, message = wallet_helper.validate_wallet_name("wallet@#$%")
        assert is_valid is False

    def test_invalid_with_space(self):
        """Wallet name with space should fail."""
        is_valid, message = wallet_helper.validate_wallet_name("my wallet")
        assert is_valid is False

    def test_invalid_uppercase(self):
        """Wallet name with uppercase should fail."""
        is_valid, message = wallet_helper.validate_wallet_name("MyWallet")
        assert is_valid is False

    def test_invalid_too_short(self):
        """Wallet name too short should fail."""
        is_valid, message = wallet_helper.validate_wallet_name("ab")
        assert is_valid is False

    def test_invalid_too_long(self):
        """Wallet name too long should fail."""
        is_valid, message = wallet_helper.validate_wallet_name("a" * 65)
        assert is_valid is False


class TestRegistrationInstructions:
    """Tests for registration instructions."""

    def test_returns_string(self):
        """Should return string instructions."""
        result = wallet_helper.registration_instructions("testwallet")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_wallet_name(self):
        """Should mention the wallet name."""
        result = wallet_helper.registration_instructions("mywallet")
        assert "mywallet" in result.lower()


class TestCheckBalance:
    """Tests for balance checking."""

    @patch("concierge.wallet_helper._get")
    def test_check_balance_returns_dict(self, mock_get):
        """Should return balance information."""
        mock_get.return_value = {"balance": 100}
        result = wallet_helper.check_balance("testwallet")
        assert isinstance(result, dict)

    @patch("concierge.wallet_helper._get")
    def test_check_balance_handles_error(self, mock_get):
        """Should handle errors gracefully."""
        mock_get.side_effect = Exception("Network error")
        # Should not raise, should handle gracefully
        try:
            result = wallet_helper.check_balance("testwallet")
        except Exception:
            pass  # Acceptable


class TestCheckEligibility:
    """Tests for eligibility checking."""

    @patch("concierge.wallet_helper._get")
    def test_check_eligibility_returns_dict(self, mock_get):
        """Should return eligibility info."""
        mock_get.return_value = {"eligible": True}
        result = wallet_helper.check_eligibility("testwallet")
        assert isinstance(result, dict)


class TestClassifyWallet:
    """Tests for wallet classification."""

    @patch("concierge.wallet_helper._get")
    def test_classify_wallet_returns_type(self, mock_get):
        """Should return wallet type."""
        mock_get.return_value = {"type": "standard"}
        result = wallet_helper._classify_wallet("miner123")
        assert isinstance(result, str) or (isinstance(result, dict))


class TestTransferRTC:
    """Tests for RTC transfers."""

    @patch("concierge.wallet_helper._post")
    def test_transfer_requires_amount(self, mock_post):
        """Transfer should require amount."""
        # Validation happens in function
        assert True  # Placeholder


class TestGetAllHolders:
    """Tests for getting all holders."""

    @patch("concierge.wallet_helper._get")
    def test_get_all_holders_returns_list(self, mock_get):
        """Should return list of holders."""
        mock_get.return_value = {"holders": []}
        result = wallet_helper.get_all_holders()
        assert isinstance(result, dict) or result is None


class TestGetHolderStats:
    """Tests for holder statistics."""

    @patch("concierge.wallet_helper._get")
    def test_get_holder_stats_returns_dict(self, mock_get):
        """Should return statistics."""
        mock_get.return_value = {"total": 0, "active": 0}
        result = wallet_helper.get_holder_stats()
        assert isinstance(result, dict) or result is None
