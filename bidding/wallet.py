"""
Wallet functionality for Polymarket betting.
Handles authentication, balance checking, and placing bets.
"""

import os
from typing import Dict, Optional, List
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from eth_account import Account
from eth_account.signers.local import LocalAccount
import json
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv
import requests

# Import constants
from src.constants import CLOB_API_HOST

load_dotenv()

USDC_CONTRACT_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    }
]

class PolymarketWallet:
    """Handles wallet operations for Polymarket betting."""
    
    def __init__(self, api_key: str = None, private_key: str = None):
        """
        Initialize the wallet with API key and private key.
        
        Args:
            api_key: Polymarket API key
            private_key: Wallet private key (optional, can be generated)
        """
        self.api_key = api_key or os.getenv('POLYMARKET_API_KEY')
        # API key is optional for wallet operations, so do not raise an error if missing
        # if not self.api_key:
        #     raise ValueError("API key is required. Set POLYMARKET_API_KEY environment variable or pass it to constructor.")
        self.private_key = private_key or os.getenv('POLYMARKET_PRIVATE_KEY')
        
        # Initialize CLOB client with authentication
        self.clob_client = ClobClient(
            host=CLOB_API_HOST,
            chain_id=137,  # Polygon network
            key=self.private_key,
            signature_type=1  # EIP-712
        )
        
        # Initialize account if private key is provided
        self.account = None
        self.wallet_address = None
        if self.private_key:
            self.account = Account.from_key(self.private_key)
            self.wallet_address = self.account.address
        else:
            print("Warning: No private key provided. Wallet address is not set.")
    
    def get_balance(self) -> float:
        """
        Get the current wallet balance in USDC.
        
        Returns:
            float: Balance in USDC
        """
        try:
            if not self.wallet_address:
                print("Error: Wallet address is not set.")
                return 0.0
            # Connect to Polygon RPC
            w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
            contract = w3.eth.contract(address=USDC_CONTRACT_ADDRESS, abi=USDC_ABI)
            balance = contract.functions.balanceOf(self.wallet_address).call()
            # USDC has 6 decimals
            return balance / 1e6
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0.0
    
    def place_bet(self, token_id: str, amount: float, price: float, side: str = "buy") -> Optional[Dict]:
        """
        Place a bet on Polymarket.
        
        Args:
            token_id: The token ID to bet on
            amount: Amount to bet in USDC
            price: Price to bet at (0-1)
            side: "buy" or "sell"
            
        Returns:
            Dictionary with order details if successful, None if failed
        """
        try:
            # Create order arguments
            order_args = OrderArgs(
                token_id=token_id,
                price=str(price),
                size=str(amount),
                side=side,
                order_type=OrderType.LIMIT
            )
            
            # Place the order
            response = self.clob_client.create_order(order_args)
            
            if response and "order_id" in response:
                print(f"Successfully placed {side} order for {amount} USDC at {price*100:.2f}%")
                return response
            else:
                print("Failed to place order")
                return None
                
        except Exception as e:
            print(f"Error placing bet: {e}")
            return None
    
    def get_open_orders(self) -> List[Dict]:
        """
        Get all open orders for the wallet.
        
        Returns:
            List of open orders
        """
        try:
            orders = self.clob_client.get_orders()
            return orders
        except Exception as e:
            print(f"Error getting open orders: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: ID of the order to cancel
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.clob_client.cancel_order(order_id)
            return response.get("success", False)
        except Exception as e:
            print(f"Error canceling order: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """
        Get the status of an order.
        
        Args:
            order_id: ID of the order to check
            
        Returns:
            Dictionary with order status if found, None otherwise
        """
        try:
            orders = self.get_open_orders()
            for order in orders:
                if order.get("order_id") == order_id:
                    return order
            return None
        except Exception as e:
            print(f"Error getting order status: {e}")
            return None
    
    def get_portfolio_cash(self) -> float:
        """
        Get the user's Polymarket portfolio cash balance (as shown in the UI).
        Returns:
            float: Cash balance in USD
        """
        if not self.wallet_address:
            print("Error: Wallet address is not set.")
            return 0.0
        try:
            url = f"https://api.polymarket.com/v4/users/{self.wallet_address}/portfolio"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                cash = data.get('cash', 0.0)
                return float(cash)
            else:
                print(f"Failed to fetch portfolio: {response.status_code}")
                return 0.0
        except Exception as e:
            print(f"Error fetching portfolio cash: {e}")
            return 0.0

    @staticmethod
    def get_portfolio_cash_by_address(address: str) -> float:
        """
        Get the Polymarket portfolio cash balance for any address.
        Args:
            address: The wallet address to query
        Returns:
            float: Cash balance in USD
        """
        try:
            url = f"https://api.polymarket.com/v4/users/{address}/portfolio"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                cash = data.get('cash', 0.0)
                return float(cash)
            else:
                print(f"Failed to fetch portfolio for {address}: {response.status_code}")
                return 0.0
        except Exception as e:
            print(f"Error fetching portfolio cash for {address}: {e}")
            return 0.0 