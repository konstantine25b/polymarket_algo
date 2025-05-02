"""
Wallet functionality for checking balances on Polygon (Matic) network.
"""

import os
import logging
from typing import Dict, Optional, Tuple, Any
from web3 import Web3
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

# Import constants
from src.constants import CLOB_API_HOST

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# USDC contract address on Polygon
POLYGON_USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
POLYGON_RPC_URL = "https://polygon-rpc.com"
MATIC_DECIMALS = 18
USDC_DECIMALS = 6

def load_wallet_from_env() -> Tuple[str, str]:
    """
    Load wallet address and private key from environment variables.
    
    Returns:
        tuple: (wallet_address, private_key)
    """
    # Load environment variables if not already loaded
    load_dotenv()
    
    wallet_address = os.getenv("WALLET_ADDRESS")
    private_key = os.getenv("WALLET_PRIVATE_KEY")
    
    if not wallet_address:
        raise ValueError("WALLET_ADDRESS not found in environment variables")
        
    logger.info(f"Loaded wallet: {wallet_address[:6]}...{wallet_address[-4:]}")
    return wallet_address, private_key

def check_wallet_balance(wallet_address: Optional[str] = None) -> Dict[str, Any]:
    """
    Check the balance of MATIC and USDC for a given wallet on Polygon network.
    
    Args:
        wallet_address: Ethereum wallet address to check. If None, uses the address from .env
        
    Returns:
        dict: A dictionary with balance information in the format:
            {
                "wallet": "0x123...abc",
                "matic_balance": 1.234,
                "usdc_balance": 100.0,
                "success": True
            }
    """
    if not wallet_address:
        wallet_address, _ = load_wallet_from_env()
    
    result = {
        "wallet": wallet_address,
        "matic_balance": 0.0,
        "usdc_balance": 0.0,
        "success": False,
        "error": None
    }
    
    try:
        # First try to get USDC balance from CLOB API
        usdc_balance = _get_usdc_balance_from_clob(wallet_address)
        if usdc_balance is not None:
            result["usdc_balance"] = usdc_balance
            result["success"] = True
        
        # Get MATIC balance from RPC
        matic_balance = _get_matic_balance_from_rpc(wallet_address)
        if matic_balance is not None:
            result["matic_balance"] = matic_balance
            result["success"] = True
            
        # If CLOB API didn't work, try to get USDC balance from RPC
        if usdc_balance is None:
            rpc_usdc_balance = _get_usdc_balance_from_rpc(wallet_address)
            if rpc_usdc_balance is not None:
                result["usdc_balance"] = rpc_usdc_balance
                result["success"] = True
                
        # Log results
        if result["success"]:
            logger.info(f"Balance for {wallet_address[:6]}...{wallet_address[-4:]}: "
                        f"{result['matic_balance']:.4f} MATIC, {result['usdc_balance']:.2f} USDC")
        else:
            logger.error(f"Failed to get balance for {wallet_address}")
            
    except Exception as e:
        error_msg = f"Error checking balance: {str(e)}"
        logger.error(error_msg)
        result["error"] = error_msg
    
    return result

def _get_usdc_balance_from_clob(wallet_address: str) -> Optional[float]:
    """Get USDC balance from Polymarket CLOB API."""
    try:
        clob_client = ClobClient(host=CLOB_API_HOST, chain_id=137)  # 137 is for Polygon
        
        # Try balance_allowance first
        try:
            balance_result = clob_client.get_balance_allowance(wallet_address)
            if balance_result and hasattr(balance_result, 'balance'):
                usdc_balance = float(balance_result.balance) / (10 ** USDC_DECIMALS)  # Convert from wei
                return usdc_balance
        except Exception as e:
            logger.debug(f"Error using CLOB get_balance_allowance: {e}")
        
        # Try regular get_balance
        try:
            balance = clob_client.get_balance(wallet_address)
            if balance and hasattr(balance, 'usdc'):
                usdc_balance = float(balance.usdc) / (10 ** USDC_DECIMALS)  # Convert from wei
                return usdc_balance
        except Exception as e:
            logger.debug(f"Error using CLOB get_balance: {e}")
            
        return None
    except Exception as e:
        logger.debug(f"Error connecting to CLOB API: {e}")
        return None

def _get_matic_balance_from_rpc(wallet_address: str) -> Optional[float]:
    """Get MATIC balance using Web3 RPC."""
    try:
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))
        if not w3.is_connected():
            logger.warning("Failed to connect to Polygon RPC")
            return None
            
        balance_wei = w3.eth.get_balance(wallet_address)
        matic_balance = float(balance_wei) / (10 ** MATIC_DECIMALS)
        return matic_balance
    except Exception as e:
        logger.debug(f"Error getting MATIC balance from RPC: {e}")
        return None

def _get_usdc_balance_from_rpc(wallet_address: str) -> Optional[float]:
    """Get USDC balance using Web3 RPC."""
    try:
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))
        if not w3.is_connected():
            logger.warning("Failed to connect to Polygon RPC")
            return None
            
        # USDC token contract ABI for 'balanceOf' function
        abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        # Create contract instance
        usdc_contract = w3.eth.contract(address=POLYGON_USDC_ADDRESS, abi=abi)
        
        # Call balanceOf function
        balance_wei = usdc_contract.functions.balanceOf(wallet_address).call()
        usdc_balance = float(balance_wei) / (10 ** USDC_DECIMALS)
        return usdc_balance
    except Exception as e:
        logger.debug(f"Error getting USDC balance from RPC: {e}")
        return None

if __name__ == "__main__":
    # Simple test to run this file directly
    balance_info = check_wallet_balance()
    print(f"Wallet: {balance_info['wallet']}")
    print(f"MATIC Balance: {balance_info['matic_balance']:.4f} MATIC")
    print(f"USDC Balance: {balance_info['usdc_balance']:.2f} USDC") 