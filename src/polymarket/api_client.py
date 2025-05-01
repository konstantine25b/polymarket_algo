"""
Client for interacting with Polymarket APIs.
This is a simplified version of the main API client, focused on order book functionality.
"""

# Import required libraries
import requests
import re
import json
from typing import List, Dict, Optional, Any, Tuple
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams

# Import constants
from src.constants import (
    GAMMA_API_HOST,
    CLOB_API_HOST,
    POLYMARKET_API_HOST,
    POLYMARKET_ORDER_BOOK_API
)

class PolymarketAPIClient:
    """Client for interacting with Polymarket APIs."""
    
    # Class-level singleton instance
    _instance = None
    
    @classmethod
    def _get_instance(cls):
        """
        Get or create a singleton instance of the PolymarketAPIClient.
        
        Returns:
            PolymarketAPIClient: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
            # Initialize clob_client for the instance
            cls._instance.clob_client = ClobClient(host=CLOB_API_HOST, chain_id=137)  # 137 is for Polygon
            cls._instance.conditions_and_outcomes = {}
        
        return cls._instance
    
    @staticmethod
    def extract_slug_from_url(url: str) -> Optional[str]:
        """Extracts the event slug from a Polymarket event URL."""
        match = re.search(r'event/([^/?]+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def extract_tid_from_url(url: str) -> Optional[str]:
        """Extracts the thread ID from a Polymarket event URL."""
        match = re.search(r'tid=(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_market_details_from_gamma(event_slug: str) -> Tuple[Optional[List[Dict[str, str]]], Optional[str]]:
        """
        Fetches event details from the Gamma API to get market tokens.

        Args:
            event_slug: The URL slug for the event.

        Returns:
            A tuple containing:
            - A list of dictionaries, each containing 'outcome', 'token_id', and 'question'
              or None if fetching fails or no markets are found.
            - The event title as a string, or None if not found.
        """
        try:
            url = f"{GAMMA_API_HOST}/events?slug={event_slug}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Check if data is a list (direct event list) or dict (contains 'events')
            if isinstance(data, list):
                if not data:
                    print(f"No event data found for slug: {event_slug} (empty list response)")
                    return None, None
                event = data[0] # Assume the first element is the target event
            elif isinstance(data, dict) and data.get("events"):
                if not data["events"]:
                     print(f"No event data found for slug: {event_slug} (empty 'events' list)")
                     return None, None
                event = data["events"][0]
            else:
                print(f"Unexpected data format received for slug: {event_slug}")
                print(f"Data received: {data}") # Log the unexpected data
                return None, None

            # Extract event title for reference
            event_title = event.get("title", "Unknown Event")
            print(f"Event Title: {event_title}")

            # Proceed with the extracted event object
            markets = event.get("markets", [])
            if not markets:
                print(f"No market data found in the event for slug: {event_slug}")
                return None, event_title

            print(f"Found {len(markets)} markets in the event")
            
            market_details = []

            for market in markets:
                # Get outcomes from the outcomes field (formatted as JSON string)
                question = market.get("question", "Unknown")
                outcomes_str = market.get("outcomes")
                token_ids_str = market.get("clobTokenIds")
                
                if not outcomes_str or not token_ids_str:
                    print(f"  [Debug] Missing outcomes or token IDs for market: {question}")
                    continue
                
                try:
                    # Parse JSON strings
                    outcomes = json.loads(outcomes_str)
                    token_ids = json.loads(token_ids_str)
                    
                    # If lengths don't match, we can't reliably pair them
                    if len(outcomes) != len(token_ids):
                        print(f"  [Debug] Mismatch between outcomes ({len(outcomes)}) and token IDs ({len(token_ids)})")
                        continue
                    
                    # Pair outcomes with token IDs
                    for i, (outcome, token_id) in enumerate(zip(outcomes, token_ids)):
                        print(f"  [Debug] Pairing outcome: {outcome} with token_id: {token_id}")
                        market_details.append({
                            "question": question,
                            "outcome": outcome,
                            "token_id": token_id,
                            "market_id": market.get("id")  # Store the market ID directly from the response
                        })
                except json.JSONDecodeError as e:
                    print(f"  [Debug] Error parsing JSON for market {question}: {e}")
                except Exception as e:
                    print(f"  [Debug] Unexpected error processing market {question}: {e}")

            print(f"[Debug] Finished processing markets. market_details count: {len(market_details)}")
            return market_details if market_details else None, event_title

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Gamma API: {e}")
            return None, None
        except Exception as e:
            print(f"An error occurred processing Gamma API data: {e}")
            return None, None
            
    @classmethod
    def get_order_frames(cls, event_slug=None, thread_id=None):
        """
        Get order frames from gamma and clob for a given event.
        
        Args:
            event_slug (str): The event slug. 
            thread_id (str): Optional thread ID from the URL.
            
        Returns:
            dict: Dictionary mapping market questions to order frames with buy and sell orders
        """
        if event_slug is None:
            print("Error: event_slug must be provided.")
            return None
            
        clob_client = cls._get_instance().clob_client
        
        # Get market details
        market_details, event_title = cls.get_market_details_from_gamma(event_slug)
        
        if not market_details:
            print(f"No markets found for event {event_slug}")
            return None
            
        print(f"Found {len(market_details)} markets for event: {event_title}")
        
        # Build dictionary that maps market questions to IDs
        market_question_map = {}
        token_data = {}
        
        # Group by question to collect YES and NO outcomes
        questions_map = {}
        for detail in market_details:
            question = detail.get("question", "Unknown Question")
            market_id = detail.get("market_id", "")
            outcome = detail.get("outcome", "")
            token_id = detail.get("token_id", "")
            
            if question not in questions_map:
                questions_map[question] = {
                    "market_id": market_id,
                    "outcomes": []
                }
            
            questions_map[question]["outcomes"].append({
                "name": outcome,
                "token_id": token_id
            })
        
        # Map the YES and NO outcomes for each question
        for question, data in questions_map.items():
            market_id = data["market_id"]
            yes_token_id = None
            no_token_id = None
            
            # Find YES and NO token IDs
            for outcome in data["outcomes"]:
                if outcome["name"].upper() == "YES":
                    yes_token_id = outcome["token_id"]
                    print(f"DEBUG: Paired YES outcome: {outcome}")
                elif outcome["name"].upper() == "NO":
                    no_token_id = outcome["token_id"]
                    print(f"DEBUG: Paired NO outcome: {outcome}")
            
            if yes_token_id and no_token_id:
                market_question_map[question] = market_id
                token_data[market_id] = {
                    "yes_token_id": yes_token_id,
                    "no_token_id": no_token_id
                }
        
        # Build order frames
        order_frames = {}
        
        for question, market_id in market_question_map.items():
            tokens = token_data.get(market_id, {})
            yes_token_id = tokens.get("yes_token_id")
            no_token_id = tokens.get("no_token_id")
            
            # Try multiple methods to get real order book data
            real_order_data = None
            
            # Method 1: Try fetching directly from CLOB API using get_order_books
            try:
                print(f"Attempting to fetch real order book data for market: {question}")
                order_book_data = cls.fetch_order_book_from_clob(yes_token_id)
                
                if order_book_data and order_book_data.get("buy_orders") and order_book_data.get("sell_orders"):
                    real_order_data = {
                        "buy_orders": order_book_data["buy_orders"],
                        "sell_orders": order_book_data["sell_orders"],
                        "market_id": market_id,
                        "is_synthetic": False
                    }
                    print(f"✅ Successfully retrieved real order book data for market: {question}")
            except Exception as e:
                print(f"Error fetching order book using CLOB API for {question}: {e}")
            
            # Method 2: Try fetching from Polymarket API directly
            if not real_order_data and market_id:
                try:
                    print(f"Attempting to fetch order book from direct API for market: {question}")
                    order_book_data = cls.get_order_book_from_direct_api(market_id)
                    
                    if order_book_data:
                        # Extract and format buy and sell orders
                        buy_orders = []
                        sell_orders = []
                        
                        # Process bids from API response
                        for bid in order_book_data.get("bids", []):
                            price = float(bid.get("price", 0))
                            size = float(bid.get("size", 0))
                            
                            buy_orders.append({
                                "price": price * 100,  # Convert to percentage points
                                "size": size,
                                "total": price * size
                            })
                        
                        # Process asks from API response
                        for ask in order_book_data.get("asks", []):
                            price = float(ask.get("price", 0))
                            size = float(ask.get("size", 0))
                            
                            sell_orders.append({
                                "price": price * 100,  # Convert to percentage points
                                "size": size,
                                "total": price * size
                            })
                        
                        if buy_orders or sell_orders:
                            real_order_data = {
                                "buy_orders": buy_orders,
                                "sell_orders": sell_orders,
                                "market_id": market_id,
                                "is_synthetic": False
                            }
                            print(f"✅ Successfully retrieved real order book data from direct API for market: {question}")
                except Exception as e:
                    print(f"Error fetching order book from direct API for {question}: {e}")
            
            # Method 3: Try the alternate Polymarket order book API
            if not real_order_data and market_id:
                try:
                    print(f"Attempting to fetch from alternate order book API for market: {question}")
                    alt_api_url = f"{POLYMARKET_ORDER_BOOK_API}?marketId={market_id}"
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Referer": "https://polymarket.com/"
                    }
                    
                    response = requests.get(alt_api_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        buy_orders = []
                        for order in data.get("buyOrders", []):
                            price = float(order.get("price", 0))
                            size = float(order.get("size", 0))
                            
                            if price > 0 and size > 0:
                                buy_orders.append({
                                    "price": price * 100,  # Convert to percentage
                                    "size": size,
                                    "total": price * size
                                })
                        
                        sell_orders = []
                        for order in data.get("sellOrders", []):
                            price = float(order.get("price", 0))
                            size = float(order.get("size", 0))
                            
                            if price > 0 and size > 0:
                                sell_orders.append({
                                    "price": price * 100,  # Convert to percentage
                                    "size": size,
                                    "total": price * size
                                })
                        
                        if buy_orders or sell_orders:
                            real_order_data = {
                                "buy_orders": buy_orders,
                                "sell_orders": sell_orders,
                                "market_id": market_id,
                                "is_synthetic": False
                            }
                            print(f"✅ Successfully retrieved real order book data from alternate API for market: {question}")
                except Exception as e:
                    print(f"Error fetching from alternate order book API for {question}: {e}")
            
            # If all methods failed, skip this market
            if not real_order_data:
                print(f"❌ Could not fetch real order book data for market: {question}")
                continue
            
            # Add to order frames
            order_frames[question] = real_order_data
            
        return order_frames
        
    @staticmethod
    def get_order_book_from_direct_api(market_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch order book data directly from the Polymarket API.
        
        Args:
            market_id: The market ID
            
        Returns:
            Dictionary of order book data or None if request fails
        """
        try:
            # Build the URL with the market ID
            api_url = f"{POLYMARKET_API_HOST}/markets/{market_id}/orderbook"
            
            # Make the request
            headers = {
                # Add standard headers to appear like a browser request
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://polymarket.com/"
            }
            
            response = requests.get(api_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {})
            else:
                print(f"Failed to fetch order book for market {market_id}, status code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching order book from direct API: {e}")
            return None
            
    @staticmethod
    def fetch_order_book_from_clob(token_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch order book data directly from the CLOB API.
        
        Args:
            token_id: The token ID
            
        Returns:
            Dictionary of order book data or None if request fails
        """
        try:
            # Initialize CLOB client
            client = ClobClient(host=CLOB_API_HOST, chain_id=137)
            
            # Create BookParams with token ID
            params = [BookParams(token_id=token_id)]
            
            # Fetch order books using the get_order_books method
            order_books = client.get_order_books(params=params)
            
            # Check if we got valid data back
            if order_books and len(order_books) > 0:
                order_book = order_books[0]  # Take the first result
                
                # Convert the CLOB data format to our standard format
                buy_orders = []
                sell_orders = []
                
                # Process bids (buy orders)
                for bid in order_book.bids:
                    price = float(bid.price)
                    size = float(bid.size)
                    
                    if price > 0 and size > 0:
                        buy_orders.append({
                            "price": price * 100,  # Convert to percentage
                            "size": size,
                            "total": (price * size)  # Total in dollars
                        })
                
                # Process asks (sell orders)
                for ask in order_book.asks:
                    price = float(ask.price)
                    size = float(ask.size)
                    
                    if price > 0 and size > 0:
                        sell_orders.append({
                            "price": price * 100,  # Convert to percentage
                            "size": size,
                            "total": (price * size)  # Total in dollars
                        })
                
                # Sort orders appropriately
                buy_orders.sort(key=lambda x: x["price"], reverse=True)
                sell_orders.sort(key=lambda x: x["price"])
                
                return {
                    "buy_orders": buy_orders,
                    "sell_orders": sell_orders,
                    "is_synthetic": False
                }
            else:
                print(f"No order book data returned for token {token_id}")
                return None
                
        except Exception as e:
            print(f"Error fetching from CLOB API: {e}")
            return None 