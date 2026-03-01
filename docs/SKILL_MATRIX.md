# Skill Matrix

This matrix helps you self-select bounties that match your skills. Pick a row that matches what you can ship quickly, then browse the live bounty feed.

## Matrix (skills → bounty types)

| Primary skill | Typical bounty types | What you’ll usually do | Example repos / issues |
|---|---|---|---|
| **Python (APIs)** | API endpoints, bugfixes, automation scripts | FastAPI/Flask routes, background jobs, CLI tools | BoTTube, bounty-concierge, RustChain tooling |
| **Python (testing)** | Add/expand test coverage | Write pytest tests, fixtures, mocks, CI fixes | BoTTube `tests/`, bounty-concierge test suite |
| **JavaScript / TypeScript (frontend)** | UI fixes, dashboard features, docs sites | React/Next UI work, state management, fetch integration | cal.com, highlight.io, various dashboards |
| **Node.js (backend)** | REST endpoints, bots, SDKs | Express/Fastify APIs, SDK wrappers, webhook handlers | BoTTube JS SDK, automation bots |
| **DevOps / CI** | GitHub Actions, Dockerization, release automation | Add CI workflows, docker-compose, caching, lint/test steps | Many Scottcjn repos (CI + docs micro-bounties) |
| **Docs / Technical writing** | README improvements, platform guides, contributor onboarding | Write concise docs, setup guides, API usage examples | `docs/`, `CONTRIBUTING.md`, API docs |
| **Security (basic)** | Hardening, secrets scanning, headers, safe defaults | Add security headers, env validation, remove hardcoded tokens | SECURITY.md + code hardening |
| **Data / research** | Platform comparisons, datasets, benchmarking notes | Collect and normalize data, provide citations and links | Dataset bounties in various orgs |

## How to pick a bounty fast

1. Prefer issues with **clear acceptance criteria** and **no existing PRs**.
2. Prefer bounties that are **testable locally** (unit tests over manual demos).
3. If you’re new: start with **docs** or **tests**.

## Where to find bounties

- GitHub issue search: `label:bounty state:open`
- RustChain ecosystem bounties: https://github.com/Scottcjn/rustchain-bounties
