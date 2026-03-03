"""PoW dual-mining helpers for Warthog (Janushash).

This module provides:
- process/service/screen detection for external PoW miners
- RustChain node RPC proof checks
- pool endpoint/account configuration proof
- managed subprocess launch/stop with log capture
- bonus multiplier calculation based on verifications
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests

NODE_RPC_URL = "http://127.0.0.1:3000"

POOL_ENDPOINTS = {
    "woolypooly": "stratum+tcp://pool.woolypooly.com:3140",
    "cedric-crispin": "stratum+tcp://warthog.cedric-crispin.com:3008",
    "herominers": "stratum+tcp://warthog.herominers.com:1140",
    "accpool": "stratum+tcp://warthog.acc-pool.pw:1140",
}

MULTIPLIER_MANAGED_SUBPROCESS = 1.5
MULTIPLIER_EXTERNAL_MINER = 1.15
MULTIPLIER_POOL_VERIFIED = 1.3
MULTIPLIER_NODE_VERIFIED = 1.5


@dataclass
class ManagedMiner:
    """Represents a managed miner subprocess."""

    process: subprocess.Popen
    command: List[str]
    log_path: str
    logger_thread: Optional[threading.Thread] = None


def _run_command(command: List[str], timeout: int = 5) -> Tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except FileNotFoundError:
        return 127, "", f"Command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out: {' '.join(command)}"
    except Exception as exc:  # pragma: no cover - defensive
        return 1, "", str(exc)


def _load_json(resp: requests.Response):
    """Safely parse JSON from a response."""
    try:
        return resp.json()
    except ValueError:
        return {
            "error": "Non-JSON response",
            "status_code": resp.status_code,
            "body": (resp.text or "")[:500],
        }


def _canonical_pool_name(name: str) -> Optional[str]:
    """Normalize pool aliases to known keys."""
    if not name:
        return None
    normalized = name.strip().lower().replace("_", "-")
    aliases = {
        "wooly": "woolypooly",
        "woolypooly": "woolypooly",
        "cedric": "cedric-crispin",
        "cedric-crispin": "cedric-crispin",
        "hero": "herominers",
        "herominers": "herominers",
        "acc": "accpool",
        "accpool": "accpool",
        "acc-pool": "accpool",
    }
    return aliases.get(normalized)


def resolve_pool_endpoint(pool_name: Optional[str], pool_url: Optional[str] = None) -> Dict:
    """Resolve a known pool endpoint or accept an explicit pool URL."""
    if pool_url:
        return {
            "verified": True,
            "pool": pool_name or "custom",
            "endpoint": pool_url,
            "source": "explicit-url",
        }

    canonical = _canonical_pool_name(pool_name or "")
    if not canonical:
        return {
            "verified": False,
            "error": "Unknown pool. Use one of: woolypooly, cedric-crispin, herominers, accpool",
        }

    return {
        "verified": True,
        "pool": canonical,
        "endpoint": POOL_ENDPOINTS[canonical],
        "source": "known-pool",
    }


def detect_pow_processes() -> Dict:
    """Detect Warthog/Janushash PoW miners via process, systemd, and screen checks."""
    result = {
        "detected": False,
        "external_miner_detected": False,
        "processes": [],
        "systemd_services": [],
        "screen_sessions": [],
        "errors": [],
    }

    rc, stdout, stderr = _run_command(["ps", "-eo", "args"])
    if rc != 0:
        result["errors"].append(f"Process listing failed: {stderr or stdout}")
        lines = []
    else:
        lines = stdout.splitlines()

    bz_re = re.compile(r"\\bbzminer\\b.*(?:-a\\s+warthog|-a=warthog)", re.IGNORECASE)
    janus_re = re.compile(r"\\bjanusminer(?:-ubuntu\\S*)?\\b", re.IGNORECASE)
    node_re = re.compile(r"\\bwart-node(?:-linux)?\\b", re.IGNORECASE)

    for line in lines:
        cmd = line.strip()
        if not cmd:
            continue
        if bz_re.search(cmd):
            result["processes"].append({"type": "bzminer", "source": "ps", "cmd": cmd})
        elif janus_re.search(cmd):
            result["processes"].append({"type": "janusminer", "source": "ps", "cmd": cmd})
        elif node_re.search(cmd):
            result["processes"].append({"type": "wart-node", "source": "ps", "cmd": cmd})

    for service in ("rustchain-miner", "wart-node"):
        s_rc, s_out, s_err = _run_command(["systemctl", "is-active", service])
        active = s_rc == 0 and s_out.strip() == "active"
        svc = {
            "name": service,
            "active": active,
            "status": s_out.strip() or s_err.strip() or "unknown",
        }
        result["systemd_services"].append(svc)

    sc_rc, sc_out, sc_err = _run_command(["screen", "-ls"])
    if sc_rc == 0:
        for line in sc_out.splitlines():
            if "wart" in line.lower():
                result["screen_sessions"].append(line.strip())
    elif sc_rc != 127:
        result["errors"].append(f"screen -ls failed: {sc_err or sc_out}")

    result["detected"] = bool(
        result["processes"]
        or any(s["active"] for s in result["systemd_services"])
        or result["screen_sessions"]
    )
    result["external_miner_detected"] = result["detected"]
    return result


def query_node_rpc(address: str, base_url: str = NODE_RPC_URL, timeout: int = 5) -> Dict:
    """Query node RPC proof endpoints for chain, eligibility, and balance."""
    if not address:
        return {"verified": False, "error": "Address is required for node proof"}

    endpoints = {
        "chain_head": f"{base_url}/chain/head",
        "mine_eligibility": f"{base_url}/chain/mine/{address}",
        "balance": f"{base_url}/account/{address}/balance",
    }

    payload = {"verified": False, "address": address, "results": {}, "errors": []}

    for key, url in endpoints.items():
        try:
            resp = requests.get(url, timeout=timeout)
            data = _load_json(resp)
            payload["results"][key] = {
                "ok": resp.ok,
                "status_code": resp.status_code,
                "data": data,
            }
            if not resp.ok:
                payload["errors"].append(f"{key}: HTTP {resp.status_code}")
            if isinstance(data, dict) and data.get("error"):
                payload["errors"].append(f"{key}: {data['error']}")
        except requests.RequestException as exc:
            payload["results"][key] = {"ok": False, "status_code": None, "error": str(exc)}
            payload["errors"].append(f"{key}: {exc}")

    payload["verified"] = len(payload["errors"]) == 0
    return payload


def verify_pool_account(address: str, pool_name: Optional[str], pool_url: Optional[str] = None) -> Dict:
    """Validate pool configuration/account parameters.

    This verifies that the selected pool endpoint is recognized (or explicit)
    and that an address is provided for payout attribution.
    """
    if not address:
        return {"verified": False, "error": "Address is required for pool verification"}

    resolved = resolve_pool_endpoint(pool_name, pool_url)
    if not resolved.get("verified"):
        return resolved

    return {
        "verified": True,
        "address": address,
        "pool": resolved["pool"],
        "endpoint": resolved["endpoint"],
        "proof": "pool-config-validated",
    }


def build_bzminer_command(wallet: str, pool_url: str, miner_path: str = "bzminer") -> List[str]:
    """Build command for bzminer warthog mining."""
    if not wallet:
        raise ValueError("wallet is required")
    if not pool_url:
        raise ValueError("pool_url is required")
    return [miner_path, "-a", "warthog", "-w", wallet, "-p", pool_url]


def build_janusminer_command(
    wallet: str,
    miner_path: str = "janusminer-ubuntu22",
    host: str = "127.0.0.1",
    port: int = 3000,
) -> List[str]:
    """Build command for Janusminer against local node."""
    if not wallet:
        raise ValueError("wallet is required")
    return [miner_path, "-a", wallet, "-h", host, "-p", str(port)]


def _pump_logs(pipe, log_file):
    """Stream child process output into log file."""
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            log_file.write(line)
            log_file.flush()
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def start_managed_miner(command: List[str], log_path: str = "warthog_miner.log") -> ManagedMiner:
    """Start a managed miner subprocess and redirect stdout/stderr to log file."""
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    log_file = open(log_path, "a", encoding="utf-8")

    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
    except Exception:
        log_file.close()
        raise

    thread = None
    if proc.stdout is not None:
        thread = threading.Thread(target=_pump_logs, args=(proc.stdout, log_file), daemon=True)
        thread.start()

    return ManagedMiner(process=proc, command=command, log_path=log_path, logger_thread=thread)


def stop_managed_miner(managed: ManagedMiner, timeout: int = 10) -> Dict:
    """Stop a managed miner subprocess cleanly."""
    proc = managed.process
    if proc.poll() is not None:
        return {"stopped": True, "already_exited": True, "returncode": proc.returncode}

    proc.terminate()
    try:
        proc.wait(timeout=timeout)
        return {"stopped": True, "already_exited": False, "returncode": proc.returncode}
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
        return {
            "stopped": True,
            "already_exited": False,
            "force_killed": True,
            "returncode": proc.returncode,
        }


def calculate_bonus_multiplier(
    managed_subprocess_running: bool,
    external_miner_detected: bool,
    pool_account_verified: bool,
    node_rpc_verified: bool,
) -> Dict:
    """Calculate combined bonus multiplier from PoW proofs."""
    multiplier = 1.0
    factors = []

    if managed_subprocess_running:
        multiplier *= MULTIPLIER_MANAGED_SUBPROCESS
        factors.append({"name": "managed_pow_subprocess", "multiplier": MULTIPLIER_MANAGED_SUBPROCESS})

    if external_miner_detected:
        multiplier *= MULTIPLIER_EXTERNAL_MINER
        factors.append({"name": "external_miner_detected", "multiplier": MULTIPLIER_EXTERNAL_MINER})

    if pool_account_verified:
        multiplier *= MULTIPLIER_POOL_VERIFIED
        factors.append({"name": "pool_account_verified", "multiplier": MULTIPLIER_POOL_VERIFIED})

    if node_rpc_verified:
        multiplier *= MULTIPLIER_NODE_VERIFIED
        factors.append({"name": "node_rpc_verified", "multiplier": MULTIPLIER_NODE_VERIFIED})

    return {
        "base": 1.0,
        "total_multiplier": round(multiplier, 6),
        "factors": factors,
    }


def summarize_for_console(summary: Dict) -> str:
    """Format summary object for human-readable CLI output."""
    return json.dumps(summary, indent=2, sort_keys=True, default=str)
