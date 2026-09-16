# SPDX-License-Identifier: MIT
"""Multi-repo bounty aggregator for RustChain.

Fetches open issues labelled 'bounty' from configured GitHub repositories,
parses reward amounts, estimates difficulty, and tags required skills.
"""

import json
import re
import sys
from datetime import datetime, timezone

import requests

from concierge.config import GITHUB_TOKEN, REPOS


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_bounties(repos=None, token=None):
    """Fetch open bounty issues from one or more GitHub repos.

    Args:
        repos:  List of 'owner/repo' strings.  Defaults to config.REPOS.
        token:  GitHub personal-access token.  Defaults to config.GITHUB_TOKEN.

    Returns:
        List of dicts, one per bounty issue, with keys:
            repo, number, title, body, url, labels, created_at, reward_rtc,
            difficulty, skills
    """
    repos = repos or REPOS
    token = token or GITHUB_TOKEN

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    bounties = []
    for repo in repos:
        api_url = f"https://api.github.com/repos/{repo}/issues"
        params = {"labels": "bounty", "state": "open", "per_page": 100, "page": 1}

        while True:
            try:
                resp = requests.get(api_url, headers=headers, params=params, timeout=15)
                if resp.status_code == 404:
                    break
                resp.raise_for_status()
            except requests.RequestException as exc:
                print(f"[warn] failed to fetch {repo}: {exc}", file=sys.stderr)
                break

            for issue in resp.json():
                # Skip pull requests that come through the issues endpoint
                if "pull_request" in issue:
                    continue

                title = issue.get("title", "")
                body = issue.get("body", "") or ""
                label_names = [lb["name"] for lb in issue.get("labels", [])]

                reward = parse_reward(title, body)
                difficulty = estimate_difficulty(title, label_names, reward)
                skills = tag_skills(title, body)

                bounties.append({
                    "repo": repo,
                    "number": issue["number"],
                    "title": title,
                    "body": body,
                    "url": issue["html_url"],
                    "labels": label_names,
                    "created_at": issue.get("created_at", ""),
                    "reward_rtc": reward,
                    "difficulty": difficulty,
                    "skills": skills,
                })

            if not getattr(resp, "links", {}).get("next"):
                break
            params["page"] += 1

    return bounties


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_RTC_PATTERN = re.compile(r"(?<![A-Za-z0-9])(\d+(?:[.,]\d+)?)\s*RTC\b", re.IGNORECASE)


def parse_reward(title, body):
    """Extract the first RTC reward amount from a title or body string.

    Looks for patterns like '150 RTC', '1,000 RTC', '0.5 RTC'.
    Returns the amount as a float, or 0.0 if nothing found.
    """
    for text in (title, body):
        match = _RTC_PATTERN.search(text)
        if match:
            raw = match.group(1).replace(",", "")
            try:
                return float(raw)
            except ValueError:
                continue
    return 0.0


def estimate_difficulty(title, labels, reward):
    """Estimate bounty difficulty tier from reward size and labels.

    Tiers:
        micro     --  < 10 RTC
        standard  --  10-50 RTC
        major     --  50-200 RTC
        critical  --  200+ RTC

    Labels named 'critical', 'major', 'micro', or 'standard' override the
    reward-based estimate.
    """
    label_lower = [lb.lower() for lb in labels]
    for tier in ("critical", "major", "standard", "micro"):
        if tier in label_lower:
            return tier

    if reward >= 200:
        return "critical"
    if reward >= 50:
        return "major"
    if reward >= 10:
        return "standard"
    return "micro"


_SKILL_KEYWORDS = {
    "python": ["python", ".py", "flask", "django", "pip"],
    "rust": ["rust", "cargo", "rustc", ".rs"],
    "javascript": ["javascript", "node", "npm", "react", "svelte", "typescript", ".js", ".ts"],
    "docker": ["docker", "container", "dockerfile", "compose"],
    "ci/cd": ["ci/cd", "github actions", "workflow", "pipeline", "ci cd"],
    "documentation": ["documentation", "docs", "readme", "write-up", "writeup"],
    "security": ["security", "audit", "vulnerability", "red team", "penetration"],
    "social-media": ["social", "twitter", "moltbook", "bottube", "youtube", "dev.to"],
    "translation": ["translation", "translate", "i18n", "localization"],
}


def tag_skills(title, body):
    """Return a list of skill tags relevant to this bounty.

    Scans title and body for keyword matches.
    """
    combined = f"{title} {body}".lower()
    matched = []
    for skill, keywords in _SKILL_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                matched.append(skill)
                break
    return sorted(matched)


# ---------------------------------------------------------------------------
# Aggregation & formatting
# ---------------------------------------------------------------------------

def aggregate(repos=None, token=None):
    """Fetch, enrich, sort, and return all bounties as a summary dict.

    Returns:
        {
            "updated_at": ISO-8601 timestamp,
            "total_count": int,
            "bounties": [sorted list, highest RTC first],
        }
    """
    bounties = fetch_bounties(repos, token)
    bounties.sort(key=lambda b: b["reward_rtc"], reverse=True)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(bounties),
        "bounties": bounties,
    }


def format_markdown(bounties):
    """Format a list of bounty dicts as a Markdown table.

    Columns: #, Repo, Title, RTC, Tier, Skills
    """
    lines = [
        "| # | Repo | Title | RTC | Tier | Skills |",
        "|---|------|-------|-----|------|--------|",
    ]
    for b in bounties:
        repo_short = b["repo"].split("/")[-1]
        skills = ", ".join(b["skills"]) if b["skills"] else "-"
        title_short = b["title"][:60]
        lines.append(
            f"| {b['number']} | {repo_short} | {title_short} | "
            f"{b['reward_rtc']:.1f} | {b['difficulty']} | {skills} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    data = aggregate()
    print(json.dumps(data, indent=2, default=str))
