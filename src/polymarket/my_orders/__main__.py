"""
Main entry point for the my_orders module when run directly.
Usage: python -m src.polymarket.my_orders
"""

import os
import sys
import json
import logging
import traceback
from .orders import get_all_orders
from .client import get_clob_client, check_connection
from src.constants import MARKET_ID

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if required environment variables are set."""
    missing_vars = []
    if not os.getenv('WALLET_ADDRESS'):
        missing_vars.append('WALLET_ADDRESS')
    if not os.getenv('WALLET_PRIVATE_KEY'):
        missing_vars.append('WALLET_PRIVATE_KEY')
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        print(f"ERROR: The following required environment variables are not set: {', '.join(missing_vars)}")
        print("Please check your .env file and make sure these variables are defined.")
        return False
    return True

def verify_api_connection():
    """
    Explicitly verify connection to the Polymarket API.
    
    Returns:
        tuple: (bool, dict or str) True and API data if connection is successful,
               or False and error message if connection failed
    """
    try:
        # Get client and wallet address
        client, wallet_address = get_clob_client()
        # Pass wallet_address to check_connection
        is_connected, api_data = check_connection(client, wallet_address)
        logger.info("Polymarket API connection successful")
        return True, api_data
    except Exception as e:
        # Get detailed error information if available
        error_info = getattr(e, 'args', [])
        if len(error_info) > 1 and isinstance(error_info[1], dict):
            error_data = error_info[1]
        else:
            error_data = {"error_message": str(e)}
        
        logger.error(f"API connection failed: {str(e)}")
        return False, error_data

def display_api_info(details, verbose=False):
    """
    Display API connection and response information.
    
    Args:
        details (dict): API response details
        verbose (bool): Whether to show verbose output
    """
    print("\nPolymarket API Information:")
    print(f"  Wallet Address: {details.get('wallet_address', 'unknown')}")
    print(f"  API Host: {details.get('api_host', 'unknown')}")
    print(f"  Chain ID: {details.get('chain_id', 'unknown')}")
    print(f"  Orders Count: {details.get('orders_count', 0)}")
    
    if verbose and "raw_response" in details:
        print("\nRaw API Response:")
        if isinstance(details["raw_response"], list):
            print(f"  [List with {len(details['raw_response'])} items]")
            if len(details["raw_response"]) > 0:
                print(json.dumps(details["raw_response"][0], indent=2))
                if len(details["raw_response"]) > 1:
                    print(f"  ... and {len(details['raw_response'])-1} more items")
        else:
            print(json.dumps(details["raw_response"], indent=2))

def main():
    """Display all orders from Polymarket."""
    show_verbose = "--verbose" in sys.argv or "--debug" in sys.argv
    show_debug = "--debug" in sys.argv
    
    # Show header
    print("\n===== POLYMARKET ORDERS =====\n")
    
    # Verify environment variables first
    if not check_environment():
        sys.exit(1)
    
    # First, explicitly verify API connection and show status
    connection_ok, api_data = verify_api_connection()
    if not connection_ok:
        print("ERROR: Cannot connect to Polymarket API")
        if isinstance(api_data, dict):
            print(f"Reason: {api_data.get('error_message', 'Unknown error')}")
            print("\nAPI Connection Details:")
            print(f"  Host: {api_data.get('host', 'unknown')}")
            print(f"  Wallet: {api_data.get('user_wallet', 'unknown')}")
        else:
            print(f"Reason: {api_data}")
            
        print("\nPossible solutions:")
        print("1. Verify your WALLET_ADDRESS and WALLET_PRIVATE_KEY in the .env file")
        print("2. Check your internet connection")
        print("3. Make sure you have completed at least one trade on Polymarket")
        print("4. Ensure your wallet has proper allowances set on Polymarket")
        sys.exit(1)
    
    # Show API connection details
    print("✅ Connected to Polymarket API successfully")
    if show_verbose:
        print("\nAPI Connection Details:")
        print(f"  Host: {api_data.get('host', 'unknown')}")
        print(f"  Wallet: {api_data.get('user_wallet', 'unknown')}")
        print(f"  Orders Count: {api_data.get('orders_count', 0)}")
        
        if show_debug:
            print("\nRaw API Response:")
            print(json.dumps(api_data.get('raw_response', {}), indent=2))
    
    try:
        logger.info("Retrieving orders from Polymarket...")
        # Get orders with detailed response
        orders, details = get_all_orders(return_details=True)
        
        print(f"Found {len(orders)} orders:")
        
        # Display API details if verbose mode
        if show_verbose:
            display_api_info(details, verbose=show_debug)
        
        if not orders:
            print("No orders found for your account.")
            print("\nPossible reasons:")
            print("1. You haven't placed any orders on Polymarket")
            print("2. All your orders have been filled or canceled")
            print("3. The wallet address in your .env file doesn't match your Polymarket account")
            
            # Display wallet info for verification
            wallet = details.get('wallet_address', 'unknown')
            print(f"\nCurrent wallet address: {wallet}")
            print("Verify this matches the wallet you use on Polymarket.")
            
            return
            
        for order in orders:
            print(f"Order ID: {order.get('orderId')}")
            print(f"  Market: {order.get('marketId')}")
            print(f"  Side: {order.get('side')}")
            print(f"  Status: {order.get('status')}")
            print(f"  Price: {order.get('price')}")
            print(f"  Size: {order.get('size')}")
            print("="*50)
    
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error retrieving orders: {str(e)}")
        logger.debug(f"Error details: {error_details}")
        
        print(f"ERROR: Failed to retrieve orders: {str(e)}")
        print("\nPossible solutions:")
        print("1. Verify your WALLET_ADDRESS and WALLET_PRIVATE_KEY in the .env file")
        print("2. Check your internet connection")
        print("3. Make sure you have completed at least one trade on Polymarket")
        print("4. Ensure your wallet has proper allowances set on Polymarket")
        
        if show_debug:
            print("\nDetailed error information:")
            print(error_details)
            
        sys.exit(1)

if __name__ == "__main__":
    main() 