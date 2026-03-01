"""Tests for wallet helper functions."""

import pytest
from unittest.mock import patch, MagicMock

from concierge.wallet_helper import validate_wallet_name


class TestValidateWalletName:
    """Test wallet name validation."""

    def test_valid_simple_name(self):
        """Test simple valid wallet name."""
        is_valid, msg = validate_wallet_name("my-wallet")
        assert is_valid is True
        assert "Valid" in msg

    def test_valid_name_with_numbers(self):
        """Test valid name with numbers."""
        is_valid, _ = validate_wallet_name("wallet123")
        assert is_valid is True

    def test_valid_name_alphanumeric(self):
        """Test valid alphanumeric name."""
        is_valid, _ = validate_wallet_name("abc123xyz")
        assert is_valid is True

    def test_invalid_too_short(self):
        """Test name too short is invalid."""
        is_valid, msg = validate_wallet_name("ab")
        assert is_valid is False
        assert "at least 3 characters" in msg

    def test_invalid_too_long(self):
        """Test name too long is invalid."""
        long_name = "a" * 65
        is_valid, msg = validate_wallet_name(long_name)
        assert is_valid is False
        assert "64 characters" in msg

    def test_invalid_starts_with_hyphen(self):
        """Test name starting with hyphen is invalid."""
        is_valid, _ = validate_wallet_name("-wallet")
        assert is_valid is False

    def test_invalid_ends_with_hyphen(self):
        """Test name ending with hyphen is invalid."""
        is_valid, _ = validate_wallet_name("wallet-")
        assert is_valid is False

    def test_invalid_uppercase(self):
        """Test uppercase letters are invalid."""
        is_valid, msg = validate_wallet_name("MyWallet")
        assert is_valid is False
        assert "lowercase" in msg

    def test_invalid_special_chars(self):
        """Test special characters are invalid."""
        is_valid, _ = validate_wallet_name("wallet@123")
        assert is_valid is False

    def test_valid_with_hyphens(self):
        """Test valid name with hyphens in middle."""
        is_valid, _ = validate_wallet_name("my-test-wallet")
        assert is_valid is True

    def test_valid_minimum_length(self):
        """Test minimum valid length (3 chars)."""
        is_valid, _ = validate_wallet_name("abc")
        assert is_valid is True

    def test_valid_maximum_length(self):
        """Test maximum valid length (64 chars)."""
        name = "a" + "b" * 62 + "c"
        is_valid, _ = validate_wallet_name(name)
        assert is_valid is True

    def test_empty_name_invalid(self):
        """Test empty name is invalid."""
        is_valid, msg = validate_wallet_name("")
        assert is_valid is False
        assert "cannot be empty" in msg

    def test_none_name_invalid(self):
        """Test None name is invalid."""
        is_valid, _ = validate_wallet_name(None)
        assert is_valid is False


class TestWalletHelpersIntegration:
    """Integration tests for wallet helpers."""

    def test_wallet_name_validation_comprehensive(self):
        """Test comprehensive wallet name validation."""
        valid_names = [
            "test-wallet",
            "mywallet",
            "wallet123",
            "abc",
            "a-b-c",
        ]
        
        invalid_names = [
            "ab",  # too short
            "-wallet",  # starts with hyphen
            "wallet-",  # ends with hyphen
            "MyWallet",  # uppercase
            "wallet@",  # special char
            "wallet_name",  # underscore
        ]
        
        for name in valid_names:
            is_valid, _ = validate_wallet_name(name)
            assert is_valid is True, f"{name} should be valid"
        
        for name in invalid_names:
            is_valid, _ = validate_wallet_name(name)
            assert is_valid is False, f"{name} should be invalid"
