# src/polymarket/get_event_data.py

import requests
import re
import json
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams

# --- Configuration ---
GAMMA_API_HOST = "https://gamma-api.polymarket.com"
CLOB_API_HOST = "https://clob.polymarket.com"

def extract_slug_from_url(url: str) -> str | None:
    """Extracts the event slug from a Polymarket event URL."""
    match = re.search(r'event/([^/?]+)', url)
    return match.group(1) if match else None

def get_market_details_from_gamma(event_slug: str) -> list[dict] | None:
    """
    Fetches event details from the Gamma API to get market tokens.

    Args:
        event_slug: The URL slug for the event.

    Returns:
        A list of dictionaries, each containing 'outcome' and 'token_id',
        or None if fetching fails or no markets are found.
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
                return None
            event = data[0] # Assume the first element is the target event
        elif isinstance(data, dict) and data.get("events"):
            if not data["events"]:
                 print(f"No event data found for slug: {event_slug} (empty 'events' list)")
                 return None
            event = data["events"][0]
        else:
            print(f"Unexpected data format received for slug: {event_slug}")
            print(f"Data received: {data}") # Log the unexpected data
            return None

        # Proceed with the extracted event object
        markets = event.get("markets", [])
        if not markets:
            print(f"No market data found in the event for slug: {event_slug}")
            return None

        print(f"Found {len(markets)} markets in the event")
        
        market_details = []

        for market in markets:
            # Get outcomes from the outcomes field (formatted as JSON string)
            outcomes_str = market.get("outcomes")
            token_ids_str = market.get("clobTokenIds")
            
            if not outcomes_str or not token_ids_str:
                print(f"  [Debug] Missing outcomes or token IDs for market: {market.get('question', 'Unknown')}")
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
                        "outcome": outcome,
                        "token_id": token_id
                    })
            except json.JSONDecodeError as e:
                print(f"  [Debug] Error parsing JSON for market {market.get('question', 'Unknown')}: {e}")
            except Exception as e:
                print(f"  [Debug] Unexpected error processing market {market.get('question', 'Unknown')}: {e}")

        print(f"[Debug] Finished processing markets. market_details count: {len(market_details)}")
        return market_details if market_details else None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Gamma API: {e}")
        return None
    except Exception as e:
        print(f"An error occurred processing Gamma API data: {e}")
        return None

def get_market_prices_from_clob(token_ids: list[str]) -> dict[str, float] | None:
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


if __name__ == "__main__":
    event_url = "https://polymarket.com/event/elon-musk-of-tweets-april-11-18-628?tid=1744827985479"
    print(f"Fetching data for event: {event_url}")

    event_slug = extract_slug_from_url(event_url)

    if not event_slug:
        print("Could not extract event slug from URL.")
    else:
        print(f"Extracted slug: {event_slug}")
        market_details = get_market_details_from_gamma(event_slug)

        if market_details:
            print(f"Found {len(market_details)} market outcomes from Gamma API:")
            token_ids_to_fetch = [md["token_id"] for md in market_details]
            # print(f"Token IDs: {token_ids_to_fetch}") # Debugging

            prices = get_market_prices_from_clob(token_ids_to_fetch)

            if prices is not None:
                print("\n--- Market Data ---")
                found_prices = False
                for detail in market_details:
                    token_id = detail["token_id"]
                    outcome = detail["outcome"]
                    price = prices.get(token_id)

                    if price is not None:
                        percentage = f"{price * 100:.0f}%" # Format as percentage
                        print(f"Range: {outcome}, Percentage: {percentage}")
                        found_prices = True
                    else:
                        print(f"Range: {outcome}, Percentage: (Price not found)")

                if not found_prices:
                     print("\nCould not retrieve prices for any market outcomes.")

            else:
                print("\nFailed to retrieve prices from CLOB API.")
        else:
            print("Could not retrieve market details from Gamma API.") 