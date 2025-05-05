#!/usr/bin/env python3
"""
Command-line script for executing Polymarket market buy orders.
"""

import sys
import os
from dotenv import load_dotenv
from src.polymarket.bidding import PolymarketClient
from src.polymarket.bidding.buy.market import MarketBuyOrder

def run_market_buy(token_id, amount):
    """
    Execute a market buy order with the given token ID and amount.
    
    Args:
        token_id (str): The token ID to buy
        amount (float): The amount to buy
        
    Returns:
        dict: The response from the order execution
    """
    # Initialize client
    client = PolymarketClient()
    print(f"Connected with wallet: {client.get_wallet_address()}")
    
    # Create and execute market buy order
    market_buy = MarketBuyOrder(client)
    response = market_buy.execute_order(token_id, amount)
    
    return response

def main():
    # Check if token_id and amount are provided as arguments
    if len(sys.argv) < 3:
        print("Usage: python -m src.polymarket.bidding.buy.market.run <token_id> <amount>")
        sys.exit(1)
        
    token_id = sys.argv[1]
    amount = float(sys.argv[2])
    
    try:
        response = run_market_buy(token_id, amount)
        print("Order executed successfully!")
        print(response)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 