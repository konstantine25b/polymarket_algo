"""
Polymarket Client for interacting with the CLOB API.
Handles authentication and order creation.
"""

import os
import time
import random
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
        Configure advanced browser-like headers and session settings to avoid Cloudflare blocks.
        This helps the requests appear more like legitimate browser traffic.
        """
        try:
            # More realistic browser headers with randomization
            user_agents = [
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Linux"',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Origin': 'https://polymarket.com',
                'Referer': 'https://polymarket.com/'
            }
            
            # Try to configure the session
            session = None
            if hasattr(self.client, '_session') and self.client._session:
                session = self.client._session
            elif hasattr(self.client, 'session') and self.client.session:
                session = self.client.session
            
            if session:
                session.headers.update(headers)
                
                # Additional session configuration to mimic browser behavior
                session.cookies.clear()  # Start fresh
                
                # Add some realistic timing
                time.sleep(random.uniform(0.1, 0.5))
                
                print("Successfully configured advanced headers for Cloudflare bypass")
            else:
                print("Warning: Could not access session object for header configuration")
                
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
    
    def _human_like_delay(self):
        """
        Add a small random delay to mimic human behavior and avoid rate limiting.
        """
        delay = random.uniform(0.5, 2.0)  # Random delay between 0.5-2 seconds
        time.sleep(delay)
        
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