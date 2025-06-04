#!/usr/bin/env python3
"""
Comprehensive unit tests for RunInitializer class.

Tests all functionality including:
- Run creation
- Market creation and management
- Position management (buy/sell)
- Balance management
- Price updates
- Error handling
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.simulation.initialization.run_initializer import RunInitializer


class TestRunInitializer(unittest.TestCase):
    """Test cases for RunInitializer class."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.initializer = RunInitializer(base_runs_dir=self.temp_dir)
        self.test_run_name = "test_run"
        self.test_market_name = "Test Market"
        self.initial_balance = 10000.0
    
    def tearDown(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_new_run_default_name(self):
        """Test creating a new run with default timestamp name."""
        result = self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('run_id', result)
        self.assertIn('run_name', result)
        self.assertIn('run_directory', result)
        self.assertIn('json_file_path', result)
        self.assertIn('initial_data', result)
        
        # Check file was created
        json_path = Path(result['json_file_path'])
        self.assertTrue(json_path.exists())
        
        # Check JSON structure
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data['whole_market_name'], self.test_market_name)
        self.assertEqual(data['initial_balance'], self.initial_balance)
        self.assertEqual(data['current_balance'], self.initial_balance)
        self.assertEqual(data['total_balance'], self.initial_balance)
        self.assertEqual(data['balance_of_shares'], 0.0)
        self.assertEqual(data['balance_invested'], 0.0)
        self.assertEqual(len(data['shares']), 0)
        self.assertEqual(len(data['positions']), 0)
        self.assertEqual(len(data['markets']), 0)
        self.assertEqual(len(data['transactions']), 0)
        self.assertEqual(len(data['total_balances']), 1)
    
    def test_create_new_run_custom_name(self):
        """Test creating a new run with custom name."""
        result = self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        self.assertEqual(result['run_name'], self.test_run_name)
        
        # Check directory was created with correct name
        run_dir = Path(self.temp_dir) / self.test_run_name
        self.assertTrue(run_dir.exists())
    
    def test_create_market_success(self):
        """Test successful market creation."""
        # First create a run
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        # Create a market
        success = self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        self.assertTrue(success)
        
        # Check market was added to JSON
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(len(run_data['markets']), 1)
        
        market = run_data['markets'][0]
        self.assertEqual(market['market_id'], "0x123")
        self.assertEqual(market['market_name'], "Bitcoin $100k")
        self.assertEqual(market['description'], "Bitcoin reaches $100k")
        self.assertEqual(market['category'], "crypto")
        self.assertEqual(market['initial_price'], 0.30)
        self.assertEqual(market['current_price'], 0.30)
        self.assertEqual(market['current_bid'], 0.29)
        self.assertEqual(market['current_ask'], 0.31)
        self.assertEqual(len(market['price_history']), 1)
    
    def test_create_market_duplicate_id(self):
        """Test creating market with duplicate ID."""
        # First create a run and market
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        # Try to create another market with same ID
        success = self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Different Market",
            description="Different description",
            category="prediction",
            initial_price=0.50,
            bid_price=0.49,
            ask_price=0.51
        )
        
        self.assertFalse(success)
    
    def test_create_market_nonexistent_run(self):
        """Test creating market for nonexistent run."""
        success = self.initializer.create_market(
            run_name="nonexistent_run",
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        self.assertFalse(success)
    
    def test_add_position_success(self):
        """Test successful position addition."""
        # Create run and market
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        # Add position
        success = self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=100.0
        )
        
        self.assertTrue(success)
        
        # Check position was added
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(len(run_data['positions']), 1)
        self.assertEqual(len(run_data['shares']), 1)
        self.assertEqual(len(run_data['transactions']), 1)
        
        position = run_data['positions'][0]
        self.assertEqual(position['market_id'], "0x123")
        self.assertEqual(position['num_shares'], 100.0)
        self.assertEqual(position['initial_price_per_share'], 0.31)  # Ask price
        self.assertEqual(position['initial_total_price'], 31.0)
        self.assertEqual(position['current_price_per_share'], 0.30)  # Market price
        self.assertEqual(position['total_invested'], 31.0)
        
        # Check balances
        self.assertEqual(run_data['current_balance'], self.initial_balance - 31.0)
        self.assertEqual(run_data['balance_invested'], 31.0)
        self.assertEqual(run_data['balance_of_shares'], 30.0)  # Market value
        self.assertEqual(run_data['total_balance'], self.initial_balance - 1.0)  # Loss due to spread
    
    def test_add_position_merge_existing(self):
        """Test adding shares to existing position."""
        # Setup
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        # Add first position
        self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=100.0
        )
        
        # Add more shares to same position
        success = self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=50.0
        )
        
        self.assertTrue(success)
        
        # Check merged position
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(len(run_data['positions']), 1)  # Still only one position
        
        position = run_data['positions'][0]
        self.assertEqual(position['num_shares'], 150.0)
        self.assertEqual(position['total_invested'], 46.5)  # 100*0.31 + 50*0.31
        
        share = run_data['shares'][0]
        self.assertEqual(share['num_shares'], 150.0)
    
    def test_add_position_insufficient_funds(self):
        """Test adding position with insufficient funds."""
        # Create run with small balance
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=10.0,  # Small balance
            run_name=self.test_run_name
        )
        
        self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        # Try to buy more than we can afford
        success = self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=100.0  # Would cost 31.0
        )
        
        self.assertFalse(success)
        
        # Check no position was added
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(len(run_data['positions']), 0)
        self.assertEqual(run_data['current_balance'], 10.0)  # Unchanged
    
    def test_add_position_allow_negative(self):
        """Test adding position with negative balance allowed."""
        # Create run with small balance
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=10.0,
            run_name=self.test_run_name
        )
        
        self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        # Buy with negative balance allowed
        success = self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=100.0,
            allow_negative_balance=True
        )
        
        self.assertTrue(success)
        
        # Check negative balance
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(run_data['current_balance'], -21.0)  # 10 - 31
        self.assertEqual(len(run_data['positions']), 1)
    
    def test_add_position_nonexistent_market(self):
        """Test adding position for nonexistent market."""
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        success = self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x999",  # Doesn't exist
            num_shares=100.0
        )
        
        self.assertFalse(success)
    
    def test_sell_position_success(self):
        """Test successful position sale."""
        # Setup with position
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=100.0
        )
        
        # Sell partial position
        success = self.initializer.sell_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=50.0
        )
        
        self.assertTrue(success)
        
        # Check remaining position
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(len(run_data['positions']), 1)
        
        position = run_data['positions'][0]
        self.assertEqual(position['num_shares'], 50.0)
        self.assertAlmostEqual(position['total_invested'], 15.5, places=7)  # Half of original investment
        
        # Check transactions
        transactions = run_data['transactions']
        self.assertEqual(len(transactions), 2)  # BUY + SELL
        
        sell_tx = transactions[1]
        self.assertEqual(sell_tx['type'], 'SELL')
        self.assertEqual(sell_tx['num_shares'], 50.0)
        self.assertEqual(sell_tx['price_per_share'], 0.29)  # Bid price
        self.assertAlmostEqual(sell_tx['total_amount'], 14.5, places=7)
        self.assertAlmostEqual(sell_tx['cost_basis'], 15.5, places=7)
        self.assertAlmostEqual(sell_tx['profit_loss'], -1.0, places=7)  # Loss due to spread
    
    def test_sell_entire_position(self):
        """Test selling entire position."""
        # Setup with position
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=100.0
        )
        
        # Sell entire position
        success = self.initializer.sell_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=100.0
        )
        
        self.assertTrue(success)
        
        # Check position was removed
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(len(run_data['positions']), 0)
        self.assertEqual(len(run_data['shares']), 0)
        
        # Check final balance
        # Bought at 0.31, sold at 0.29, loss of 0.02 per share
        expected_balance = self.initial_balance - (100 * 0.02)
        self.assertEqual(run_data['current_balance'], expected_balance)
        self.assertEqual(run_data['balance_of_shares'], 0.0)
        self.assertEqual(run_data['balance_invested'], 0.0)
    
    def test_sell_position_insufficient_shares(self):
        """Test selling more shares than available."""
        # Setup with small position
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=50.0
        )
        
        # Try to sell more than we have
        success = self.initializer.sell_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=100.0
        )
        
        self.assertFalse(success)
        
        # Check position unchanged
        run_data = self.initializer.get_run_info(self.test_run_name)
        position = run_data['positions'][0]
        self.assertEqual(position['num_shares'], 50.0)
    
    def test_update_market_prices(self):
        """Test updating market prices."""
        # Setup with position
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=100.0
        )
        
        # Update prices
        price_updates = {
            "0x123": {
                "price": 0.35,
                "bid": 0.34,
                "ask": 0.36
            }
        }
        
        success = self.initializer.update_market_prices(
            run_name=self.test_run_name,
            price_updates=price_updates
        )
        
        self.assertTrue(success)
        
        # Check market was updated
        run_data = self.initializer.get_run_info(self.test_run_name)
        market = run_data['markets'][0]
        self.assertEqual(market['current_price'], 0.35)
        self.assertEqual(market['current_bid'], 0.34)
        self.assertEqual(market['current_ask'], 0.36)
        self.assertEqual(len(market['price_history']), 2)
        
        # Check position was updated
        position = run_data['positions'][0]
        self.assertEqual(position['current_price_per_share'], 0.35)
        self.assertEqual(position['current_total_price'], 35.0)
        self.assertEqual(position['current_value_if_sold'], 34.0)
        # Win/loss % = (35 - 31) / 31 * 100 = 12.9%
        self.assertAlmostEqual(position['win_loss_percentage'], 12.903225806451612, places=5)
        
        # Check balances updated
        self.assertEqual(run_data['balance_of_shares'], 35.0)  # Current market value
        self.assertEqual(run_data['balance_invested'], 31.0)   # Original investment unchanged
    
    def test_add_balance(self):
        """Test adding balance to run."""
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        success = self.initializer.add_balance(
            run_name=self.test_run_name,
            amount=1000.0,
            description="Test funding"
        )
        
        self.assertTrue(success)
        
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(run_data['current_balance'], self.initial_balance + 1000.0)
        self.assertEqual(run_data['total_balance'], self.initial_balance + 1000.0)
        
        # Check transaction was recorded
        transactions = run_data['transactions']
        self.assertEqual(len(transactions), 1)
        
        tx = transactions[0]
        self.assertEqual(tx['type'], 'BALANCE_ADD')
        self.assertEqual(tx['amount'], 1000.0)
        self.assertEqual(tx['description'], "Test funding")
    
    def test_add_balance_negative_amount(self):
        """Test adding negative balance amount."""
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        success = self.initializer.add_balance(
            run_name=self.test_run_name,
            amount=-100.0
        )
        
        self.assertFalse(success)
        
        # Check balance unchanged
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(run_data['current_balance'], self.initial_balance)
    
    def test_remove_balance(self):
        """Test removing balance from run."""
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        success = self.initializer.remove_balance(
            run_name=self.test_run_name,
            amount=500.0,
            description="Test withdrawal"
        )
        
        self.assertTrue(success)
        
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(run_data['current_balance'], self.initial_balance - 500.0)
        self.assertEqual(run_data['total_balance'], self.initial_balance - 500.0)
        
        # Check transaction was recorded
        transactions = run_data['transactions']
        self.assertEqual(len(transactions), 1)
        
        tx = transactions[0]
        self.assertEqual(tx['type'], 'BALANCE_REMOVE')
        self.assertEqual(tx['amount'], 500.0)
        self.assertEqual(tx['description'], "Test withdrawal")
    
    def test_remove_balance_insufficient_funds(self):
        """Test removing more balance than available."""
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=100.0,
            run_name=self.test_run_name
        )
        
        success = self.initializer.remove_balance(
            run_name=self.test_run_name,
            amount=200.0
        )
        
        self.assertFalse(success)
        
        # Check balance unchanged
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(run_data['current_balance'], 100.0)
    
    def test_remove_balance_allow_negative(self):
        """Test removing balance with negative allowed."""
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=100.0,
            run_name=self.test_run_name
        )
        
        success = self.initializer.remove_balance(
            run_name=self.test_run_name,
            amount=200.0,
            allow_negative=True
        )
        
        self.assertTrue(success)
        
        run_data = self.initializer.get_run_info(self.test_run_name)
        self.assertEqual(run_data['current_balance'], -100.0)
    
    def test_list_runs(self):
        """Test listing simulation runs."""
        # Initially no runs
        runs = self.initializer.list_runs()
        self.assertEqual(len(runs), 0)
        
        # Create some runs
        self.initializer.create_new_run("Market 1", 1000.0, "run1")
        self.initializer.create_new_run("Market 2", 2000.0, "run2")
        
        runs = self.initializer.list_runs()
        self.assertEqual(len(runs), 2)
        self.assertIn("run1", runs)
        self.assertIn("run2", runs)
    
    def test_get_run_info_nonexistent(self):
        """Test getting info for nonexistent run."""
        info = self.initializer.get_run_info("nonexistent")
        self.assertIsNone(info)
    
    def test_fractional_shares(self):
        """Test handling of fractional shares."""
        # Setup
        self.initializer.create_new_run(
            market_name=self.test_market_name,
            initial_balance=self.initial_balance,
            run_name=self.test_run_name
        )
        
        self.initializer.create_market(
            run_name=self.test_run_name,
            market_id="0x123",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        
        # Add fractional shares
        success = self.initializer.add_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=75.5
        )
        
        self.assertTrue(success)
        
        # Check position
        run_data = self.initializer.get_run_info(self.test_run_name)
        position = run_data['positions'][0]
        self.assertEqual(position['num_shares'], 75.5)
        self.assertAlmostEqual(position['total_invested'], 75.5 * 0.31, places=7)
        
        # Sell fractional shares
        success = self.initializer.sell_position(
            run_name=self.test_run_name,
            market_id="0x123",
            num_shares=25.3
        )
        
        self.assertTrue(success)
        
        # Check remaining
        run_data = self.initializer.get_run_info(self.test_run_name)
        position = run_data['positions'][0]
        self.assertAlmostEqual(position['num_shares'], 50.2, places=1)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for complete trading scenarios."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.initializer = RunInitializer(base_runs_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)
    
    def test_complete_trading_scenario(self):
        """Test a complete trading scenario from start to finish."""
        run_name = "integration_test"
        
        # 1. Create simulation
        result = self.initializer.create_new_run(
            market_name="Crypto Predictions",
            initial_balance=10000.0,
            run_name=run_name
        )
        self.assertIsNotNone(result)
        
        # 2. Create two markets
        success1 = self.initializer.create_market(
            run_name=run_name,
            market_id="btc_100k",
            market_name="Bitcoin $100k",
            description="Bitcoin reaches $100k by end of year",
            category="crypto",
            initial_price=0.30,
            bid_price=0.29,
            ask_price=0.31
        )
        self.assertTrue(success1)
        
        success2 = self.initializer.create_market(
            run_name=run_name,
            market_id="eth_5k",
            market_name="Ethereum $5k",
            description="Ethereum reaches $5k by end of year",
            category="crypto",
            initial_price=0.45,
            bid_price=0.44,
            ask_price=0.46
        )
        self.assertTrue(success2)
        
        # 3. Buy positions
        buy1 = self.initializer.add_position(
            run_name=run_name,
            market_id="btc_100k",
            num_shares=100.0
        )
        self.assertTrue(buy1)
        
        buy2 = self.initializer.add_position(
            run_name=run_name,
            market_id="eth_5k",
            num_shares=50.0
        )
        self.assertTrue(buy2)
        
        # Check balances after purchases
        run_data = self.initializer.get_run_info(run_name)
        expected_invested = (100 * 0.31) + (50 * 0.46)  # 31 + 23 = 54
        expected_market_value = (100 * 0.30) + (50 * 0.45)  # 30 + 22.5 = 52.5
        expected_cash = 10000 - 54  # 9946
        expected_total = expected_cash + expected_market_value  # 9946 + 52.5 = 9998.5
        
        self.assertAlmostEqual(run_data['balance_invested'], expected_invested, places=7)
        self.assertAlmostEqual(run_data['balance_of_shares'], expected_market_value, places=7)
        self.assertAlmostEqual(run_data['current_balance'], expected_cash, places=7)
        self.assertAlmostEqual(run_data['total_balance'], expected_total, places=7)
        
        # 4. Update prices (BTC up, ETH down)
        price_updates = {
            "btc_100k": {"price": 0.35, "bid": 0.34, "ask": 0.36},
            "eth_5k": {"price": 0.40, "bid": 0.39, "ask": 0.41}
        }
        
        update_success = self.initializer.update_market_prices(run_name, price_updates)
        self.assertTrue(update_success)
        
        # Check updated balances
        run_data = self.initializer.get_run_info(run_name)
        new_market_value = (100 * 0.35) + (50 * 0.40)  # 35 + 20 = 55
        new_total = expected_cash + new_market_value  # 9946 + 55 = 10001
        
        self.assertAlmostEqual(run_data['balance_of_shares'], new_market_value, places=7)
        self.assertAlmostEqual(run_data['balance_invested'], expected_invested, places=7)  # Unchanged
        self.assertAlmostEqual(run_data['total_balance'], new_total, places=7)
        
        # 5. Sell some BTC (profit)
        sell_success = self.initializer.sell_position(
            run_name=run_name,
            market_id="btc_100k",
            num_shares=50.0
        )
        self.assertTrue(sell_success)
        
        # Check after sale
        run_data = self.initializer.get_run_info(run_name)
        sale_proceeds = 50 * 0.34  # 17.0 (bid price)
        cost_basis_sold = 50 * 0.31  # 15.5
        profit = sale_proceeds - cost_basis_sold  # 1.5
        
        new_cash = expected_cash + sale_proceeds  # 9946 + 17 = 9963
        remaining_btc_value = 50 * 0.35  # 17.5
        eth_value = 50 * 0.40  # 20
        new_market_value = remaining_btc_value + eth_value  # 37.5
        new_invested = (50 * 0.31) + (50 * 0.46)  # 15.5 + 23 = 38.5
        
        self.assertAlmostEqual(run_data['current_balance'], new_cash, places=7)
        self.assertAlmostEqual(run_data['balance_of_shares'], new_market_value, places=7)
        self.assertAlmostEqual(run_data['balance_invested'], new_invested, places=7)
        
        # 6. Add more funding
        funding_success = self.initializer.add_balance(
            run_name=run_name,
            amount=2000.0,
            description="Additional investment"
        )
        self.assertTrue(funding_success)
        
        # 7. Buy more ETH
        buy3 = self.initializer.add_position(
            run_name=run_name,
            market_id="eth_5k",
            num_shares=30.0
        )
        self.assertTrue(buy3)
        
        # Final check
        run_data = self.initializer.get_run_info(run_name)
        
        # Verify we have correct number of transactions
        self.assertEqual(len(run_data['transactions']), 5)  # 2 buys + 1 sell + 1 balance_add + 1 more buy
        
        # Verify we have 2 positions
        self.assertEqual(len(run_data['positions']), 2)
        
        # Verify ETH position was merged correctly
        eth_position = None
        for pos in run_data['positions']:
            if pos['market_id'] == 'eth_5k':
                eth_position = pos
                break
        
        self.assertIsNotNone(eth_position)
        self.assertEqual(eth_position['num_shares'], 80.0)  # 50 + 30
        expected_eth_invested = (50 * 0.46) + (30 * 0.41)  # 23 + 12.3 = 35.3
        self.assertAlmostEqual(eth_position['total_invested'], expected_eth_invested, places=7)
        
        print(f"Final run data:")
        print(f"  Current Balance: ${run_data['current_balance']:,.2f}")
        print(f"  Balance of Shares: ${run_data['balance_of_shares']:,.2f}")
        print(f"  Balance Invested: ${run_data['balance_invested']:,.2f}")
        print(f"  Total Balance: ${run_data['total_balance']:,.2f}")
        print(f"  Profit/Loss: ${run_data['balance_of_shares'] - run_data['balance_invested']:,.2f}")

    def test_bear_market_scenario(self):
        """Test trading during a bear market with declining prices."""
        run_name = "bear_market_test"
        
        # Create simulation with moderate balance
        self.initializer.create_new_run(
            market_name="Bear Market Predictions",
            initial_balance=5000.0,
            run_name=run_name
        )
        
        # Create markets with initially high prices
        self.initializer.create_market(
            run_name=run_name,
            market_id="btc_crash",
            market_name="Bitcoin Crash Protection",
            description="Bitcoin won't crash below $30k",
            category="crypto",
            initial_price=0.80,  # High confidence initially
            bid_price=0.78,
            ask_price=0.82
        )
        
        self.initializer.create_market(
            run_name=run_name,
            market_id="tech_recession",
            market_name="Tech Recession",
            description="Tech stocks will decline 20%+",
            category="economics", 
            initial_price=0.25,  # Low probability initially
            bid_price=0.23,
            ask_price=0.27
        )
        
        # Initial positions - buy high confidence market
        self.initializer.add_position(
            run_name=run_name,
            market_id="btc_crash",
            num_shares=50.0  # Cost: 50 * 0.82 = $41
        )
        
        # Small contrarian bet
        self.initializer.add_position(
            run_name=run_name,
            market_id="tech_recession", 
            num_shares=100.0  # Cost: 100 * 0.27 = $27
        )
        
        # Check initial state
        run_data = self.initializer.get_run_info(run_name)
        self.assertAlmostEqual(run_data['balance_invested'], 68.0, places=7)  # 41 + 27
        self.assertAlmostEqual(run_data['current_balance'], 4932.0, places=7)  # 5000 - 68
        
        # Market turns bearish - prices crash
        bear_market_update = {
            "btc_crash": {"price": 0.15, "bid": 0.14, "ask": 0.16},  # Massive decline
            "tech_recession": {"price": 0.75, "bid": 0.73, "ask": 0.77}  # Tech recession confirmed
        }
        
        self.initializer.update_market_prices(run_name, bear_market_update)
        
        # Check portfolio damage
        run_data = self.initializer.get_run_info(run_name)
        new_market_value = (50 * 0.15) + (100 * 0.75)  # 7.5 + 75 = 82.5
        
        self.assertAlmostEqual(run_data['balance_of_shares'], 82.5, places=7)
        self.assertAlmostEqual(run_data['balance_invested'], 68.0, places=7)  # Unchanged
        
        # Portfolio P&L: 82.5 - 68 = +14.5 (contrarian bet paid off!)
        profit_loss = run_data['balance_of_shares'] - run_data['balance_invested']
        self.assertAlmostEqual(profit_loss, 14.5, places=7)
        
        # Cut losses on bad position, keep winner
        sell_loser = self.initializer.sell_position(
            run_name=run_name,
            market_id="btc_crash",
            num_shares=50.0  # Sell at bid: 50 * 0.14 = $7
        )
        self.assertTrue(sell_loser)
        
        # Verify loss cutting
        run_data = self.initializer.get_run_info(run_name)
        btc_loss = 7.0 - 41.0  # -34.0 loss
        self.assertAlmostEqual(run_data['current_balance'], 4932.0 + 7.0, places=7)  # Got $7 back
        self.assertEqual(len(run_data['positions']), 1)  # Only tech recession position remains
        
        print(f"Bear Market Results:")
        print(f"  Initial Investment: $68.00")
        print(f"  BTC Position Loss: ${btc_loss:.2f}")
        print(f"  Tech Position Value: ${75 * 100 / 100:.2f} (from $27 cost)")
        print(f"  Final Cash: ${run_data['current_balance']:,.2f}")
        print(f"  Final Portfolio: ${run_data['total_balance']:,.2f}")

    def test_momentum_trading_scenario(self):
        """Test momentum trading with multiple entries and exits."""
        run_name = "momentum_test"
        
        # Create simulation for active trading
        self.initializer.create_new_run(
            market_name="Momentum Trading",
            initial_balance=15000.0,
            run_name=run_name
        )
        
        # Create volatile market
        self.initializer.create_market(
            run_name=run_name,
            market_id="ai_breakthrough",
            market_name="AI Breakthrough This Year",
            description="Major AI breakthrough announced in 2024",
            category="technology",
            initial_price=0.40,
            bid_price=0.38,
            ask_price=0.42
        )
        
        # Phase 1: Initial position on momentum
        self.initializer.add_position(
            run_name=run_name,
            market_id="ai_breakthrough",
            num_shares=200.0  # Cost: 200 * 0.42 = $84
        )
        
        # Phase 2: Price starts moving up
        self.initializer.update_market_prices(run_name, {
            "ai_breakthrough": {"price": 0.55, "bid": 0.53, "ask": 0.57}
        })
        
        # Add to winning position (pyramid)
        self.initializer.add_position(
            run_name=run_name,
            market_id="ai_breakthrough",
            num_shares=150.0  # Cost: 150 * 0.57 = $85.50
        )
        
        # Phase 3: Strong momentum continues
        self.initializer.update_market_prices(run_name, {
            "ai_breakthrough": {"price": 0.72, "bid": 0.70, "ask": 0.74}
        })
        
        # Take partial profits
        self.initializer.sell_position(
            run_name=run_name,
            market_id="ai_breakthrough",
            num_shares=100.0  # Sell at bid: 100 * 0.70 = $70
        )
        
        # Phase 4: Market peaks and reverses
        self.initializer.update_market_prices(run_name, {
            "ai_breakthrough": {"price": 0.85, "bid": 0.83, "ask": 0.87}  # Peak
        })
        
        # Take more profits at peak
        self.initializer.sell_position(
            run_name=run_name,
            market_id="ai_breakthrough", 
            num_shares=150.0  # Sell at bid: 150 * 0.83 = $124.50
        )
        
        # Phase 5: Market reverses
        self.initializer.update_market_prices(run_name, {
            "ai_breakthrough": {"price": 0.60, "bid": 0.58, "ask": 0.62}
        })
        
        # Final position check
        run_data = self.initializer.get_run_info(run_name)
        
        # Should have 100 shares remaining (350 bought - 250 sold)
        self.assertEqual(len(run_data['positions']), 1)
        remaining_position = run_data['positions'][0]
        self.assertEqual(remaining_position['num_shares'], 100.0)
        
        # Calculate total performance
        total_invested = (200 * 0.42) + (150 * 0.57)  # 84 + 85.5 = 169.5
        total_sold_proceeds = (100 * 0.70) + (150 * 0.83)  # 70 + 124.5 = 194.5
        remaining_value = 100 * 0.60  # 60.0
        
        # Total value = cash from sales + remaining position value
        # Cash should be: 15000 - 169.5 + 194.5 = 15025
        # Total portfolio = 15025 + 60 = 15085
        
        self.assertAlmostEqual(run_data['current_balance'], 15025.0, places=7)
        self.assertAlmostEqual(run_data['balance_of_shares'], 60.0, places=7)
        self.assertAlmostEqual(run_data['total_balance'], 15085.0, places=7)
        
        # Profit = 15085 - 15000 = $85
        profit = run_data['total_balance'] - 15000.0
        self.assertAlmostEqual(profit, 85.0, places=7)
        
        print(f"Momentum Trading Results:")
        print(f"  Total Invested: ${total_invested:.2f}")
        print(f"  Total Sold For: ${total_sold_proceeds:.2f}")
        print(f"  Remaining Value: ${remaining_value:.2f}")
        print(f"  Final Portfolio: ${run_data['total_balance']:,.2f}")
        print(f"  Total Profit: ${profit:.2f}")
        print(f"  Number of Transactions: {len(run_data['transactions'])}")

    def test_diversification_scenario(self):
        """Test portfolio diversification across multiple markets."""
        run_name = "diversification_test"
        
        # Create large portfolio simulation
        self.initializer.create_new_run(
            market_name="Diversified Portfolio",
            initial_balance=25000.0,
            run_name=run_name
        )
        
        # Create multiple markets across different categories
        markets = [
            ("crypto_bull", "Crypto Bull Market", "crypto", 0.35, 0.33, 0.37),
            ("fed_rates", "Fed Cuts Rates", "economics", 0.60, 0.58, 0.62),
            ("ai_stocks", "AI Stocks +50%", "technology", 0.45, 0.43, 0.47),
            ("climate_action", "Climate Legislation", "politics", 0.30, 0.28, 0.32),
            ("election_outcome", "Election Outcome", "politics", 0.50, 0.48, 0.52)
        ]
        
        # Create all markets
        for market_id, name, category, price, bid, ask in markets:
            success = self.initializer.create_market(
                run_name=run_name,
                market_id=market_id,
                market_name=name,
                description=f"Market for {name}",
                category=category,
                initial_price=price,
                bid_price=bid,
                ask_price=ask
            )
            self.assertTrue(success)
        
        # Diversify across all markets (equal weight ~$5000 each)
        allocations = [
            ("crypto_bull", 135),    # ~$5000 / 0.37 = 135 shares
            ("fed_rates", 80),       # ~$5000 / 0.62 = 80 shares  
            ("ai_stocks", 106),      # ~$5000 / 0.47 = 106 shares
            ("climate_action", 156), # ~$5000 / 0.32 = 156 shares
            ("election_outcome", 96) # ~$5000 / 0.52 = 96 shares
        ]
        
        total_invested = 0
        for market_id, shares in allocations:
            success = self.initializer.add_position(
                run_name=run_name,
                market_id=market_id,
                num_shares=float(shares)
            )
            self.assertTrue(success)
            
            # Calculate actual cost
            market_data = None
            run_data = self.initializer.get_run_info(run_name)
            for market in run_data['markets']:
                if market['market_id'] == market_id:
                    market_data = market
                    break
            cost = shares * market_data['current_ask']
            total_invested += cost
        
        # Check initial diversification
        run_data = self.initializer.get_run_info(run_name)
        self.assertEqual(len(run_data['positions']), 5)
        self.assertEqual(len(run_data['markets']), 5)
        self.assertAlmostEqual(run_data['balance_invested'], total_invested, places=2)
        
        # Simulate different market outcomes
        # Crypto and AI do well, Fed disappoints, Politics mixed
        market_outcomes = {
            "crypto_bull": {"price": 0.75, "bid": 0.73, "ask": 0.77},      # +114% gain
            "fed_rates": {"price": 0.25, "bid": 0.23, "ask": 0.27},        # -58% loss  
            "ai_stocks": {"price": 0.68, "bid": 0.66, "ask": 0.70},        # +51% gain
            "climate_action": {"price": 0.40, "bid": 0.38, "ask": 0.42},   # +33% gain
            "election_outcome": {"price": 0.35, "bid": 0.33, "ask": 0.37}  # -30% loss
        }
        
        self.initializer.update_market_prices(run_name, market_outcomes)
        
        # Analyze portfolio performance
        run_data = self.initializer.get_run_info(run_name)
        
        # Calculate individual position values
        position_values = {}
        for position in run_data['positions']:
            market_id = position['market_id']
            current_price = None
            for market in run_data['markets']:
                if market['market_id'] == market_id:
                    current_price = market['current_price']
                    break
            position_values[market_id] = position['num_shares'] * current_price
        
        total_portfolio_value = sum(position_values.values())
        self.assertAlmostEqual(run_data['balance_of_shares'], total_portfolio_value, places=7)
        
        # Test rebalancing - sell winners, buy losers
        # Sell half of crypto position (big winner)
        crypto_position = None
        for pos in run_data['positions']:
            if pos['market_id'] == 'crypto_bull':
                crypto_position = pos
                break
        
        self.initializer.sell_position(
            run_name=run_name,
            market_id="crypto_bull",
            num_shares=crypto_position['num_shares'] / 2
        )
        
        # Buy more fed_rates (big loser, potential recovery)
        self.initializer.add_position(
            run_name=run_name,
            market_id="fed_rates",
            num_shares=100.0
        )
        
        # Final portfolio check
        final_data = self.initializer.get_run_info(run_name)
        
        # Should still have 5 positions
        self.assertEqual(len(final_data['positions']), 5)
        
        # Should have more transactions (5 initial + 1 sale + 1 buy = 7)
        self.assertEqual(len(final_data['transactions']), 7)
        
        print(f"Diversification Results:")
        print(f"  Initial Investment: ${total_invested:,.2f}")
        print(f"  Portfolio Value: ${final_data['balance_of_shares']:,.2f}")
        print(f"  Cash Balance: ${final_data['current_balance']:,.2f}")
        print(f"  Total Portfolio: ${final_data['total_balance']:,.2f}")
        profit_loss = final_data['total_balance'] - 25000.0
        print(f"  Total P&L: ${profit_loss:,.2f}")
        print(f"  Individual Positions:")
        for position in final_data['positions']:
            market_name = None
            current_price = None
            for market in final_data['markets']:
                if market['market_id'] == position['market_id']:
                    market_name = market['market_name']
                    current_price = market['current_price']
                    break
            value = position['num_shares'] * current_price
            pnl = value - position['total_invested']
            print(f"    {market_name}: {position['num_shares']:.0f} shares, ${value:.2f} value, ${pnl:+.2f} P&L")

    def test_risk_management_scenario(self):
        """Test risk management with stop losses and position sizing."""
        run_name = "risk_management_test"
        
        # Create focused trading simulation
        self.initializer.create_new_run(
            market_name="Risk Management Trading",
            initial_balance=20000.0,
            run_name=run_name
        )
        
        # Create high-risk, high-reward market
        self.initializer.create_market(
            run_name=run_name,
            market_id="meme_stock",
            market_name="Meme Stock Rally",
            description="Meme stocks rally 100%+ this quarter",
            category="stocks",
            initial_price=0.20,  # Low probability, high reward
            bid_price=0.18,
            ask_price=0.22
        )
        
        # Conservative position sizing - only risk 5% of portfolio
        risk_amount = 20000.0 * 0.05  # $1000 max risk
        shares = risk_amount / 0.22   # ~454 shares
        
        self.initializer.add_position(
            run_name=run_name,
            market_id="meme_stock",
            num_shares=454.0
        )
        
        # Check initial position
        run_data = self.initializer.get_run_info(run_name)
        initial_cost = 454.0 * 0.22
        self.assertAlmostEqual(run_data['balance_invested'], initial_cost, places=2)
        
        # Scenario 1: Position moves against us - implement stop loss
        # Price drops 50% - cut losses quickly
        self.initializer.update_market_prices(run_name, {
            "meme_stock": {"price": 0.10, "bid": 0.09, "ask": 0.11}
        })
        
        # Execute stop loss - sell entire position to limit damage
        stop_loss_success = self.initializer.sell_position(
            run_name=run_name,
            market_id="meme_stock",
            num_shares=454.0
        )
        self.assertTrue(stop_loss_success)
        
        # Check damage limitation
        run_data = self.initializer.get_run_info(run_name)
        sale_proceeds = 454.0 * 0.09  # Sold at bid
        loss = initial_cost - sale_proceeds
        
        # Loss should be contained to manageable amount
        self.assertLess(loss, 1200.0)  # Less than 6% of total portfolio
        self.assertEqual(len(run_data['positions']), 0)  # Position closed
        
        expected_cash = 20000.0 - initial_cost + sale_proceeds
        self.assertAlmostEqual(run_data['current_balance'], expected_cash, places=2)
        
        # Scenario 2: New opportunity with proper position sizing
        self.initializer.create_market(
            run_name=run_name,
            market_id="safe_bet",
            market_name="Safe Market Bet",
            description="High probability outcome",
            category="economics",
            initial_price=0.70,
            bid_price=0.68,
            ask_price=0.72
        )
        
        # Larger position since higher probability
        safe_risk_amount = 20000.0 * 0.15  # 15% risk on safer bet
        safe_shares = safe_risk_amount / 0.72
        
        self.initializer.add_position(
            run_name=run_name,
            market_id="safe_bet",
            num_shares=safe_shares
        )
        
        # Market moves favorably
        self.initializer.update_market_prices(run_name, {
            "safe_bet": {"price": 0.85, "bid": 0.83, "ask": 0.87}
        })
        
        # Take partial profits at good level
        partial_sale = self.initializer.sell_position(
            run_name=run_name,
            market_id="safe_bet",
            num_shares=safe_shares / 2  # Sell half
        )
        self.assertTrue(partial_sale)
        
        # Final risk management check
        final_data = self.initializer.get_run_info(run_name)
        
        # Should have one remaining position (half of safe bet)
        self.assertEqual(len(final_data['positions']), 1)
        
        # Total transactions: 1 risky buy + 1 stop loss + 1 safe buy + 1 partial sale = 4
        self.assertEqual(len(final_data['transactions']), 4)
        
        # Portfolio should be close to break-even or slightly positive
        total_return = final_data['total_balance'] - 20000.0
        
        print(f"Risk Management Results:")
        print(f"  Initial Portfolio: $20,000.00")
        print(f"  Stop Loss Amount: ${loss:.2f}")
        print(f"  Final Portfolio: ${final_data['total_balance']:,.2f}")
        print(f"  Net Return: ${total_return:+.2f}")
        print(f"  Max Risk Per Trade: Limited to 5-15% of portfolio")
        print(f"  Risk Management: Stop loss executed automatically")

    def test_long_term_holding_scenario(self):
        """Test long-term buy and hold strategy with regular additions."""
        run_name = "long_term_test"
        
        # Create long-term investment simulation
        self.initializer.create_new_run(
            market_name="Long-term Investment Strategy",
            initial_balance=10000.0,
            run_name=run_name
        )
        
        # Create stable, long-term growth market
        self.initializer.create_market(
            run_name=run_name,
            market_id="tech_growth",
            market_name="Tech Sector 10-Year Growth",
            description="Tech sector outperforms over 10 years",
            category="technology",
            initial_price=0.65,
            bid_price=0.63,
            ask_price=0.67
        )
        
        # Initial investment - dollar cost averaging approach
        monthly_investment = 1000.0
        
        # Month 1: Initial position
        shares_month1 = monthly_investment / 0.67
        self.initializer.add_position(
            run_name=run_name,
            market_id="tech_growth",
            num_shares=shares_month1
        )
        
        # Month 2: Market dips - good buying opportunity
        self.initializer.update_market_prices(run_name, {
            "tech_growth": {"price": 0.55, "bid": 0.53, "ask": 0.57}
        })
        
        # Add more funds and buy the dip
        self.initializer.add_balance(run_name, monthly_investment, "Month 2 investment")
        shares_month2 = monthly_investment / 0.57
        self.initializer.add_position(
            run_name=run_name,
            market_id="tech_growth",
            num_shares=shares_month2
        )
        
        # Month 3: Market recovers
        self.initializer.update_market_prices(run_name, {
            "tech_growth": {"price": 0.70, "bid": 0.68, "ask": 0.72}
        })
        
        self.initializer.add_balance(run_name, monthly_investment, "Month 3 investment")
        shares_month3 = monthly_investment / 0.72
        self.initializer.add_position(
            run_name=run_name,
            market_id="tech_growth",
            num_shares=shares_month3
        )
        
        # Month 6: Strong growth
        self.initializer.update_market_prices(run_name, {
            "tech_growth": {"price": 0.80, "bid": 0.78, "ask": 0.82}
        })
        
        self.initializer.add_balance(run_name, monthly_investment, "Month 6 investment")
        shares_month6 = monthly_investment / 0.82
        self.initializer.add_position(
            run_name=run_name,
            market_id="tech_growth",
            num_shares=shares_month6
        )
        
        # Year end: Significant appreciation
        self.initializer.update_market_prices(run_name, {
            "tech_growth": {"price": 0.85, "bid": 0.83, "ask": 0.87}
        })
        
        # Check long-term results
        run_data = self.initializer.get_run_info(run_name)
        
        # Should have one large position from multiple purchases
        self.assertEqual(len(run_data['positions']), 1)
        position = run_data['positions'][0]
        
        # Total shares should be sum of all purchases
        total_shares = shares_month1 + shares_month2 + shares_month3 + shares_month6
        self.assertAlmostEqual(position['num_shares'], total_shares, places=2)
        
        # Total invested should be 4 * $1000 = $4000
        self.assertAlmostEqual(run_data['balance_invested'], 4000.0, places=2)
        
        # Current value should be total_shares * 0.85
        current_value = total_shares * 0.85
        self.assertAlmostEqual(run_data['balance_of_shares'], current_value, places=2)
        
        # Calculate average cost basis
        average_cost = 4000.0 / total_shares
        current_price = 0.85
        
        # Should have multiple balance additions and position additions
        balance_add_txs = [tx for tx in run_data['transactions'] if tx['type'] == 'BALANCE_ADD']
        buy_txs = [tx for tx in run_data['transactions'] if tx['type'] == 'BUY']
        
        self.assertEqual(len(balance_add_txs), 3)  # 3 additional funding rounds
        self.assertEqual(len(buy_txs), 4)  # 4 purchase transactions
        
        # Total return calculation
        total_portfolio = run_data['total_balance']
        total_invested = 10000.0 + (3 * 1000.0)  # Initial + 3 additions
        total_return = total_portfolio - total_invested
        return_pct = (total_return / total_invested) * 100
        
        print(f"Long-term Holding Results:")
        print(f"  Total Invested: ${total_invested:,.2f}")
        print(f"  Average Cost Basis: ${average_cost:.4f}")
        print(f"  Current Price: ${current_price:.4f}")
        print(f"  Total Shares: {total_shares:.2f}")
        print(f"  Portfolio Value: ${total_portfolio:,.2f}")
        print(f"  Total Return: ${total_return:+,.2f} ({return_pct:+.1f}%)")
        print(f"  Dollar Cost Averaging: Bought at multiple price points")

    def test_comprehensive_trading_system_stress_test(self):
        """Comprehensive stress test covering all system functionality including error conditions."""
        run_name = "stress_test_comprehensive"
        
        print("\n🔥 COMPREHENSIVE SYSTEM STRESS TEST 🔥")
        print("Testing all functionality with success and error conditions")
        
        # Phase 1: Create simulation and test initial setup
        print("\n--- Phase 1: Run Creation and Initial Setup ---")
        
        # Create simulation with large initial balance
        result = self.initializer.create_new_run(
            market_name="Comprehensive Trading System Test",
            initial_balance=50000.0,
            run_name=run_name
        )
        self.assertIsNotNone(result)
        print(f"✅ Created simulation with ${50000:,} initial balance")
        
        # Test run info retrieval
        run_data = self.initializer.get_run_info(run_name)
        self.assertIsNotNone(run_data)
        self.assertEqual(run_data['current_balance'], 50000.0)
        print(f"✅ Run info retrieval works correctly")
        
        # Test nonexistent run info retrieval
        nonexistent_data = self.initializer.get_run_info("nonexistent_run_12345")
        self.assertIsNone(nonexistent_data)
        print(f"✅ Nonexistent run handling works correctly")
        
        # Phase 2: Create multiple markets across categories
        print("\n--- Phase 2: Market Creation (10 Markets) ---")
        
        markets_to_create = [
            ("crypto_btc", "Bitcoin $100k by 2025", "Bitcoin reaches $100k", "crypto", 0.35, 0.33, 0.37),
            ("crypto_eth", "Ethereum $10k by 2025", "Ethereum reaches $10k", "crypto", 0.28, 0.26, 0.30),
            ("stocks_apple", "Apple $300 by 2025", "Apple stock hits $300", "stocks", 0.45, 0.43, 0.47),
            ("stocks_nvidia", "NVIDIA $2000 by 2025", "NVIDIA reaches $2000", "stocks", 0.52, 0.50, 0.54),
            ("economics_fed", "Fed Cuts Rates 2024", "Federal Reserve cuts rates", "economics", 0.75, 0.73, 0.77),
            ("economics_recession", "US Recession 2024", "US enters recession", "economics", 0.25, 0.23, 0.27),
            ("politics_election", "2024 Election Outcome", "Specific election outcome", "politics", 0.50, 0.48, 0.52),
            ("technology_ai", "AGI Achieved by 2030", "Artificial General Intelligence", "technology", 0.15, 0.13, 0.17),
            ("climate_warming", "1.5C Warming Exceeded", "Climate warming threshold", "climate", 0.85, 0.83, 0.87),
            ("sports_superbowl", "Specific Team Wins SB", "Team wins Super Bowl", "sports", 0.12, 0.10, 0.14)
        ]
        
        created_markets = []
        for market_id, name, desc, category, price, bid, ask in markets_to_create:
            success = self.initializer.create_market(
                run_name=run_name,
                market_id=market_id,
                market_name=name,
                description=desc,
                category=category,
                initial_price=price,
                bid_price=bid,
                ask_price=ask
            )
            self.assertTrue(success)
            created_markets.append(market_id)
            print(f"✅ Created market: {name} ({market_id})")
        
        # Test duplicate market creation (should fail)
        duplicate_success = self.initializer.create_market(
            run_name=run_name,
            market_id="crypto_btc",  # Already exists
            market_name="Duplicate Bitcoin Market",
            description="This should fail",
            category="crypto",
            initial_price=0.50,
            bid_price=0.48,
            ask_price=0.52
        )
        self.assertFalse(duplicate_success)
        print(f"✅ Duplicate market creation properly rejected")
        
        # Test market creation for nonexistent run (should fail)
        nonexistent_run_market = self.initializer.create_market(
            run_name="nonexistent_run_12345",
            market_id="test_market",
            market_name="Test Market",
            description="Should fail",
            category="test",
            initial_price=0.50,
            bid_price=0.48,
            ask_price=0.52
        )
        self.assertFalse(nonexistent_run_market)
        print(f"✅ Market creation for nonexistent run properly rejected")
        
        # Verify all markets were created
        run_data = self.initializer.get_run_info(run_name)
        self.assertEqual(len(run_data['markets']), 10)
        print(f"✅ All 10 markets successfully created")
        
        # Phase 3: Position Management - Success and Error Cases
        print("\n--- Phase 3: Position Management (Success & Error Cases) ---")
        
        # Create successful positions across different markets
        position_data = [
            ("crypto_btc", 1000.0),      # $370 cost
            ("crypto_eth", 1500.0),      # $450 cost  
            ("stocks_apple", 800.0),     # $376 cost
            ("stocks_nvidia", 600.0),    # $324 cost
            ("economics_fed", 400.0),    # $308 cost
            ("technology_ai", 2000.0),   # $340 cost
            ("climate_warming", 300.0),  # $261 cost
        ]
        
        total_invested = 0
        for market_id, shares in position_data:
            success = self.initializer.add_position(
                run_name=run_name,
                market_id=market_id,
                num_shares=shares
            )
            self.assertTrue(success)
            
            # Calculate cost
            run_data = self.initializer.get_run_info(run_name)
            for market in run_data['markets']:
                if market['market_id'] == market_id:
                    cost = shares * market['current_ask']
                    total_invested += cost
                    print(f"✅ Created position: {shares} shares of {market_id} for ${cost:.2f}")
                    break
        
        print(f"✅ Total invested in positions: ${total_invested:.2f}")
        
        # Test error cases for position creation
        print("\n--- Testing Position Creation Error Cases ---")
        
        # Get current balance to ensure insufficient funds test works
        run_data = self.initializer.get_run_info(run_name)
        current_balance = run_data['current_balance']
        
        # Calculate a position that would definitely exceed available funds
        # Use crypto_btc at ask price (currently ~$0.37) 
        crypto_btc_market = None
        for market in run_data['markets']:
            if market['market_id'] == 'crypto_btc':
                crypto_btc_market = market
                break
        
        if crypto_btc_market:
            ask_price = crypto_btc_market['current_ask']
            # Calculate shares needed to exceed available balance by significant margin
            excessive_shares = (current_balance / ask_price) + 50000.0  # Definitely more than we can afford
        else:
            excessive_shares = 1000000.0  # Fallback to very large number
        
        # Test insufficient funds (should fail)
        insufficient_funds = self.initializer.add_position(
            run_name=run_name,
            market_id="crypto_btc",
            num_shares=excessive_shares  # Guaranteed to exceed available funds
        )
        self.assertFalse(insufficient_funds)
        print(f"✅ Insufficient funds position creation properly rejected")
        print(f"   Attempted: {excessive_shares:,.0f} shares, Available funds: ${current_balance:,.2f}")
        
        # Test position for nonexistent market (should fail)
        nonexistent_market_position = self.initializer.add_position(
            run_name=run_name,
            market_id="nonexistent_market_xyz",
            num_shares=100.0
        )
        self.assertFalse(nonexistent_market_position)
        print(f"✅ Position creation for nonexistent market properly rejected")
        
        # Test position for nonexistent run (should fail)
        nonexistent_run_position = self.initializer.add_position(
            run_name="nonexistent_run_12345",
            market_id="crypto_btc",
            num_shares=100.0
        )
        self.assertFalse(nonexistent_run_position)
        print(f"✅ Position creation for nonexistent run properly rejected")
        
        # Test negative balance override
        negative_balance_success = self.initializer.add_position(
            run_name=run_name,
            market_id="sports_superbowl",
            num_shares=50000.0,  # Huge position to force negative balance
            allow_negative_balance=True
        )
        self.assertTrue(negative_balance_success)
        print(f"✅ Negative balance override works correctly")
        
        # Check current state
        run_data = self.initializer.get_run_info(run_name)
        self.assertEqual(len(run_data['positions']), 8)  # 7 normal + 1 negative balance
        print(f"✅ Portfolio now has {len(run_data['positions'])} positions")
        print(f"   Current balance: ${run_data['current_balance']:,.2f}")
        print(f"   Total balance: ${run_data['total_balance']:,.2f}")
        
        # Phase 4: Position Merging and Additional Purchases
        print("\n--- Phase 4: Position Merging and Additional Purchases ---")
        
        # Add more shares to existing positions (should merge)
        merge_additions = [
            ("crypto_btc", 500.0),
            ("stocks_apple", 300.0),
            ("economics_fed", 200.0)
        ]
        
        for market_id, additional_shares in merge_additions:
            # Get position before
            run_data = self.initializer.get_run_info(run_name)
            before_position = None
            for pos in run_data['positions']:
                if pos['market_id'] == market_id:
                    before_position = pos
                    break
            
            success = self.initializer.add_position(
                run_name=run_name,
                market_id=market_id,
                num_shares=additional_shares,
                allow_negative_balance=True
            )
            self.assertTrue(success)
            
            # Get position after
            run_data = self.initializer.get_run_info(run_name)
            after_position = None
            for pos in run_data['positions']:
                if pos['market_id'] == market_id:
                    after_position = pos
                    break
            
            # Verify merge
            expected_shares = before_position['num_shares'] + additional_shares
            self.assertAlmostEqual(after_position['num_shares'], expected_shares, places=5)
            print(f"✅ Position merge: {market_id} now has {after_position['num_shares']:.1f} shares")
        
        # Still should have same number of positions (merging, not creating new)
        run_data = self.initializer.get_run_info(run_name)
        self.assertEqual(len(run_data['positions']), 8)
        print(f"✅ Position count unchanged after merging: {len(run_data['positions'])} positions")
        
        # Phase 5: Market Price Updates - Simulate Market Volatility
        print("\n--- Phase 5: Market Price Updates and Volatility ---")
        
        # Create multiple price update scenarios
        price_update_scenarios = [
            # Scenario 1: Crypto bull run
            {
                "crypto_btc": {"price": 0.55, "bid": 0.53, "ask": 0.57},
                "crypto_eth": {"price": 0.42, "bid": 0.40, "ask": 0.44},
            },
            # Scenario 2: Stock market correction
            {
                "stocks_apple": {"price": 0.35, "bid": 0.33, "ask": 0.37},
                "stocks_nvidia": {"price": 0.38, "bid": 0.36, "ask": 0.40},
            },
            # Scenario 3: Economic uncertainty
            {
                "economics_fed": {"price": 0.85, "bid": 0.83, "ask": 0.87},
                "economics_recession": {"price": 0.35, "bid": 0.33, "ask": 0.37},
            },
            # Scenario 4: Mixed market with extreme moves
            {
                "technology_ai": {"price": 0.05, "bid": 0.03, "ask": 0.07},  # Crash
                "climate_warming": {"price": 0.95, "bid": 0.93, "ask": 0.97},  # Spike
                "sports_superbowl": {"price": 0.25, "bid": 0.23, "ask": 0.27},
                "politics_election": {"price": 0.65, "bid": 0.63, "ask": 0.67},
            }
        ]
        
        for i, price_update in enumerate(price_update_scenarios, 1):
            success = self.initializer.update_market_prices(run_name, price_update)
            self.assertTrue(success)
            
            run_data = self.initializer.get_run_info(run_name)
            print(f"✅ Price Update Scenario {i}: Updated {len(price_update)} markets")
            print(f"   New total balance: ${run_data['total_balance']:,.2f}")
            print(f"   Market value: ${run_data['balance_of_shares']:,.2f}")
        
        # Test price update error cases
        print("\n--- Testing Price Update Error Cases ---")
        
        # Test price update for nonexistent run
        nonexistent_run_update = self.initializer.update_market_prices(
            "nonexistent_run_12345",
            {"crypto_btc": {"price": 0.50, "bid": 0.48, "ask": 0.52}}
        )
        self.assertFalse(nonexistent_run_update)
        print(f"✅ Price update for nonexistent run properly rejected")
        
        # Test price update with nonexistent market (should succeed but skip invalid markets)
        mixed_update = self.initializer.update_market_prices(run_name, {
            "crypto_btc": {"price": 0.60, "bid": 0.58, "ask": 0.62},  # Valid
            "nonexistent_market": {"price": 0.50, "bid": 0.48, "ask": 0.52}  # Invalid
        })
        self.assertTrue(mixed_update)  # Should succeed for valid markets
        print(f"✅ Mixed price update (valid + invalid markets) handled correctly")
        
        # Phase 6: Position Selling - Success and Error Cases
        print("\n--- Phase 6: Position Selling (Success & Error Cases) ---")
        
        # Test successful partial sales
        partial_sales = [
            ("crypto_btc", 200.0),
            ("stocks_apple", 150.0),
            ("economics_fed", 100.0)
        ]
        
        for market_id, shares_to_sell in partial_sales:
            # Get position before sale
            run_data = self.initializer.get_run_info(run_name)
            before_position = None
            for pos in run_data['positions']:
                if pos['market_id'] == market_id:
                    before_position = pos
                    break
            
            success = self.initializer.sell_position(
                run_name=run_name,
                market_id=market_id,
                num_shares=shares_to_sell
            )
            self.assertTrue(success)
            
            # Get position after sale
            run_data = self.initializer.get_run_info(run_name)
            after_position = None
            for pos in run_data['positions']:
                if pos['market_id'] == market_id:
                    after_position = pos
                    break
            
            expected_remaining = before_position['num_shares'] - shares_to_sell
            self.assertAlmostEqual(after_position['num_shares'], expected_remaining, places=5)
            print(f"✅ Partial sale: {market_id} sold {shares_to_sell} shares, {expected_remaining:.1f} remaining")
        
        # Test complete position sale
        complete_sale_success = self.initializer.sell_position(
            run_name=run_name,
            market_id="technology_ai",
            num_shares=2000.0  # Should be all shares
        )
        self.assertTrue(complete_sale_success)
        
        # Verify position was completely removed
        run_data = self.initializer.get_run_info(run_name)
        ai_position_exists = any(pos['market_id'] == 'technology_ai' for pos in run_data['positions'])
        self.assertFalse(ai_position_exists)
        print(f"✅ Complete position sale: technology_ai position completely removed")
        
        # Test selling error cases
        print("\n--- Testing Position Selling Error Cases ---")
        
        # Test selling more shares than available
        oversell_attempt = self.initializer.sell_position(
            run_name=run_name,
            market_id="crypto_eth",
            num_shares=10000.0  # More than available
        )
        self.assertFalse(oversell_attempt)
        print(f"✅ Overselling attempt properly rejected")
        
        # Test selling from nonexistent market
        nonexistent_market_sell = self.initializer.sell_position(
            run_name=run_name,
            market_id="nonexistent_market_xyz",
            num_shares=100.0
        )
        self.assertFalse(nonexistent_market_sell)
        print(f"✅ Selling from nonexistent market properly rejected")
        
        # Test selling from nonexistent run
        nonexistent_run_sell = self.initializer.sell_position(
            run_name="nonexistent_run_12345",
            market_id="crypto_btc",
            num_shares=100.0
        )
        self.assertFalse(nonexistent_run_sell)
        print(f"✅ Selling from nonexistent run properly rejected")
        
        # Phase 7: Balance Management - Success and Error Cases
        print("\n--- Phase 7: Balance Management (Success & Error Cases) ---")
        
        # Test successful balance additions
        balance_additions = [
            (5000.0, "Additional funding round 1"),
            (2500.0, "Emergency funding"),
            (7500.0, "Major investment round")
        ]
        
        for amount, description in balance_additions:
            before_balance = self.initializer.get_run_info(run_name)['current_balance']
            
            success = self.initializer.add_balance(
                run_name=run_name,
                amount=amount,
                description=description
            )
            self.assertTrue(success)
            
            after_balance = self.initializer.get_run_info(run_name)['current_balance']
            self.assertAlmostEqual(after_balance, before_balance + amount, places=2)
            print(f"✅ Added ${amount:,.2f}: {description}")
        
        # Test balance addition error cases
        print("\n--- Testing Balance Management Error Cases ---")
        
        # Test negative balance addition
        negative_add = self.initializer.add_balance(
            run_name=run_name,
            amount=-1000.0,
            description="Should fail"
        )
        self.assertFalse(negative_add)
        print(f"✅ Negative balance addition properly rejected")
        
        # Test balance addition to nonexistent run
        nonexistent_run_add = self.initializer.add_balance(
            run_name="nonexistent_run_12345",
            amount=1000.0,
            description="Should fail"
        )
        self.assertFalse(nonexistent_run_add)
        print(f"✅ Balance addition to nonexistent run properly rejected")
        
        # Test successful balance removal
        current_balance = self.initializer.get_run_info(run_name)['current_balance']
        removal_amount = min(5000.0, current_balance - 1000.0)  # Leave some balance
        
        if removal_amount > 0:
            remove_success = self.initializer.remove_balance(
                run_name=run_name,
                amount=removal_amount,
                description="Profit taking"
            )
            self.assertTrue(remove_success)
            print(f"✅ Removed ${removal_amount:,.2f} successfully")
        
        # Test balance removal error cases
        
        # Test removing more than available (without override)
        excessive_removal = self.initializer.remove_balance(
            run_name=run_name,
            amount=999999.0,  # Way more than available
            description="Should fail"
        )
        self.assertFalse(excessive_removal)
        print(f"✅ Excessive balance removal properly rejected")
        
        # Test balance removal with negative override
        negative_override_success = self.initializer.remove_balance(
            run_name=run_name,
            amount=10000.0,
            description="Force negative balance",
            allow_negative=True
        )
        self.assertTrue(negative_override_success)
        print(f"✅ Balance removal with negative override works")
        
        # Phase 8: Final State Verification and Statistics
        print("\n--- Phase 8: Final State Verification ---")
        
        final_data = self.initializer.get_run_info(run_name)
        
        # Verify data integrity
        self.assertIsNotNone(final_data)
        self.assertEqual(len(final_data['markets']), 10)  # All markets still exist
        self.assertGreaterEqual(len(final_data['positions']), 6)  # Some positions remain
        self.assertGreaterEqual(len(final_data['transactions']), 20)  # Many transactions recorded
        
        # Calculate final statistics
        total_market_value = final_data['balance_of_shares']
        total_invested = final_data['balance_invested']
        current_cash = final_data['current_balance']
        total_portfolio = final_data['total_balance']
        
        # Count transactions by type
        transaction_counts = {}
        for tx in final_data['transactions']:
            tx_type = tx['type']
            transaction_counts[tx_type] = transaction_counts.get(tx_type, 0) + 1
        
        print(f"\n🎯 FINAL STRESS TEST RESULTS:")
        print(f"{'='*50}")
        print(f"Markets Created: {len(final_data['markets'])}")
        print(f"Active Positions: {len(final_data['positions'])}")
        print(f"Total Transactions: {len(final_data['transactions'])}")
        print(f"Transaction Breakdown:")
        for tx_type, count in transaction_counts.items():
            print(f"  {tx_type}: {count}")
        print(f"\nPortfolio Summary:")
        print(f"  Current Cash: ${current_cash:,.2f}")
        print(f"  Market Value: ${total_market_value:,.2f}")
        print(f"  Total Invested: ${total_invested:,.2f}")
        print(f"  Total Portfolio: ${total_portfolio:,.2f}")
        print(f"  Net P&L: ${total_market_value - total_invested:+,.2f}")
        
        if transaction_counts.get('BALANCE_ADD', 0) > 0:
            print(f"\n🎯 Additional Balance Additions:")
            for tx in final_data['transactions']:
                if tx['type'] == 'BALANCE_ADD':
                    print(f"  ${tx.get('amount', 0):,.2f}: {tx.get('description', 'Balance addition')}")
        
        print(f"\n✅ COMPREHENSIVE STRESS TEST COMPLETED SUCCESSFULLY!")
        print(f"   All functionality tested including error conditions")
        print(f"   System handled complex scenarios robustly")

    def test_extreme_edge_cases_and_fractional_scenarios(self):
        """Test extreme edge cases, fractional shares, and boundary conditions."""
        run_name = "edge_cases_test"
        
        print("\n🎢 EXTREME EDGE CASES & FRACTIONAL SCENARIOS TEST 🎢")
        print("Testing boundary conditions, fractional shares, and edge cases")
        
        # Phase 1: Setup with minimal balance for edge case testing
        print("\n--- Phase 1: Minimal Balance Setup ---")
        
        # Start with very small balance to test edge cases
        self.initializer.create_new_run(
            market_name="Edge Cases Testing",
            initial_balance=100.0,  # Small balance for edge testing
            run_name=run_name
        )
        print(f"✅ Created simulation with minimal ${100} balance")
        
        # Phase 2: Create markets with extreme price ranges
        print("\n--- Phase 2: Markets with Extreme Prices ---")
        
        extreme_markets = [
            # Very low probability events
            ("black_swan", "Black Swan Event", "Extremely rare event", "events", 0.001, 0.0005, 0.0015),
            ("lottery_win", "Lottery Jackpot", "Someone wins lottery", "gambling", 0.000001, 0.0000005, 0.0000015),
            
            # Very high probability events  
            ("sun_rises", "Sun Rises Tomorrow", "Sun will rise", "certainty", 0.9999, 0.9995, 0.9999),
            ("year_ends", "Year Ends in December", "Calendar year ends", "certainty", 0.9998, 0.9996, 0.9999),
            
            # Mid-range with tight spreads
            ("coin_flip", "Coin Flip Heads", "Fair coin lands heads", "random", 0.5000, 0.4999, 0.5001),
            
            # Extreme volatility potential
            ("volatile_stock", "Volatile Stock Move", "Stock moves 50%+", "stocks", 0.20, 0.15, 0.25),
            
            # Zero probability edge case
            ("impossible", "Impossible Event", "Mathematically impossible", "test", 0.0, 0.0, 0.001),
            
            # Maximum probability edge case  
            ("certain", "Certain Event", "Will definitely happen", "test", 1.0, 0.999, 1.0),
        ]
        
        for market_id, name, desc, category, price, bid, ask in extreme_markets:
            success = self.initializer.create_market(
                run_name=run_name,
                market_id=market_id,
                market_name=name,
                description=desc,
                category=category,
                initial_price=price,
                bid_price=bid,
                ask_price=ask
            )
            self.assertTrue(success)
            print(f"✅ Created extreme market: {name} (p={price})")
        
        # Phase 3: Fractional Share Testing
        print("\n--- Phase 3: Fractional Share Operations ---")
        
        # Test very small fractional positions
        fractional_tests = [
            ("coin_flip", 0.1),           # 0.1 shares
            ("volatile_stock", 0.001),    # 0.001 shares  
            ("sun_rises", 0.00001),       # Tiny fraction
            ("black_swan", 10000.0),      # Large number of very cheap shares
        ]
        
        for market_id, shares in fractional_tests:
            success = self.initializer.add_position(
                run_name=run_name,
                market_id=market_id,
                num_shares=shares,
                allow_negative_balance=True  # Allow for testing
            )
            self.assertTrue(success)
            print(f"✅ Created fractional position: {shares} shares of {market_id}")
        
        # Verify fractional positions exist
        run_data = self.initializer.get_run_info(run_name)
        self.assertEqual(len(run_data['positions']), len(fractional_tests))
        
        # Phase 4: Extreme Price Movement Simulations
        print("\n--- Phase 4: Extreme Price Movements ---")
        
        # Simulate extreme market crashes and spikes
        extreme_price_scenarios = [
            # Complete collapse scenarios
            {
                "volatile_stock": {"price": 0.001, "bid": 0.0005, "ask": 0.0015},  # 95% crash
                "black_swan": {"price": 0.5, "bid": 0.48, "ask": 0.52},            # 50000% spike!
            },
            
            # Certainty collapse (impossible but testing)
            {
                "sun_rises": {"price": 0.01, "bid": 0.005, "ask": 0.015},  # "Impossible" event
                "certain": {"price": 0.02, "bid": 0.015, "ask": 0.025},    # Certain becomes uncertain
            },
            
            # Extreme spike scenario
            {
                "lottery_win": {"price": 0.1, "bid": 0.08, "ask": 0.12},   # 100,000x increase
                "impossible": {"price": 0.5, "bid": 0.45, "ask": 0.55},    # Impossible becomes possible
            },
            
            # Reversion scenario
            {
                "coin_flip": {"price": 0.7, "bid": 0.68, "ask": 0.72},     # Bias introduced
                "year_ends": {"price": 0.99999, "bid": 0.99995, "ask": 1.0}, # Near certainty
            }
        ]
        
        for i, price_update in enumerate(extreme_price_scenarios, 1):
            success = self.initializer.update_market_prices(run_name, price_update)
            self.assertTrue(success)
            
            run_data = self.initializer.get_run_info(run_name)
            print(f"✅ Extreme Price Scenario {i}: Portfolio value now ${run_data['total_balance']:,.8f}")
            
            # Check for any positions with extreme values
            for position in run_data['positions']:
                if position['current_total_price'] > 1000:  # Extreme gains
                    print(f"   💰 EXTREME GAIN: {position['market_id']} worth ${position['current_total_price']:,.2f}")
                elif position['current_total_price'] < 0.01:  # Extreme losses
                    print(f"   📉 EXTREME LOSS: {position['market_id']} worth ${position['current_total_price']:.8f}")
        
        # Phase 5: Fractional Selling and Precision Testing
        print("\n--- Phase 5: Fractional Selling and Precision ---")
        
        # Test fractional selling with extreme precision
        fractional_sales = [
            ("coin_flip", 0.05),          # Sell half of 0.1 position
            ("black_swan", 3333.333),     # Sell 1/3 with repeating decimal
            ("sun_rises", 0.000005),      # Sell half of tiny position
            ("volatile_stock", 0.0001),   # Sell small fraction
        ]
        
        for market_id, shares_to_sell in fractional_sales:
            # Get position before
            run_data = self.initializer.get_run_info(run_name)
            before_position = None
            for pos in run_data['positions']:
                if pos['market_id'] == market_id:
                    before_position = pos
                    break
            
            if before_position and before_position['num_shares'] >= shares_to_sell:
                success = self.initializer.sell_position(
                    run_name=run_name,
                    market_id=market_id,
                    num_shares=shares_to_sell
                )
                self.assertTrue(success)
                
                # Verify precision
                run_data = self.initializer.get_run_info(run_name)
                after_position = None
                for pos in run_data['positions']:
                    if pos['market_id'] == market_id:
                        after_position = pos
                        break
                
                if after_position:  # Position still exists
                    expected_remaining = before_position['num_shares'] - shares_to_sell
                    self.assertAlmostEqual(after_position['num_shares'], expected_remaining, places=10)
                    print(f"✅ Fractional sale: {market_id} sold {shares_to_sell}, {expected_remaining:.10f} remaining")
        
        # Phase 6: Balance Precision and Extreme Operations
        print("\n--- Phase 6: Balance Precision and Extreme Operations ---")
        
        # Test extremely small balance operations
        micro_operations = [
            (0.01, "Penny addition"),
            (0.001, "Tenth of a cent"),  
            (0.0001, "Hundredth of a cent"),
        ]
        
        for amount, description in micro_operations:
            success = self.initializer.add_balance(
                run_name=run_name,
                amount=amount,
                description=description
            )
            self.assertTrue(success)
            print(f"✅ Micro balance operation: +${amount} ({description})")
        
        # Test extremely large balance operation
        mega_addition = self.initializer.add_balance(
            run_name=run_name,
            amount=1000000.0,  # $1M addition
            description="Mega funding round"
        )
        self.assertTrue(mega_addition)
        print(f"✅ Mega balance operation: +$1,000,000")
        
        # Phase 7: Mass Position Creation with Tiny Amounts
        print("\n--- Phase 7: Mass Tiny Position Creation ---")
        
        # Create many tiny positions to test system limits
        mass_positions = []
        for i in range(20):  # Create 20 tiny positions
            shares = 0.0001 * (i + 1)  # Increasing tiny amounts
            market_id = "coin_flip"  # Use same market to test merging
            
            success = self.initializer.add_position(
                run_name=run_name,
                market_id=market_id,
                num_shares=shares
            )
            self.assertTrue(success)
            mass_positions.append(shares)
        
        # Verify all positions were merged into one
        run_data = self.initializer.get_run_info(run_name)
        coin_flip_positions = [pos for pos in run_data['positions'] if pos['market_id'] == 'coin_flip']
        self.assertEqual(len(coin_flip_positions), 1)  # Should be merged
        
        expected_total_shares = sum(mass_positions) + 0.05  # Previous fractional + new additions
        actual_shares = coin_flip_positions[0]['num_shares']
        self.assertAlmostEqual(actual_shares, expected_total_shares, places=8)
        print(f"✅ Mass tiny positions merged: {actual_shares:.10f} total shares")
        
        # Phase 8: Zero and Negative Edge Cases
        print("\n--- Phase 8: Zero and Negative Edge Cases ---")
        
        # Test zero share operations (should fail)
        zero_position = self.initializer.add_position(
            run_name=run_name,
            market_id="year_ends",
            num_shares=0.0
        )
        self.assertFalse(zero_position)
        print(f"✅ Zero share position properly rejected")
        
        # Test negative share operations (should fail)
        negative_position = self.initializer.add_position(
            run_name=run_name,
            market_id="year_ends", 
            num_shares=-100.0
        )
        self.assertFalse(negative_position)
        print(f"✅ Negative share position properly rejected")
        
        # Test selling zero shares (should fail)
        zero_sell = self.initializer.sell_position(
            run_name=run_name,
            market_id="coin_flip",
            num_shares=0.0
        )
        self.assertFalse(zero_sell)
        print(f"✅ Zero share sale properly rejected")
        
        # Phase 9: Final Edge Case Verification
        print("\n--- Phase 9: Final Edge Case State ---")
        
        final_data = self.initializer.get_run_info(run_name)
        
        # Verify extreme values are handled correctly
        total_positions = len(final_data['positions'])
        total_transactions = len(final_data['transactions'])
        
        # Check for any extreme values in final state
        extreme_values_found = []
        for position in final_data['positions']:
            if position['current_total_price'] > 10000:
                extreme_values_found.append(f"High value: {position['market_id']} = ${position['current_total_price']:,.2f}")
            elif position['current_total_price'] < 0.001:
                extreme_values_found.append(f"Low value: {position['market_id']} = ${position['current_total_price']:.10f}")
            
            if position['num_shares'] > 10000:
                extreme_values_found.append(f"High shares: {position['market_id']} = {position['num_shares']:,.2f}")
            elif position['num_shares'] < 0.001:
                extreme_values_found.append(f"Low shares: {position['market_id']} = {position['num_shares']:.10f}")
        
        print(f"\n🎯 EDGE CASES TEST RESULTS:")
        print(f"{'='*50}")
        print(f"Extreme Markets Created: {len(extreme_markets)}")
        print(f"Final Active Positions: {total_positions}")
        print(f"Total Transactions: {total_transactions}")
        print(f"Current Balance: ${final_data['current_balance']:,.8f}")
        print(f"Market Value: ${final_data['balance_of_shares']:,.8f}")
        print(f"Total Portfolio: ${final_data['total_balance']:,.8f}")
        
        if extreme_values_found:
            print(f"\nExtreme Values Detected:")
            for extreme in extreme_values_found:
                print(f"  {extreme}")
        
        print(f"\n✅ EDGE CASES TEST COMPLETED SUCCESSFULLY!")
        print(f"   System handled extreme scenarios and edge cases")
        print(f"   Fractional precision maintained throughout")
        print(f"   Error conditions properly caught and handled")
        
        # Final assertions to ensure system integrity
        self.assertGreater(total_positions, 0)
        self.assertGreaterEqual(total_transactions, 30)  # Should have many transactions
        self.assertIsInstance(final_data['current_balance'], (int, float))
        self.assertIsInstance(final_data['balance_of_shares'], (int, float))
        self.assertIsInstance(final_data['total_balance'], (int, float))


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2) 