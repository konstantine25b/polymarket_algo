# src/polymarket/main.py

import argparse
import os
import sys
from typing import Optional, List, Dict, Any

from src.polymarket.api_client import PolymarketAPIClient
from src.polymarket.data_storage import DataStorage
from src.polymarket.visualization import MarketVisualizer

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Polymarket Data Analyzer")
    
    # Required URL argument
    parser.add_argument("--url", type=str, help="Polymarket event URL")
    
    # Optional arguments
    parser.add_argument("--no-plot", action="store_true", help="Skip plot generation")
    parser.add_argument("--compare", action="store_true", help="Compare with previous data if available")
    parser.add_argument("--list-events", action="store_true", help="List all stored events")
    parser.add_argument("--output-dir", type=str, default="results", help="Base directory for output")
    
    return parser.parse_args()

def setup_directories(base_dir: str) -> tuple:
    """Create necessary directories for output."""
    data_dir = os.path.join(base_dir, "data")
    plots_dir = os.path.join(base_dir, "plots")
    
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)
    
    return data_dir, plots_dir

def list_stored_events(storage: DataStorage):
    """List all events for which data is stored."""
    events = storage.list_stored_events()
    if not events:
        print("No stored events found.")
        return
    
    print("\nStored events:")
    for i, event_slug in enumerate(events, 1):
        latest_file = storage.get_latest_data_file(event_slug)
        if latest_file:
            data = storage.load_json(latest_file)
            if data:
                title = data.get("event_title", "Unknown title")
                timestamp = data.get("timestamp", "Unknown time")
                print(f"{i}. {title} ({event_slug}) - Last updated: {timestamp}")
            else:
                print(f"{i}. {event_slug} - Data file exists but couldn't be loaded")
        else:
            print(f"{i}. {event_slug} - No data file found")

def process_event(url: str, 
                  no_plot: bool, 
                  compare: bool, 
                  data_dir: str, 
                  plots_dir: str) -> None:
    """Process a Polymarket event: fetch data, store it, and visualize it."""
    # Initialize components
    api_client = PolymarketAPIClient()
    storage = DataStorage(data_dir)
    visualizer = MarketVisualizer(plots_dir)
    
    # Fetch data
    print(f"Fetching data for: {url}")
    market_data, event_title = api_client.get_event_data(url)
    
    if not market_data:
        print("Failed to retrieve market data. Exiting.")
        return
    
    # Extract slug for file naming
    event_slug = api_client.extract_slug_from_url(url)
    if not event_slug:
        print("Could not extract event slug from URL. Using 'unknown' as fallback.")
        event_slug = "unknown"
    
    # Store data
    print(f"Storing data for event: {event_title}")
    json_file = storage.save_json(event_slug, market_data, event_title)
    csv_file = storage.save_csv(event_slug, market_data, event_title)
    
    # Generate visualization if not disabled
    if not no_plot:
        print("Generating visualization...")
        plot_file = visualizer.plot_market_probabilities(market_data, event_title, event_slug)
        if plot_file:
            print(f"Generated plot: {plot_file}")
        
        # Compare with previous data if requested
        if compare:
            # Get the previous data file (excluding the one we just created)
            previous_files = [f for f in os.listdir(os.path.join(data_dir, "json")) 
                             if f.startswith(event_slug) and f.endswith(".json") 
                             and os.path.join(data_dir, "json", f) != json_file]
            
            if previous_files:
                # Sort by modification time (newest first)
                previous_files.sort(key=lambda x: os.path.getmtime(os.path.join(data_dir, "json", x)), reverse=True)
                previous_file = os.path.join(data_dir, "json", previous_files[0])
                
                print(f"Comparing with previous data: {previous_file}")
                previous_data = storage.load_json(previous_file)
                
                if previous_data and "market_data" in previous_data:
                    comparison_file = visualizer.plot_market_comparison(
                        market_data, previous_data["market_data"], event_title, event_slug)
                    
                    if comparison_file:
                        print(f"Generated comparison plot: {comparison_file}")
                else:
                    print("Could not load previous data for comparison.")
            else:
                print("No previous data found for comparison.")
    
    print(f"Processing completed for event: {event_title}")

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Create output directories
    data_dir, plots_dir = setup_directories(args.output_dir)
    
    # Initialize storage for listing events
    storage = DataStorage(data_dir)
    
    # List stored events if requested
    if args.list_events:
        list_stored_events(storage)
        return
    
    # Check if URL is provided when needed
    if not args.url:
        print("Error: No URL provided. Use --url to specify a Polymarket event URL.")
        print("Use --list-events to see all stored events.")
        return
    
    # Process the specified event
    process_event(args.url, args.no_plot, args.compare, data_dir, plots_dir)

if __name__ == "__main__":
    main() 