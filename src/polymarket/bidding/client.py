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
        
        # Add browser-like headers to avoid Cloudflare blocks
        self._configure_headers()
        
        # Set up API credentials
        self._setup_api_credentials()
    
    def _configure_headers(self):
        """
        Configure browser-like headers to avoid Cloudflare blocks.
        This helps the requests appear more like legitimate browser traffic.
        """
        try:
            # Add browser-like headers to the client's session
            if hasattr(self.client, '_session') and self.client._session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
                self.client._session.headers.update(headers)
            elif hasattr(self.client, 'session') and self.client.session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
                self.client.session.headers.update(headers)
        except Exception as e:
            # If header configuration fails, continue anyway - it's not critical
            print(f"Warning: Could not configure headers: {e}")
    
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