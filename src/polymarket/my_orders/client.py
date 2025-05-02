"""
Client module for interacting with Polymarket CLOB API.
"""

import os
import sys
import json
import traceback
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from src.constants import CLOB_API_HOST

# Load environment variables
load_dotenv()

def check_connection(client, wallet_address):
    """
    Explicitly check if the connection to the Polymarket API is working.
    
    Args:
        client (ClobClient): The initialized CLOB client
        wallet_address (str): The wallet address used for this client
        
    Returns:
        tuple: (bool, dict) True if connection is successful and API response data,
               or False and error details if connection failed
        
    Raises:
        Exception: Details about connection failure
    """
    try:
        # Test API connection by making a simple request
        response = client.get_orders()
        
        # Create formatted response data for debugging
        api_data = {
            "status": "success",
            "orders_count": len(response) if response else 0,
            "raw_response": response,
            "user_wallet": wallet_address,
            "host": client.host
        }
        
        # If we get here without exception, connection is working
        return True, api_data
    except Exception as e:
        # Format detailed error info
        error_data = {
            "status": "error",
            "error_message": str(e),
            "host": getattr(client, 'host', CLOB_API_HOST),
            "user_wallet": wallet_address
        }
        
        error_msg = f"Failed to connect to Polymarket API: {str(e)}"
        raise Exception(error_msg, error_data)

def get_clob_client():
    """
    Initialize and return a CLOB client configured with credentials from .env file.
    
    Returns:
        tuple: (ClobClient, str) The initialized CLOB client and the wallet address
        
    Raises:
        ValueError: If required environment variables are missing
        Exception: For connection issues or API errors
    """
    # Get private key and wallet address from .env
    private_key = os.getenv('WALLET_PRIVATE_KEY')
    wallet_address = os.getenv('WALLET_ADDRESS')
    
    if not private_key or not wallet_address:
        raise ValueError("WALLET_PRIVATE_KEY and WALLET_ADDRESS must be set in .env file")
    
    # Ensure private key has 0x prefix
    if not private_key.startswith('0x'):
        private_key = f"0x{private_key}"
    
    # Ensure wallet address has 0x prefix
    if not wallet_address.startswith('0x'):
        wallet_address = f"0x{wallet_address}"
    
    try:
        # Create CLOB client using MetaMask configuration
        client = ClobClient(
            host=CLOB_API_HOST,  # Using host from constants.py
            key=private_key,
            chain_id=POLYGON,  # 137 for Polygon Mainnet
          
        )
        
        # Set API credentials with better error handling
        try:
            api_creds = client.create_or_derive_api_creds()
            if not api_creds:
                raise ValueError("Failed to generate API credentials. Check your private key.")
            print("api_creds", api_creds)
            client.set_api_creds(api_creds)
            
            # Explicitly check connection with our new function
            is_connected, api_data = check_connection(client, wallet_address)
            print("is_connected", is_connected)
            print("api_data", api_data)
            if not is_connected:
                raise ValueError("Failed to authenticate with Polymarket API. Connection check failed.")
                
            # Return both the client and the wallet address
            return client, wallet_address
            
        except Exception as api_error:
            # If error has additional data, extract it
            error_data = getattr(api_error, 'args', [])
            if len(error_data) > 1 and isinstance(error_data[1], dict):
                error_details = json.dumps(error_data[1], indent=2)
                raise ValueError(f"Failed to set API credentials: {str(api_error)}. Details: {error_details}")
            else:
                raise ValueError(f"Failed to set API credentials: {str(api_error)}. Make sure your private key is correct and your wallet has made at least one trade on Polymarket.")
            
    except Exception as e:
        error_details = traceback.format_exc()
        raise Exception(f"Failed to initialize Polymarket CLOB client: {str(e)}\n\nTechnical details: {error_details}") 