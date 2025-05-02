"""
Module for retrieving and handling Polymarket orders.
"""

import logging
import json
import traceback
from typing import Dict, List, Any, Optional, Tuple
from .client import get_clob_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_all_orders(return_details: bool = False) -> List[Dict[str, Any]] or Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Retrieve all current orders from Polymarket using the CLOB API.
    
    Args:
        return_details (bool, optional): Whether to return additional details about the API request. 
                                        Defaults to False.
    
    Returns:
        If return_details is False:
            List[Dict[str, Any]]: List of orders from Polymarket
        If return_details is True:
            Tuple[List[Dict[str, Any]], Dict[str, Any]]: Tuple containing list of orders and details dict
        
    Raises:
        Exception: If there's an error retrieving orders
    """
    try:
        logger.info("Connecting to Polymarket CLOB API...")
        client, funder_address = get_clob_client()  # Now unpacking both client and funder_address
        
        logger.info("Retrieving orders...")
        orders = client.get_orders()
        print("orders", orders)
        # Collect additional details about the API request
        request_details = {
            "wallet_address": funder_address,  # Using funder_address directly
            "api_host": client.host,
            "orders_count": len(orders) if orders else 0,
            "chain_id": client.chain_id,
            "raw_response": orders
        }
        print("request_details", request_details)
        
        if orders:
            logger.info(f"Successfully retrieved {len(orders)} orders")
        else:
            logger.info("No orders found for this account")
        
        if return_details:
            return orders, request_details
        return orders
    except Exception as e:
        logger.error(f"Error retrieving orders: {str(e)}")
        error_details = traceback.format_exc()
        logger.debug(f"Error details: {error_details}")
        raise Exception(f"Failed to retrieve orders: {str(e)}")

def get_orders_by_status(status: str, return_details: bool = False) -> List[Dict[str, Any]] or Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Retrieve orders filtered by status.
    
    Args:
        status (str): Order status to filter by (e.g., 'open', 'filled', 'canceled')
        return_details (bool, optional): Whether to return additional details. Defaults to False.
    
    Returns:
        If return_details is False:
            List[Dict[str, Any]]: List of filtered orders
        If return_details is True:
            Tuple[List[Dict[str, Any]], Dict[str, Any]]: Tuple containing filtered orders and details dict
        
    Raises:
        Exception: If there's an error retrieving or filtering orders
    """
    try:
        if return_details:
            all_orders, details = get_all_orders(return_details=True)
        else:
            all_orders = get_all_orders()
            
        filtered_orders = [order for order in all_orders if order.get('status', '').lower() == status.lower()]
        logger.info(f"Filtered {len(filtered_orders)} orders with status '{status}'")
        
        if return_details:
            details["filtered_count"] = len(filtered_orders)
            details["filter_type"] = "status"
            details["filter_value"] = status
            return filtered_orders, details
        return filtered_orders
    except Exception as e:
        logger.error(f"Error filtering orders by status '{status}': {str(e)}")
        raise Exception(f"Failed to filter orders by status: {str(e)}")

def get_orders_by_market(market_id: str, return_details: bool = False) -> List[Dict[str, Any]] or Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Retrieve orders filtered by market ID.
    
    Args:
        market_id (str): Market ID to filter by
        return_details (bool, optional): Whether to return additional details. Defaults to False.
    
    Returns:
        If return_details is False:
            List[Dict[str, Any]]: List of filtered orders for the specified market
        If return_details is True:
            Tuple[List[Dict[str, Any]], Dict[str, Any]]: Tuple containing filtered orders and details dict
        
    Raises:
        Exception: If there's an error retrieving or filtering orders
    """
    try:
        if return_details:
            all_orders, details = get_all_orders(return_details=True)
        else:
            all_orders = get_all_orders()
            
        filtered_orders = [order for order in all_orders if order.get('marketId') == market_id]
        logger.info(f"Filtered {len(filtered_orders)} orders for market '{market_id}'")
        
        if return_details:
            details["filtered_count"] = len(filtered_orders)
            details["filter_type"] = "market"
            details["filter_value"] = market_id
            return filtered_orders, details
        return filtered_orders
    except Exception as e:
        logger.error(f"Error filtering orders by market '{market_id}': {str(e)}")
        raise Exception(f"Failed to filter orders by market: {str(e)}")

def get_orders_by_side(side: str, return_details: bool = False) -> List[Dict[str, Any]] or Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Retrieve orders filtered by side (buy or sell).
    
    Args:
        side (str): Order side to filter by ('buy' or 'sell')
        return_details (bool, optional): Whether to return additional details. Defaults to False.
    
    Returns:
        If return_details is False:
            List[Dict[str, Any]]: List of filtered orders for the specified side
        If return_details is True:
            Tuple[List[Dict[str, Any]], Dict[str, Any]]: Tuple containing filtered orders and details dict
        
    Raises:
        ValueError: If side is not 'buy' or 'sell'
        Exception: If there's an error retrieving or filtering orders
    """
    side = side.lower()
    if side not in ['buy', 'sell']:
        logger.error(f"Invalid side value: '{side}'. Must be 'buy' or 'sell'")
        raise ValueError("Side must be either 'buy' or 'sell'")
    
    try:
        if return_details:
            all_orders, details = get_all_orders(return_details=True)
        else:
            all_orders = get_all_orders()
            
        filtered_orders = [order for order in all_orders if order.get('side', '').lower() == side]
        logger.info(f"Filtered {len(filtered_orders)} '{side}' orders")
        
        if return_details:
            details["filtered_count"] = len(filtered_orders)
            details["filter_type"] = "side"
            details["filter_value"] = side
            return filtered_orders, details
        return filtered_orders
    except Exception as e:
        logger.error(f"Error filtering orders by side '{side}': {str(e)}")
        raise Exception(f"Failed to filter orders by side: {str(e)}") 