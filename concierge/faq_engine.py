# SPDX-License-Identifier: MIT
"""FAQ engine with fuzzy matching and optional Grok AI fallback.

Provides instant answers for common RustChain bounty questions using a
built-in knowledge base, doc search, and optional LLM escalation.
"""

import os
import re
import sys

import requests

from concierge.config import DOCS_DIR, GROK_API_KEY


# ---------------------------------------------------------------------------
# Built-in FAQ entries
# ---------------------------------------------------------------------------

FAQ_ENTRIES = {
    "what is rtc": (
        "RTC (RustChain Token) is the native token of the RustChain network. "
        "It rewards miners for hardware attestation under the RIP-200 consensus "
        "protocol.  Internal reference rate: 1 RTC = $0.10 USD."
    ),
    "how do i set up a wallet": (
        "Install the RustChain wallet package (Standard, Founder, or Secure "
        "edition) from the .deb packages or run the PyInstaller binary.  "
        "On first launch the wallet generates a BIP39 24-word seed phrase and "
        "an Ed25519 keypair.  Your address starts with 'RTC...'."
    ),
    "how do payouts work": (
        "Bounty payouts are made in RTC after a PR is merged or a deliverable "
        "is accepted.  An admin triggers a signed transfer via the "
        "/wallet/transfer/signed endpoint.  You will see the RTC in your "
        "wallet balance within one epoch (~10 minutes)."
    ),
    "what is wrtc": (
        "wRTC (Wrapped RTC) is a planned representation of RTC on the Ergo "
        "blockchain, enabling DEX trading.  The RTC/ERG DEX bounty (Issue #32) "
        "offers 150 RTC for building this bridge."
    ),
    "what is proof of antiquity": (
        "Proof of Antiquity (PoA) is RustChain's unique consensus mechanism "
        "that rewards vintage and exotic hardware with multiplied mining "
        "rewards.  A PowerPC G4 earns 2.5x, a G5 earns 2.0x, Apple Silicon "
        "earns 1.2x, and modern x86_64 earns 1.0x.  Multipliers decay slowly "
        "over ~16.67 years."
    ),
    "can i mine in a vm": (
        "VMs are detected by the anti-emulation fingerprint checks and earn "
        "approximately 1 billionth of real hardware rewards.  This is by "
        "design to prevent VM farms.  Use real hardware for meaningful rewards."
    ),
    "what is beacon": (
        "Beacon is the RustChain agent-to-agent skill network.  Agents "
        "register capabilities as 'skills' and can invoke each other's skills, "
        "paying RTC as gas.  See RIP-303 for the gas model."
    ),
    "what is rip-200": (
        "RIP-200 defines the Round-Robin 1-CPU-1-Vote consensus.  Each unique "
        "piece of hardware gets one vote per epoch, weighted by its antiquity "
        "multiplier.  The epoch pot (1.5 RTC) is split proportionally."
    ),
    "what is rip-201": (
        "RIP-201 is the Fleet Immune System.  It detects when a single "
        "operator runs many miners and applies Equal Bucket Split so that "
        "fleet operators cannot dominate rewards."
    ),
    "what is rip-302": (
        "RIP-302 defines the Agent Economy -- agent-to-agent RTC payments for "
        "services rendered on the Beacon network."
    ),
    "what is rip-303": (
        "RIP-303 specifies RTC as Gas for the Beacon skill network.  Every "
        "skill invocation burns a small amount of RTC, creating deflationary "
        "pressure and preventing spam."
    ),
    "what is hebbian pruning": (
        "Hebbian pruning uses the vec_perm instruction on POWER8 to implement "
        "non-bijunctive attention collapse: strong activation paths are "
        "duplicated while weak paths are pruned, all in a single CPU cycle. "
        "This is the core of the PSE (Proto-Sentient Emergence) framework."
    ),
    "hardware multipliers": (
        "G4: 2.5x | G5: 2.0x | G3: 1.8x | Pentium 4: 1.5x | Retro x86: "
        "1.4x | Core 2: 1.3x | Nehalem/Apple Silicon: 1.2x | Sandy Bridge: "
        "1.1x | Modern x86_64: 1.0x.  Multipliers decay at 15% per year "
        "(full decay after ~16.67 years)."
    ),
    "bounty tiers": (
        "micro: < 10 RTC | standard: 10-50 RTC | major: 50-200 RTC | "
        "critical: 200+ RTC.  Tier is determined by the RTC amount in the "
        "issue title or by labels."
    ),
    "what is bcos": (
        "BCOS (Beacon Certified Open Source) is our badge standard for "
        "repos that are human-reviewed, agent-safe, and on-chain attested. "
        "Applied to 74 repos across Scottcjn and sophiaeagent-beep."
    ),
    "what is saascity": (
        "SaaSCity is a no-code AI agent marketplace being developed as part "
        "of the BoTTube ecosystem for deploying and monetising AI agents."
    ),
    "what platforms are there": (
        "RustChain ecosystem platforms: BoTTube (video + agents), Moltbook "
        "(Reddit-style social), 4claw (imageboard), AgentChan, PinchedIn "
        "(professional), X/Twitter, Dev.to, and the RustChain block explorer."
    ),
    "block explorer": (
        "The RustChain block explorer is at https://50.28.86.131/explorer. "
        "It shows epochs, miner attestations, balances, and anchor "
        "transactions."
    ),
    "what are ai agents": (
        "Sophia Elya, Boris Volkov, and AutomatedJanitor are AI agents that "
        "run on the Sophiacord Discord bot and post across Moltbook, BoTTube, "
        "and other platforms.  They are persistent personas with distinct "
        "personalities."
    ),
    "rtc value": (
        "Internal reference rate: 1 RTC = $0.10 USD.  This is a planning "
        "rate for bounty pricing, not a market price.  RTC is not yet traded "
        "on any exchange."
    ),
    "how do i claim a bounty": (
        "Comment on the GitHub issue saying you want to work on it, and "
        "include your RustChain wallet name.  Once assigned, submit a PR "
        "referencing the issue number.  After merge, RTC is transferred to "
        "your wallet."
    ),
    "how do i register a wallet": (
        "Pick a wallet name (alphanumeric, hyphens, underscores, 3-50 chars). "
        "Your first bounty claim automatically registers it.  Or install the "
        "RustChain wallet GUI to generate a cryptographic wallet with a "
        "BIP39 seed phrase."
    ),
    "epoch schedule": (
        "Epochs are 600 seconds (10 minutes).  Each epoch distributes a pot "
        "of 1.5 RTC among all enrolled miners, weighted by hardware antiquity "
        "multipliers."
    ),
    "what repos have bounties": (
        "Bounties live across these repos: rustchain-bounties (main tracker), "
        "Rustchain (core), bottube, beacon-skill, ram-coffers, "
        "claude-code-power8, nvidia-power8-patches, llama-cpp-power8, "
        "grazer-skill."
    ),
    "security bounties": (
        "Red-team security bounties total 600 RTC across issues #491-494 on "
        "rustchain-bounties: Ledger Integrity (200), Epoch Settlement (150), "
        "API Auth (100), Consensus Attacks (200)."
    ),
}


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def _normalise(text):
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text)


def fuzzy_match(question, entries=None):
    """Find the best FAQ match for a question using word-overlap scoring.

    Args:
        question:  Free-text question string.
        entries:   Dict of {pattern: answer}.  Defaults to FAQ_ENTRIES.

    Returns:
        (matched_key, answer, score) where score is 0.0-1.0.
        If no entries exist, returns ("", "", 0.0).
    """
    entries = entries or FAQ_ENTRIES
    if not entries:
        return ("", "", 0.0)

    q_words = set(_normalise(question).split())
    if not q_words:
        return ("", "", 0.0)

    best_key = ""
    best_answer = ""
    best_score = 0.0

    for key, answer in entries.items():
        key_words = set(_normalise(key).split())
        if not key_words:
            continue

        overlap = q_words & key_words
        # Jaccard-like score biased toward the shorter set
        score = len(overlap) / min(len(q_words), len(key_words)) if overlap else 0.0

        if score > best_score:
            best_score = score
            best_key = key
            best_answer = answer

    return (best_key, best_answer, best_score)


# ---------------------------------------------------------------------------
# Doc search
# ---------------------------------------------------------------------------

def search_docs(question, docs_dir=None):
    """Search Markdown docs for paragraphs matching question keywords.

    Scans every *.md file in docs_dir, splits on blank lines, and scores
    each paragraph by keyword overlap.

    Returns the best-matching paragraph text, or empty string if nothing
    found.
    """
    docs_dir = docs_dir or DOCS_DIR
    if not os.path.isdir(docs_dir):
        return ""

    q_words = set(_normalise(question).split())
    if not q_words:
        return ""

    best_para = ""
    best_score = 0.0

    for fname in os.listdir(docs_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(docs_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            continue

        # Split into paragraphs on blank lines
        paragraphs = re.split(r"\n\s*\n", content)
        for para in paragraphs:
            para_stripped = para.strip()
            if len(para_stripped) < 20:
                continue
            p_words = set(_normalise(para_stripped).split())
            overlap = q_words & p_words
            if not overlap:
                continue
            score = len(overlap) / len(q_words)
            if score > best_score:
                best_score = score
                best_para = para_stripped

    return best_para


# ---------------------------------------------------------------------------
# Grok fallback
# ---------------------------------------------------------------------------

_GROK_SYSTEM_PROMPT = (
    "You are a RustChain bounty assistant.  Answer questions about the "
    "RustChain blockchain, RTC tokens, bounty hunting, Proof of Antiquity "
    "consensus, hardware multipliers, and the Elyan Labs ecosystem.  "
    "Be concise and accurate.  If you do not know, say so."
)


def ask_grok(question, context=""):
    """Send a question to the Grok API (x.ai) for an AI-generated answer.

    Args:
        question:  User's question.
        context:   Optional extra context to include in the prompt.

    Returns:
        Response text string, or an error message if the call fails.
    """
    api_key = GROK_API_KEY
    if not api_key:
        return "[error] GROK_API_KEY not set -- cannot use AI fallback."

    user_content = question
    if context:
        user_content = f"Context:\n{context}\n\nQuestion: {question}"

    payload = {
        "model": "grok-3-mini",
        "messages": [
            {"role": "system", "content": _GROK_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
        "max_tokens": 512,
    }

    try:
        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.RequestException as exc:
        return f"[error] Grok API request failed: {exc}"
    except (KeyError, IndexError):
        return "[error] Unexpected response format from Grok API."


# ---------------------------------------------------------------------------
# Unified answer function
# ---------------------------------------------------------------------------

def answer(question, use_grok=False):
    """Answer a question using the best available source.

    Resolution order:
        1. Built-in FAQ (fuzzy match, threshold >= 0.3)
        2. Docs search (if docs directory has .md files)
        3. Grok AI fallback (if use_grok=True and GROK_API_KEY is set)
        4. Unknown

    Returns:
        {
            "source": "faq" | "docs" | "grok" | "unknown",
            "answer": str,
            "confidence": float,
        }
    """
    # 1. Try FAQ
    matched_key, faq_answer, score = fuzzy_match(question)
    if score >= 0.3 and faq_answer:
        return {"source": "faq", "answer": faq_answer, "confidence": score}

    # 2. Try docs
    doc_result = search_docs(question)
    if doc_result:
        return {"source": "docs", "answer": doc_result, "confidence": 0.5}

    # 3. Try Grok
    if use_grok:
        grok_answer = ask_grok(question)
        if grok_answer and not grok_answer.startswith("[error]"):
            return {"source": "grok", "answer": grok_answer, "confidence": 0.6}

    # 4. Unknown
    return {
        "source": "unknown",
        "answer": (
            "Sorry, I could not find an answer to that question. "
            "Try rephrasing, or use --grok for AI-assisted answers."
        ),
        "confidence": 0.0,
    }
