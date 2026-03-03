"""Cross-platform engagement helpers for the RustChain ecosystem.

Star repos, check Dev.to stats, upvote on SaaSCity, and generate
social-bounty proof.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import requests

from concierge import config


# ---------------------------------------------------------------------------
# SaaSCity listing slugs for RustChain ecosystem products
# ---------------------------------------------------------------------------

SAASCITY_LISTINGS: Dict[str, str] = {
    "RustChain": "rustchain",
    "BoTTube": "bottube",
}

SAASCITY_API_BASE = "https://www.saascity.com/api"


# ---------------------------------------------------------------------------
# GitHub star helpers
# ---------------------------------------------------------------------------

def star_repo(owner: str, repo: str, token: str) -> bool:
    """Star a single GitHub repository.

    Uses PUT /user/starred/{owner}/{repo} which is idempotent -- starring an
    already-starred repo is a no-op that still returns 204.

    Returns True on success (HTTP 204), False otherwise.
    """
    url = f"https://api.github.com/user/starred/{owner}/{repo}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        resp = requests.put(url, headers=headers, timeout=15)
        return resp.status_code == 204
    except requests.RequestException:
        return False


def star_all_ecosystem_repos(token: str) -> Dict[str, bool]:
    """Star every repository listed in config.REPOS.

    Returns a dict mapping ``"owner/repo"`` to a boolean success flag.
    """
    results: Dict[str, bool] = {}
    for full_name in config.REPOS:
        owner, repo = full_name.split("/", 1)
        results[full_name] = star_repo(owner, repo, token)
    return results


# ---------------------------------------------------------------------------
# Dev.to article stats
# ---------------------------------------------------------------------------

def check_devto_articles(api_key: str) -> List[dict]:
    """Fetch the authenticated user's Dev.to articles.

    Returns a list of dicts with keys: title, url, page_views,
    positive_reactions.
    """
    url = "https://dev.to/api/articles/me"
    headers = {"api-key": api_key, "Accept": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    articles = []
    for item in resp.json():
        articles.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "page_views": item.get("page_views_count", 0),
                "positive_reactions": item.get("positive_reactions_count", 0),
            }
        )
    return articles


# ---------------------------------------------------------------------------
# Engagement proof generation
# ---------------------------------------------------------------------------

def generate_engagement_proof(platform: str, action: str, proof_url: str) -> str:
    """Format a markdown comment suitable for claiming a social bounty.

    Parameters
    ----------
    platform : str
        Name of the platform (e.g. "Twitter", "Dev.to", "Moltbook").
    action : str
        What was done (e.g. "shared article", "starred repos", "upvoted").
    proof_url : str
        A public URL that proves the action was taken.

    Returns
    -------
    str
        Markdown-formatted proof comment ready to paste into a GitHub issue.
    """
    return (
        f"**Engagement Proof**\n\n"
        f"- **Platform:** {platform}\n"
        f"- **Action:** {action}\n"
        f"- **Proof:** [{proof_url}]({proof_url})\n\n"
        f"Requesting payout per the bounty terms."
    )


# ---------------------------------------------------------------------------
# SaaSCity upvote integration
# ---------------------------------------------------------------------------

class SaaSCityError(Exception):
    """Raised when a SaaSCity API call fails."""


def saascity_upvote(
    api_key: Optional[str] = None,
    listings: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
) -> Dict[str, bool]:
    """Upvote RustChain and BoTTube listings on SaaSCity.

    Sends a POST request to the SaaSCity upvote endpoint for each listing
    slug.  The API key is read from the ``SAASCITY_KEY`` environment variable
    if not supplied directly.

    Parameters
    ----------
    api_key : str, optional
        SaaSCity API key.  Defaults to ``config.SAASCITY_KEY`` (env var
        ``SAASCITY_KEY``).
    listings : dict, optional
        Mapping of display name -> slug to upvote.  Defaults to
        ``SAASCITY_LISTINGS`` (RustChain + BoTTube).
    dry_run : bool
        When True, print what would be upvoted and return without making any
        network calls.

    Returns
    -------
    dict
        Mapping of display name -> True (success) / False (failure).

    Raises
    ------
    SaaSCityError
        If ``api_key`` is not available and ``SAASCITY_KEY`` is unset.
    """
    resolved_key = api_key or config.SAASCITY_KEY
    if not resolved_key and not dry_run:
        raise SaaSCityError(
            "SAASCITY_KEY environment variable is required. "
            "Obtain an API key at https://www.saascity.com and set "
            "SAASCITY_KEY=<your-key>."
        )

    target_listings = listings if listings is not None else SAASCITY_LISTINGS

    if dry_run:
        print("[dry-run] Would upvote the following SaaSCity listings:")
        for name, slug in target_listings.items():
            print(f"  {name}  ->  {SAASCITY_API_BASE}/listings/{slug}/upvote")
        return {name: True for name in target_listings}

    results: Dict[str, bool] = {}
    headers = {
        "Authorization": f"Bearer {resolved_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    for name, slug in target_listings.items():
        url = f"{SAASCITY_API_BASE}/listings/{slug}/upvote"
        try:
            resp = requests.post(url, headers=headers, timeout=15)
            # 200 = upvoted, 201 = upvoted (created), 204 = success no-content
            # 409 = already upvoted today (idempotent -- treat as success)
            if resp.status_code in (200, 201, 204, 409):
                results[name] = True
            else:
                results[name] = False
        except requests.RequestException:
            results[name] = False

    return results
