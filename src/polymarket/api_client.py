# src/polymarket/api_client.py

import requests
import re
import json
from typing import List, Dict, Optional, Any, Tuple
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams
import time

# --- Configuration ---
GAMMA_API_HOST = "https://gamma-api.polymarket.com"
CLOB_API_HOST = "https://clob.polymarket.com"
POLYMARKET_API_HOST = "https://polymarket.com/api"
POLYMARKET_ORDER_BOOK_API = "https://strapi-matic.poly.market/order-books"

class PolymarketAPIClient:
    """Client for interacting with Polymarket APIs."""
    
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
    
    @classmethod
    def get_order_frames(cls, event_slug: str, thread_id: Optional[str] = None) -> Optional[Dict[str, Dict[str, List[Dict[str, float]]]]]:
        """
        Fetches order frames (buy/sell orders) for an event using the Polymarket API.
        
        Args:
            event_slug: The event slug identifier
            thread_id: Optional thread ID from the URL
            
        Returns:
            A dictionary of market questions mapping to dictionaries containing:
                - 'buy_orders': List of buy orders for YES outcomes
                - 'sell_orders': List of sell orders for YES outcomes
                
            Example:
            {
                "Market Question 1": {
                    "buy_orders": [
                        {"price": 95.5, "size": 100.0, "total": 9550.0},
                        ...
                    ],
                    "sell_orders": [
                        {"price": 97.8, "size": 200.0, "total": 19560.0},
                        ...
                    ],
                    "market_id": "token_id_here"
                },
                ...
            }
            
            Returns None if fetching fails.
        """
        try:
            # First try to get market details from the Polymarket API directly
            market_details, event_title = cls.get_market_details_from_polymarket_api(event_slug, thread_id)
            
            # If that fails, fall back to the Gamma API
            if not market_details:
                print("Falling back to Gamma API...")
                market_details, event_title = cls.get_market_details_from_gamma(event_slug)
            
            if not market_details:
                print("Could not retrieve market details from any API.")
                return None
            
            # Group market details by question and store market IDs
            market_question_map = {}
            
            for item in market_details:
                question = item.get("question", "")
                market_id = item.get("market_id")
                
                if not question or not market_id:
                    continue
                    
                if question not in market_question_map:
                    market_question_map[question] = {
                        "market_id": market_id,
                        "outcomes": []
                    }
                
                # Add the outcome if it's not already in the list
                outcome = {
                    "value": item.get("outcome", ""),
                    "token_id": item.get("token_id", ""),
                    "outcome_id": item.get("outcome_id", "")
                }
                
                if outcome not in market_question_map[question]["outcomes"]:
                    market_question_map[question]["outcomes"].append(outcome)
            
            # Fetch real order book data
            order_frames = {}
            
            # Process max 5 markets to prevent long execution times
            market_count = 0
            max_markets = 5
            
            for question, market_info in market_question_map.items():
                # Limit the number of markets processed 
                market_count += 1
                if market_count > max_markets:
                    print(f"Only processing the first {max_markets} markets to prevent long execution times")
                    break
                
                market_id = market_info.get("market_id")
                
                if not market_id:
                    print(f"No market ID found for question: {question}")
                    continue
                
                # Fetch real order book data
                print(f"Fetching real order book data for {question} (Market ID: {market_id})")
                
                # Make the API request with retry mechanism
                max_retries = 3
                real_order_data = None
                
                for attempt in range(max_retries):
                    try:
                        api_url = f"{POLYMARKET_ORDER_BOOK_API}?marketId={market_id}"
                        response = requests.get(api_url, timeout=15)
                        
                        if response.status_code == 200:
                            order_data = response.json()
                            
                            # Process buy orders
                            buy_orders = []
                            for order in order_data.get('buyOrders', []):
                                price = float(order.get('price', 0))
                                size = float(order.get('size', 0))
                                buy_orders.append({
                                    "price": price,
                                    "size": size,
                                    "total": (price * size) / 100  # Convert to dollars
                                })
                            
                            # Process sell orders
                            sell_orders = []
                            for order in order_data.get('sellOrders', []):
                                price = float(order.get('price', 0))
                                size = float(order.get('size', 0))
                                sell_orders.append({
                                    "price": price,
                                    "size": size,
                                    "total": (price * size) / 100  # Convert to dollars
                                })
                            
                            # Sort orders
                            buy_orders = sorted(buy_orders, key=lambda x: x['price'], reverse=True)
                            sell_orders = sorted(sell_orders, key=lambda x: x['price'])
                            
                            # Only consider this successful if we got some orders
                            if buy_orders or sell_orders:
                                real_order_data = {
                                    "buy_orders": buy_orders,
                                    "sell_orders": sell_orders,
                                    "market_id": market_id,
                                    "is_synthetic": False
                                }
                                print(f"Successfully fetched real order book data with {len(buy_orders)} buy orders and {len(sell_orders)} sell orders")
                                break  # Exit retry loop on success
                            else:
                                print(f"Got empty order book data. Retrying ({attempt+1}/{max_retries})")
                                if attempt < max_retries - 1:
                                    time.sleep(1)  # Wait before retrying
                        else:
                            print(f"API request failed with status {response.status_code}, attempt {attempt+1}/{max_retries}")
                            if attempt < max_retries - 1:
                                time.sleep(1)  # Wait before retrying
                                
                    except Exception as e:
                        print(f"Error fetching order book for {question}: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(1)  # Wait before retrying
                
                # If we couldn't get real data, look for token IDs and generate synthetic data as a fallback
                if not real_order_data:
                    yes_outcome = next((o for o in market_info.get("outcomes", []) if o.get("value", "").lower() == "yes"), None)
                    
                    if yes_outcome and yes_outcome.get("token_id"):
                        yes_token_id = yes_outcome.get("token_id")
                        print(f"Using synthetic order data for {question}")
                        
                        # Get the price from CLOB API for synthetic data
                        prices = cls.get_market_prices_from_clob([yes_token_id])
                        yes_price = prices.get(yes_token_id, 0.5) if prices else 0.5
                        
                        # Create synthetic data based on the current price
                        buy_orders = []
                        sell_orders = []
                        
                        # Generate buy orders (slightly below the midpoint price)
                        for i in range(5):
                            price_discount = (i + 1) * 0.5  # Increasing discount
                            buy_price = max(1.0, yes_price * 100 - price_discount)
                            size = 100 / (i + 1)  # Decreasing size
                            buy_orders.append({
                                "price": round(buy_price, 1),
                                "size": round(size, 2),
                                "total": round((size * buy_price) / 100, 2)  # Total in dollars
                            })
                        
                        # Generate sell orders (slightly above the midpoint price)
                        for i in range(5):
                            price_premium = (i + 1) * 0.5  # Increasing premium
                            sell_price = min(99.0, yes_price * 100 + price_premium)
                            size = 100 / (i + 1)  # Decreasing size
                            sell_orders.append({
                                "price": round(sell_price, 1),
                                "size": round(size, 2),
                                "total": round((size * sell_price) / 100, 2)  # Total in dollars
                            })
                        
                        order_frames[question] = {
                            "buy_orders": buy_orders,
                            "sell_orders": sell_orders,
                            "market_id": market_id,
                            "is_synthetic": True
                        }
                    else:
                        print(f"Skipping question '{question}' - no YES outcome token ID found")
                        continue
                else:
                    # Use real order book data
                    order_frames[question] = real_order_data
            
            if order_frames:
                print(f"Successfully processed order frames for {len(order_frames)} markets")
                return order_frames
            else:
                print("No order frames could be generated or fetched")
                return None
            
        except Exception as e:
            print(f"An error occurred processing order frames: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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