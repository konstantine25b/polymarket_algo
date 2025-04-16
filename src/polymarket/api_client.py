# src/polymarket/api_client.py

import requests
import re
import json
from typing import List, Dict, Optional, Any, Tuple
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams

# --- Configuration ---
GAMMA_API_HOST = "https://gamma-api.polymarket.com"
CLOB_API_HOST = "https://clob.polymarket.com"

class PolymarketAPIClient:
    """Client for interacting with Polymarket APIs."""
    
    @staticmethod
    def extract_slug_from_url(url: str) -> Optional[str]:
        """Extracts the event slug from a Polymarket event URL."""
        match = re.search(r'event/([^/?]+)', url)
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
                            "token_id": token_id
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
    def get_event_data(cls, event_url: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetches all relevant data for a Polymarket event.
        
        Args:
            event_url: The URL of the Polymarket event.
            
        Returns:
            A tuple of (market_data, event_title) where market_data is a list of dictionaries 
            containing outcome details with prices, and event_title is the title of the event.
        """
        # Extract the event slug from the URL
        event_slug = cls.extract_slug_from_url(event_url)
        if not event_slug:
            print("Could not extract event slug from URL.")
            return None, None
            
        print(f"Extracted slug: {event_slug}")
        
        # Get market details from Gamma API
        market_details, event_title = cls.get_market_details_from_gamma(event_slug)
        
        if not market_details:
            print("Could not retrieve market details from Gamma API.")
            return None, event_title
            
        # Get token IDs to fetch prices
        token_ids_to_fetch = [md["token_id"] for md in market_details]
        
        # Fetch prices from CLOB API
        prices = cls.get_market_prices_from_clob(token_ids_to_fetch)
        
        if prices is None:
            print("Failed to retrieve prices from CLOB API.")
            return None, event_title
            
        # Combine market details with price data
        market_data = []
        for detail in market_details:
            token_id = detail["token_id"]
            outcome = detail["outcome"]
            question = detail["question"]
            
            price = prices.get(token_id)
            if price is not None:
                percentage = price * 100  # Convert to percentage
                detail["price"] = price
                detail["percentage"] = percentage
            else:
                detail["price"] = None
                detail["percentage"] = None
                
            market_data.append(detail)
            
        return market_data, event_title 