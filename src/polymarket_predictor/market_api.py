import requests
from typing import Dict, List, Optional, Any
import json

# Import constants
from src.constants import (
    CLOB_API_HOST as API_ENDPOINT,
    MARKET_ID,
    MARKET_HASH,
    EVENT_HASH,
    FULL_EVENT_HASH,
    TWEET_COUNT_FRAMES
)

def get_market_details() -> Optional[Dict[str, Any]]:
    """
    Get details about the Polymarket prediction market
    
    Returns:
        dict: Market details or None if request fails
    """
    try:
        response = requests.get(f"{API_ENDPOINT}markets/{MARKET_ID}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch from Polymarket API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching market details: {e}")
        return None

def parse_count_frames(market_details: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parse tweet count frames from market details
    
    Args:
        market_details: Market details from the Polymarket API
        
    Returns:
        list: Count frames extracted from market details
    """
    if not market_details:
        return []
    
    count_frames = []
    markets = market_details.get("markets", [])
    for market in markets:
        outcomes = market.get("outcomes", [])
        for outcome in outcomes:
            title = outcome.get("title", "")
            token_id = outcome.get("tokenId", "")
            print(f"  [Debug] Pairing outcome: {title} with token_id: {token_id}")
    
    print(f"[Debug] Finished processing markets. market_details count: {len(markets)}")
    
    # Process by finding the event details
    events = market_details.get("events", [])
    if events:
        print(f"Retrieved {len(events)} count frames from Polymarket")
        # Assuming the first event is the one we want
        return events
    
    return []

def get_count_frames() -> List[Dict[str, Any]]:
    """
    Get count frames either from API or fallback to constants
    
    Returns:
        list: Count frames for prediction
    """
    # First try to get from API
    market_details = get_market_details()
    if market_details:
        api_frames = parse_count_frames(market_details)
        if api_frames:
            return api_frames
    
    # Fallback to constants if API fails or returns empty
    print("Using count frames from constants file")
    return TWEET_COUNT_FRAMES 