# src/polymarket/main.py

import os
import sys
import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from tabulate import tabulate

# Import our modules
from src.polymarket.api_client import PolymarketAPIClient
from src.polymarket.data_storage import DataStorage
from src.polymarket.visualization import Visualization

# Default Polymarket event URL
DEFAULT_URL = "https://polymarket.com/event/elon-musk-of-tweets-april-11-18-628?tid=1744890836764"

# Data output paths
DATA_DIR = Path("src/polymarket/data")
PLOTS_DIR = Path("src/polymarket/plots")

def setup_output_directories():
    """Set up necessary directories for data and visualization output."""
    # Create data directories
    (DATA_DIR / "json").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "csv").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "order_books").mkdir(parents=True, exist_ok=True)
    
    # Create visualizations directory
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    (PLOTS_DIR / "order_books").mkdir(parents=True, exist_ok=True)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Polymarket Data Analyzer")
    
    # Main arguments
    parser.add_argument("--url", type=str, default=DEFAULT_URL,
                        help="URL of the Polymarket event (default: {})".format(DEFAULT_URL))
    parser.add_argument("--save-data", action="store_true",
                        help="Save data to JSON and CSV files")
    parser.add_argument("--compare", action="store_true",
                        help="Compare with previous data for the same event")
    parser.add_argument("--list-events", action="store_true",
                        help="List stored events")
    parser.add_argument("--generate-plot", action="store_true",
                        help="Generate visualization plots for market probabilities")
    parser.add_argument("--order-frames", action="store_true",
                        help="Fetch and display order book frames")
    parser.add_argument("--detailed-orders", action="store_true",
                        help="Show detailed buy and sell orders (requires --order-frames)")
    parser.add_argument("--save-orders", action="store_true",
                        help="Save order book data to JSON (requires --order-frames)")
    parser.add_argument("--visualize-orders", action="store_true",
                        help="Generate visualizations of order books (requires --order-frames)")
    
    return parser.parse_args()

def process_event(url: str, save_data: bool = False, generate_plot: bool = False, compare: bool = False) -> bool:
    """
    Process a Polymarket event by fetching data, saving it, and visualizing it.
    
    Args:
        url: URL of the Polymarket event
        save_data: Whether to save data to files
        generate_plot: Whether to generate visualization plots
        compare: Whether to compare with previous data
        
    Returns:
        True if processing was successful, False otherwise
    """
    # Extract event slug and thread ID from the URL
    event_slug = PolymarketAPIClient.extract_slug_from_url(url)
    thread_id = PolymarketAPIClient.extract_tid_from_url(url)
    
    if not event_slug:
        print("Failed to extract event slug from URL. Please check the URL format.")
        return False
    
    # Extract data from Polymarket APIs
    market_data, event_title = PolymarketAPIClient.get_event_data(url)
    
    if not market_data:
        print("Failed to fetch data. Please check the URL and try again.")
        return False
    
    # Generate timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Initialize data storage
    data_storage = DataStorage(str(DATA_DIR))
    
    # Display market percentages
    print(f"\nEvent: {event_title}")
    print("\nMarket Percentages:")
    
    # Group by question to only show YES outcomes
    questions = {}
    for item in market_data:
        question = item.get('question', '')
        outcome = item.get('outcome', '')
        percentage = item.get('percentage', 0)
        
        # Only include valid percentages for YES outcomes
        if outcome.lower() == 'yes' and percentage is not None:
            questions[question] = percentage
    
    # Print sorted by percentage (descending)
    if questions:
        sorted_questions = sorted(questions.items(), key=lambda x: x[1], reverse=True)
        for question, percentage in sorted_questions:
            print(f"{percentage:.1f}% - {question}")
    else:
        print("No valid market percentages found.")
    
    # Save data if requested
    if save_data:
        json_path = str(DATA_DIR / "json" / f"{event_slug}_{timestamp}.json")
        csv_path = str(DATA_DIR / "csv" / f"{event_slug}_{timestamp}.csv")
        
        data_storage.save_json(event_slug, market_data, event_title)
        data_storage.save_csv(event_slug, market_data, event_title)
        
        print(f"\nData saved to {DATA_DIR / 'json'} and {DATA_DIR / 'csv'}")
    
    # Generate visualization if requested
    if generate_plot:
        visualization = Visualization()
        
        # Filter out markets with very low percentages (< 0.1%) to prevent visualization issues
        filtered_market_data = []
        for item in market_data:
            percentage = item.get('percentage', 0)
            if percentage is None or percentage < 0.1:
                continue
            filtered_market_data.append(item)
            
        # Only generate the plot if we have data that can be visualized
        if filtered_market_data:
            fig = visualization.plot_market_probabilities(filtered_market_data, event_title)
            plot_path = PLOTS_DIR / f"{event_slug}_probabilities.png"
            visualization.save_plot(fig, plot_path)
            
            print(f"\nVisualization saved to {plot_path}")
        else:
            print("\nNo valid data for visualization.")
        
        # Compare with previous data if requested
        if compare and save_data:
            # Find the most recent data file for this event (excluding the one we just created)
            previous_files = list(DATA_DIR.glob(f"json/{event_slug}_*.json"))
            previous_files = [f for f in previous_files if str(f) != json_path]
            
            if previous_files:
                # Sort by modification time (newest first)
                previous_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                previous_data_path = previous_files[0]
                
                # Load previous data
                previous_data = data_storage.load_json(str(previous_data_path))
                if previous_data:
                    # Filter previous data too
                    filtered_previous_data = []
                    for item in previous_data.get("market_data", []):
                        percentage = item.get('percentage', 0)
                        if percentage is None or percentage < 0.1:
                            continue
                        filtered_previous_data.append(item)
                    
                    # Generate comparison visualization if we have valid data
                    if filtered_previous_data and filtered_market_data:
                        compare_fig = visualization.plot_comparison(
                            current_data=filtered_market_data,
                            previous_data=filtered_previous_data,
                            event_title=f"{event_title} - Comparison"
                        )
                        
                        # Save comparison plot
                        compare_plot_path = PLOTS_DIR / f"{event_slug}_comparison.png"
                        visualization.save_plot(compare_fig, compare_plot_path)
                        print(f"Comparison visualization saved to {compare_plot_path}")
                    else:
                        print("No valid data for comparison visualization.")
                else:
                    print("Could not load previous data for comparison.")
            else:
                print("No previous data found for comparison.")
    
    print(f"\nProcessing for event '{event_title}' completed successfully.")
    
    return True

def list_stored_events():
    """List all stored events in the data directory."""
    json_files = list((DATA_DIR / "json").glob("*.json"))
    
    if not json_files:
        print("No stored events found.")
        return
    
    events = {}
    data_storage = DataStorage(str(DATA_DIR))
    
    for file_path in json_files:
        try:
            data = data_storage.load_json(str(file_path))
            if data:
                event_title = data.get("event_title", "Unknown Event")
                timestamp = file_path.stem.split("_")[-2:]
                timestamp_str = "_".join(timestamp)
                
                if event_title not in events:
                    events[event_title] = []
                
                events[event_title].append({
                    "timestamp": timestamp_str,
                    "file": file_path
                })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    print("Stored Events:")
    for event_title, timestamps in events.items():
        print(f"\n{event_title}")
        for entry in timestamps:
            print(f"  - {entry['timestamp']} ({entry['file']})")

def get_order_frames(url: str, detailed: bool = False, save_orders: bool = False, visualize_orders: bool = False):
    """
    Fetch and display order frames (buy/sell orders) for a Polymarket event.
    
    Args:
        url: URL of the Polymarket event
        detailed: Whether to show detailed order information
        save_orders: Whether to save order book data to JSON
        visualize_orders: Whether to generate visualizations of order books
    """
    # Extract event slug and thread ID from the URL
    event_slug = PolymarketAPIClient.extract_slug_from_url(url)
    thread_id = PolymarketAPIClient.extract_tid_from_url(url)
    
    if not event_slug:
        print("Could not extract event slug from URL.")
        return
    
    try:
        print(f"Fetching order frames for {url}")
        order_frames = PolymarketAPIClient.get_order_frames(event_slug, thread_id)
        
        if not order_frames:
            print("No order frames found for this event.")
            return
        
        # Display order frames for each market
        for question, frames in order_frames.items():
            # Check if data is synthetic
            is_synthetic = frames.get("is_synthetic", True)
            data_source = "[SYNTHETIC DATA]" if is_synthetic else "[REAL MARKET DATA]"
            
            print(f"\n\n== {question} ==")
            print(f"{data_source}")
            
            # Display buy orders (bids)
            buy_orders = frames.get("buy_orders", [])
            if buy_orders:
                # Sort buy orders by price (highest first)
                buy_orders.sort(key=lambda x: x["price"], reverse=True)
                
                # Determine how many orders to show
                display_orders = buy_orders if detailed else buy_orders[:5]
                
                print(f"\nBUY ORDERS (Bids) - {'All' if detailed else 'Top 5'}")
                buy_table = tabulate(
                    [[f"{order['price']:.1f}¢", f"{order['size']:.2f}", f"${order['total']:.2f}"] 
                     for order in display_orders],
                    headers=["Price", "Size", "Total"],
                    tablefmt="simple"
                )
                print(buy_table)
            else:
                print("\nNo buy orders found.")
            
            # Display sell orders (asks)
            sell_orders = frames.get("sell_orders", [])
            if sell_orders:
                # Sort sell orders by price (lowest first)
                sell_orders.sort(key=lambda x: x["price"])
                
                # Determine how many orders to show
                display_orders = sell_orders if detailed else sell_orders[:5]
                
                print(f"\nSELL ORDERS (Asks) - {'All' if detailed else 'Top 5'}")
                sell_table = tabulate(
                    [[f"{order['price']:.1f}¢", f"{order['size']:.2f}", f"${order['total']:.2f}"] 
                     for order in display_orders],
                    headers=["Price", "Size", "Total"],
                    tablefmt="simple"
                )
                print(sell_table)
            else:
                print("\nNo sell orders found.")
            
            # Calculate spread if both buy and sell orders exist
            if buy_orders and sell_orders:
                best_bid = buy_orders[0]["price"]
                best_ask = sell_orders[0]["price"]
                spread = best_ask - best_bid
                
                # Avoid division by zero
                if best_bid > 0:
                    spread_percentage = (spread / best_bid) * 100
                    print(f"\nMarket Spread: {spread:.1f}¢ ({spread_percentage:.2f}%)")
                else:
                    print(f"\nMarket Spread: {spread:.1f}¢")
                    
                # Add explanatory note for synthetic data
                if is_synthetic:
                    print("\nNote: This data is synthetically generated based on real midpoint prices.")
                    print("Orders are simulated and do not represent actual market liquidity.")
        
        # Save order book data if requested
        if save_orders:
            # Prepare the data for saving
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Get event title
            event_title = ""
            market_data, title = PolymarketAPIClient.get_event_data(url)
            if title:
                event_title = title
            
            # Create data structure
            order_data = {
                "event_slug": event_slug,
                "event_title": event_title,
                "timestamp": datetime.now().isoformat(),
                "order_frames": order_frames
            }
            
            # Save to JSON file
            order_book_dir = DATA_DIR / "order_books"
            order_book_dir.mkdir(exist_ok=True)
            json_path = order_book_dir / f"{event_slug}_orderbook_{timestamp}.json"
            
            with open(json_path, 'w') as f:
                json.dump(order_data, f, indent=2)
            
            print(f"\nOrder book data saved to {json_path}")
        
        # Generate visualizations if requested
        if visualize_orders:
            visualization = Visualization()
            
            # Get event title if not already fetched
            if 'event_title' not in locals() or not event_title:
                market_data, event_title = PolymarketAPIClient.get_event_data(url)
                if not event_title:
                    event_title = f"Event {event_slug}"
            
            # Generate visualizations
            figures = visualization.plot_order_book(order_frames, event_title)
            
            # Create directory for order book visualizations
            order_viz_dir = PLOTS_DIR / "order_books"
            order_viz_dir.mkdir(exist_ok=True)
            
            # Save each figure
            for question, fig in figures.items():
                # Create a safe filename from the question
                safe_question = "".join(c if c.isalnum() else "_" for c in question)
                safe_question = safe_question[:50]  # Limit length
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = order_viz_dir / f"{event_slug}_{safe_question}_{timestamp}.png"
                
                visualization.save_plot(fig, plot_path)
                print(f"Order book visualization for '{question}' saved to {plot_path}")
                
    except Exception as e:
        print(f"An error occurred while processing order frames: {e}")
        return

def main():
    """Main entry point for the Polymarket Data Analyzer."""
    args = parse_args()
    
    # Create output directories
    setup_output_directories()
    
    if args.list_events:
        list_stored_events()
        return
    
    # First, display the basic event information and percentages
    process_event(args.url, args.save_data, args.generate_plot, args.compare)
    
    # Only fetch and display order frames if explicitly requested
    if args.order_frames:
        get_order_frames(args.url, args.detailed_orders, args.save_orders, args.visualize_orders)

if __name__ == "__main__":
    main() 