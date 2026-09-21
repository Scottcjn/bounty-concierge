# SPDX-License-Identifier: MIT
"""Wallet operations via the RustChain node API.

Provides balance checks, wallet existence checks, pending transfer lookups,
name validation, registration guidance, and holder/stats tracking for bounty
hunters and admins.
"""

import os
import re

import requests

from concierge.config import RUSTCHAIN_NODE_URL

# All requests to the self-signed node use verify=False.
_VERIFY = False
_TIMEOUT = 10

_WALLET_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,62}[a-z0-9]$")

# Canonical on-chain address: literal "RTC" + sha256(pubkey)[:40] as lowercase
# hex -- exactly 43 characters.  Anything that *looks* like an address but is
# not canonical (truncated, extended, uppercase hex, non-hex) has historically
# been accepted as a destination and stranded real bounty money on unspendable
# balances, so it is rejected here rather than treated as a plain name.
_RTC_ADDRESS_HEX_LEN = 40
_RTC_ADDRESS_LEN = 3 + _RTC_ADDRESS_HEX_LEN
_RTC_ADDRESS_RE = re.compile(r"RTC[0-9a-f]{40}")
# "Address-shaped": a lowercased/mixed-case RTC prefix followed by a long hex
# run.  Used to tell an intended-but-malformed address apart from a name.
_RTC_ADDRESS_LIKE_RE = re.compile(r"rtc[0-9a-f]{20,}", re.IGNORECASE)


def is_rtc_address(value):
    """Return True only for a canonical RTC address (RTC + 40 lowercase hex).

    Uses fullmatch: a trailing newline or space is NOT canonical.
    """
    return bool(value) and _RTC_ADDRESS_RE.fullmatch(value) is not None


def looks_like_rtc_address(value):
    """Return True if *value* appears to be an RTC address (canonical or not).

    Anything with the exact uppercase ``RTC`` prefix is address-shaped: a
    valid wallet *name* is lowercase, so such a string can never be a name
    and is always an attempted address (``RTC-agent-...``, ``RTC64aa...``).
    A case-insensitive ``rtc`` prefix followed by 20+ hex characters is also
    treated as an attempted (lowercased) address.
    """
    if not value:
        return False
    if value.startswith("RTC"):
        return True
    return _RTC_ADDRESS_LIKE_RE.fullmatch(value) is not None


def validate_rtc_address(value):
    """Validate a string that is meant to be an on-chain RTC address.

    Returns:
        (is_valid, message) tuple.  The message on failure says precisely
        what is wrong (length, case, non-hex) so a contributor can fix it.
    """
    if not value:
        return (False, "Address cannot be empty.")
    if is_rtc_address(value):
        return (True, "Valid RTC address.")
    if not value.startswith("RTC"):
        return (False, "RTC address must start with the uppercase prefix 'RTC'.")
    body = value[3:]
    if len(body) != _RTC_ADDRESS_HEX_LEN:
        return (
            False,
            "RTC address must be exactly %d characters (RTC + %d hex); got %d. "
            "Truncated or extended addresses cannot receive RTC."
            % (_RTC_ADDRESS_LEN, _RTC_ADDRESS_HEX_LEN, len(value)),
        )
    if re.fullmatch(r"[0-9a-fA-F]{40}", body) and body != body.lower():
        return (False, "RTC address hex must be lowercase.")
    return (False, "RTC address must be 'RTC' followed by 40 lowercase hex "
                   "characters (0-9, a-f).")


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _get(path, params=None, headers=None):
    """Issue a GET to the RustChain node, returning parsed JSON or error dict."""
    url = f"{RUSTCHAIN_NODE_URL}{path}"
    try:
        resp = requests.get(url, params=params, headers=headers,
                            verify=_VERIFY, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"error": f"Could not connect to node at {RUSTCHAIN_NODE_URL}"}
    except requests.Timeout:
        return {"error": "Request to node timed out (10s)"}
    except requests.RequestException as exc:
        return {"error": f"Request failed: {exc}"}
    except ValueError:
        return {"error": "Node returned non-JSON response"}


def _post(path, data=None, headers=None):
    """Issue a POST to the RustChain node, returning parsed JSON or error dict."""
    url = f"{RUSTCHAIN_NODE_URL}{path}"
    try:
        resp = requests.post(url, json=data, headers=headers,
                             verify=_VERIFY, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"error": f"Could not connect to node at {RUSTCHAIN_NODE_URL}"}
    except requests.Timeout:
        return {"error": "Request to node timed out (10s)"}
    except requests.RequestException as exc:
        return {"error": f"Request failed: {exc}"}
    except ValueError:
        return {"error": "Node returned non-JSON response"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_wallet_name(name):
    """Validate a proposed wallet name.

    Two forms are accepted:

    1. A canonical on-chain address: ``RTC`` + exactly 40 lowercase hex
       characters (43 chars total).  Anything address-shaped that is not
       canonical is rejected with a specific reason -- it is *not* silently
       treated as a name, because that is how payouts get stranded.
    2. A human-readable wallet name:
        - 3 to 64 characters
        - Lowercase alphanumeric and hyphens only
        - Must start and end with a letter or digit (not a hyphen)

    Args:
        name: Proposed wallet name or address string.

    Returns:
        (is_valid, message) tuple.
    """
    if not name:
        return (False, "Wallet name cannot be empty.")
    if is_rtc_address(name):
        return (True, "Valid RTC address.")
    if looks_like_rtc_address(name):
        return validate_rtc_address(name)
    if len(name) < 3:
        return (False, "Wallet name must be at least 3 characters.")
    if len(name) > 64:
        return (False, "Wallet name must be 64 characters or fewer.")
    if name != name.lower():
        return (False, "Wallet name must be lowercase.")
    if not _WALLET_NAME_RE.match(name):
        return (
            False,
            "Wallet name may only contain lowercase letters, digits, and "
            "hyphens, and must start and end with a letter or digit.",
        )
    return (True, "Valid wallet name.")


def check_wallet_exists(name):
    """Check whether a wallet already exists on the RustChain node.

    Sends GET https://50.28.86.131/balance?miner_id=NAME and inspects the
    response.  A wallet exists if the node returns balance data without an
    error.

    Args:
        name: The wallet / miner identifier string.

    Returns:
        True if the wallet exists, False otherwise.
    """
    result = _get("/balance", params={"miner_id": name})
    if "error" in result:
        return False
    # A zero balance still means the wallet entry exists.
    return True


def get_balance(name):
    """Return the RTC balance for a given wallet / miner ID.

    Args:
        name: The miner or wallet identifier string.

    Returns:
        Parsed JSON dict from the node, e.g.
        ``{"miner_id": "...", "balance_rtc": 42.5}``
        or an error dict on failure.
    """
    return _get("/balance", params={"miner_id": name})


def get_pending_transfers(name):
    """Check the /wallet/pending endpoint for pending transfers.

    Args:
        name: The wallet / miner identifier string.

    Returns:
        A list of pending transfer dicts, or an empty list on error.
    """
    result = _get("/wallet/pending", params={"miner_id": name})
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        if "error" in result:
            return []
        return result.get("pending", [])
    return []


def register_wallet_guide(name):
    """Print instructions for registering a new wallet.

    Args:
        name: The desired wallet name.

    Returns:
        Multi-line instruction string.
    """
    valid, msg = validate_wallet_name(name)
    if not valid:
        return f"Invalid wallet name '{name}': {msg}"

    return (
        f"Wallet registration for: {name}\n"
        f"\n"
        f"Option 1 -- Claim a bounty (automatic registration)\n"
        f"  Comment on any bounty issue on GitHub with:\n"
        f"    \"I would like to claim this bounty. Wallet: {name}\"\n"
        f"  Your wallet is registered when the first RTC transfer is made.\n"
        f"\n"
        f"Option 2 -- Install the RustChain Wallet GUI\n"
        f"  Download the .deb package or PyInstaller binary from the\n"
        f"  rustchain-bounties repo releases.  The wallet generates a\n"
        f"  BIP39 seed phrase and Ed25519 keypair automatically.\n"
        f"\n"
        f"Option 3 -- Open a registration issue\n"
        f"  Create an issue on Scottcjn/rustchain-bounties titled:\n"
        f"    \"Wallet Registration: {name}\"\n"
        f"  An admin will set up your wallet entry.\n"
    )


def transfer_rtc(from_wallet, to_wallet, amount, admin_key=None):
    """Transfer RTC between wallets via the admin transfer endpoint.

    Requires the RC_ADMIN_KEY environment variable or explicit admin_key.

    Args:
        from_wallet: Source miner/wallet ID.
        to_wallet: Destination miner/wallet ID.
        amount: Amount of RTC to transfer (float).
        admin_key: Optional admin key override.

    Returns:
        Parsed JSON dict from the node (includes pending_id on success),
        or an error dict on failure.
    """
    key = admin_key or os.environ.get("RC_ADMIN_KEY", "")
    if not key:
        return {"error": "RC_ADMIN_KEY is required for transfers"}
    return _post(
        "/wallet/transfer",
        data={"from_miner": from_wallet, "to_miner": to_wallet,
              "amount_rtc": amount},
        headers={"X-Admin-Key": key},
    )


# ---------------------------------------------------------------------------
# Legacy aliases (backwards compatibility)
# ---------------------------------------------------------------------------

def check_balance(wallet_id):
    """Alias for get_balance(). Kept for backwards compatibility."""
    return get_balance(wallet_id)


def check_eligibility(wallet_id):
    """Check lottery / epoch eligibility for a wallet.

    Args:
        wallet_id: The miner or wallet identifier string.

    Returns:
        Parsed JSON dict from the node, or an error dict.
    """
    return _get("/lottery/eligibility", params={"miner_id": wallet_id})


def registration_instructions(name):
    """Alias for register_wallet_guide(). Kept for backwards compatibility."""
    return register_wallet_guide(name)


# ---------------------------------------------------------------------------
# Wallet tracking / holder stats (requires RC_ADMIN_KEY)
# ---------------------------------------------------------------------------

_FOUNDER_WALLETS = {"founder_community", "founder_founders",
                    "founder_dev_fund", "founder_team_bounty"}
_PLATFORM_WALLETS = {"bottube_platform", "minecraft_rewards_pool"}
_REDTEAM_MARKERS = ("exploit", "redteam", "replay", "clockspoof", "rl-a-")


def _classify_wallet(miner_id):
    """Return a category string for the wallet."""
    if miner_id in _FOUNDER_WALLETS:
        return "founder"
    if miner_id in _PLATFORM_WALLETS:
        return "platform"
    if any(m in miner_id for m in _REDTEAM_MARKERS):
        return "redteam"
    if is_rtc_address(miner_id):
        return "address"
    if looks_like_rtc_address(miner_id):
        # RTC-prefixed but not canonical: truncated/extended/mixed-case.
        # Balances here are unspendable until merged to a real address.
        return "malformed-address"
    if miner_id.endswith("RTC") and len(miner_id) > 30:
        return "auto-hash"
    return "named"


def get_all_holders(admin_key=None):
    """Fetch all wallet balances from the node (requires admin key).

    Returns:
        List of dicts with keys: miner_id, amount_rtc, category.
        Sorted by balance descending. None-id entries are filtered.
    """
    key = admin_key or os.environ.get("RC_ADMIN_KEY", "")
    if not key:
        return {"error": "RC_ADMIN_KEY is required for holder listing"}

    result = _get("/api/balances", headers={"X-Admin-Key": key})
    if "error" in result:
        return result

    raw = result.get("balances", [])
    holders = []
    for w in raw:
        mid = w.get("miner_id")
        if not mid:
            continue
        holders.append({
            "miner_id": mid,
            "amount_rtc": w.get("amount_rtc", 0.0),
            "category": _classify_wallet(mid),
        })
    holders.sort(key=lambda h: h["amount_rtc"], reverse=True)
    return holders


def get_holder_stats(admin_key=None):
    """Compute summary statistics across all wallets.

    Returns:
        Dict with aggregate stats, or an error dict.
    """
    holders = get_all_holders(admin_key)
    if isinstance(holders, dict) and "error" in holders:
        return holders

    total_rtc = sum(h["amount_rtc"] for h in holders)
    nonzero = [h for h in holders if h["amount_rtc"] > 0]

    by_cat = {}
    for h in holders:
        cat = h["category"]
        by_cat.setdefault(cat, {"count": 0, "rtc": 0.0})
        by_cat[cat]["count"] += 1
        by_cat[cat]["rtc"] += h["amount_rtc"]

    # Distribution tiers
    tiers = {
        "whale (>=1000)": [h for h in nonzero if h["category"] not in ("founder", "platform") and h["amount_rtc"] >= 1000],
        "large (100-999)": [h for h in nonzero if h["category"] not in ("founder", "platform") and 100 <= h["amount_rtc"] < 1000],
        "medium (10-99)": [h for h in nonzero if h["category"] not in ("founder", "platform") and 10 <= h["amount_rtc"] < 100],
        "micro (<10)": [h for h in nonzero if h["category"] not in ("founder", "platform") and h["amount_rtc"] < 10],
    }

    return {
        "total_wallets": len(holders),
        "wallets_with_balance": len(nonzero),
        "empty_wallets": len(holders) - len(nonzero),
        "total_rtc": total_rtc,
        "categories": by_cat,
        "distribution": {k: {"count": len(v), "rtc": sum(h["amount_rtc"] for h in v)} for k, v in tiers.items()},
    }


def get_active_miners():
    """Fetch the list of currently attesting miners.

    Returns:
        List of miner dicts from /api/miners, or an error dict.
    """
    result = _get("/api/miners")
    if isinstance(result, list):
        return result
    return result


def get_epoch_info():
    """Fetch current epoch/slot info.

    Returns:
        Dict with epoch, slot, enrolled_miners, etc.
    """
    return _get("/epoch")
