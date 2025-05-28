"""
Get Prices Module
----------------

Simple module for fetching prices from Polymarket order book data.
"""

import subprocess
import json
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams
from py_clob_client.exceptions import PolyApiException


def get_prices():
    """
    Get prices for all active markets.
    
    Returns:
        dict: Market data with prices and names, keyed by token_id
        Format: {
            token_id: {
                "question": "Market question",
                "BUY": price,
                "SELL": price
            }
        }
    """
    try:
        # Get current market data from order book system
        cmd = ["python", "-m", "src.polymarket.order_book.show_market_status", "--json", "--refresh"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the JSON output
        try:
            market_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            # Try to extract JSON part if there's extra text
            stdout = result.stdout
            json_start = stdout.find('{')
            json_end = stdout.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                json_str = stdout[json_start:json_end+1]
                market_data = json.loads(json_str)
            else:
                print("Failed to parse market data JSON")
                return None
        
        # Extract market info and get prices
        markets = market_data.get('markets', {})
        if not markets:
            print("No markets found")
            return None
        
        # Get prices for all tokens
        client = ClobClient("https://clob.polymarket.com")
        all_prices = {}
        
        for market_id, market_info in markets.items():
            token_id = market_info.get('token_id')
            question = market_info.get('original_question', 'Unknown Market')
            
            if not token_id:
                continue
            
            try:
                # Get BUY and SELL prices
                token_params = [
                    BookParams(token_id=token_id, side="BUY"),
                    BookParams(token_id=token_id, side="SELL"),
                ]
                
                prices = client.get_prices(params=token_params)
                
                if prices and token_id in prices:
                    price_data = prices[token_id]
                    all_prices[token_id] = {
                        "question": question,
                        "market_id": market_id,
                        "BUY": price_data.get('BUY'),
                        "SELL": price_data.get('SELL')
                    }
                    
            except Exception as e:
                print(f"Error getting prices for {market_id}: {e}")
                continue
        
        return all_prices
        
    except subprocess.CalledProcessError as e:
        print(f"Error running order book command: {e}")
        return None
    except Exception as e:
        print(f"Error getting prices: {e}")
        return None


def get_price(token_id):
    """
    Get price for a specific token ID.
    
    Args:
        token_id (str): The token ID to get prices for
    
    Returns:
        dict: Market data with prices and name
        Format: {
            "question": "Market question",
            "market_id": "market_id", 
            "BUY": price,
            "SELL": price
        }
    """
    try:
        all_prices = get_prices()
        if all_prices and token_id in all_prices:
            return all_prices[token_id]
        else:
            print(f"Token ID {token_id} not found")
            return None
            
    except Exception as e:
        print(f"Error getting price for token {token_id}: {e}")
        return None


def main():
    """Main function to demonstrate price fetching."""
    print("=== Polymarket Price Fetching ===\n")
    
    # Get all market prices
    print("Fetching all market prices...")
    all_prices = get_prices()
    
    if all_prices:
        print(f"✅ Found {len(all_prices)} active markets:\n")
        
        for token_id, data in all_prices.items():
            question = data.get('question', 'Unknown')
            market_id = data.get('market_id', 'Unknown')
            buy_price = data.get('BUY', 'N/A')
            sell_price = data.get('SELL', 'N/A')
            
            # Format prices
            try:
                buy_str = f"${float(buy_price):.3f}" if buy_price != 'N/A' and buy_price is not None else 'N/A'
                sell_str = f"${float(sell_price):.3f}" if sell_price != 'N/A' and sell_price is not None else 'N/A'
            except (ValueError, TypeError):
                buy_str = 'N/A'
                sell_str = 'N/A'
            
            print(f"{token_id} - {question}")
            print(f"     Market ID: {market_id}")
            print(f"     BUY: {buy_str}, SELL: {sell_str}")
            print()
    else:
        print("❌ Failed to fetch market prices")
    
    print("💡 Use get_prices() for all active markets")
    print("💡 Use get_price(token_id) for a specific market")


if __name__ == "__main__":
    main() 