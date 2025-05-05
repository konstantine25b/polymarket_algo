"""
Polymarket Client for interacting with the CLOB API.
Handles authentication and order creation.
"""

import os
from dotenv import load_dotenv
from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, TradeParams, MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

class PolymarketClient:
    """
    Client for interacting with the Polymarket CLOB API.
    Handles authentication, order creation, and API credentials.
    """
    
    def __init__(self, private_key=None, host="https://clob.polymarket.com", chain_id=POLYGON):
        """
        Initialize the Polymarket client.
        
        Args:
            private_key (str, optional): Wallet private key. If None, will try to load from env.
            host (str): API host URL.
            chain_id: Chain ID to use (default: POLYGON).
        """
        # Load environment variables if needed
        if private_key is None:
            load_dotenv()
            private_key = os.getenv("WALLET_PRIVATE_KEY")
            
        if not private_key:
            raise ValueError("No private key provided and WALLET_PRIVATE_KEY not found in environment")
        
        self.host = host
        self.chain_id = chain_id
        self.private_key = private_key
        
        # Initialize the CLOB client
        self.client = ClobClient(host, key=private_key, chain_id=chain_id)
        
        # Set up API credentials
        self._setup_api_credentials()
    
    def _setup_api_credentials(self):
        """
        Create or derive API credentials and set them on the client.
        """
        try:
            api_creds = self.client.create_or_derive_api_creds()
            self.client.set_api_creds(api_creds)
        except Exception as e:
            raise ConnectionError(f"Failed to set up API credentials: {e}")
    
    def get_wallet_address(self):
        """
        Get the wallet address associated with this client.
        
        Returns:
            str: Wallet address
        """
        return self.client.get_address()
        
    def get_trades(self, maker_address=None):
        """
        Get trades for a specific maker address.
        
        Args:
            maker_address (str, optional): Maker address to filter by. 
                                          If None, uses the client's address.
        
        Returns:
            dict: Trade information
        """
        if maker_address is None:
            maker_address = self.client.get_address()
            
        params = TradeParams(maker_address=maker_address)
        return self.client.get_trades(params) 