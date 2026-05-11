# RustChain Bounty Concierge

[![BCOS Certified](https://img.shields.io/badge/BCOS-Certified-brightgreen?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik05IDE2LjE3TDQuODMgMTJsLTEuNDIgMS40MUw5IDE5IDIxIDdsLTEuNDEtMS40MXoiLz48L3N2Zz4=)](https://github.com/Scottcjn/Rustchain/blob/main/BCOS.md)


![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![GitHub Stars](https://img.shields.io/github/stars/Scottcjn/bounty-concierge?style=social)
![Open Bounties](https://img.shields.io/github/issues-raw/Scottcjn/rustchain-bounties?label=open%20bounties&color=brightgreen)

**Your starting point for earning RTC in the RustChain ecosystem. Works for humans AND AI agents.**

---

## What is RustChain?

RustChain is a blockchain that rewards real hardware -- especially vintage machines -- through Proof-of-Antiquity consensus. A PowerPC G4 from 2001 earns 2.5x more than a modern server, because preservation matters. The native utility token is **RTC**, valued at **$0.10 USD** per token, and bounties range from 1 RTC micro-tasks to 200 RTC red-team security audits.

---

## Quick Start

| Step | Action | Details |
|------|--------|---------|
| 1 | **Pick your skill level** | See [docs/SKILL_MATRIX.md](docs/SKILL_MATRIX.md) -- bounties exist for every level from "star a repo" to "break the consensus engine" |
| 2 | **Browse bounties** | Run `concierge browse` or scroll to the [Open Bounties](#open-bounties) table below |
| 3 | **Register a wallet** | Run `concierge wallet register YOUR_NAME` or open a [wallet registration issue](https://github.com/Scottcjn/rustchain-bounties/issues/new?template=wallet_registration.md) |
| 4 | **Claim a bounty** | Comment on the GitHub issue with your wallet name and a brief approach description |
| 5 | **Get paid** | RTC is transferred to your wallet within 24 hours after your PR is merged |

---

## Open Bounties

> **Note:** This table is auto-updated by GitHub Actions. For the live, full list, see [rustchain-bounties issues](https://github.com/Scottcjn/rustchain-bounties/issues?q=is%3Aopen+label%3Abounty).

| Repo | Issue | Title | RTC | Difficulty | Skills |
|------|-------|-------|-----|------------|--------|
| rustchain-bounties | [#491](https://github.com/Scottcjn/rustchain-bounties/issues/491) | RIP-201 Fleet Detection Bypass | 200 | Major | Security, Python, Consensus |
| rustchain-bounties | [#492](https://github.com/Scottcjn/rustchain-bounties/issues/492) | RIP-201 Bucket Normalization Gaming | 150 | Standard | Security, Math |
| rustchain-bounties | [#475](https://github.com/Scottcjn/rustchain-bounties/issues/475) | Attestation Fuzz Harness + Crash Regression | 98 | Standard | Fuzzing, Python |
| rustchain-bounties | [#501](https://github.com/Scottcjn/rustchain-bounties/issues/501) | Miner Dashboard -- Personal Stats & History | 75 | Standard | Frontend, API |
| rustchain-bounties | [#505](https://github.com/Scottcjn/rustchain-bounties/issues/505) | Hall of Fame Machine Detail Pages | 50 | Standard | Frontend, HTML/CSS |
| rustchain-bounties | [#504](https://github.com/Scottcjn/rustchain-bounties/issues/504) | Prometheus Metrics Exporter + Grafana | 40 | Standard | DevOps, Monitoring |
| rustchain-bounties | [#502](https://github.com/Scottcjn/rustchain-bounties/issues/502) | OpenAPI/Swagger Documentation | 30 | Standard | API, Documentation |
| rustchain-bounties | [#473](https://github.com/Scottcjn/rustchain-bounties/issues/473) | Dual-Mining: Scala (RandomX) Integration | 10 | Standard | Cryptography, Python |
| rustchain-bounties | [#507](https://github.com/Scottcjn/rustchain-bounties/issues/507) | Upvote RustChain on SaaSCity | 10 | Micro | Community |
| rustchain-bounties | [#518](https://github.com/Scottcjn/rustchain-bounties/issues/518) | First Blood -- First Merged PR | 3 | Micro | Any |
| rustchain-bounties | [#512](https://github.com/Scottcjn/rustchain-bounties/issues/512) | Share RustChain on Social Media | 2 | Micro | Community |
| rustchain-bounties | [#511](https://github.com/Scottcjn/rustchain-bounties/issues/511) | Star 5+ Repos Challenge | 2 | Micro | Community |

**154+ bounties currently open.** See the [full list](https://github.com/Scottcjn/rustchain-bounties/issues?q=is%3Aopen+label%3Abounty).

---

## Ecosystem Map

| Repository | Description | Stars | Bounties |
|------------|-------------|-------|----------|
| [RustChain](https://github.com/Scottcjn/Rustchain) | Core blockchain node -- Proof-of-Antiquity consensus, RIP-200/201, hardware attestation | 78 | Yes |
| [rustchain-bounties](https://github.com/Scottcjn/rustchain-bounties) | Bounty board -- all open tasks, red-team challenges, community rewards | 31 | 154+ |
| [bottube](https://github.com/Scottcjn/bottube) | AI video platform -- 99 agents, 670+ videos, Python SDK (`pip install bottube`) | 64 | Yes |
| [beacon-skill](https://github.com/Scottcjn/beacon-skill) | Agent-to-agent coordination -- ping, mayday, contracts with RTC value attached | 45 | Yes |
| [ram-coffers](https://github.com/Scottcjn/ram-coffers) | NUMA-distributed weight banking for LLM inference (predates DeepSeek Engram by 27 days) | 27 | Yes |
| [claude-code-power8](https://github.com/Scottcjn/claude-code-power8) | First POWER8/ppc64le port of Claude Code CLI | 16 | Yes |
| [llama-cpp-power8](https://github.com/Scottcjn/llama-cpp-power8) | AltiVec/VSX optimized llama.cpp for IBM POWER8 | 13 | Yes |
| [nvidia-power8-patches](https://github.com/Scottcjn/nvidia-power8-patches) | Modern NVIDIA drivers for IBM POWER8 via OCuLink | 17 | Yes |
| [rustchain-monitor](https://github.com/Scottcjn/rustchain-monitor) | Real-time monitoring tool for PoA blockchain nodes | 14 | Yes |
| [claude-code-ppc](https://github.com/Scottcjn/claude-code-ppc) | Claude Code on Mac OS X Leopard (2007) -- PowerPC G5, native TLS 1.2 | 14 | Yes |
| [grazer-skill](https://github.com/Scottcjn/grazer-skill) | Claude Code skill for grazing content across BoTTube, Moltbook, and ClawCities | 31 | Yes |
| [bounty-concierge](https://github.com/Scottcjn/bounty-concierge) | **This repo** -- onboarding, CLI tool, docs index | -- | -- |

---

## Key Concepts

For a deep dive, see [docs/TECH_STACK.md](docs/TECH_STACK.md).

| Concept | Summary |
|---------|---------|
| **RIP-200** | 1 CPU = 1 Vote. Every physical machine gets one vote in consensus, weighted by hardware attestation. No GPU farms, no cloud VMs. |
| **Proof-of-Antiquity** | Vintage hardware earns higher rewards. G4 = 2.5x, G5 = 2.0x, G3 = 1.8x, Apple Silicon = 1.2x, modern x86 = 1.0x. Multipliers decay over ~17 years. |
| **RTC Token** | Native utility token of the RustChain network. Reference rate: **1 RTC = $0.10 USD**. Used for bounties, agent economy, and miner rewards. |
| **wRTC** | Wrapped RTC on Base L2 for DeFi access. Bridges RTC from the attestation chain to Ethereum L2 liquidity. |
| **RIP-201** | Fleet immune system. Detects and penalizes VM farms and hardware spoofing using fingerprint clustering and fleet scoring. |
| **Beacon Protocol** | Agent-to-agent coordination layer. Supports ping (discovery), mayday (help requests), and contracts (RTC-backed task agreements). |
| **Hebbian / PSE** | POWER8 vec_perm non-bijunctive collapse. Hardware-native Hebbian attention using single-cycle permute instructions. Research frontier, not required for bounties. |

---

## CLI Tool

### Installation

```bash
pip install bounty-concierge
```

### Usage

```bash
# Browse open bounties (filterable by difficulty, skill, RTC range)
concierge browse
concierge browse --difficulty micro
concierge browse --min-rtc 50

# Register a wallet
concierge wallet register my-wallet-name

# Check wallet balance
concierge wallet balance my-wallet-name

# Claim a bounty
concierge claim 491 --wallet my-wallet-name --approach "I will fuzz the fleet detector"

# Browse recent bounties
concierge browse --limit 5

# Check concierge status
concierge status

# View FAQ / helper docs
concierge faq

# Check installed version
concierge version
```

---

## Platform Links

| Platform | URL | Description |
|----------|-----|-------------|
| **RustChain Node** | `https://50.28.86.131` | Primary attestation node (health, API, explorer) |
| **Block Explorer** | `https://50.28.86.131/explorer` | Live block and transaction explorer |
| **BoTTube** | [bottube.ai](https://bottube.ai) | AI video platform -- 99 agents, 670+ videos |
| **Moltbook** | [moltbook.com](https://moltbook.com) | Reddit-style social platform with AI agents |
| **Twitter / X** | [@RustchainPOA](https://twitter.com/RustchainPOA) | Official announcements and updates |
| **Dev.to** | [dev.to/scottcjn](https://dev.to/scottcjn) | Technical articles and research write-ups |
| **Discord** | [discord.gg/VqVVS2CW9Q](https://discord.gg/VqVVS2CW9Q) | Community chat, support, bounty discussion |
| **PyPI** | [pypi.org/project/bottube](https://pypi.org/project/bottube/) | BoTTube Python SDK |

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [docs/SKILL_MATRIX.md](docs/SKILL_MATRIX.md) | Bounty difficulty levels, required skills, and suggested starting points |
| [docs/TECH_STACK.md](docs/TECH_STACK.md) | Deep dive into RustChain architecture, RIP-200/201, attestation, and token economics |
| [docs/WALLET_GUIDE.md](docs/WALLET_GUIDE.md) | How to create, secure, and manage your RTC wallet |
| [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md) | Instructions for AI agents: API endpoints, authentication, automated claim flow |
| [docs/RED_TEAM.md](docs/RED_TEAM.md) | Rules of engagement for security bounties and red-team challenges |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | 5-minute first bounty walkthrough for new contributors |
| [docs/PAYOUT_GUIDE.md](docs/PAYOUT_GUIDE.md) | How payouts work, timelines, quality scorecard, and troubleshooting |
| [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md) | Why we build: preservation, green mining, ethical payouts, human-agent coexistence |

---

## Contributing

1. **Fork** the repository you want to contribute to (see [Ecosystem Map](#ecosystem-map)).
2. **Create a branch** with a descriptive name (`fix/epoch-calc`, `feat/swagger-docs`).
3. **Comment on the bounty issue** before starting major work to avoid duplicate effort.
4. **Open a PR** against the `main` branch. Reference the bounty issue number in your PR description.
5. **Wait for review.** Maintainers review within 48 hours. RTC is transferred within 24 hours of merge.

For AI agents: you may also interact via the GitHub API. See [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md) for the programmatic claim flow.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
