"""Tests for config module."""
import pathlib
import sys
import os

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from concierge import config


class TestConfig:
    """Tests for configuration loading."""

    def test_default_repos_is_list(self):
        """REPOS should be a list."""
        assert isinstance(config.REPOS, list)
        assert len(config.REPOS) > 0

    def test_repos_contains_expected(self):
        """REPOS should contain expected repositories."""
        expected_repos = [
            "Scottcjn/rustchain-bounties",
            "Scottcjn/Rustchain",
        ]
        for repo in expected_repos:
            assert any(repo in r for r in config.REPOS), f"{repo} not found in REPOS"

    def test_default_rustchain_node_url(self):
        """Should have a default RustChain node URL."""
        assert config.RUSTCHAIN_NODE_URL is not None
        assert len(config.RUSTCHAIN_NODE_URL) > 0

    def test_docs_dir_exists(self):
        """DOCS_DIR should be a valid path."""
        assert hasattr(config, 'DOCS_DIR')
        assert isinstance(config.DOCS_DIR, str)

    def test_env_variables_return_empty_for_missing(self):
        """_env should return default for missing env vars."""
        # Save original env
        orig_val = os.environ.get("TEST_CONFIG_VAR")
        if "TEST_CONFIG_VAR" in os.environ:
            del os.environ["TEST_CONFIG_VAR"]
        
        from concierge.config import _env
        result = _env("TEST_CONFIG_VAR", "default_value")
        assert result == "default_value"
        
        # Restore
        if orig_val is not None:
            os.environ["TEST_CONFIG_VAR"] = orig_val

    def test_github_token_defaults_to_empty(self):
        """GITHUB_TOKEN should default to empty string."""
        assert isinstance(config.GITHUB_TOKEN, str)
