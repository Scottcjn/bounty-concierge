"""Command-line interface for the RustChain Bounty Concierge.

Subcommands:
    browse   -- List and filter open bounties across all repos
    faq      -- Ask a question about RustChain or bounties
    wallet   -- Register a wallet or check balance
    status   -- Check pending payouts for a wallet
    engage   -- Cross-platform engagement (star repos, Dev.to stats)
    announce -- Preview or post bounty announcements
    claim    -- Show claim instructions for a specific bounty
    version  -- Print version string
"""

import argparse
import json
import sys

from concierge import __version__
from concierge import config
from concierge.bounty_index import aggregate, fetch_bounties
from concierge.faq_engine import answer as faq_answer
from concierge.wallet_helper import (
    check_wallet_exists,
    get_active_miners,
    get_all_holders,
    get_balance,
    get_epoch_info,
    get_holder_stats,
    get_pending_transfers,
    register_wallet_guide,
    transfer_rtc,
    validate_wallet_name,
)
from concierge.payout_tracker import check_pending, check_history, format_payout_status
from concierge.skill_matcher import recommend
from concierge.discord_bridge import (
    already_migrated,
    debit_discord_balance,
    get_discord_balance,
    get_migration_history,
    list_discord_holders,
    record_migration,
    record_migration_force,
)

# Optional modules -- degrade gracefully if missing or broken.
try:
    from concierge.engagement import (
        star_all_ecosystem_repos,
        check_devto_articles,
        saascity_upvote,
        SaaSCityError,
    )
except ImportError:
    star_all_ecosystem_repos = None
    check_devto_articles = None
    saascity_upvote = None
    SaaSCityError = None

try:
    from concierge.announcer import format_announcement
except ImportError:
    format_announcement = None


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_json(obj):
    """Pretty-print a Python object as JSON."""
    print(json.dumps(obj, indent=2, default=str))


def _truncate(text, width):
    """Truncate text to width, adding '...' if needed."""
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


def _print_bounty_table(bounties):
    """Print a formatted ASCII table of bounties."""
    if not bounties:
        print("No bounties found matching your filters.")
        return

    # Column widths
    w_num = 5
    w_repo = 22
    w_title = 42
    w_rtc = 8
    w_tier = 10
    w_skills = 28

    header = (
        f"{'#':<{w_num}} "
        f"{'Repo':<{w_repo}} "
        f"{'Title':<{w_title}} "
        f"{'RTC':>{w_rtc}} "
        f"{'Tier':<{w_tier}} "
        f"{'Skills':<{w_skills}}"
    )
    sep = "-" * len(header)

    print(sep)
    print(header)
    print(sep)

    for b in bounties:
        repo_short = b["repo"].split("/")[-1]
        skills_str = ", ".join(b["skills"]) if b["skills"] else "-"
        print(
            f"{b['number']:<{w_num}} "
            f"{_truncate(repo_short, w_repo):<{w_repo}} "
            f"{_truncate(b['title'], w_title):<{w_title}} "
            f"{b['reward_rtc']:>{w_rtc}.1f} "
            f"{b['difficulty']:<{w_tier}} "
            f"{_truncate(skills_str, w_skills):<{w_skills}}"
        )

    print(sep)
    print(f"Total: {len(bounties)} bounties")


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def _cmd_browse(args):
    """Handle the 'browse' subcommand."""
    repos = None
    if args.repo:
        # Allow short names like 'bottube' -> 'Scottcjn/bottube'
        repos = []
        for r in args.repo:
            if "/" not in r:
                r = f"Scottcjn/{r}"
            repos.append(r)

    if args.dry_run:
        print("[dry-run] Would fetch bounties from GitHub API")
        if repos:
            print(f"[dry-run] Repos: {', '.join(repos)}")
        if args.skill:
            print(f"[dry-run] Skill filter: {args.skill}")
        if args.tier:
            print(f"[dry-run] Tier filter: {args.tier}")
        return

    all_bounties = fetch_bounties(repos=repos)

    # Apply filters
    filtered = all_bounties

    if args.skill:
        skill_lower = args.skill.lower()
        filtered = [b for b in filtered if skill_lower in [s.lower() for s in b["skills"]]]

    if args.tier:
        tier_lower = args.tier.lower()
        filtered = [b for b in filtered if b["difficulty"] == tier_lower]

    if args.min_rtc is not None:
        filtered = [b for b in filtered if b["reward_rtc"] >= args.min_rtc]

    if args.max_rtc is not None:
        filtered = [b for b in filtered if b["reward_rtc"] <= args.max_rtc]

    # Sort by RTC descending
    filtered.sort(key=lambda b: b["reward_rtc"], reverse=True)

    # Limit
    filtered = filtered[: args.limit]

    if args.json:
        _print_json(filtered)
    else:
        _print_bounty_table(filtered)


def _cmd_faq(args):
    """Handle the 'faq' subcommand."""
    question = " ".join(args.question)
    if not question.strip():
        print("Please provide a question.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[dry-run] Would look up FAQ for: {question}")
        return

    result = faq_answer(question, use_grok=args.grok)

    if args.json:
        _print_json(result)
    else:
        source_label = f"[{result['source']}]"
        conf = f"(confidence: {result['confidence']:.0%})"
        print(f"{source_label} {conf}")
        print()
        print(result["answer"])


def _cmd_wallet(args):
    """Handle the 'wallet' subcommand."""
    action = args.wallet_action

    if not action:
        print("Usage: concierge wallet {register,balance,holders,stats,miners,migrate}",
              file=sys.stderr)
        print("Run 'concierge wallet --help' for details.", file=sys.stderr)
        sys.exit(1)

    if action == "register":
        name = args.name
        valid, msg = validate_wallet_name(name)
        if not valid:
            print(f"Error: {msg}", file=sys.stderr)
            sys.exit(1)
        if args.dry_run:
            print(f"[dry-run] Would show registration guide for wallet: {name}")
            return
        guide = register_wallet_guide(name)
        if args.json:
            _print_json({"wallet_name": name, "guide": guide})
        else:
            print(guide)

    elif action == "balance":
        name = args.name
        if args.dry_run:
            print(f"[dry-run] Would check balance for: {name}")
            return
        result = get_balance(name)
        if args.json:
            _print_json(result)
        else:
            if "error" in result:
                print(f"Error: {result['error']}", file=sys.stderr)
                sys.exit(1)
            print(f"Wallet:  {name}")
            if "balance_rtc" in result:
                print(f"Balance: {result['balance_rtc']:.6f} RTC")
            elif "amount_i64" in result:
                print(f"Balance: {result['amount_i64'] / 1_000_000:.6f} RTC")
            else:
                for k, v in result.items():
                    print(f"  {k}: {v}")

    elif action == "holders":
        if args.dry_run:
            print("[dry-run] Would fetch all wallet holders (requires RC_ADMIN_KEY)")
            return
        holders = get_all_holders()
        if isinstance(holders, dict) and "error" in holders:
            print("Error: %s" % holders["error"], file=sys.stderr)
            sys.exit(1)
        # Filter
        cat_filter = getattr(args, "category", None)
        if cat_filter:
            holders = [h for h in holders if h["category"] == cat_filter]
        min_bal = getattr(args, "min_balance", None)
        if min_bal is not None:
            holders = [h for h in holders if h["amount_rtc"] >= min_bal]
        limit = getattr(args, "limit", 50)
        holders = holders[:limit]
        if args.json:
            _print_json(holders)
        else:
            print("%-4s %-45s %12s  %s" % ("#", "Wallet", "Balance RTC", "Category"))
            print("-" * 75)
            for i, h in enumerate(holders, 1):
                print("%-4d %-45s %12.2f  %s" % (
                    i, h["miner_id"][:45], h["amount_rtc"], h["category"]))
            print("-" * 75)
            print("Showing %d wallets" % len(holders))

    elif action == "stats":
        if args.dry_run:
            print("[dry-run] Would compute wallet statistics (requires RC_ADMIN_KEY)")
            return
        stats = get_holder_stats()
        if isinstance(stats, dict) and "error" in stats:
            print("Error: %s" % stats["error"], file=sys.stderr)
            sys.exit(1)
        if args.json:
            _print_json(stats)
        else:
            print("=== RustChain Wallet Statistics ===")
            print()
            print("Total wallets:        %d" % stats["total_wallets"])
            print("With balance:         %d" % stats["wallets_with_balance"])
            print("Empty:                %d" % stats["empty_wallets"])
            print("Total RTC:            {:,.2f}".format(stats["total_rtc"]))
            print()
            print("--- By Category ---")
            for cat, info in sorted(stats["categories"].items(),
                                    key=lambda x: x[1]["rtc"], reverse=True):
                pct = info["rtc"] / stats["total_rtc"] * 100 if stats["total_rtc"] else 0
                print("  %-15s %4d wallets  %12.2f RTC  (%5.1f%%)" % (
                    cat, info["count"], info["rtc"], pct))
            print()
            print("--- User Distribution (excl. founder/platform) ---")
            for tier, info in stats["distribution"].items():
                print("  %-20s %4d holders  %12.2f RTC" % (
                    tier, info["count"], info["rtc"]))

    elif action == "miners":
        if args.dry_run:
            print("[dry-run] Would fetch active miners list")
            return
        miners = get_active_miners()
        if isinstance(miners, dict) and "error" in miners:
            print("Error: %s" % miners["error"], file=sys.stderr)
            sys.exit(1)
        epoch = get_epoch_info()
        if args.json:
            _print_json({"epoch": epoch, "miners": miners})
        else:
            if not isinstance(epoch, dict) or "error" in epoch:
                print("Epoch info unavailable")
            else:
                print("Epoch %s | Slot %s | Enrolled: %s | Pot: %s RTC" % (
                    epoch.get("epoch", "?"), epoch.get("slot", "?"),
                    epoch.get("enrolled_miners", "?"), epoch.get("epoch_pot", "?")))
            print()
            print("%-4s %-40s %-15s %s" % ("#", "Miner", "Architecture", "Multiplier"))
            print("-" * 70)
            for i, m in enumerate(miners, 1):
                print("%-4d %-40s %-15s %sx" % (
                    i, m["miner"][:40], m.get("device_arch", "?"),
                    m.get("antiquity_multiplier", "?")))
            print("-" * 70)
            print("%d active miners" % len(miners))

    elif action == "migrate":
        _cmd_wallet_migrate(args)

    else:
        print("Unknown wallet action: %s" % action, file=sys.stderr)
        sys.exit(1)


def _cmd_wallet_migrate(args):
    """Handle the 'wallet migrate' subcommand."""
    from concierge import config as _cfg

    # --- history ---
    if args.history:
        history = get_migration_history()
        if args.json:
            _print_json(history)
        elif not history:
            print("No migrations recorded yet.")
        else:
            print("%-4s %-20s %-25s %10s  %-10s  %s" % (
                "#", "Discord ID", "Target Wallet", "RTC", "Status", "Date"))
            print("-" * 100)
            for i, m in enumerate(history, 1):
                print("%-4d %-20s %-25s %10.2f  %-10s  %s" % (
                    i, m["discord_user_id"], m["target_wallet"],
                    m["amount_rtc"], m["status"], m["created_at"]))
        return

    # --- list ---
    if getattr(args, "list", False):
        min_bal = getattr(args, "min_balance", 0.1)
        if args.dry_run:
            print("[dry-run] Would query Discord economy DB on NAS for holders >= %.2f RTC" % min_bal)
            return
        holders = list_discord_holders(min_balance=min_bal)
        if isinstance(holders, dict) and "error" in holders:
            print("Error: %s" % holders["error"], file=sys.stderr)
            sys.exit(1)
        if args.json:
            _print_json(holders)
        elif not holders:
            print("No Discord holders found with balance >= %.2f RTC" % min_bal)
        else:
            total = sum(h["balance"] for h in holders)
            print("=== Discord Economy Holders (>= %.2f RTC) ===" % min_bal)
            print()
            print("%-4s %-22s %10s %12s %12s  %s" % (
                "#", "Discord User ID", "Balance", "Earned", "Spent", "Migrated?"))
            print("-" * 90)
            for i, h in enumerate(holders, 1):
                migrated = "YES" if already_migrated(h["user_id"]) else "-"
                print("%-4d %-22s %10.4f %12.4f %12.4f  %s" % (
                    i, h["user_id"], h["balance"],
                    h.get("total_earned", 0), h.get("total_spent", 0),
                    migrated))
            print("-" * 90)
            print("%d holders  |  %.4f RTC total" % (len(holders), total))
        return

    # --- migrate a specific user ---
    user_id = args.user
    to_wallet = args.to_wallet

    if not user_id or not to_wallet:
        print("Error: --user and --to are required for migration.", file=sys.stderr)
        print("  concierge wallet migrate --user DISCORD_ID --to WALLET_NAME")
        print("  concierge wallet migrate --list    (to see eligible users)")
        print("  concierge wallet migrate --history (to see past migrations)")
        sys.exit(1)

    # Validate target wallet name
    valid, msg = validate_wallet_name(to_wallet)
    if not valid:
        print("Error: Invalid target wallet name: %s" % msg, file=sys.stderr)
        sys.exit(1)

    # Check for prior migration
    if not args.force and already_migrated(user_id):
        print("Error: Discord user %s has already been migrated." % user_id,
              file=sys.stderr)
        print("Use --force to re-migrate.", file=sys.stderr)
        sys.exit(1)

    # Fetch Discord balance
    discord_info = get_discord_balance(user_id)
    if isinstance(discord_info, dict) and "error" in discord_info:
        print("Error: %s" % discord_info["error"], file=sys.stderr)
        sys.exit(1)

    balance = discord_info.get("balance", 0)
    if balance < 0.1:
        print("Error: Discord balance %.4f RTC is below minimum (0.1 RTC)" % balance,
              file=sys.stderr)
        sys.exit(1)

    source_wallet = _cfg.MIGRATION_SOURCE_WALLET

    print("=== Discord-to-Chain Migration ===")
    print()
    print("  Discord user:    %s" % user_id)
    print("  Discord balance: %.4f RTC" % balance)
    print("  Target wallet:   %s" % to_wallet)
    print("  Source wallet:   %s" % source_wallet)
    print("  Amount:          %.4f RTC" % balance)
    print()

    if args.dry_run:
        print("[dry-run] Would transfer %.4f RTC from %s to %s" % (
            balance, source_wallet, to_wallet))
        print("[dry-run] Then debit Discord user %s by %.4f RTC" % (user_id, balance))
        return

    # Step 1: On-chain credit (BEFORE Discord debit -- safety first)
    print("Step 1/3: Transferring %.4f RTC on-chain (%s -> %s)..." % (
        balance, source_wallet, to_wallet))
    chain_result = transfer_rtc(source_wallet, to_wallet, balance)
    if isinstance(chain_result, dict) and "error" in chain_result:
        print("FAILED: On-chain transfer error: %s" % chain_result["error"],
              file=sys.stderr)
        sys.exit(1)

    tx_id = chain_result.get("pending_id", chain_result.get("tx_id", "unknown"))
    print("  OK -- pending_id: %s" % tx_id)

    # Step 2: Debit Discord balance
    print("Step 2/3: Debiting Discord balance...")
    debit_result = debit_discord_balance(user_id, balance)
    if isinstance(debit_result, dict) and "error" in debit_result:
        print("WARNING: Discord debit failed: %s" % debit_result["error"],
              file=sys.stderr)
        print("  On-chain transfer succeeded but Discord balance NOT debited.",
              file=sys.stderr)
        print("  Manual fix needed on NAS.", file=sys.stderr)
        # Still record as partial
        if args.force:
            record_migration_force(user_id, to_wallet, balance, str(tx_id), "partial")
        else:
            record_migration(user_id, to_wallet, balance, str(tx_id), "partial")
        sys.exit(1)
    print("  OK -- Discord balance zeroed")

    # Step 3: Record locally
    print("Step 3/3: Recording migration...")
    if args.force:
        record_migration_force(user_id, to_wallet, balance, str(tx_id))
    else:
        record_migration(user_id, to_wallet, balance, str(tx_id))
    print("  OK")

    print()
    print("Migration complete: %.4f RTC -> %s" % (balance, to_wallet))


def _cmd_status(args):
    """Handle the 'status' subcommand."""
    wallet = args.wallet
    if not wallet:
        print("Error: --wallet is required for status checks.", file=sys.stderr)
        sys.exit(1)

    valid, msg = validate_wallet_name(wallet)
    if not valid:
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[dry-run] Would check payout status for wallet: {wallet}")
        return

    pending = check_pending(wallet)
    history = check_history(wallet)

    if args.json:
        _print_json({"wallet": wallet, "pending": pending, "history": history})
    else:
        print(f"Payout status for: {wallet}")
        print()
        print(format_payout_status(pending, history))


def _cmd_engage(args):
    """Handle the 'engage' subcommand."""
    if args.star_repos:
        if star_all_ecosystem_repos is None:
            print(
                "Error: engagement module is not available.",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.dry_run:
            print("[dry-run] Would star the following repos:")
            for repo in config.REPOS:
                print(f"  {repo}")
            return

        token = config.GITHUB_TOKEN
        if not token:
            print(
                "Error: GITHUB_TOKEN environment variable is required to star repos.",
                file=sys.stderr,
            )
            sys.exit(1)

        results = star_all_ecosystem_repos(token)
        if args.json:
            _print_json(results)
        else:
            for repo, ok in results.items():
                status = "starred" if ok else "FAILED"
                print(f"  {repo}: {status}")

    elif args.devto:
        if check_devto_articles is None:
            print(
                "Error: engagement module is not available.",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.dry_run:
            print("[dry-run] Would fetch Dev.to article stats")
            return

        api_key = config.DEVTO_API_KEY
        if not api_key:
            print(
                "Error: DEVTO_API_KEY environment variable is required.",
                file=sys.stderr,
            )
            sys.exit(1)

        articles = check_devto_articles(api_key)
        if args.json:
            _print_json(articles)
        else:
            if not articles:
                print("No Dev.to articles found.")
            else:
                print("Dev.to Articles:")
                for a in articles:
                    print(
                        f"  {a['title']}"
                        f"  views={a['page_views']}"
                        f"  reactions={a['positive_reactions']}"
                    )
                    print(f"    {a['url']}")

    elif args.saascity:
        if saascity_upvote is None:
            print(
                "Error: engagement module is not available.",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.dry_run:
            saascity_upvote(dry_run=True)
            return

        api_key = config.SAASCITY_KEY
        if not api_key:
            print(
                "Error: SAASCITY_KEY environment variable is required to upvote on SaaSCity.",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            results = saascity_upvote(api_key=api_key)
        except SaaSCityError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            _print_json(results)
        else:
            for listing, ok in results.items():
                status = "upvoted" if ok else "FAILED"
                print(f"  {listing}: {status}")

    else:
        print(
            "Specify an engagement action: --star-repos, --devto, or --saascity",
            file=sys.stderr,
        )
        sys.exit(1)


def _cmd_announce(args):
    """Handle the 'announce' subcommand."""
    if format_announcement is None:
        print(
            "Error: announcer module is not available.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.dry_run:
        print("[dry-run] Announcement preview (fetching bounties)...")
        print()

    bounties = fetch_bounties()
    bounties.sort(key=lambda b: b["reward_rtc"], reverse=True)

    # Map to the format expected by format_announcement
    formatted_bounties = []
    for b in bounties:
        formatted_bounties.append({
            "title": b["title"],
            "rtc": b["reward_rtc"],
            "url": b["url"],
            "difficulty": b["difficulty"],
            "labels": b["labels"],
        })

    content = format_announcement(formatted_bounties)

    if args.json:
        _print_json(content)
    else:
        if args.dry_run:
            print("[dry-run] Announcement preview (not posted):")
            print()
        print("--- Short (Twitter) ---")
        print(content.get("short", ""))
        print()
        print("--- Medium (4claw / AgentChan) ---")
        print(content.get("medium", ""))
        print()
        print("--- Long (Moltbook / Dev.to) ---")
        print(content.get("long", ""))


def _cmd_claim(args):
    """Handle the 'claim' subcommand."""
    repo = args.repo
    if "/" not in repo:
        repo = f"Scottcjn/{repo}"
    issue_num = args.issue
    wallet = args.wallet

    valid, msg = validate_wallet_name(wallet)
    if not valid:
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)

    issue_url = f"https://github.com/{repo}/issues/{issue_num}"

    if args.dry_run:
        print(f"[dry-run] Would claim issue #{issue_num} in {repo}")
        print(f"[dry-run] Wallet: {wallet}")
        return

    if args.json:
        _print_json({
            "action": "claim",
            "repo": repo,
            "issue": issue_num,
            "wallet": wallet,
            "url": issue_url,
        })
    else:
        print(f"Claim instructions for issue #{issue_num}")
        print(f"Repository: {repo}")
        print(f"Issue URL:  {issue_url}")
        print(f"Wallet:     {wallet}")
        print()
        print("Next steps:")
        print(f"  1. Visit {issue_url}")
        print(f"  2. Comment: \"I would like to claim this bounty. Wallet: {wallet}\"")
        print(f"  3. Wait for assignment from a maintainer")
        print(f"  4. Submit your PR referencing #{issue_num}")
        print(f"  5. RTC will be transferred after merge and review")


def _cmd_version(args):
    """Handle the 'version' subcommand."""
    if args.json:
        _print_json({"version": __version__})
    else:
        print(f"bounty-concierge {__version__}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _add_common_flags(parser):
    """Add --dry-run and --json flags to a parser or subparser."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview actions without making network calls",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as JSON",
    )


def _build_parser():
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="concierge",
        description="RustChain Bounty Concierge -- CLI for bounty hunters",
    )
    _add_common_flags(parser)

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # --- browse ---
    p_browse = sub.add_parser("browse", help="List and filter open bounties")
    _add_common_flags(p_browse)
    p_browse.add_argument("--repo", nargs="+", help="Filter by repo (short name or owner/repo)")
    p_browse.add_argument("--skill", help="Filter by required skill")
    p_browse.add_argument("--tier", choices=["micro", "standard", "major", "critical"],
                          help="Filter by difficulty tier")
    p_browse.add_argument("--min-rtc", type=float, help="Minimum RTC reward")
    p_browse.add_argument("--max-rtc", type=float, help="Maximum RTC reward")
    p_browse.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")

    # --- faq ---
    p_faq = sub.add_parser("faq", help="Ask a question about RustChain or bounties")
    _add_common_flags(p_faq)
    p_faq.add_argument("question", nargs="+", help="Your question")
    p_faq.add_argument("--grok", action="store_true", default=False,
                       help="Use Grok AI for unanswered questions (requires GROK_API_KEY)")

    # --- wallet ---
    p_wallet = sub.add_parser("wallet", help="Wallet operations")
    _add_common_flags(p_wallet)
    wallet_sub = p_wallet.add_subparsers(dest="wallet_action", help="Wallet action")

    p_w_register = wallet_sub.add_parser("register", help="Get wallet registration instructions")
    _add_common_flags(p_w_register)
    p_w_register.add_argument("name", help="Desired wallet name")

    p_w_balance = wallet_sub.add_parser("balance", help="Check wallet RTC balance")
    _add_common_flags(p_w_balance)
    p_w_balance.add_argument("name", help="Wallet or miner ID")

    p_w_holders = wallet_sub.add_parser("holders", help="List all wallet holders")
    _add_common_flags(p_w_holders)
    p_w_holders.add_argument("--category", choices=["named", "founder", "platform", "auto-hash", "redteam"],
                             help="Filter by wallet category")
    p_w_holders.add_argument("--min-balance", type=float, help="Minimum RTC balance")
    p_w_holders.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")

    p_w_stats = wallet_sub.add_parser("stats", help="Wallet holder statistics")
    _add_common_flags(p_w_stats)

    p_w_miners = wallet_sub.add_parser("miners", help="List active attesting miners")
    _add_common_flags(p_w_miners)

    p_w_migrate = wallet_sub.add_parser(
        "migrate", help="Migrate Discord economy balances to on-chain wallets")
    _add_common_flags(p_w_migrate)
    p_w_migrate.add_argument("--list", action="store_true",
                             help="List Discord holders eligible for migration")
    p_w_migrate.add_argument("--user", help="Discord user ID to migrate")
    p_w_migrate.add_argument("--to", dest="to_wallet", help="Target on-chain wallet name")
    p_w_migrate.add_argument("--history", action="store_true",
                             help="Show migration history")
    p_w_migrate.add_argument("--force", action="store_true",
                             help="Re-migrate even if already done")
    p_w_migrate.add_argument("--min-balance", type=float, default=0.1,
                             help="Minimum balance for --list (default: 0.1)")

    # --- status ---
    p_status = sub.add_parser("status", help="Check pending payouts for a wallet")
    _add_common_flags(p_status)
    p_status.add_argument("--wallet", required=True, help="Wallet or miner ID")

    # --- engage ---
    p_engage = sub.add_parser("engage", help="Cross-platform engagement actions")
    _add_common_flags(p_engage)
    p_engage.add_argument("--star-repos", action="store_true", default=False,
                          help="Star all RustChain ecosystem repos on GitHub")
    p_engage.add_argument("--devto", action="store_true", default=False,
                          help="Check Dev.to article stats")
    p_engage.add_argument("--saascity", action="store_true", default=False,
                          help="Upvote RustChain and BoTTube on SaaSCity "
                               "(requires SAASCITY_KEY)")

    # --- announce ---
    p_announce = sub.add_parser("announce", help="Preview or post bounty announcements")
    _add_common_flags(p_announce)

    # --- claim ---
    p_claim = sub.add_parser("claim", help="Show claim instructions for a bounty")
    _add_common_flags(p_claim)
    p_claim.add_argument("--issue", type=int, required=True, help="Issue number")
    p_claim.add_argument("--repo", default="Scottcjn/rustchain-bounties",
                         help="Repository (default: Scottcjn/rustchain-bounties)")
    p_claim.add_argument("--wallet", required=True, help="Your wallet name")

    # --- version ---
    p_version = sub.add_parser("version", help="Show version")
    _add_common_flags(p_version)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Main CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "browse": _cmd_browse,
        "faq": _cmd_faq,
        "wallet": _cmd_wallet,
        "status": _cmd_status,
        "engage": _cmd_engage,
        "announce": _cmd_announce,
        "claim": _cmd_claim,
        "version": _cmd_version,
    }

    handler = dispatch.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            sys.exit(130)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
