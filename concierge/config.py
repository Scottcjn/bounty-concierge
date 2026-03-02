"""Configuration module for RustChain Bounty Concierge.

All settings are loaded from environment variables with sensible defaults.
"""

import os


def _env(key, default=""):
    """Read an environment variable, returning default if unset or empty."""
    return os.environ.get(key, default) or default


# --- API tokens (optional -- features degrade gracefully without them) ---

GITHUB_TOKEN = _env("GITHUB_TOKEN")
RC_ADMIN_KEY = _env("RC_ADMIN_KEY")
DEVTO_API_KEY = _env("DEVTO_API_KEY")
GROK_API_KEY = _env("GROK_API_KEY")
SAASCITY_KEY = _env("SAASCITY_KEY")

# --- RustChain node ---

RUSTCHAIN_NODE_URL = _env("RUSTCHAIN_NODE_URL", "https://50.28.86.131")

# --- Repositories to aggregate bounties from ---

REPOS = [
    "Scottcjn/rustchain-bounties",
    "Scottcjn/Rustchain",
    "Scottcjn/bottube",
    "Scottcjn/beacon-skill",
    "Scottcjn/ram-coffers",
    "Scottcjn/claude-code-power8",
    "Scottcjn/nvidia-power8-patches",
    "Scottcjn/llama-cpp-power8",
    "Scottcjn/grazer-skill",
]

# --- Discord economy NAS (for wallet migration) ---

DISCORD_NAS_HOST = _env("DISCORD_NAS_HOST", "192.168.0.160")
DISCORD_NAS_USER = _env("DISCORD_NAS_USER", "sophia")
DISCORD_NAS_PASSWORD = _env("DISCORD_NAS_PASSWORD")
DISCORD_DB_PATH = _env(
    "DISCORD_DB_PATH",
    "/mnt/nvme/sophia/databases/rustcoin_economy.db",
)
MIGRATION_SOURCE_WALLET = _env("MIGRATION_SOURCE_WALLET", "founder_team_bounty")

# --- Docs directory (for FAQ doc search) ---

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
