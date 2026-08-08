# SPDX-License-Identifier: MIT
"""Cross-platform bounty announcement formatter and dispatcher.

This is a *simplified* wrapper.  For full posting with Moltbook math
solving and agent rotation, use ``bounty_poster.py`` directly.
"""

from __future__ import annotations

from typing import Dict, List


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_announcement(bounties: List[dict]) -> Dict[str, str]:
    """Create platform-specific formatted content from a list of bounties.

    Each bounty dict is expected to have at least: ``title``, ``rtc``,
    ``url``, and optionally ``difficulty`` and ``labels``.

    Returns a dict with three keys:

    * ``"short"``  -- Twitter-length (<=280 chars).
    * ``"medium"`` -- 4claw / AgentChan length.
    * ``"long"``   -- Moltbook / Dev.to length.
    """
    if not bounties:
        return {"short": "", "medium": "", "long": ""}

    # -- short (Twitter) ---------------------------------------------------
    top = bounties[0]
    short = (
        f"New RustChain bounty: {top['title']} "
        f"({top.get('rtc', '?')} RTC) "
        f"{top.get('url', '')}"
    )
    if len(short) > 280:
        short = short[:277] + "..."

    # -- medium (4claw / AgentChan) ----------------------------------------
    lines = ["Open RustChain bounties:\n"]
    for b in bounties[:5]:
        lines.append(
            f"- {b['title']} | {b.get('rtc', '?')} RTC | {b.get('url', '')}"
        )
    if len(bounties) > 5:
        lines.append(f"\n+{len(bounties) - 5} more at "
                      "https://github.com/Scottcjn/rustchain-bounties/issues")
    medium = "\n".join(lines)

    # -- long (Moltbook / Dev.to) ------------------------------------------
    long_lines = [
        "# Open RustChain Bounties\n",
        "| Title | RTC | Difficulty | Link |",
        "|-------|-----|------------|------|",
    ]
    for b in bounties:
        diff = b.get("difficulty", "--")
        long_lines.append(
            f"| {b['title']} | {b.get('rtc', '?')} | {diff} "
            f"| [link]({b.get('url', '')}) |"
        )
    long_lines.append(
        "\n1 RTC = $0.15 USD.  "
        "See https://github.com/Scottcjn/bounty-concierge for details."
    )
    long = "\n".join(long_lines)

    return {"short": short, "medium": medium, "long": long}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def post_announcement(platform: str, content: str, platform_config: dict) -> dict:
    """Post *content* to the specified *platform*.

    Parameters
    ----------
    platform : str
        One of ``"moltbook"``, ``"4claw"``, ``"agentchan"``, ``"devto"``,
        ``"twitter"``.
    content : str
        The formatted text to post.
    platform_config : dict
        Platform-specific settings (API keys, submolt names, etc.).

    Returns
    -------
    dict
        ``{"ok": bool, "url": str, "error": str}``
    """
    try:
        handler = _PLATFORM_HANDLERS.get(platform)
        if handler is None:
            return {
                "ok": False,
                "url": "",
                "error": f"Unknown platform: {platform}",
            }
        return handler(content, platform_config)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": "", "error": str(exc)}


# ---------------------------------------------------------------------------
# Per-platform handlers (stubs -- extend as needed)
# ---------------------------------------------------------------------------

def _post_moltbook(content: str, cfg: dict) -> dict:
    import requests

    api_key = cfg.get("api_key", "")
    submolt = cfg.get("submolt", "rustchain")
    title = cfg.get("title", "Open RustChain Bounties")

    resp = requests.post(
        "https://www.moltbook.com/api/v1/posts",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "content": content,
            "title": title,
            "submolt_name": submolt,
        },
        timeout=30,
    )
    data = resp.json() if resp.ok else {}
    url = data.get("url", "")
    return {"ok": resp.ok, "url": url, "error": "" if resp.ok else resp.text}


def _post_stub(content: str, cfg: dict) -> dict:
    """Placeholder for platforms not yet wired up."""
    return {
        "ok": False,
        "url": "",
        "error": "Platform handler not yet implemented.",
    }


_PLATFORM_HANDLERS = {
    "moltbook": _post_moltbook,
    "4claw": _post_stub,
    "agentchan": _post_stub,
    "devto": _post_stub,
    "twitter": _post_stub,
}
