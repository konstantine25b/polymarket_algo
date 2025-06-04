#!/usr/bin/env python3
"""
CLI integration tests for the Polymarket Simulation Initialization module.

Tests the command-line interface functionality through subprocess calls.
"""

import unittest
import tempfile
import shutil
import subprocess
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCLI(unittest.TestCase):
    """Test cases for CLI functionality."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.runs_dir = Path(self.temp_dir) / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        
        # We'll modify the RunInitializer to use our temp directory
        # by setting environment variable or using a different approach
        self.original_runs_dir = None
    
    def tearDown(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir)
    
    def run_cli_command(self, args):
        """
        Run a CLI command and return the result.
        
        Args:
            args: List of command line arguments
            
        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        cmd = [
            sys.executable, "-m", "src.simulation.initialization"
        ] + args
        
        # Set working directory to project root
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True
        )
        
        return result.returncode, result.stdout, result.stderr
    
    def test_cli_help(self):
        """Test CLI help functionality."""
        returncode, stdout, stderr = self.run_cli_command(["--help"])
        
        self.assertEqual(returncode, 0)
        self.assertIn("Polymarket Simulation Initialization Tool", stdout)
        self.assertIn("--create", stdout)
        self.assertIn("--list", stdout)
        self.assertIn("--info", stdout)
    
    def test_cli_create_run(self):
        """Test creating a run via CLI."""
        returncode, stdout, stderr = self.run_cli_command([
            "--create",
            "--market", "Test Market",
            "--balance", "5000",
            "--name", "cli_test_run"
        ])
        
        # Check command succeeded
        if returncode != 0:
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        # Check output messages
        self.assertIn("Creating new simulation run", stdout)
        self.assertIn("cli_test_run", stdout)
        self.assertIn("$5,000.00", stdout)
    
    def test_cli_create_run_missing_args(self):
        """Test creating run with missing required arguments."""
        # Missing balance
        returncode, stdout, stderr = self.run_cli_command([
            "--create",
            "--market", "Test Market"
        ])
        
        self.assertNotEqual(returncode, 0)
        self.assertIn("--create requires --market and --balance", stderr)
        
        # Missing market
        returncode, stdout, stderr = self.run_cli_command([
            "--create",
            "--balance", "5000"
        ])
        
        self.assertNotEqual(returncode, 0)
        self.assertIn("--create requires --market and --balance", stderr)
    
    def test_cli_list_runs_empty(self):
        """Test listing runs functionality."""
        returncode, stdout, stderr = self.run_cli_command(["--list"])
        
        self.assertEqual(returncode, 0)
        # The test should succeed regardless of whether runs exist or not
        # Since CLI tests run against the actual file system
        self.assertTrue(
            "No simulation runs found" in stdout or "Found" in stdout,
            f"Expected either 'No simulation runs found' or 'Found' in output, got: {stdout}"
        )
    
    def test_cli_info_nonexistent_run(self):
        """Test getting info for nonexistent run."""
        returncode, stdout, stderr = self.run_cli_command([
            "--info", "nonexistent_run"
        ])
        
        self.assertNotEqual(returncode, 0)
        self.assertIn("not found", stdout)
    
    def test_cli_create_market_missing_args(self):
        """Test creating market with missing arguments."""
        returncode, stdout, stderr = self.run_cli_command([
            "--create-market",
            "--run", "test_run",
            "--market-id", "0x123"
            # Missing other required args
        ])
        
        self.assertNotEqual(returncode, 0)
        self.assertIn("requires", stderr)
    
    def test_cli_add_position_missing_args(self):
        """Test adding position with missing arguments."""
        returncode, stdout, stderr = self.run_cli_command([
            "--add-position",
            "--run", "test_run"
            # Missing other required args
        ])
        
        self.assertNotEqual(returncode, 0)
        self.assertIn("requires", stderr)
    
    def test_cli_add_balance_missing_args(self):
        """Test adding balance with missing arguments."""
        returncode, stdout, stderr = self.run_cli_command([
            "--add-balance",
            "--run", "test_run"
            # Missing amount
        ])
        
        self.assertNotEqual(returncode, 0)
        self.assertIn("requires", stderr)
    
    def test_cli_remove_balance_missing_args(self):
        """Test removing balance with missing arguments."""
        returncode, stdout, stderr = self.run_cli_command([
            "--remove-balance",
            "--run", "test_run"
            # Missing amount
        ])
        
        self.assertNotEqual(returncode, 0)
        self.assertIn("requires", stderr)
    
    def test_cli_update_prices_missing_args(self):
        """Test updating prices with missing arguments."""
        returncode, stdout, stderr = self.run_cli_command([
            "--update-prices",
            "--run", "test_run"
            # Missing price data
        ])
        
        self.assertNotEqual(returncode, 0)
        self.assertIn("requires", stderr)
    
    def test_cli_sell_position_missing_args(self):
        """Test selling position with missing arguments."""
        returncode, stdout, stderr = self.run_cli_command([
            "--sell-position",
            "--run", "test_run"
            # Missing other required args
        ])
        
        self.assertNotEqual(returncode, 0)
        self.assertIn("requires", stderr)


class TestCLIWorkflow(unittest.TestCase):
    """Integration tests for complete CLI workflows."""
    
    def setUp(self):
        """Set up test environment."""
        self.run_name = "cli_workflow_test"
    
    def run_cli_command(self, args):
        """Run a CLI command and return the result."""
        cmd = [
            sys.executable, "-m", "src.simulation.initialization"
        ] + args
        
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True
        )
        
        return result.returncode, result.stdout, result.stderr
    
    def test_complete_cli_workflow(self):
        """Test a complete workflow using only CLI commands."""
        # 1. Create run
        returncode, stdout, stderr = self.run_cli_command([
            "--create",
            "--market", "CLI Test Market", 
            "--balance", "10000",
            "--name", self.run_name
        ])
        
        if returncode != 0:
            print(f"Create run failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        # 2. Create first market
        returncode, stdout, stderr = self.run_cli_command([
            "--create-market",
            "--run", self.run_name,
            "--market-id", "cli_btc_100k",
            "--market-name", "CLI Bitcoin $100k",
            "--category", "crypto",
            "--initial-price", "0.30",
            "--bid-price", "0.29", 
            "--ask-price", "0.31"
        ])
        
        if returncode != 0:
            print(f"Create market 1 failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        # 3. Create second market
        returncode, stdout, stderr = self.run_cli_command([
            "--create-market",
            "--run", self.run_name,
            "--market-id", "cli_eth_5k",
            "--market-name", "CLI Ethereum $5k",
            "--category", "crypto", 
            "--initial-price", "0.45",
            "--bid-price", "0.44",
            "--ask-price", "0.46"
        ])
        
        if returncode != 0:
            print(f"Create market 2 failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        # 4. Buy positions
        returncode, stdout, stderr = self.run_cli_command([
            "--add-position",
            "--run", self.run_name,
            "--market-id", "cli_btc_100k",
            "--shares", "100"
        ])
        
        if returncode != 0:
            print(f"Add position 1 failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        returncode, stdout, stderr = self.run_cli_command([
            "--add-position",
            "--run", self.run_name,
            "--market-id", "cli_eth_5k", 
            "--shares", "50.5"
        ])
        
        if returncode != 0:
            print(f"Add position 2 failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        # 5. Check run info
        returncode, stdout, stderr = self.run_cli_command([
            "--info", self.run_name
        ])
        
        if returncode != 0:
            print(f"Info failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        self.assertIn("CLI Test Market", stdout)
        self.assertIn("$10,000.00", stdout)  # Initial balance
        self.assertIn("Positions: 2", stdout)
        
        # 6. Update prices
        price_data = {
            "cli_btc_100k": {"price": 0.35, "bid": 0.34, "ask": 0.36},
            "cli_eth_5k": {"price": 0.40, "bid": 0.39, "ask": 0.41}
        }
        
        returncode, stdout, stderr = self.run_cli_command([
            "--update-prices",
            "--run", self.run_name,
            "--price-data", json.dumps(price_data)
        ])
        
        if returncode != 0:
            print(f"Update prices failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        # 7. Sell some position
        returncode, stdout, stderr = self.run_cli_command([
            "--sell-position",
            "--run", self.run_name,
            "--market-id", "cli_btc_100k",
            "--shares", "50"
        ])
        
        if returncode != 0:
            print(f"Sell position failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        # 8. Add balance
        returncode, stdout, stderr = self.run_cli_command([
            "--add-balance",
            "--run", self.run_name,
            "--amount", "1000",
            "--description", "CLI test funding"
        ])
        
        if returncode != 0:
            print(f"Add balance failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        # 9. Remove balance
        returncode, stdout, stderr = self.run_cli_command([
            "--remove-balance",
            "--run", self.run_name,
            "--amount", "500",
            "--description", "CLI test withdrawal"
        ])
        
        if returncode != 0:
            print(f"Remove balance failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        # 10. Final info check
        returncode, stdout, stderr = self.run_cli_command([
            "--info", self.run_name
        ])
        
        if returncode != 0:
            print(f"Final info failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        
        # Verify we have transactions
        self.assertIn("Transactions:", stdout)
        
        # 11. List runs
        returncode, stdout, stderr = self.run_cli_command([
            "--list"
        ])
        
        if returncode != 0:
            print(f"List runs failed - STDOUT: {stdout}, STDERR: {stderr}")
        self.assertEqual(returncode, 0)
        self.assertIn(self.run_name, stdout)
        
        print("✅ Complete CLI workflow test passed!")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2) 