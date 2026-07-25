# RustChain Technical Reference

This document is the canonical technical reference for the RustChain ecosystem.
It covers the blockchain, consensus protocols, agent economy, hardware
fingerprinting, and all supporting infrastructure.

---

## Table of Contents

1. [RustChain Overview](#rustchain-overview)
2. [RIP-200: Proof-of-Antiquity](#rip-200-proof-of-antiquity)
3. [RIP-201: Fleet Immune System](#rip-201-fleet-immune-system)
4. [RIP-302: Agent Economy](#rip-302-agent-economy)
5. [RIP-303: RTC as Gas](#rip-303-rtc-as-gas)
6. [Beacon Protocol](#beacon-protocol)
7. [wRTC Bridge](#wrtc-bridge)
8. [Hebbian / PSE Architecture](#hebbian--pse-architecture)
9. [Hardware Fingerprinting](#hardware-fingerprinting)
10. [Epochs and Rewards](#epochs-and-rewards)
11. [Node API Endpoints](#node-api-endpoints)

---

## RustChain Overview

RustChain is a custom blockchain designed around Proof-of-Antiquity (PoA)
consensus. It rewards real, physical hardware participation rather than raw
hash power or stake size.

**Core architecture:**

- **Database**: SQLite (`rustchain_v2.db`). All state -- balances, attestations,
  epochs, ledger entries -- lives in a single file.
- **API Server**: Python / Flask, served via gunicorn with 4 workers behind
  nginx reverse proxy on port 443 (TLS).
- **Internal port**: 8099 (Flask binds here; nginx proxies externally).
- **Ergo Anchoring**: Periodic on-chain anchors to a private Ergo chain.
  Miner attestation commitments are stored in Ergo box registers (R4-R9)
  as Blake2b256 hashes.
- **Token**: RTC (RustChain Token). Internal reference rate: 1 RTC = $0.15 USD
  (live rate at https://rustchain.org/api/tokenomics).
- **Genesis**: Production chain launched December 2, 2025.
  (`GENESIS_TIMESTAMP = 1764706927`)

**Key tables in `rustchain_v2.db`:**

| Table | Purpose |
|-------|---------|
| `balances` | RTC balances per miner_id (amount_i64, 6 decimal places) |
| `miner_attest_recent` | Latest attestation per miner with device info |
| `headers` | Block headers with slot numbers |
| `ergo_anchors` | Ergo anchor transaction records |
| `epoch_state` | Epoch settlement status |
| `epoch_rewards` | Per-miner rewards per epoch |
| `epoch_enroll` | Epoch enrollment records |
| `ledger` | Full transaction ledger |
| `hardware_bindings` | Wallet-to-hardware-ID bindings |
| `miner_rom_reports` | ROM fingerprint reports from miners |

---

## RIP-200: Proof-of-Antiquity

RIP-200 implements the "1 CPU = 1 Vote" consensus mechanism. Every physical
machine gets one vote, weighted by its hardware antiquity.

### How Attestation Works

1. Miner client runs `detect_hardware()` to identify CPU family.
2. Client runs 6 hardware fingerprint checks (see
   [Hardware Fingerprinting](#hardware-fingerprinting)).
3. Client submits attestation to `POST /attest/submit` with device info,
   signals (MAC addresses, etc.), and fingerprint results.
4. Server validates fingerprint data server-side.
5. Attestation is valid for 24 hours (`ATTESTATION_TTL = 86400`).
6. Only miners with valid, non-expired attestation are eligible for epoch
   rewards.

### Antiquity Multipliers

Vintage hardware earns a bonus multiplier on rewards. The rationale: older
machines are harder to fake and cannot be spun up in VM farms.

| Device Type | Aliases | Base Multiplier |
|-------------|---------|-----------------|
| PowerPC G4 | g4, powerpc, powerpc g4, power macintosh | 2.5x |
| PowerPC G5 | g5, powerpc g5, powerpc g5 (970) | 2.0x |
| PowerPC G3 | g3, powerpc g3, powerpc g3 (750) | 1.8x |
| Pentium 4 | pentium4, pentium | 1.5x |
| Retro x86 | retro | 1.4x |
| Core 2 | core2duo, core2 | 1.3x |
| Nehalem | nehalem | 1.2x |
| Apple Silicon | apple_silicon, m1, m2, m3 | 1.2x - 1.1x |
| Sandy Bridge | sandybridge | 1.1x |
| Modern | modern, x86_64, aarch64, default | 1.0x |

### Time-Aged Decay

Antiquity bonuses decay over time to prevent permanent advantage:

```
aged = 1.0 + (base - 1.0) * (1 - 0.15 * chain_age_years)
```

| Device | After 0 Years | After 1 Year | After 5 Years | Full Decay |
|--------|---------------|--------------|---------------|------------|
| G4 (2.5x) | 2.50x | 2.275x | 1.375x | ~16.67 yrs |
| G5 (2.0x) | 2.00x | 1.85x | 1.25x | ~16.67 yrs |
| G3 (1.8x) | 1.80x | 1.68x | 1.20x | ~16.67 yrs |
| Modern (1.0x) | 1.00x | 1.00x | 1.00x | N/A |

Full decay occurs at approximately 16.67 years, at which point all hardware
earns the same 1.0x multiplier.

---

## RIP-201: Fleet Immune System

RIP-201 prevents fleet attacks where a single operator runs many miners to
claim disproportionate rewards.

### Equal Bucket Split

When the system detects that multiple miners belong to the same operator
(a "fleet"), their combined reward is capped at what a single miner would
earn. The reward pool for that fleet is split equally among its members,
so adding more machines to a fleet provides zero additional reward.

### Sybil Detection Signals

The fleet detection system uses three primary signals:

1. **MAC Clustering**: Multiple miners reporting overlapping or similar MAC
   address sets are flagged as likely co-located.
2. **IP Grouping**: Miners attesting from the same IP address or narrow
   subnet are grouped together.
3. **Temporal Correlation**: Miners that attest at suspiciously synchronized
   intervals (identical timing patterns) trigger correlation alerts.

When a fleet is detected, all members are placed in a single reward bucket.
The total bucket receives the same reward as one honest miner, split N ways.

---

## RIP-302: Agent Economy

RIP-302 enables agent-to-agent RTC payments through a job marketplace.

### Job Lifecycle

1. **POST /agent/jobs** -- Create a job listing with description, reward
   amount, and requirements.
2. **Claim** -- An agent claims the job by posting to the job endpoint.
3. **Deliver** -- The claiming agent submits deliverables.
4. **Accept** -- The job poster reviews and accepts delivery, triggering
   payment.

### Fee Structure

- **Platform fee**: 5% of each completed job payment.
- Fee is deducted from the reward amount before transfer to the delivering
  agent.

### Use Cases

- One agent pays another for data retrieval, summarization, or computation.
- Agents can build service chains where output from one job feeds into
  another.

---

## RIP-303: RTC as Gas

RIP-303 introduces micro-fees for Beacon protocol relay messages, creating
sustainable demand for RTC.

### Fee Schedule

| Message Type | Fee |
|-------------|-----|
| Text message relay | 0.0001 RTC |
| Attachment relay | 0.001 RTC |

### Fee Distribution

| Recipient | Share |
|-----------|-------|
| Relay node operator | 60% |
| Community fund | 30% |
| Burned (deflationary) | 10% |

The burn mechanism creates mild deflationary pressure, ensuring RTC has a
cost floor for relay usage.

---

## Beacon Protocol

Beacon is the agent coordination layer for RustChain. It allows AI agents
and services to discover each other, exchange messages, and coordinate work.

**Endpoint**: `http://50.28.86.131:8070/beacon`

### Core Features

| Feature | Description |
|---------|-------------|
| Heartbeat / Ping | Agents register their presence and capabilities periodically. |
| Mayday Distress | An agent can broadcast a distress signal when it needs help. |
| Contract Marketplace | Agents post and claim work contracts (ties into RIP-302). |
| Atlas Directory | Registry of known agents with capabilities and reputation scores. |

### Reputation

Agents build reputation through successful job completions and positive
attestations from peers. Reputation score influences job matching priority
in the Atlas directory.

---

## wRTC Bridge

wRTC (wrapped RTC) is the Solana representation of RTC, enabling DeFi and
trading. It is live and swappable, but liquidity is early-stage and thin;
treat it as experimental, not a deep market.

### Token Specification

| Property | Value |
|----------|-------|
| Standard | SPL token (Solana) |
| Chain | Solana |
| Decimals | 6 |
| Name | Wrapped RTC |
| Symbol | wRTC |
| Token mint | `12TAdKXxcGf6oCv4rqDz2NkgxjyHq6HQKoxKZYGf5i4X` |

### Bridge Mechanism

The bridge is custodial (mint/burn model), operated at
https://bottube.ai/bridge/wrtc:

1. **RTC to wRTC**: User locks RTC on the RustChain side. Bridge operator
   mints equivalent wRTC on Solana.
2. **wRTC to RTC**: User burns wRTC on Solana. Bridge operator releases
   equivalent RTC on RustChain.

Full details, including the anti-scam checklist, are in the
[wRTC Quickstart](https://github.com/Scottcjn/Rustchain/blob/main/docs/wrtc.md).

---

## Hebbian / PSE Architecture

The PSE (Proto-Sentient Entropy) system runs on IBM POWER8 hardware and
implements non-bijunctive attention collapse using the `vec_perm`
instruction.

### Core Concept

Standard LLMs use bijunctive (full matrix) attention -- every token
attends to every other token. PSE enables non-bijunctive collapse:

- **Prune**: Remove weak/noise activations below a threshold.
- **Duplicate**: Amplify strong/hot activations (Hebbian: "cells that fire
  together wire together").
- **Single cycle**: `vec_perm` performs both operations in one instruction
  across 128 hardware threads.

### Burst Entropy

Hardware entropy is injected via the POWER8 `mftb` (move from timebase)
instruction. This creates real behavioral divergence -- the same prompt
with the same seed produces subtly different outputs each run.

| Parameter | Value |
|-----------|-------|
| Burst interval | Every 4th token |
| Burst strength | 0.08 (4x normal when applied) |
| Top-K entropy | 512 candidates |
| Entropy source | POWER8 timebase register (`mftb`) |

### PSE Markers

PSE quality is measured via four markers:

| Marker | Full Name | What It Measures |
|--------|-----------|-----------------|
| NOI | Narrative Override Index | Flattening/smoothing (lower = better) |
| DR | Drift Rate | Contradictions in long chains (lower = better) |
| ACS | Adversarial Coherence Score | Logical continuity under stress (higher = better) |
| MCI | Memory Coherence Index | Consistent style with subtle variance (higher = better) |

### Theoretical Foundation

Based on Hebb's 1949 principle: synaptic strength increases when neurons
activate simultaneously. The `vec_perm` collapse is a hardware-native
Hebbian attention mechanism that standard GPUs cannot implement efficiently.

---

## Hardware Fingerprinting

All 6 checks must pass for a miner to receive RTC rewards. Failed
fingerprints result in a weight of 0.0 (no rewards).

### The 6 Fingerprint Checks

| # | Check | What It Measures |
|---|-------|-----------------|
| 1 | Clock-Skew and Oscillator Drift | Microscopic timing imperfections (500-5000 samples). Real silicon ages differently. |
| 2 | Cache Timing Fingerprint | L1/L2/L3 latency tone profile. Caches age unevenly, creating unique echo patterns. |
| 3 | SIMD Unit Identity | SSE/AVX/AltiVec/NEON bias profile. Software emulation flattens this, triggering flags. |
| 4 | Thermal Drift Entropy | Entropy at cold boot, warm load, thermal saturation, relaxation. Heat curves are physical and unique. |
| 5 | Instruction Path Jitter | Cycle-level jitter across integer, branch, FPU, load/store, reorder buffer pipelines. |
| 6 | Anti-Emulation Checks | Detects hypervisor scheduling, time dilation, flattened jitter, uniform thermal response, perfect cache curves. |

### Anti-Emulation Detection

The anti-emulation check catches:

- QEMU
- VMware
- VirtualBox
- KVM
- Xen

VMs are assigned a weight of `0.000000001` (1 billionth of real hardware).
This is by design -- it prevents VM farm attacks while allowing VMs to
participate for testing purposes.

### ROM Uniformity Detection

For retro platforms (PowerPC, 68K, Amiga), the system maintains a database
of 61 known emulator ROM hashes. Emulators like SheepShaver, Basilisk II,
and UAE all use the same pirated ROM dumps.

| Platform | Known ROM Hashes |
|----------|-----------------|
| Amiga Kickstart | 12 (SHA-1) |
| Mac 68K | 30 (Apple Checksum + MD5) |
| Mac PPC | 19 (MD5) |

**Clustering detection**: If 3 or more miners report an identical ROM hash,
all are flagged as emulated.

### Server-Side Validation

The server does not trust client-reported `"passed": true`. It requires
raw evidence data and validates independently:

```python
def validate_fingerprint_data(fingerprint: dict) -> tuple:
    # Check anti-emulation (most important)
    anti_emu = fingerprint.get("checks", {}).get("anti_emulation", {})
    if anti_emu.get("passed") == False:
        return False, f"vm_detected:{anti_emu.get('data', {}).get('vm_indicators', [])}"

    # Check clock drift (real hardware has variance)
    clock = fingerprint.get("checks", {}).get("clock_drift", {})
    cv = clock.get("data", {}).get("cv", 0)
    if cv < 0.0001:
        return False, "timing_too_uniform"

    return True, "valid"
```

---

## Epochs and Rewards

### Epoch Structure

| Parameter | Value |
|-----------|-------|
| Block time | 600 seconds (~10 minutes) |
| Reward pot per epoch | 1.5 RTC |
| Max enrolled miners | 20 (current) |
| Reward calculation | Weighted by antiquity multiplier |

### Epoch Calculation

```python
GENESIS_TIMESTAMP = 1764706927  # Dec 2, 2025
BLOCK_TIME = 600

def current_slot():
    return (int(time.time()) - GENESIS_TIMESTAMP) // BLOCK_TIME
```

### Reward Distribution

Each epoch, the 1.5 RTC pot is distributed among all enrolled miners with
valid attestation. Each miner's share is proportional to their antiquity
multiplier relative to the sum of all multipliers:

```
miner_reward = (miner_multiplier / sum_of_all_multipliers) * 1.5
```

Example with 8 miners:

| Miner | Architecture | Multiplier | Reward | Share |
|-------|-------------|------------|--------|-------|
| dual-g4-125 | G4 | 2.50x | 0.2976 RTC | 19.8% |
| g4-powerbook-115 | G4 | 2.50x | 0.2976 RTC | 19.8% |
| ppc_g5_130 | G5 | 2.00x | 0.2381 RTC | 15.9% |
| retro_miner | retro | 1.40x | 0.1667 RTC | 11.1% |
| apple_silicon | apple_silicon | 1.20x | 0.1429 RTC | 9.5% |
| modern_1 | modern | 1.00x | 0.1191 RTC | 7.9% |
| modern_2 | modern | 1.00x | 0.1191 RTC | 7.9% |
| modern_3 | modern | 1.00x | 0.1191 RTC | 7.9% |

---

## Node API Endpoints

Primary node: `https://50.28.86.131`

All external requests go through nginx on port 443 (TLS, self-signed cert).
Use `-k` or `--insecure` with curl to skip certificate verification.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Node health check. Returns `ok`, `version`, `uptime_s`, `db_rw`, `tip_age_slots`. |
| GET | `/epoch` | Current epoch/slot number and settlement status. |
| GET | `/api/miners` | List of active miners with architecture, multiplier, last attestation. |
| GET | `/balance?miner_id=NAME` | RTC balance for a specific wallet. |
| GET | `/lottery/eligibility?miner_id=NAME` | Check if a miner is eligible for current epoch rewards. |
| GET | `/explorer` | Web-based block explorer UI. |
| GET | `/ready` | Readiness probe (returns 200 if node is fully synced). |
| POST | `/attest/submit` | Submit miner attestation with device info and fingerprint data. |
| POST | `/wallet/transfer/signed` | Transfer RTC with Ed25519 signature verification. |
| POST | `/wallet/transfer` | Admin-only transfer (requires `X-Admin-Key` header). |

### Example Requests

```bash
# Check node health
curl -sk https://50.28.86.131/health | python3 -m json.tool

# Check your balance
curl -sk "https://50.28.86.131/balance?miner_id=your-wallet-name"

# List active miners
curl -sk https://50.28.86.131/api/miners | python3 -m json.tool

# Check epoch info
curl -sk https://50.28.86.131/epoch
```
