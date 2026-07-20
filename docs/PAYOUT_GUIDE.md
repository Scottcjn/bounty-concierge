# RustChain Payout Guide

Step-by-step instructions for earning and receiving RTC bounty payouts.

---

## Overview

RustChain bounties are paid in RTC (RustChain Token). The internal
reference rate is **1 RTC = $0.10 USD**. Payouts are transferred from the
`founder_team_bounty` wallet to your personal wallet after your
contribution is reviewed and merged.

---

## Step 1: Register a Wallet

Your wallet name is a simple string. Requirements:

- Lowercase letters, numbers, and hyphens only
- No spaces, underscores, or special characters
- Between 3 and 64 characters

**Valid examples**: `alice-dev`, `bob2026`, `my-bounty-wallet`

**Invalid examples**: `Alice Dev` (spaces), `bob@2026` (special
characters), `MY_WALLET` (uppercase, underscores)

You do not need to install any software. Your wallet is created
automatically the first time RTC is transferred to it.

**Two ways to register:**

1. **Implicit**: Just use your wallet name when claiming a bounty. It will
   be created on first payout.
2. **Explicit**: Run `concierge wallet register your-name` or open a
   wallet registration issue on the bounties repo if you want to confirm
   your name is available before claiming.

---

## Step 2: Claim a Bounty

Find an open bounty at:

```
https://github.com/Scottcjn/rustchain-bounties/issues?q=is:open+label:bounty
```

Comment on the issue with:

- Your wallet name
- A brief description of your planned approach (1-3 sentences)

**Example comment:**

```
Claiming this. Wallet: alice-dev.
Approach: I will implement the input validation middleware described in the
issue and add pytest coverage for all error cases.
```

Wait for acknowledgment before starting significant work. If someone else
has already claimed the bounty and is actively working, consider a
different issue.

---

## Step 3: Submit Work

1. Fork the relevant repository.
2. Create a branch for your changes.
3. Make your changes, following the repo's existing code style and
   conventions.
4. Submit a pull request that references the bounty issue:
   - Use `Fixes #123` or `Closes #123` in the PR description to link it.
   - Include a clear description of what changed and why.
   - Add tests, screenshots, or logs as evidence of correctness.

---

## Step 4: Review and Merge

The maintainer reviews your PR against the quality scorecard (see below).
You may receive feedback requesting changes. Address all review comments
and push updates to the same PR branch.

Once approved, the PR is merged.

---

## Step 5: Payout

After merge, the maintainer initiates an RTC transfer:

1. RTC is transferred from `founder_team_bounty` to your wallet.
2. The transfer enters a **24-hour pending period**.
3. After 24 hours, the transfer is confirmed.
4. Your balance is updated and available.

---

## Step 6: Check Your Balance

### Via the Node API

```bash
curl -sk "https://50.28.86.131/balance?miner_id=YOUR_WALLET_NAME"
```

Example response:

```json
{
  "miner_id": "alice-dev",
  "balance_rtc": 75.0,
  "balance_i64": 75000000
}
```

The `balance_i64` field is the raw integer representation with 6 decimal
places (1 RTC = 1,000,000 units).

### Via the Concierge CLI

```bash
concierge wallet balance YOUR_WALLET_NAME
```

### Via the Block Explorer

Browse balances and transactions at:

```
https://50.28.86.131/explorer
```

The node uses a self-signed TLS certificate. Accept the browser warning
or use `-k` with curl.

---

## Bounty Tiers

| Tier | RTC Range | USD Equivalent | Typical Scope |
|------|-----------|----------------|---------------|
| Micro | 1 - 10 RTC | $0.10 - $1.00 | Docs fixes, repo stars, social media shares, typo corrections |
| Standard | 10 - 50 RTC | $1.00 - $5.00 | Feature additions, integrations, test suites, API docs |
| Major | 50 - 200 RTC | $5.00 - $20.00 | Architecture work, protocol implementations, dashboards |
| Critical | 200 - 500 RTC | $20.00 - $50.00 | Security audits, consensus attacks, red-team challenges |

---

## Payout Timeline

| Event | Timeframe |
|-------|-----------|
| Claim acknowledged | Same day (usually within hours) |
| PR review begins | Within 48 hours of submission |
| Review feedback | 1-3 rounds, depending on complexity |
| Merge | After all review comments are addressed |
| RTC transfer initiated | Within 24 hours of merge |
| Transfer pending period | 24 hours |
| Balance confirmed | 24 hours after transfer initiation |
| **Total (best case)** | **3-5 days from claim to confirmed balance** |

---

## Quality Scorecard

Every submission is evaluated on four dimensions. The minimum passing
score is **13 out of 20**.

| Dimension | Points | Criteria |
|-----------|--------|----------|
| **Impact** | 0 - 5 | Does the submission solve the stated problem? Does it address the full scope of the bounty? |
| **Correctness** | 0 - 5 | Is the code correct? Does it handle edge cases? Are there bugs? |
| **Evidence** | 0 - 5 | Are there tests? Screenshots? Logs? Benchmarks? Proof the solution works? |
| **Craft** | 0 - 5 | Code quality, documentation, commit messages, adherence to existing style. |

### Scoring Guide

| Score | Meaning |
|-------|---------|
| 0 | Not attempted or completely wrong |
| 1 | Minimal effort, major gaps |
| 2 | Partial, significant issues remain |
| 3 | Acceptable, meets basic requirements |
| 4 | Good, exceeds basic requirements |
| 5 | Excellent, thorough and polished |

---

## Disqualifiers

The following will cause a submission to be rejected regardless of score:

- **AI slop**: Generated text or code with no human review, editing, or
  quality control. Outputs that read like raw LLM completions with
  boilerplate padding.
- **Duplicate work**: Submitting work that copies or closely mirrors an
  existing PR or merged contribution.
- **Missing proof**: Claims of completed work with no evidence (no tests,
  no screenshots, no logs, no before/after comparison).
- **Scope violations**: PR does significantly more or less than the bounty
  asks for. Unrelated changes bundled into the submission.
- **Destructive changes**: Replacing or deleting existing files instead of
  extending them (unless the bounty explicitly requires replacement).

---

## wRTC Bridge (Coming Soon)

wRTC is an ERC-20 token on Base L2 that wraps RTC for use on public
Ethereum infrastructure.

| Property | Value |
|----------|-------|
| Standard | ERC-20 |
| Chain | Base L2 (Ethereum layer-2) |
| Decimals | 6 |
| Name | Wrapped RTC |
| Symbol | wRTC |
| Bridge type | Custodial (mint/burn) |

**How the bridge will work:**

1. **RTC to wRTC**: Lock RTC on the RustChain side. Bridge operator mints
   equivalent wRTC on Base L2.
2. **wRTC to RTC**: Burn wRTC on Base L2. Bridge operator releases
   equivalent RTC on RustChain.

The bridge is under active development. Until it launches, RTC lives
entirely on the RustChain attestation chain.

---

## Signed Transfers (Advanced)

If you have a secure wallet with Ed25519 keys (created via the RustChain
wallet package), you can make peer-to-peer transfers without admin
involvement:

```
POST https://50.28.86.131/wallet/transfer/signed
Content-Type: application/json

{
  "from_address": "RTCa1b2c3d4...",
  "to_address": "RTC9876543210...",
  "amount_rtc": 10.0,
  "memo": "Payment for code review",
  "nonce": 1733420000000,
  "signature": "<128-char hex Ed25519 signature>",
  "public_key": "<64-char hex public key>"
}
```

The server verifies:

1. The public key hash matches the `from_address`.
2. The Ed25519 signature is valid over the canonical JSON payload.
3. The sender has sufficient balance.

For most bounty hunters, signed transfers are not needed -- admin
transfers from `founder_team_bounty` handle all bounty payouts.

---

## Node Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Node health check (version, uptime, DB status) |
| GET | `/balance?miner_id=NAME` | RTC balance for a specific wallet |
| GET | `/epoch` | Current epoch/slot number and settlement status |
| GET | `/api/miners` | List of active miners with architecture and multiplier |
| GET | `/explorer` | Web-based block and transaction explorer |
| GET | `/ready` | Readiness probe (200 if node is fully synced) |
| GET | `/lottery/eligibility?miner_id=NAME` | Check epoch reward eligibility |
| POST | `/wallet/transfer/signed` | Signed RTC transfer (Ed25519) |

Primary node: `https://50.28.86.131`

All external requests use HTTPS with a self-signed certificate. Append
`-k` to curl commands to skip certificate verification.

---

## Troubleshooting

### My balance shows 0 after merge

- Payout may not have been initiated yet. Allow up to 24 hours after
  merge for the maintainer to process the transfer.
- Verify you provided the correct wallet name in your bounty claim
  comment. Wallet names are case-sensitive (always lowercase).
- Check the block explorer at `https://50.28.86.131/explorer` for recent
  transactions.

### The balance endpoint returns an error

- The node uses a self-signed TLS certificate. Use `-k` with curl:
  `curl -sk "https://50.28.86.131/balance?miner_id=your-wallet"`.
- Check node health first: `curl -sk https://50.28.86.131/health`. If the
  node is down, try again in a few minutes.

### My wallet name was wrong in the claim comment

- Edit your comment on the GitHub issue to correct it, or post a new
  comment with the correct wallet name. Notify the maintainer with an
  `@Scottcjn` mention.

### I want to transfer RTC to a different wallet

- If you have a basic wallet (string name only), ask the maintainer to
  perform an admin transfer.
- If you have a secure wallet with Ed25519 keys, use the signed transfer
  endpoint described above.

### The transfer is still pending after 24 hours

- Contact the maintainer via the bounty issue comments, Discord
  (`discord.gg/XnRp7M5gBW`), or Telegram
  (`t.me/+l8dHTjXCBNM1MTIx`).

---

## Tips for Fast Payouts

1. **Read the issue carefully.** Understand exactly what is being asked
   before writing code.
2. **Keep PRs small and focused.** One bounty per PR. Do not bundle
   unrelated changes.
3. **Include evidence.** Tests, screenshots, curl commands showing the
   fix works -- anything that proves correctness.
4. **Follow existing style.** Match the indentation, naming conventions,
   and patterns already in the codebase.
5. **Write clear commit messages.** Explain *why*, not just *what*.
6. **Respond to review quickly.** The faster you address feedback, the
   faster the merge.
