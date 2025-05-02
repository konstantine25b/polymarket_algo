#!/usr/bin/env python3
"""
Fetch Elon Musk tweet market order book data from Polymarket.
This script retrieves the full order book for all outcome ranges in
the current Elon Musk tweet count market.
"""

import os
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
import time

# Import from project
from src.constants import (
    POLYMARKET_ELON_TWEETS_URL,
    MARKET_HASH,
    EVENT_HASH,
    FULL_EVENT_HASH,
    DATA_DIR
)

# Create a reference to the api_client.py module
from src.polymarket.api_client import PolymarketAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_output_dirs() -> Path:
    """Create the necessary output directories for order book data."""
    # Create base data directory
    polymarket_data_dir = DATA_DIR / "order_book"
    polymarket_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a directory for our JSON files
    json_dir = polymarket_data_dir / "json"
    json_dir.mkdir(exist_ok=True)
    
    return json_dir

def save_order_book(order_frames, event_title, output_file=None):
    """Save order book data to a JSON file."""
    # Default output file if none provided
    if output_file is None:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        output_file = f"{EVENT_HASH}-{timestamp}.json"
    
    # Get the output directory
    json_dir = create_output_dirs()
    output_path = json_dir / output_file
    
    # Format the data for saving
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "event_title": event_title,
        "questions": order_frames
    }
    
    # Save the data to file
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    logger.info(f"Order book data saved to {output_path}")
    return output_path

def fetch_elon_order_book(visualize=False, output_file=None):
    """Fetch the order book for the Elon Musk tweet market from Polymarket."""
    logger.info("Fetching Elon Musk tweet market order book data...")
    
    # Extract the event slug from the URL (fallback to using EVENT_HASH)
    event_slug = PolymarketAPIClient.extract_slug_from_url(POLYMARKET_ELON_TWEETS_URL)
    if not event_slug:
        logger.warning(f"Could not extract slug from URL. Using event hash: {EVENT_HASH}")
        event_slug = EVENT_HASH
    
    logger.info(f"Using event slug: {event_slug}")
    
    # First get market details to extract token IDs
    market_details, _ = PolymarketAPIClient.get_market_details_from_gamma(event_slug)
    token_id_map = {}
    
    if market_details:
        # Create a mapping of question to token_id
        for market in market_details:
            question = market.get("question", "")
            token_id = market.get("token_id", "")
            outcome = market.get("outcome", "")
            market_id = market.get("market_id", "")
            
            # For YES outcomes, store the token ID
            if outcome.upper() == "YES":
                token_id_map[question] = {
                    "token_id": token_id,
                    "market_id": market_id
                }
    
    # Attempt to get order frames from the API
    start_time = time.time()
    order_frames = PolymarketAPIClient.get_order_frames(event_slug=event_slug)
    fetch_time = time.time() - start_time
    
    if not order_frames:
        logger.error("Failed to fetch order book data. Check the market URL and try again.")
        return None
    
    logger.info(f"Successfully fetched order book data for {len(order_frames)} markets in {fetch_time:.2f} seconds")
    
    # Add token IDs to the order frames
    for question, order_data in order_frames.items():
        # Try to match with our token ID map
        if question in token_id_map:
            order_data["token_id"] = token_id_map[question]["token_id"]
            order_data["market_id"] = token_id_map[question]["market_id"]
        else:
            # Try to match by finding a key that contains this question (partial match)
            for map_question, id_data in token_id_map.items():
                if question in map_question or map_question in question:
                    order_data["token_id"] = id_data["token_id"]
                    order_data["market_id"] = id_data["market_id"]
                    break
    
    # Infer event title from first question
    if order_frames:
        first_question = next(iter(order_frames))
        event_title = first_question.split("Will Elon tweet")[0].strip()
        if not event_title:
            event_title = "Elon Musk Tweet Count"
    else:
        event_title = "Elon Musk Tweet Count"
        
    # Save the order book data to a file
    output_path = save_order_book(order_frames, event_title, output_file)
    
    # If requested, generate visualizations
    if visualize:
        try:
            from src.polymarket.order_book.visualize_order_book import visualize_order_book
            visualize_order_book(output_path)
        except ImportError as e:
            logger.error(f"Error importing visualization module: {e}")
            logger.info("Please run the visualization script separately.")
    
    return output_path

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Fetch Elon Musk tweet market order book data")
    parser.add_argument("--visualize", action="store_true", help="Generate visualizations of the order book")
    parser.add_argument("--output", type=str, help="Custom output filename for the order book data")
    args = parser.parse_args()
    
    fetch_elon_order_book(visualize=args.visualize, output_file=args.output)

if __name__ == "__main__":
    main() 