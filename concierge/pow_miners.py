"""Dual-mining support for PoW cryptocurrencies.

Detects running miners, queries node RPCs, verifies pool accounts,
and launches stock miners as managed subprocesses for dual-mining
with RustChain Proof-of-Antiquity.

Supports: Warthog (Janushash), Ergo, Kaspa, and more.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests


@dataclass
class MinerProcess:
    """Detected running miner process."""
    name: str
    pid: int
    cmdline: str
    detected_via: str  # 'process', 'systemd', 'screen'


@dataclass
class PoolConfig:
    """Mining pool configuration."""
    name: str
    stratum_url: str
    fee_pct: float
    api_url: Optional[str] = None


# Warthog pool configurations
WARTHOG_POOLS: Dict[str, PoolConfig] = {
    "woolypooly": PoolConfig(
        name="WoolyPooly",
        stratum_url="stratum+tcp://pool.woolypooly.com:3140",
        fee_pct=0.90,
        api_url="https://api.woolypooly.com/api/v1/pool/WART/stats",
    ),
    "cedric-crispin": PoolConfig(
        name="Cedric-Crispin",
        stratum_url="warthog.cedric-crispin.com",
        fee_pct=0.10,
    ),
    "herominers": PoolConfig(
        name="HeroMiners",
        stratum_url="warthog.herominers.com",
        fee_pct=0.90,
    ),
    "accpool": PoolConfig(
        name="AccPool",
        stratum_url="warthog.acc-pool.pw",
        fee_pct=0.0,  # varies
    ),
}

# Warthog node RPC endpoints
WARTHOG_RPC_BASE = "http://localhost:3000"


# ---------------------------------------------------------------------------
# Process Detection
# ---------------------------------------------------------------------------

def detect_running_miners(pow_name: str = "warthog") -> List[MinerProcess]:
    """Detect running miners for the specified PoW.
    
    Args:
        pow_name: Name of the PoW cryptocurrency (e.g., 'warthog')
    
    Returns:
        List of detected miner processes
    """
    miners = []
    
    if pow_name == "warthog":
        # Check for bzminer with -a warthog flag
        miners.extend(_detect_process_by_cmdline(
            pattern=r"bzminer.*-a\s+warthog",
            name="bzminer",
            via="process"
        ))
        
        # Check for janusminer
        miners.extend(_detect_process_by_cmdline(
            pattern=r"janusminer",
            name="janusminer",
            via="process"
        ))
        
        # Check for wart-node
        miners.extend(_detect_process_by_cmdname(
            names=["wart-node-linux", "wart-node"],
            via="process"
        ))
        
        # Check systemd services
        miners.extend(_detect_systemd_services(
            services=["wart-node", "rustchain-miner"],
            via="systemd"
        ))
        
        # Check screen sessions
        miners.extend(_detect_screen_sessions(
            pattern="wart",
            via="screen"
        ))
    
    return miners


def _detect_process_by_cmdline(pattern: str, name: str, via: str) -> List[MinerProcess]:
    """Detect processes by command line pattern."""
    miners = []
    try:
        # Use pgrep to find matching processes
        result = subprocess.run(
            ["pgrep", "-af", pattern],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    if len(parts) >= 2:
                        pid = int(parts[0])
                        cmdline = parts[1]
                        miners.append(MinerProcess(
                            name=name, pid=pid, cmdline=cmdline, detected_via=via
                        ))
    except (subprocess.SubprocessError, ValueError, FileNotFoundError):
        pass
    return miners


def _detect_process_by_cmdname(names: List[str], via: str) -> List[MinerProcess]:
    """Detect processes by command name."""
    miners = []
    for name in names:
        try:
            result = subprocess.run(
                ["pgrep", "-x", name],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for pid_str in result.stdout.strip().split("\n"):
                    if pid_str:
                        pid = int(pid_str)
                        miners.append(MinerProcess(
                            name=name, pid=pid, cmdline=name, detected_via=via
                        ))
        except (subprocess.SubprocessError, ValueError, FileNotFoundError):
            pass
    return miners


def _detect_systemd_services(services: List[str], via: str) -> List[MinerProcess]:
    """Detect running systemd services."""
    miners = []
    for service in services:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip() == "active":
                miners.append(MinerProcess(
                    name=service, pid=0, cmdline=f"systemd service: {service}", detected_via=via
                ))
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    return miners


def _detect_screen_sessions(pattern: str, via: str) -> List[MinerProcess]:
    """Detect screen sessions matching pattern."""
    miners = []
    try:
        result = subprocess.run(
            ["screen", "-ls"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if pattern.lower() in line.lower() and "\t" in line:
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        session_name = parts[0].strip()
                        miners.append(MinerProcess(
                            name=f"screen:{session_name}",
                            pid=0,
                            cmdline=f"screen session: {session_name}",
                            detected_via=via
                        ))
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return miners


# ---------------------------------------------------------------------------
# Node RPC Integration
# ---------------------------------------------------------------------------

def query_warthog_node(endpoint: str = "/chain/head") -> Optional[Dict[str, Any]]:
    """Query Warthog node RPC.
    
    Args:
        endpoint: RPC endpoint path
    
    Returns:
        JSON response dict or None if failed
    """
    url = f"{WARTHOG_RPC_BASE}{endpoint}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except (requests.RequestException, ValueError):
        pass
    return None


def verify_warthog_node() -> bool:
    """Verify Warthog node is running and responding.
    
    Returns:
        True if node is accessible and returns valid chain data
    """
    data = query_warthog_node("/chain/head")
    if data:
        # Check for expected fields
        if "pinHash" in data or "pinHeight" in data or "worksum" in data:
            return True
    return False


def get_warthog_chain_info() -> Optional[Dict[str, Any]]:
    """Get current Warthog chain information.
    
    Returns:
        Dict with chain height, hash, worksum or None
    """
    data = query_warthog_node("/chain/head")
    if data:
        return {
            "height": data.get("pinHeight", 0),
            "hash": data.get("pinHash", ""),
            "worksum": data.get("worksum", ""),
        }
    return None


# ---------------------------------------------------------------------------
# Pool Account Verification
# ---------------------------------------------------------------------------

def verify_pool_account(pool_name: str, wallet_address: str) -> bool:
    """Verify active mining on a pool.
    
    Args:
        pool_name: Pool identifier (e.g., 'woolypooly')
        wallet_address: Miner wallet address
    
    Returns:
        True if wallet is actively mining on the pool
    """
    pool = WARTHOG_POOLS.get(pool_name)
    if not pool or not pool.api_url:
        return False
    
    try:
        resp = requests.get(f"{pool.api_url}/{wallet_address}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # Check for mining stats
            if "hashrate" in data or "shares" in data or "balance" in data:
                return True
    except (requests.RequestException, ValueError):
        pass
    return False


# ---------------------------------------------------------------------------
# Subprocess Launch
# ---------------------------------------------------------------------------

def launch_miner_subprocess(
    miner_name: str,
    wallet: str,
    pool_url: str,
    miner_path: Optional[str] = None,
) -> Optional[subprocess.Popen]:
    """Launch a stock miner as a managed subprocess.
    
    Args:
        miner_name: Miner name ('bzminer', 'janusminer')
        wallet: Wallet address
        pool_url: Pool stratum URL
        miner_path: Optional custom path to miner binary
    
    Returns:
        Popen object or None if failed
    """
    try:
        if miner_name == "bzminer":
            cmd = [
                miner_path or "bzminer",
                "-a", "warthog",
                "-w", wallet,
                "-p", pool_url,
            ]
        elif miner_name == "janusminer":
            cmd = [
                miner_path or "janusminer-ubuntu22",
                "-a", wallet,
                "-h", "127.0.0.1",
                "-p", "3000",
            ]
        else:
            return None
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        return proc
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


# ---------------------------------------------------------------------------
# CLI Integration
# ---------------------------------------------------------------------------

@dataclass
class MiningStatus:
    """Current mining status with bonus multipliers."""
    detected_miners: List[MinerProcess] = field(default_factory=list)
    node_verified: bool = False
    pool_verified: bool = False
    subprocess_launched: bool = False
    
    @property
    def bonus_multiplier(self) -> float:
        """Calculate total bonus multiplier."""
        multiplier = 1.0
        
        if self.subprocess_launched:
            multiplier *= 1.5  # Managed subprocess
        elif self.detected_miners:
            multiplier *= 1.15  # External miner detected
        
        if self.pool_verified:
            multiplier *= 1.3
        
        if self.node_verified:
            multiplier *= 1.5
        
        return multiplier


def check_mining_status(pow_name: str = "warthog") -> MiningStatus:
    """Check current dual-mining status.
    
    Args:
        pow_name: PoW cryptocurrency name
    
    Returns:
        MiningStatus with detected miners and verification status
    """
    status = MiningStatus()
    
    # Detect running miners
    status.detected_miners = detect_running_miners(pow_name)
    
    # Verify node RPC
    if pow_name == "warthog":
        status.node_verified = verify_warthog_node()
    
    return status


def mine_with_pow(
    pow_name: str = "warthog",
    wallet: Optional[str] = None,
    pool_name: Optional[str] = None,
    miner_path: Optional[str] = None,
    dry_run: bool = False,
    detect_only: bool = False,
) -> MiningStatus:
    """Start dual-mining with specified PoW.
    
    Args:
        pow_name: PoW cryptocurrency (e.g., 'warthog')
        wallet: Wallet address for mining rewards
        pool_name: Pool to mine on
        miner_path: Custom path to miner binary
        dry_run: Preview without launching
        detect_only: Only detect, don't launch
    
    Returns:
        MiningStatus with results
    """
    status = check_mining_status(pow_name)
    
    if detect_only or dry_run:
        return status
    
    if not wallet:
        print("Error: wallet address required to launch miner")
        return status
    
    pool = WARTHOG_POOLS.get(pool_name or "woolypooly")
    if not pool:
        print(f"Error: unknown pool '{pool_name}'")
        return status
    
    # Launch miner subprocess
    proc = launch_miner_subprocess(
        miner_name="bzminer",
        wallet=wallet,
        pool_url=pool.stratum_url,
        miner_path=miner_path,
    )
    
    if proc:
        status.subprocess_launched = True
        print(f"Launched {pool.name} dual-mining (PID: {proc.pid})")
    else:
        print("Failed to launch miner subprocess")
    
    return status
