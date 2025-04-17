# src/polymarket/clob_utils.py

import json
import requests
import time
from typing import List, Dict, Any, Optional, Tuple, Union
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams

# --- Configuration ---
CLOB_API_HOST = "https://clob.polymarket.com"
POLYMARKET_API_HOST = "https://polymarket.com/api"

class ClobUtils:
    """Utility functions for working with the Polymarket CLOB API."""
    
    def __init__(self, host: str = CLOB_API_HOST, chain_id: int = 137):
        """
        Initialize the ClobUtils.
        
        Args:
            host: The CLOB API host URL
            chain_id: The blockchain chain ID (137 for Polygon)
        """
        self.client = ClobClient(host=host, chain_id=chain_id)
    
    def get_sampling_markets(self, next_cursor: str = "") -> Dict[str, Any]:
        """
        Get available CLOB markets that have rewards enabled.
        
        Args:
            next_cursor: Pagination cursor ('' for beginning, 'LTE=' for the end)
            
        Returns:
            Dictionary containing market data with reward information
        """
        try:
            response = self.client.get_sampling_markets(next_cursor=next_cursor)
            return response
        except Exception as e:
            print(f"Error fetching sampling markets: {e}")
            return {"data": [], "next_cursor": "", "limit": 0, "count": 0}
    
    def get_simplified_markets(self, next_cursor: str = "") -> Dict[str, Any]:
        """
        Get available CLOB markets in a reduced schema.
        
        Args:
            next_cursor: Pagination cursor ('' for beginning, 'LTE=' for the end)
            
        Returns:
            Dictionary containing simplified market data
        """
        try:
            response = self.client.get_simplified_markets(next_cursor=next_cursor)
            return response
        except Exception as e:
            print(f"Error fetching simplified markets: {e}")
            return {"data": [], "next_cursor": "", "limit": 0, "count": 0}
    
    def get_sampling_simplified_markets(self, next_cursor: str = "") -> Dict[str, Any]:
        """
        Get available CLOB markets with rewards in a reduced schema.
        
        Args:
            next_cursor: Pagination cursor ('' for beginning, 'LTE=' for the end)
            
        Returns:
            Dictionary containing simplified market data with reward information
        """
        try:
            response = self.client.get_sampling_simplified_markets(next_cursor=next_cursor)
            return response
        except Exception as e:
            print(f"Error fetching sampling simplified markets: {e}")
            return {"data": [], "next_cursor": "", "limit": 0, "count": 0}
    
    def get_market(self, condition_id: str) -> Dict[str, Any]:
        """
        Get a single CLOB market by condition ID.
        
        Args:
            condition_id: The condition ID of the market
            
        Returns:
            Dictionary containing market information
        """
        try:
            response = self.client.get_market(condition_id=condition_id)
            return response
        except Exception as e:
            print(f"Error fetching market {condition_id}: {e}")
            return {}
    
    def get_order_book(self, token_id: str) -> Dict[str, Any]:
        """
        Get order book for a specific token.
        
        Args:
            token_id: The token ID to get the order book for
            
        Returns:
            Dictionary containing order book information
        """
        try:
            response = self.client.get_order_book(token_id)
            return response
        except Exception as e:
            print(f"Error fetching order book for token {token_id}: {e}")
            return {}
    
    def get_order_book_direct(self, token_id: str) -> Dict[str, Any]:
        """
        Get order book using direct API call (not through py_clob_client).
        
        Args:
            token_id: The token ID to get the order book for
            
        Returns:
            Dictionary containing order book information
        """
        try:
            url = f"{CLOB_API_HOST}/book?token_id={token_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching order book directly for token {token_id}: {e}")
            return {}
    
    def get_order_books(self, token_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get order books for multiple tokens.
        
        Args:
            token_ids: List of token IDs to get order books for
            
        Returns:
            List of dictionaries containing order book information
        """
        params = [BookParams(token_id=tid) for tid in token_ids]
        try:
            response = self.client.get_order_books(params=params)
            return response
        except Exception as e:
            print(f"Error fetching order books: {e}")
            return []
    
    def get_price(self, token_id: str, side: str) -> float:
        """
        Get the price for a market (best bid or best ask).
        
        Args:
            token_id: The token ID to get the price for
            side: Either 'buy' or 'sell'
            
        Returns:
            The price as a float
        """
        try:
            response = self.client.get_price(token_id=token_id, side=side)
            price_str = response.get("price", "0")
            return float(price_str)
        except Exception as e:
            print(f"Error fetching price for token {token_id}, side {side}: {e}")
            return 0.0
    
    def get_price_direct(self, token_id: str, side: str) -> float:
        """
        Get price using direct API call (not through py_clob_client).
        
        Args:
            token_id: The token ID to get the price for
            side: 'buy' or 'sell'
            
        Returns:
            The price as a float
        """
        try:
            url = f"{CLOB_API_HOST}/price?token_id={token_id}&side={side.lower()}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data.get("price", "0"))
        except Exception as e:
            print(f"Error fetching price directly for token {token_id}, side {side}: {e}")
            return 0.0
    
    def get_prices(self, token_ids: List[str], sides: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Get prices for multiple tokens and sides.
        
        Args:
            token_ids: List of token IDs to get prices for
            sides: List of sides ("BUY" or "SELL") corresponding to each token ID
            
        Returns:
            Dictionary mapping token IDs to dictionaries of side:price pairs
        """
        if len(token_ids) != len(sides):
            print("Error: token_ids and sides must have the same length")
            return {}
        
        params = [BookParams(token_id=tid, side=side) for tid, side in zip(token_ids, sides)]
        try:
            response = self.client.get_prices(params=params)
            
            # Convert string prices to floats
            result = {}
            for token_id, side_prices in response.items():
                result[token_id] = {}
                for side, price_str in side_prices.items():
                    result[token_id][side] = float(price_str)
            
            return result
        except Exception as e:
            print(f"Error fetching prices: {e}")
            return {}
    
    def get_midpoint(self, token_id: str) -> float:
        """
        Get the midpoint price for a market.
        
        Args:
            token_id: The token ID to get the midpoint for
            
        Returns:
            The midpoint price as a float
        """
        try:
            response = self.client.get_midpoint(token_id)
            mid_str = response.get("mid", "0.5")
            return float(mid_str)
        except Exception as e:
            print(f"Error fetching midpoint for token {token_id}: {e}")
            # Try fallback method using buy and sell prices
            try:
                buy_price = self.get_price_direct(token_id, "buy")
                sell_price = self.get_price_direct(token_id, "sell")
                
                if buy_price > 0 and sell_price > 0:
                    return (buy_price + sell_price) / 2
                return 0.5
            except Exception as e2:
                print(f"Fallback midpoint calculation also failed: {e2}")
                return 0.5
    
    def get_midpoint_direct(self, token_id: str) -> float:
        """
        Get midpoint using direct API call (not through py_clob_client).
        
        Args:
            token_id: The token ID to get the midpoint for
            
        Returns:
            The midpoint price as a float
        """
        try:
            url = f"{CLOB_API_HOST}/midpoint?token_id={token_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data.get("mid", "0.5"))
        except Exception as e:
            print(f"Error fetching midpoint directly for token {token_id}: {e}")
            return 0.5
    
    def get_midpoints(self, token_ids: List[str]) -> Dict[str, float]:
        """
        Get midpoint prices for multiple tokens.
        
        Args:
            token_ids: List of token IDs to get midpoints for
            
        Returns:
            Dictionary mapping token IDs to midpoint prices
        """
        params = [BookParams(token_id=tid) for tid in token_ids]
        try:
            response = self.client.get_midpoints(params=params)
            
            # Convert string midpoints to floats
            result = {}
            for token_id, mid_str in response.items():
                try:
                    result[token_id] = float(mid_str)
                except (ValueError, TypeError):
                    result[token_id] = 0.5
            
            return result
        except Exception as e:
            print(f"Error fetching midpoints: {e}")
            return {}
    
    def get_spread(self, token_id: str) -> Dict[str, Any]:
        """
        Get the spread for a market.
        
        Args:
            token_id: The token ID to get the spread for
            
        Returns:
            Dictionary containing spread information
        """
        try:
            response = self.client.get_spread(token_id)
            return response
        except Exception as e:
            print(f"Error fetching spread for token {token_id}: {e}")
            # Try to calculate spread from buy and sell prices
            try:
                buy_price = self.get_price_direct(token_id, "buy")
                sell_price = self.get_price_direct(token_id, "sell")
                
                if buy_price > 0 and sell_price > 0:
                    spread = sell_price - buy_price
                    return {"spread": str(spread)}
                return {}
            except Exception as e2:
                print(f"Fallback spread calculation also failed: {e2}")
                return {}
    
    def fetch_polymarket_markets(self) -> List[Dict[str, Any]]:
        """
        Fetch markets from Polymarket API (instead of CLOB API).
        
        Returns:
            List of markets with token IDs
        """
        try:
            url = f"{POLYMARKET_API_HOST}/markets"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            markets = data.get("data", [])
            print(f"Fetched {len(markets)} markets from Polymarket API")
            
            # Extract relevant market info
            result = []
            for market in markets:
                market_data = {
                    "condition_id": market.get("id", ""),
                    "question": market.get("question", ""),
                    "tokens": []
                }
                
                # Extract YES and NO outcomes
                outcomes = market.get("outcomes", [])
                for outcome in outcomes:
                    token_data = {
                        "token_id": outcome.get("ctf_token_id", ""),
                        "outcome": outcome.get("value", "")
                    }
                    market_data["tokens"].append(token_data)
                
                if market_data["tokens"]:
                    result.append(market_data)
            
            return result
            
        except Exception as e:
            print(f"Error fetching markets from Polymarket API: {e}")
            return []
    
    def fetch_all_markets(self) -> List[Dict[str, Any]]:
        """
        Fetch all available markets using pagination.
        
        Returns:
            List of all markets
        """
        # First try to get markets from simplified markets endpoint
        all_markets = []
        next_cursor = ""
        
        try:
            print("Attempting to fetch markets from CLOB API...")
            for attempt in range(3):  # Try up to 3 times
                response = self.get_simplified_markets(next_cursor)
                
                if not response or "data" not in response:
                    print(f"Invalid response from simplified_markets (attempt {attempt+1}/3)")
                    time.sleep(1)
                    continue
                
                # Add markets to the result list
                markets = response.get("data", [])
                if markets:
                    all_markets.extend(markets)
                
                # Check if we've reached the end
                next_cursor = response.get("next_cursor", "LTE=")
                if next_cursor == "LTE=" or not markets:
                    break
            
            if all_markets:
                print(f"Successfully fetched {len(all_markets)} markets from CLOB API")
                return all_markets
        except Exception as e:
            print(f"Error with CLOB API call: {e}")
        
        # If CLOB API fails, fall back to Polymarket API
        print("CLOB API didn't return valid markets. Falling back to Polymarket API...")
        poly_markets = self.fetch_polymarket_markets()
        
        if poly_markets:
            return poly_markets
        
        # If both methods fail, return some sample data for testing
        print("WARNING: Unable to fetch real market data. Using sample data for testing.")
        return self._get_sample_markets()
    
    def _get_sample_markets(self) -> List[Dict[str, Any]]:
        """
        Get sample market data for testing when API calls fail.
        
        Returns:
            List of sample markets
        """
        return [
            {
                "condition_id": "sample_condition_1",
                "tokens": [
                    {
                        "token_id": "sample_token_yes_1",
                        "outcome": "YES"
                    },
                    {
                        "token_id": "sample_token_no_1",
                        "outcome": "NO"
                    }
                ]
            },
            {
                "condition_id": "sample_condition_2",
                "tokens": [
                    {
                        "token_id": "sample_token_yes_2",
                        "outcome": "YES"
                    },
                    {
                        "token_id": "sample_token_no_2",
                        "outcome": "NO"
                    }
                ]
            }
        ]
    
    def fetch_all_rewarded_markets(self) -> List[Dict[str, Any]]:
        """
        Fetch all markets with rewards using pagination.
        
        Returns:
            List of all markets with rewards
        """
        all_markets = []
        next_cursor = ""
        
        try:
            for attempt in range(3):  # Try up to 3 times
                response = self.get_sampling_simplified_markets(next_cursor)
                
                if not response or "data" not in response:
                    print(f"Invalid response from sampling_simplified_markets (attempt {attempt+1}/3)")
                    time.sleep(1)
                    continue
                
                # Add markets to the result list
                markets = response.get("data", [])
                if markets:
                    all_markets.extend(markets)
                
                # Check if we've reached the end
                next_cursor = response.get("next_cursor", "LTE=")
                if next_cursor == "LTE=" or not markets:
                    break
        except Exception as e:
            print(f"Error fetching rewarded markets: {e}")
        
        if not all_markets:
            print("WARNING: Unable to fetch rewarded markets. Using sample data for testing.")
            return self._get_sample_markets()
        
        return all_markets
    
    def format_order_book(self, order_book: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format raw order book data into a standardized format.
        
        Args:
            order_book: Raw order book data from the API
            
        Returns:
            Formatted order book data
        """
        if not order_book:
            return {"buy_orders": [], "sell_orders": [], "is_synthetic": True}
        
        formatted = {
            "market": order_book.get("market", ""),
            "asset_id": order_book.get("asset_id", ""),
            "timestamp": order_book.get("timestamp", ""),
            "buy_orders": [],
            "sell_orders": [],
            "is_synthetic": False
        }
        
        # Format bids (buy orders)
        for bid in order_book.get("bids", []):
            try:
                price = float(bid.get("price", 0))
                size = float(bid.get("size", 0))
                
                formatted["buy_orders"].append({
                    "price": price * 100,  # Convert to percentage
                    "size": size,
                    "total": price * size  # Total in dollars
                })
            except (ValueError, TypeError) as e:
                print(f"Error parsing bid: {e}")
                continue
        
        # Format asks (sell orders)
        for ask in order_book.get("asks", []):
            try:
                price = float(ask.get("price", 0))
                size = float(ask.get("size", 0))
                
                formatted["sell_orders"].append({
                    "price": price * 100,  # Convert to percentage
                    "size": size,
                    "total": price * size  # Total in dollars
                })
            except (ValueError, TypeError) as e:
                print(f"Error parsing ask: {e}")
                continue
        
        # If no orders were successfully parsed, mark as synthetic
        if not formatted["buy_orders"] and not formatted["sell_orders"]:
            formatted["is_synthetic"] = True
        
        # Sort orders (buy highest to lowest, sell lowest to highest)
        formatted["buy_orders"].sort(key=lambda x: x["price"], reverse=True)
        formatted["sell_orders"].sort(key=lambda x: x["price"])
        
        return formatted
    
    def extract_tokens_from_markets(self, markets: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """
        Extract token pairs from simplified market data.
        
        Args:
            markets: List of simplified market data
            
        Returns:
            Dictionary mapping condition IDs to dictionaries of token information
        """
        if not markets:
            print("No markets provided to extract_tokens_from_markets")
            return {}
        
        tokens = {}
        
        for market in markets:
            condition_id = market.get("condition_id", "")
            market_tokens = market.get("tokens", [])
            
            if not condition_id:
                continue
                
            if not market_tokens:
                print(f"No tokens found for market {condition_id}")
                continue
            
            # Handle different API response formats
            if len(market_tokens) < 2:
                print(f"Insufficient tokens for market {condition_id}")
                continue
            
            yes_token = None
            no_token = None
            
            # Find YES and NO tokens
            for token in market_tokens:
                outcome = token.get("outcome", "").upper()
                if outcome == "YES":
                    yes_token = token
                elif outcome == "NO":
                    no_token = token
            
            if not yes_token or not no_token:
                # Try alternative format (ctf_token_id)
                for token in market_tokens:
                    outcome = token.get("value", "").upper()
                    if outcome == "YES":
                        yes_token = {
                            "token_id": token.get("ctf_token_id", ""),
                            "outcome": "YES"
                        }
                    elif outcome == "NO":
                        no_token = {
                            "token_id": token.get("ctf_token_id", ""),
                            "outcome": "NO"
                        }
            
            if yes_token and no_token:
                yes_token_id = yes_token.get("token_id", "")
                no_token_id = no_token.get("token_id", "")
                
                if yes_token_id and no_token_id:
                    tokens[condition_id] = {
                        "yes_token_id": yes_token_id,
                        "no_token_id": no_token_id,
                        "yes_outcome": yes_token.get("outcome", "YES"),
                        "no_outcome": no_token.get("outcome", "NO")
                    }
        
        if not tokens:
            print("Failed to extract any valid token pairs from markets")
        else:
            print(f"Successfully extracted {len(tokens)} token pairs")
            
        return tokens
        
    def generate_synthetic_order_book(self, token_id: str, midpoint: float = 0.5) -> Dict[str, Any]:
        """
        Generate synthetic order book data based on a midpoint price.
        
        Args:
            token_id: The token ID (for reference)
            midpoint: The midpoint price (0-1)
            
        Returns:
            Synthetic order book data
        """
        spread_percentage = 0.05  # 5% spread
        
        # Generate synthetic buy orders (below midpoint)
        synthetic_buy_orders = []
        for i in range(5):
            # Calculate price with decreasing values (higher index = lower price)
            price_factor = 1.0 - spread_percentage - (i * 0.01)
            buy_price = midpoint * price_factor
            
            # Size decreases as we move away from the midpoint
            size = 100 - (i * 15)
            
            if buy_price > 0:
                synthetic_buy_orders.append({
                    "price": round(buy_price * 100, 1),  # Convert to percentage points
                    "size": size,
                    "total": round(buy_price * size, 2)
                })
        
        # Generate synthetic sell orders (above midpoint)
        synthetic_sell_orders = []
        for i in range(5):
            # Calculate price with increasing values (higher index = higher price)
            price_factor = 1.0 + spread_percentage + (i * 0.01)
            sell_price = midpoint * price_factor
            
            # Size decreases as we move away from the midpoint
            size = 100 - (i * 15)
            
            if sell_price < 1:
                synthetic_sell_orders.append({
                    "price": round(sell_price * 100, 1),  # Convert to percentage points
                    "size": size,
                    "total": round(sell_price * size, 2)
                })
        
        # Sort orders (buy highest to lowest, sell lowest to highest)
        synthetic_buy_orders.sort(key=lambda x: x["price"], reverse=True)
        synthetic_sell_orders.sort(key=lambda x: x["price"])
        
        return {
            "market": "",
            "asset_id": token_id,
            "timestamp": str(int(time.time() * 1000)),
            "buy_orders": synthetic_buy_orders,
            "sell_orders": synthetic_sell_orders,
            "is_synthetic": True
        } 