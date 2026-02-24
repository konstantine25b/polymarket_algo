from ..polymarket.api_client import PolymarketAPIClient
from ..constants import DEFAULT_EVENT_SLUG, DEFAULT_THREAD_ID
import json
from datetime import datetime

def show_polymarket_data():
    print("\n=== Current Polymarket Data ===")
    print("Fetching live market data...")
    
    # Get market details
    market_details, event_title = PolymarketAPIClient.get_market_details_from_polymarket_api(
        DEFAULT_EVENT_SLUG,
        DEFAULT_THREAD_ID
    )
    
    if not market_details:
        print("Could not fetch market data. Trying alternative source...")
        market_details, event_title = PolymarketAPIClient.get_market_details_from_gamma(
            DEFAULT_EVENT_SLUG
        )
    
    if market_details:
        print(f"\nEvent: {event_title}")
        print("\nCurrent Market Prices:")
        print("-" * 50)
        
        for market in market_details:
            question = market.get('question', '')
            if 'Will Elon tweet' in question:  # Only show tweet count markets
                price = market.get('price', 0)
                percentage = market.get('percentage', 0)
                print(f"{question}")
                print(f"Current Price: {price:.3f} ({percentage:.1f}%)")
                print("-" * 50)
    else:
        print("Failed to fetch market data")

if __name__ == "__main__":
    show_polymarket_data() 