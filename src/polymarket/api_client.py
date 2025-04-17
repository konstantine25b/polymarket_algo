# src/polymarket/api_client.py

import requests
import re
import json
from typing import List, Dict, Optional, Any, Tuple
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams
import time
import random
import os
import glob

# --- Configuration ---
GAMMA_API_HOST = "https://gamma-api.polymarket.com"
CLOB_API_HOST = "https://clob.polymarket.com"
POLYMARKET_API_HOST = "https://polymarket.com/api"
POLYMARKET_ORDER_BOOK_API = "https://polymarket.com/api/order-books" # Updated endpoint

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

    @staticmethod
    def get_market_details_from_polymarket_api(event_slug: str, thread_id: Optional[str] = None) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetches event details directly from the Polymarket API.
        
        Args:
            event_slug: The URL slug for the event
            thread_id: Optional thread ID from the URL
            
        Returns:
            A tuple containing:
            - A list of dictionaries with market details
            - The event title
        """
        try:
            # Try first with the full event endpoint which includes market IDs
            full_event_url = f"{POLYMARKET_API_HOST}/events/{event_slug}"
            if thread_id:
                full_event_url += f"?tid={thread_id}"
                
            response = requests.get(full_event_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if not data or 'data' not in data:
                    print(f"No valid data found for event slug: {event_slug}")
                    return None, None
                
                event_data = data['data']
                event_title = event_data.get('title', 'Unknown Event')
                markets = event_data.get('markets', [])
                
                if not markets:
                    print(f"No markets found for event: {event_title}")
                    return None, event_title
                
                # Extract market details including market IDs
                market_details = []
                for market in markets:
                    market_id = market.get('id')
                    question = market.get('question', 'Unknown')
                    
                    for outcome in market.get('outcomes', []):
                        outcome_value = outcome.get('value', '')
                        outcome_id = outcome.get('id', '')
                        probability = outcome.get('probability', 0)
                        
                        market_details.append({
                            'market_id': market_id,
                            'question': question, 
                            'outcome': outcome_value,
                            'outcome_id': outcome_id,
                            'probability': probability
                        })
                
                return market_details, event_title
            else:
                print(f"Failed to fetch from Polymarket API: {response.status_code}")
                return None, None
                
        except Exception as e:
            print(f"Error fetching from Polymarket API: {e}")
            return None, None
    
    @staticmethod
    def get_market_prices_from_clob(token_ids: List[str]) -> Optional[Dict[str, float]]:
        """
        Fetches midpoint prices for given token IDs using the CLOB client.

        Args:
            token_ids: A list of token IDs.

        Returns:
            A dictionary mapping token_id to its midpoint price (as float),
            or None if fetching fails. Returns empty dict if input list is empty.
        """
        if not token_ids:
            return {}

        try:
            # Initialize client for read-only operations (no key needed)
            client = ClobClient(host=CLOB_API_HOST, chain_id=137) # Chain ID 137 for Polygon

            params = [BookParams(token_id=tid) for tid in token_ids]
            midpoints_response = client.get_midpoints(params=params)

            # The response format is {token_id: "price_string"}
            prices = {}
            for token_id, price_str in midpoints_response.items():
                try:
                    prices[token_id] = float(price_str)
                except (ValueError, TypeError):
                    print(f"Warning: Could not parse price '{price_str}' for token_id {token_id}")
                    prices[token_id] = None # Or handle as 0 or skip

            return prices

        except Exception as e:
            print(f"An error occurred fetching data from CLOB API: {e}")
            return None
            
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
    
    @classmethod
    def get_event_data(cls, event_url: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetches all relevant data for a Polymarket event.
        
        Args:
            event_url: The URL of the Polymarket event.
            
        Returns:
            A tuple of (market_data, event_title) where market_data is a list of dictionaries 
            containing outcome details with prices, and event_title is the title of the event.
        """
        # Extract the event slug and thread ID from the URL
        event_slug = cls.extract_slug_from_url(event_url)
        thread_id = cls.extract_tid_from_url(event_url)
        
        if not event_slug:
            print("Could not extract event slug from URL.")
            return None, None
            
        print(f"Extracted slug: {event_slug}")
        if thread_id:
            print(f"Extracted thread ID: {thread_id}")
        
        # First try the Polymarket API directly
        market_details, event_title = cls.get_market_details_from_polymarket_api(event_slug, thread_id)
        
        # If that fails, fall back to the Gamma API
        if not market_details:
            print("Falling back to Gamma API...")
            market_details, event_title = cls.get_market_details_from_gamma(event_slug)
        
        if not market_details:
            print("Could not retrieve market details from any API.")
            return None, event_title
        
        # Get token IDs to fetch prices if they exist
        token_ids_to_fetch = [md.get("token_id") for md in market_details if md.get("token_id")]
        
        if token_ids_to_fetch:
            # Fetch prices from CLOB API
            prices = cls.get_market_prices_from_clob(token_ids_to_fetch)
            
            if prices is not None:
                # Add prices to market details
                for detail in market_details:
                    token_id = detail.get("token_id")
                    if token_id and token_id in prices:
                        price = prices.get(token_id)
                        if price is not None:
                            detail["price"] = price
                            detail["percentage"] = price * 100  # Convert to percentage
        
        # If market details don't have percentages but have probabilities, use those
        for detail in market_details:
            if "percentage" not in detail and "probability" in detail:
                detail["percentage"] = float(detail["probability"]) * 100
                        
        return market_details, event_title

    @classmethod
    def get_conditions_and_outcomes(cls):
        return cls._get_instance().conditions_and_outcomes

    @classmethod
    def get_midpoint(cls, market_id, yes_token_id, no_token_id):
        """
        Get the midpoint price for a market based on YES and NO token IDs.
        
        Args:
            market_id (str): The market ID
            yes_token_id (str): The YES token ID
            no_token_id (str): The NO token ID
            
        Returns:
            float: The midpoint price (0-1)
        """
        try:
            clob_client = cls._get_instance().clob_client
            
            # Create BookParams for both YES and NO tokens
            params = [
                BookParams(token_id=yes_token_id),
                BookParams(token_id=no_token_id)
            ]
            
            # Fetch midpoints for both tokens in one call
            try:
                midpoints_response = clob_client.get_midpoints(params=params)
                
                # Extract YES midpoint
                if yes_token_id in midpoints_response:
                    yes_midpoint_str = midpoints_response.get(yes_token_id, "0.5")
                    
                    # Convert to float
                    try:
                        yes_midpoint = float(yes_midpoint_str)
                        return yes_midpoint
                    except (ValueError, TypeError):
                        print(f"Warning: Could not parse midpoint '{yes_midpoint_str}' for token_id {yes_token_id}")
                else:
                    print(f"No midpoint returned for YES token {yes_token_id}")
                
                return 0.5  # Default if midpoint can't be determined
                
            except Exception as e:
                print(f"Error getting midpoints from CLOB API for market {market_id}: {e}")
                return 0.5
                
        except Exception as e:
            print(f"Error in get_midpoint: {e}")
            return 0.5

    @classmethod
    def get_midpoints(cls, markets_data):
        """
        Get midpoint prices for multiple markets
        
        Args:
            markets_data (dict): Dictionary mapping market_id to token information
                Format: {market_id: {"yes_token_id": str, "no_token_id": str}}
                
        Returns:
            dict: Dictionary mapping market_id to midpoint price
        """
        midpoint_prices = {}
        
        for market_id, token_data in markets_data.items():
            yes_token_id = token_data.get("yes_token_id")
            no_token_id = token_data.get("no_token_id")
            
            if yes_token_id and no_token_id:
                midpoint = cls.get_midpoint(market_id, yes_token_id, no_token_id)
                midpoint_prices[market_id] = midpoint
        
        return midpoint_prices

    @classmethod
    def get_tweet_count_frames(cls) -> list[str]:
        """
        Returns count frames of tweets as an array of ranges.
        
        Dynamically extracts the tweet count frames from saved Polymarket data
        or by fetching from the Polymarket API if no saved data is available.
        
        Returns:
            list[str]: An array of tweet count ranges formatted as strings (e.g., ["125-149", "150-174", ...])
        """
        frames = []
        
        # Pattern to extract tweet count ranges from market questions
        tweet_range_pattern = r'Will Elon tweet (.*?) times'
        less_than_pattern = r'Will Elon tweet less than (\d+) times'
        more_than_pattern = r'Will Elon tweet (\d+) or more times'
        
        # Try to find the most recent Elon tweet market data in the saved files
        data_dir = os.path.join("src", "polymarket", "data", "json")
        elon_files = glob.glob(os.path.join(data_dir, "elon-musk-of-tweets-*.json"))
        
        if elon_files:
            # Sort by modification time (newest first)
            newest_file = max(elon_files, key=os.path.getmtime)
            
            try:
                with open(newest_file, 'r') as f:
                    data = json.load(f)
                
                # Extract frames from market questions
                for market in data.get('market_data', []):
                    question = market.get('question', '')
                    
                    # Skip Yes/No answers
                    if market.get('outcome') in ['Yes', 'No']:
                        continue
                        
                    # Try to match "less than X" pattern
                    less_than_match = re.search(less_than_pattern, question)
                    if less_than_match:
                        frames.append(f"less than {less_than_match.group(1)}")
                        continue
                        
                    # Try to match "X or more" pattern
                    more_than_match = re.search(more_than_pattern, question)
                    if more_than_match:
                        frames.append(f"{more_than_match.group(1)} or more")
                        continue
                    
                    # Try to match normal ranges
                    range_match = re.search(tweet_range_pattern, question)
                    if range_match:
                        frame = range_match.group(1)
                        frames.append(frame)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading market data file: {e}")
        
        # If no frames found from files, try fetching from API
        if not frames:
            try:
                # Try to get frames from active Elon tweet markets
                event_url = "https://polymarket.com/event/elon-musk-of-tweets-april-11-18-628"
                event_slug = cls.extract_slug_from_url(event_url)
                thread_id = cls.extract_tid_from_url(event_url)
                
                if event_slug:
                    market_details, _ = cls.get_market_details_from_polymarket_api(event_slug, thread_id)
                    
                    if not market_details:
                        market_details, _ = cls.get_market_details_from_gamma(event_slug)
                    
                    if market_details:
                        for market in market_details:
                            question = market.get('question', '')
                            
                            # Ignore Yes/No
                            if 'Will Elon tweet' not in question:
                                continue
                                
                            # Try to match "less than X" pattern
                            less_than_match = re.search(less_than_pattern, question)
                            if less_than_match:
                                frames.append(f"less than {less_than_match.group(1)}")
                                continue
                                
                            # Try to match "X or more" pattern
                            more_than_match = re.search(more_than_pattern, question)
                            if more_than_match:
                                frames.append(f"{more_than_match.group(1)} or more")
                                continue
                            
                            # Try to match normal ranges  
                            range_match = re.search(tweet_range_pattern, question)
                            if range_match:
                                frame = range_match.group(1)
                                frames.append(frame)
            except Exception as e:
                print(f"Error fetching market data from API: {e}")
        
        # Remove duplicates and sort
        frames = list(set(frames))
        
        # Sort the frames in a logical order
        def frame_sort_key(frame):
            if frame.startswith("less than"):
                # Sort "less than X" frames first
                return (0, int(frame.split()[-1]))
            elif frame.endswith("or more"):
                # Sort "X or more" frames last
                return (2, int(frame.split()[0]))
            else:
                # Sort normal ranges by their lower bound
                try:
                    # Handle both en-dash and regular hyphen
                    frame_text = frame.replace("–", "-")
                    lower = int(frame_text.split('-')[0].strip())
                    return (1, lower)
                except (ValueError, IndexError):
                    return (3, 0)  # Unknown format, sort at the end
                
        frames.sort(key=frame_sort_key)
        
        # If still no frames found, use default frames
        if not frames:
            frames = [
                "less than 100",
                "100-124", 
                "125-149", 
                "150-174", 
                "175-199", 
                "200-224", 
                "225-249", 
                "250-274", 
                "275-299", 
                "300-324", 
                "325-349", 
                "350-374", 
                "375-399", 
                "400 or more"
            ]
            print("No frames found from data sources, using default frames")
        
        return frames 