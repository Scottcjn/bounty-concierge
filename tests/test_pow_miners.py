"""Test suite for PoW dual-mining integration.

Tests for process detection, node RPC queries, pool verification,
and subprocess management for dual-mining with RustChain PoA.
"""

import pytest
import subprocess
import requests
from unittest.mock import Mock, patch, MagicMock

from concierge.pow_miners import (
    MinerProcess,
    PoolConfig,
    MiningStatus,
    detect_running_miners,
    query_warthog_node,
    verify_warthog_node,
    get_warthog_chain_info,
    verify_pool_account,
    launch_miner_subprocess,
    check_mining_status,
    mine_with_pow,
    WARTHOG_POOLS,
)


class TestMinerProcess:
    """Test MinerProcess dataclass."""

    def test_create_miner_process(self):
        """Test creating a MinerProcess instance."""
        miner = MinerProcess(
            name="bzminer",
            pid=12345,
            cmdline="bzminer -a warthog -w wallet123",
            detected_via="process"
        )
        assert miner.name == "bzminer"
        assert miner.pid == 12345
        assert "warthog" in miner.cmdline
        assert miner.detected_via == "process"


class TestPoolConfig:
    """Test PoolConfig dataclass."""

    def test_create_pool_config(self):
        """Test creating a PoolConfig instance."""
        pool = PoolConfig(
            name="WoolyPooly",
            stratum_url="stratum+tcp://pool.woolypooly.com:3140",
            fee_pct=0.90
        )
        assert pool.name == "WoolyPooly"
        assert "woolypooly.com" in pool.stratum_url
        assert pool.fee_pct == 0.90

    def test_pool_with_api_url(self):
        """Test pool config with API URL."""
        pool = PoolConfig(
            name="TestPool",
            stratum_url="pool.test.com",
            fee_pct=1.0,
            api_url="https://api.test.com"
        )
        assert pool.api_url == "https://api.test.com"


class TestWarthogPools:
    """Test Warthog pool configurations."""

    def test_woolypooly_config(self):
        """Test WoolyPooly pool configuration."""
        pool = WARTHOG_POOLS["woolypooly"]
        assert pool.name == "WoolyPooly"
        assert pool.fee_pct == 0.90
        assert "woolypooly.com" in pool.stratum_url

    def test_cedric_crispin_config(self):
        """Test Cedric-Crispin pool configuration."""
        pool = WARTHOG_POOLS["cedric-crispin"]
        assert pool.name == "Cedric-Crispin"
        assert pool.fee_pct == 0.10

    def test_herominers_config(self):
        """Test HeroMiners pool configuration."""
        pool = WARTHOG_POOLS["herominers"]
        assert pool.name == "HeroMiners"
        assert pool.fee_pct == 0.90


class TestDetectRunningMiners:
    """Test miner process detection."""

    @patch('concierge.pow_miners._detect_process_by_cmdline')
    @patch('concierge.pow_miners._detect_process_by_cmdname')
    @patch('concierge.pow_miners._detect_systemd_services')
    @patch('concierge.pow_miners._detect_screen_sessions')
    def test_detect_warthog_miners(self, mock_screen, mock_systemd, mock_cmdname, mock_cmdline):
        """Test detection of Warthog miners."""
        # Setup mocks
        mock_cmdline.return_value = [
            MinerProcess("bzminer", 1234, "bzminer -a warthog", "process")
        ]
        mock_cmdname.return_value = []
        mock_systemd.return_value = []
        mock_screen.return_value = []
        
        miners = detect_running_miners("warthog")
        
        assert len(miners) >= 1
        assert miners[0].name == "bzminer"
        assert miners[0].pid == 1234

    def test_detect_no_miners(self):
        """Test when no miners are running."""
        with patch('concierge.pow_miners._detect_process_by_cmdline', return_value=[]), \
             patch('concierge.pow_miners._detect_process_by_cmdname', return_value=[]), \
             patch('concierge.pow_miners._detect_systemd_services', return_value=[]), \
             patch('concierge.pow_miners._detect_screen_sessions', return_value=[]):
            
            miners = detect_running_miners("warthog")
            assert len(miners) == 0


class TestDetectProcessByCmdline:
    """Test process detection by command line."""

    @patch('subprocess.run')
    def test_detect_bzminer(self, mock_run):
        """Test detecting bzminer process."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pgrep", "-af", "bzminer"],
            returncode=0,
            stdout="12345 bzminer -a warthog -w wallet\n67890 bzminer -a ergo",
            stderr=""
        )
        
        from concierge.pow_miners import _detect_process_by_cmdline
        miners = _detect_process_by_cmdline(r"bzminer", "bzminer", "process")
        
        assert len(miners) == 2
        assert miners[0].pid == 12345
        assert miners[1].pid == 67890

    @patch('subprocess.run')
    def test_no_matching_process(self, mock_run):
        """Test when no process matches."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pgrep", "-af", "nomatch"],
            returncode=1,
            stdout="",
            stderr=""
        )
        
        from concierge.pow_miners import _detect_process_by_cmdline
        miners = _detect_process_by_cmdline(r"nomatch", "test", "process")
        
        assert len(miners) == 0


class TestQueryWarthogNode:
    """Test Warthog node RPC queries."""

    @patch('requests.get')
    def test_query_chain_head(self, mock_get):
        """Test querying /chain/head endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pinHash": "abc123",
            "pinHeight": 1000,
            "worksum": "xyz789"
        }
        mock_get.return_value = mock_response
        
        result = query_warthog_node("/chain/head")
        
        assert result is not None
        assert result["pinHeight"] == 1000
        assert result["pinHash"] == "abc123"

    @patch('requests.get')
    def test_query_node_error(self, mock_get):
        """Test handling node query errors."""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        result = query_warthog_node("/chain/head")
        
        assert result is None

    @patch('requests.get')
    def test_query_invalid_json(self, mock_get):
        """Test handling invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        result = query_warthog_node("/chain/head")
        
        assert result is None


class TestVerifyWarthogNode:
    """Test Warthog node verification."""

    @patch('concierge.pow_miners.query_warthog_node')
    def test_node_verified(self, mock_query):
        """Test successful node verification."""
        mock_query.return_value = {"pinHash": "abc", "pinHeight": 100}
        
        assert verify_warthog_node() is True

    @patch('concierge.pow_miners.query_warthog_node')
    def test_node_not_verified(self, mock_query):
        """Test failed node verification."""
        mock_query.return_value = None
        
        assert verify_warthog_node() is False

    @patch('concierge.pow_miners.query_warthog_node')
    def test_node_missing_fields(self, mock_query):
        """Test node response without expected fields."""
        mock_query.return_value = {"other": "data"}
        
        assert verify_warthog_node() is False


class TestGetWarthogChainInfo:
    """Test chain info retrieval."""

    @patch('concierge.pow_miners.query_warthog_node')
    def test_get_chain_info(self, mock_query):
        """Test getting chain information."""
        mock_query.return_value = {
            "pinHeight": 1234,
            "pinHash": "def456",
            "worksum": "work123"
        }
        
        result = get_warthog_chain_info()
        
        assert result is not None
        assert result["height"] == 1234
        assert result["hash"] == "def456"
        assert result["worksum"] == "work123"


class TestVerifyPoolAccount:
    """Test pool account verification."""

    @patch('requests.get')
    def test_verify_woolypooly(self, mock_get):
        """Test verifying WoolyPooly account."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hashrate": 1000,
            "balance": 50.5,
            "shares": 100
        }
        mock_get.return_value = mock_response
        
        result = verify_pool_account("woolypooly", "wallet123")
        
        assert result is True

    @patch('requests.get')
    def test_verify_pool_no_api(self, mock_get):
        """Test pool without API URL."""
        # cedric-crispin has no api_url
        result = verify_pool_account("cedric-crispin", "wallet123")
        
        assert result is False


class TestLaunchMinerSubprocess:
    """Test miner subprocess launching."""

    @patch('subprocess.Popen')
    def test_launch_bzminer(self, mock_popen):
        """Test launching bzminer."""
        mock_popen.return_value = Mock(pid=99999)
        
        proc = launch_miner_subprocess(
            miner_name="bzminer",
            wallet="wallet123",
            pool_url="stratum+tcp://pool.com:3140"
        )
        
        assert proc is not None
        assert proc.pid == 99999
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    def test_launch_janusminer(self, mock_popen):
        """Test launching janusminer."""
        mock_popen.return_value = Mock(pid=88888)
        
        proc = launch_miner_subprocess(
            miner_name="janusminer",
            wallet="wallet456",
            pool_url="pool.com"
        )
        
        assert proc is not None
        assert proc.pid == 88888

    @patch('subprocess.Popen')
    def test_launch_unknown_miner(self, mock_popen):
        """Test launching unknown miner."""
        proc = launch_miner_subprocess(
            miner_name="unknown",
            wallet="wallet",
            pool_url="pool.com"
        )
        
        assert proc is None


class TestMiningStatus:
    """Test MiningStatus dataclass and bonus calculation."""

    def test_default_status(self):
        """Test default mining status."""
        status = MiningStatus()
        assert len(status.detected_miners) == 0
        assert status.node_verified is False
        assert status.pool_verified is False
        assert status.subprocess_launched is False
        assert status.bonus_multiplier == 1.0

    def test_bonus_subprocess_launched(self):
        """Test bonus multiplier with subprocess."""
        status = MiningStatus(subprocess_launched=True)
        assert status.bonus_multiplier == 1.5

    def test_bonus_external_miner(self):
        """Test bonus multiplier with external miner."""
        status = MiningStatus(
            detected_miners=[MinerProcess("bzminer", 123, "cmd", "process")]
        )
        assert status.bonus_multiplier == 1.15

    def test_bonus_node_verified(self):
        """Test bonus multiplier with node verification."""
        status = MiningStatus(node_verified=True)
        assert status.bonus_multiplier == 1.5

    def test_bonus_pool_verified(self):
        """Test bonus multiplier with pool verification."""
        status = MiningStatus(pool_verified=True)
        assert status.bonus_multiplier == 1.3

    def test_bonus_combined(self):
        """Test combined bonus multipliers."""
        status = MiningStatus(
            subprocess_launched=True,
            node_verified=True,
            pool_verified=True
        )
        # 1.5 (subprocess) * 1.5 (node) * 1.3 (pool) = 2.925
        assert abs(status.bonus_multiplier - 2.925) < 0.001


class TestCheckMiningStatus:
    """Test mining status checking."""

    @patch('concierge.pow_miners.detect_running_miners')
    @patch('concierge.pow_miners.verify_warthog_node')
    def test_check_status(self, mock_verify, mock_detect):
        """Test checking mining status."""
        mock_detect.return_value = [MinerProcess("bzminer", 123, "cmd", "process")]
        mock_verify.return_value = True
        
        status = check_mining_status("warthog")
        
        assert len(status.detected_miners) == 1
        assert status.node_verified is True


class TestMineWithPow:
    """Test dual-mining initiation."""

    @patch('concierge.pow_miners.check_mining_status')
    def test_dry_run(self, mock_check):
        """Test dry run mode."""
        mock_check.return_value = MiningStatus()
        
        status = mine_with_pow(dry_run=True)
        
        assert status.subprocess_launched is False

    @patch('concierge.pow_miners.check_mining_status')
    @patch('concierge.pow_miners.launch_miner_subprocess')
    def test_launch_miner(self, mock_launch, mock_check):
        """Test launching miner."""
        mock_check.return_value = MiningStatus()
        mock_launch.return_value = Mock(pid=77777)
        
        status = mine_with_pow(
            wallet="wallet123",
            pool_name="woolypooly"
        )
        
        assert status.subprocess_launched is True
        mock_launch.assert_called_once()

    @patch('concierge.pow_miners.check_mining_status')
    def test_no_wallet(self, mock_check):
        """Test error when no wallet provided."""
        mock_check.return_value = MiningStatus()
        
        status = mine_with_pow()
        
        assert status.subprocess_launched is False


class TestMiningStatusBonusCalculations:
    """Test various bonus multiplier scenarios."""

    def test_all_bonuses(self):
        """Test maximum bonus scenario."""
        status = MiningStatus(
            detected_miners=[MinerProcess("bzminer", 1, "cmd", "process")],
            node_verified=True,
            pool_verified=True,
            subprocess_launched=True
        )
        # subprocess (1.5) * pool (1.3) * node (1.5) = 2.925
        # Note: detected_miners bonus doesn't stack with subprocess
        assert status.bonus_multiplier > 2.9

    def test_no_bonuses(self):
        """Test minimum bonus (no bonuses)."""
        status = MiningStatus()
        assert status.bonus_multiplier == 1.0

    def test_partial_bonuses(self):
        """Test partial bonus scenario."""
        status = MiningStatus(
            node_verified=True,
            pool_verified=False,
            subprocess_launched=False
        )
        assert status.bonus_multiplier == 1.5
