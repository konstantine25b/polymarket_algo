"""
Get Single Market Price CLI
--------------------------

Command line interface for fetching a specific market price by ID.
"""

import sys
from .get_prices import get_price


def main():
    """Main CLI function for getting a single market price."""
    if len(sys.argv) != 2:
        print("Usage: python -m src.polymarket.order_book.get_price <token_id>")
        print("\nExample:")
        print("python -m src.polymarket.order_book.get_price '47979392807610373586249777498703710597487450905720498331079563053270702791739'")
        return
    
    token_id = sys.argv[1]
    
    print(f"Getting price for token: {token_id}")
    
    result = get_price(token_id)
    
    if result:
        question = result.get('question', 'Unknown')
        market_id = result.get('market_id', 'Unknown')
        buy_price = result.get('BUY', 'N/A')
        sell_price = result.get('SELL', 'N/A')
        
        # Format prices
        try:
            buy_str = f"${float(buy_price):.3f}" if buy_price != 'N/A' and buy_price is not None else 'N/A'
            sell_str = f"${float(sell_price):.3f}" if sell_price != 'N/A' and sell_price is not None else 'N/A'
        except (ValueError, TypeError):
            buy_str = 'N/A'
            sell_str = 'N/A'
        
        print(f"✅ Market: {question}")
        print(f"   Market ID: {market_id}")
        print(f"   BUY: {buy_str}, SELL: {sell_str}")
    else:
        print(f"❌ Token ID '{token_id}' not found")
        print("\n💡 Use 'python -m src.polymarket.order_book.get_prices' to see all available tokens")


if __name__ == "__main__":
    main() 