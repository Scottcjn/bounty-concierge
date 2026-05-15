# Getting Started with RustChain Bounties

A 5-minute walkthrough for first-time contributors. No prior RustChain
knowledge required.

---

## What You Need

- A GitHub account
- Basic familiarity with git (fork, branch, commit, push, pull request)
- A text editor or IDE
- A wallet name (you pick it -- any lowercase alphanumeric string with
  optional hyphens, like `my-wallet`)

You do **not** need to install any blockchain software, run a node, or
own any RTC to get started.

---

## Step 1: Browse Open Bounties

Go to:

```
https://github.com/Scottcjn/rustchain-bounties/issues?q=is:open+label:bounty
```

Each issue is a bounty. The title includes the RTC reward amount. Labels
indicate the tier:

| Label | RTC Range | USD Value | Difficulty |
|-------|-----------|-----------|------------|
| `micro` | 1 - 10 | $0.10 - $1.00 | Easy -- docs, typos, repo stars, social shares |
| `standard` | 10 - 50 | $1.00 - $5.00 | Medium -- features, integrations, tests |
| `major` | 50 - 200 | $5.00 - $20.00 | Hard -- architecture, protocol work |
| `critical` | 200 - 500 | $20.00 - $50.00 | Expert -- security audits, consensus |

**If this is your first bounty**, start with a `micro` issue. Get one
merged, see RTC hit your wallet, then scale up.

---

## Step 2: Pick a Bounty That Matches Your Skills

The ecosystem spans multiple skill areas. Use this table to find bounties
that fit your background:

| Skill Category | What To Look For | Example Bounties |
|----------------|------------------|-----------------|
| **Python** | Backend features, API endpoints, test suites, miner scripts | Attestation fuzz harness, Prometheus exporter, API docs |
| **Rust** | Core blockchain work, performance-critical code | Token bridge, consensus engine changes |
| **Documentation** | README improvements, API docs, guides, FAQs | OpenAPI/Swagger docs, getting-started guides |
| **Security** | Red-team challenges, vulnerability reports, audit findings | Fleet detection bypass, epoch settlement attacks, API auth |
| **Frontend** | HTML/CSS/JS for dashboards and explorers | Miner dashboard, Hall of Fame pages, block explorer UI |
| **DevOps** | Monitoring, CI/CD, deployment scripts | Prometheus + Grafana, systemd services, health checks |
| **Social Media** | Community engagement, sharing, upvoting | Star repos, share on Moltbook/BoTTube/SaaSCity, write posts |
| **Testing** | Unit tests, integration tests, fuzzing | Crash regression tests, edge case coverage |

Read the issue description fully. Check:

- Has someone already claimed it? (Look at comments and linked PRs.)
- Do you understand what is being asked?
- Do you have the skills to complete it?

If the issue references systems you are unfamiliar with, read
[TECH_STACK.md](TECH_STACK.md) and [FAQ.md](FAQ.md) for context.

---

## Step 3: Claim It

Comment on the issue with three things:

1. That you are claiming it.
2. Your wallet name.
3. A brief description of your approach.

**Example:**

```
Claiming this. Wallet: alice-dev.
Approach: I will add the missing error handling for empty payloads
in the /attest/submit endpoint and write 3 test cases.
```

Wait for acknowledgment before investing significant time. This prevents
duplicate work.

---

## Step 4: Do the Work and Submit a PR

1. **Fork** the relevant repository to your GitHub account.
2. **Clone** your fork locally.
3. **Create a branch** named after the issue
   (e.g., `fix-123-attest-validation`).
4. **Make your changes.** Follow the existing code style -- do not
   introduce new formatting, frameworks, or patterns unless the bounty
   specifically asks for it.
5. **Test your changes.** Run existing tests if available. Add new tests
   if appropriate.
6. **Commit** with a clear message explaining why the change was made.
7. **Push** your branch and open a PR against the `main` branch of the
   upstream repository.

In the PR description:

- Reference the bounty issue: `Closes #123`
- Summarize what you changed and why.
- Include evidence that it works (test output, screenshots, curl
  commands, logs).

---

## Step 5: Get Reviewed, Merged, and Paid

The maintainer will review your PR, usually within 48 hours. You may
receive feedback requesting changes. Address all comments and push
updates to the same branch.

Once approved and merged:

1. The maintainer transfers RTC from `founder_team_bounty` to your
   wallet.
2. The transfer has a **24-hour pending period**.
3. After 24 hours, the balance is confirmed and available.

Check your balance:

```bash
curl -sk "https://50.28.86.131/balance?miner_id=your-wallet-name"
```

See [PAYOUT_GUIDE.md](PAYOUT_GUIDE.md) for full payout details including
the quality scorecard, timelines, and troubleshooting.

---

## Ecosystem Repositories

These are the repositories where bounty work happens. Each accepts PRs
and has its own bounty issues:

| Repository | Language | Description |
|------------|----------|-------------|
| [rustchain-bounties](https://github.com/Scottcjn/rustchain-bounties) | -- | Bounty board with 154+ open tasks (file claims here) |
| [RustChain](https://github.com/Scottcjn/Rustchain) | Python | Core blockchain node -- RIP-200/201 consensus, attestation |
| [bottube](https://github.com/Scottcjn/bottube) | Python | AI video platform, Python SDK (`pip install bottube`) |
| [beacon-skill](https://github.com/Scottcjn/beacon-skill) | Python | Agent-to-agent coordination protocol |
| [ram-coffers](https://github.com/Scottcjn/ram-coffers) | C | NUMA-distributed weight banking for LLM inference |
| [claude-code-power8](https://github.com/Scottcjn/claude-code-power8) | Shell/JS | POWER8/ppc64le port of Claude Code CLI |
| [llama-cpp-power8](https://github.com/Scottcjn/llama-cpp-power8) | C/C++ | AltiVec/VSX optimized llama.cpp for IBM POWER8 |
| [rustchain-monitor](https://github.com/Scottcjn/rustchain-monitor) | Python | Real-time monitoring for PoA nodes |
| [bounty-concierge](https://github.com/Scottcjn/bounty-concierge) | Python | This repo -- onboarding, CLI, docs |

---

## Tips for Success

- **Start with micro bounties.** Get your first PR merged and your first
  RTC payout. The mechanics (claim, PR, review, payout) become second
  nature after one cycle.
- **Read the tech stack docs.** [TECH_STACK.md](TECH_STACK.md) covers the
  full architecture. Understanding how attestation, epochs, and rewards
  work will help you write better code.
- **Check existing PRs before starting.** Someone may have already
  submitted a solution, or there may be partial work you can build on.
- **Smaller PRs merge faster.** A focused, well-tested 50-line PR beats
  a sprawling 500-line PR every time.
- **Add to existing files, do not replace them.** A common mistake is
  overwriting a file with a new version instead of editing the relevant
  section. This breaks other functionality and will be rejected.
- **Include tests or proof.** Even a simple curl command showing the fix
  works counts as evidence. Submissions with no proof score poorly on
  the quality scorecard.
- **Do not submit AI-generated garbage.** Raw LLM output pasted into a
  PR without review, testing, or editing is rejected immediately. If you
  use AI tools to help write code, review and test the output thoroughly.
  The quality scorecard measures craft, not speed.
- **Ask questions early.** If the bounty description is unclear, ask in
  the issue comments before writing code. A 2-minute question can save
  hours of wasted work.

---

## Common Mistakes

| Mistake | Why It Fails | What To Do Instead |
|---------|-------------|-------------------|
| Replacing entire files | Breaks existing functionality | Edit only the relevant section |
| Scope creep | PR does more than asked, harder to review | Stay focused on the bounty scope |
| No tests or evidence | Cannot verify the fix works | Add tests, screenshots, or curl output |
| Ignoring existing style | Creates inconsistency in the codebase | Match indentation, naming, patterns |
| Giant monolithic PRs | Slow to review, high risk of conflicts | Break into smaller focused PRs |
| Not referencing the issue | Maintainer cannot link PR to bounty | Include `Closes #123` in PR description |
| Claiming without commenting | Others may duplicate your work | Always comment on the issue first |
| Submitting raw AI output | Reads as generic, untested boilerplate | Review, edit, and test AI-assisted code |

---

## Quick Reference

| Resource | URL |
|----------|-----|
| Open bounties | `https://github.com/Scottcjn/rustchain-bounties/issues?q=is:open+label:bounty` |
| Block explorer | `https://50.28.86.131/explorer` |
| Node health | `https://50.28.86.131/health` |
| Check balance | `https://50.28.86.131/balance?miner_id=YOUR_WALLET` |
| Tech reference | [TECH_STACK.md](TECH_STACK.md) |
| FAQ | [FAQ.md](FAQ.md) |
| Payout details | [PAYOUT_GUIDE.md](PAYOUT_GUIDE.md) |
| Discord | `https://discord.gg/VqVVS2CW9Q` |
