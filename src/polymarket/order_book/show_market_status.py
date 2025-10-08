#!/usr/bin/env python3
"""
Show the current status of Polymarket order book for Elon Musk tweet markets.
Displays a summary of current market percentages and key statistics.
"""

import os
import re
import json
import glob
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import time
import sys

# Import from project
from src.constants import DATA_DIR, POLYMARKET_ELON_TWEETS_URL
from src.polymarket.api_client import PolymarketAPIClient
from src.polymarket.order_book.fetch_elon_market import fetch_elon_order_book

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_latest_order_book_file() -> Optional[str]:
    """Find the most recent order book data file."""
    # Get the path for stored order book data
    json_dir = DATA_DIR / "order_book" / "json"
    
    # Find all JSON files
    if not json_dir.exists():
        logger.warning("Order book data directory does not exist. No previous data found.")
        return None
        
    json_files = glob.glob(str(json_dir / "*.json"))
    
    if not json_files:
        logger.warning("No order book data files found.")
        return None
    
    # Get the most recent file based on modification time
    latest_file = max(json_files, key=os.path.getmtime)
    return latest_file

def load_order_book_data(file_path: str) -> Dict[str, Any]:
    """Load order book data from a JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def calculate_midpoint_price(buy_orders: List[Dict], sell_orders: List[Dict]) -> float:
    """Calculate the midpoint price from the best bid and ask."""
    if not buy_orders and not sell_orders:
        return 0.0
    
    # Sort orders by price
    buy_orders = sorted(buy_orders, key=lambda x: x.get('price', 0), reverse=True)
    sell_orders = sorted(sell_orders, key=lambda x: x.get('price', 0))
    
    best_bid = buy_orders[0]['price'] if buy_orders else 0
    best_ask = sell_orders[0]['price'] if sell_orders else 100
    
    # If we have both, return the midpoint
    if buy_orders and sell_orders:
        return (best_bid + best_ask) / 2
    
    # Otherwise, return the one we have
    return best_bid if buy_orders else best_ask

def calculate_market_stats(order_book_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate statistics for market data."""
    questions = order_book_data.get('questions', {})
    event_title = order_book_data.get('event_title', 'Polymarket Order Book')
    timestamp = order_book_data.get('timestamp', datetime.now().isoformat())
    
    # Try to parse timestamp into a datetime object
    try:
        dt = datetime.fromisoformat(timestamp)
        timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        timestamp_str = timestamp
    
    # Calculate stats for each market
    market_stats = {}
    for question, market_data in questions.items():
        buy_orders = market_data.get('buy_orders', [])
        sell_orders = market_data.get('sell_orders', [])
        
        # Calculate midpoint price (probability)
        midpoint = calculate_midpoint_price(buy_orders, sell_orders)
        
        # Calculate total liquidity (sum of all bids and asks)
        total_bid_size = sum(order.get('size', 0) for order in buy_orders)
        total_ask_size = sum(order.get('size', 0) for order in sell_orders)
        total_liquidity = total_bid_size + total_ask_size
        
        # Calculate bid-ask spread
        best_bid = max([order.get('price', 0) for order in buy_orders]) if buy_orders else 0
        best_ask = min([order.get('price', 0) for order in sell_orders]) if sell_orders else 100
        spread = best_ask - best_bid if (buy_orders and sell_orders) else None
        
        # Store the stats, including token_id if available
        market_stats[question] = {
            'midpoint': midpoint,
            'best_bid': best_bid,
            'best_ask': best_ask,
            'spread': spread,
            'bid_liquidity': total_bid_size,
            'ask_liquidity': total_ask_size,
            'total_liquidity': total_liquidity,
            'token_id': market_data.get('token_id', None),  # Include token_id if available
            'market_id': market_data.get('market_id', None)  # Include market_id if available
        }
    
    return {
        'event_title': event_title,
        'timestamp': timestamp_str,
        'markets': market_stats
    }

def extract_range_value(question: str) -> Tuple[float, float]:
    """Extract the numeric range from a market question."""
    # Normalize for parsing
    q = question.lower().strip()

    # Handle explicit patterns first
    # e.g., "500+ tweets"
    plus_match = re.search(r'(\d+)\s*\+', q)
    if plus_match:
        try:
            lower = float(plus_match.group(1))
            return lower, float('inf')
        except ValueError:
            pass

    # Handle special cases
    if 'less than' in question.lower():
        parts = q.split('less than')
        if len(parts) > 1:
            try:
                upper = float(parts[1].strip().split()[0])
                return 0, upper
            except (ValueError, IndexError):
                return 0, 100
    
    if 'or more' in q:
        parts = q.split('or more')
        if len(parts) > 1:
            try:
                # Extract the last number before "or more"
                nums = re.findall(r'(\d+)', parts[0])
                lower = float(nums[-1]) if nums else 0
                return lower, float('inf')
            except (ValueError, IndexError):
                return 400, float('inf')
    
    # Handle standard ranges like "175–199" or "175-199" anywhere in the string
    range_match = re.search(r'(\d+)\s*[–-]\s*(\d+)', q)
    if range_match:
        try:
            lower = float(range_match.group(1))
            upper = float(range_match.group(2))
            return lower, upper
        except ValueError:
            pass
    
    # Fallback to 0, 0 if we can't parse
    return 0, 0

def get_market_data_json(refresh: bool = True) -> Dict[str, Any]:
    """
    Get the current market status data in JSON format.
    
    This function runs the same process as show_market_status with --quick --refresh --token-ids
    but instead of displaying the data, it returns it as a structured JSON object.
    
    Args:
        refresh: If True, fetch fresh data from Polymarket, otherwise use cached data
        
    Returns:
        Dict[str, Any]: A dictionary containing structured market data with the following keys:
            - timestamp: ISO format timestamp
            - event_title: Title of the event
            - ranges: List of range names
            - markets: Dictionary mapping range names to market data
                - probability: Midpoint probability (%)
                - bid: Best bid price (%)
                - ask: Best ask price (%)
                - spread: Spread between best bid and ask (%)
                - liquidity: Total liquidity
                - token_id: Token ID for trading
    """
    # Temporarily suppress output
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    
    # Set logging to critical to suppress most logs
    original_level = logger.level
    logger.setLevel(logging.CRITICAL)
    logging.getLogger().setLevel(logging.CRITICAL)
    
    try:
        if refresh:
            # Fetch fresh order book data with minimal output
            output_path = fetch_elon_order_book()
            if not output_path:
                logger.error("Failed to fetch fresh order book data.")
                return {"error": "Failed to fetch fresh order book data"}
            file_path = output_path
        else:
            # Find the most recent order book file
            file_path = find_latest_order_book_file()
            if not file_path:
                logger.warning("No order book data found. Fetching fresh data...")
                output_path = fetch_elon_order_book()
                if not output_path:
                    logger.error("Failed to fetch order book data.")
                    return {"error": "Failed to fetch order book data"}
                file_path = output_path
        
        # Load the order book data
        order_book_data = load_order_book_data(file_path)
        
        # Extract event title
        event_title = order_book_data.get('event_title', 'Unknown Event')
        
        # Calculate stats
        stats = calculate_market_stats(order_book_data)
        
        # Process the data into a more convenient format
        ranges = []
        market_data = {}
        
        # Sort markets based on their range
        sorted_markets_for_calculation = []  # This will be used for expected value calculation
        sorted_markets_for_display = []      # This will be used for display formatting
        
        for question, question_stats in stats.get('markets', {}).items():
            lower, upper = extract_range_value(question)

            # Derive a clean, standardized display name matching prediction frames
            name = None
            q_lower = question.lower()
            # Less than X
            lt_match = re.search(r'less than\s+(\d+)', q_lower)
            if lt_match:
                name = f"<{int(lt_match.group(1))}"
            # X+
            if name is None:
                plus_match = re.search(r'(\d+)\s*\+', q_lower)
                if plus_match:
                    name = f"{int(plus_match.group(1))}+"
            # X–Y or X-Y
            if name is None and lower > 0 and upper > 0 and upper != float('inf'):
                name = f"{int(lower)}–{int(upper)}"
            # Fallback: attempt to strip leading question text and dates
            if name is None:
                display_name = question
                # Remove common prefixes irrespective of capitalization
                display_name = re.sub(r'^will\s+elon\s+musk\s+post\s+', '', display_name, flags=re.IGNORECASE)
                display_name = re.sub(r'^will\s+elon\s+tweet\s+', '', display_name, flags=re.IGNORECASE)
                # Remove dates like "from October 3 to October 10, 2025?"
                display_name = re.sub(r'\s*from\s+[a-z]+\s+\d+\s+to\s+[a-z]+\s+\d+(,\s*\d{4})?\??', '', display_name, flags=re.IGNORECASE)
                display_name = display_name.replace('times', '').replace('tweets', '').strip()
                name = display_name

            short_name = name
            
            # Add to display list with 5 elements
            sorted_markets_for_display.append((lower, upper, short_name, question_stats, question))
            
            # Add to calculation list with 4 elements (matching the expected format for calculate_expected_value)
            sorted_markets_for_calculation.append((lower, upper, short_name, question_stats))
        
        # Sort both lists
        sorted_markets_for_display.sort(key=lambda x: x[0])
        sorted_markets_for_calculation.sort(key=lambda x: x[0])
        
        # Calculate total market liquidity and expected value
        total_market_liquidity = sum(m[3].get('total_liquidity', 0) for m in sorted_markets_for_calculation)
        expected_value = calculate_expected_value(sorted_markets_for_calculation)
        
        # Process sorted markets into our return format
        for lower, upper, display_name, stats, original_question in sorted_markets_for_display:
            ranges.append(display_name)
            
            # Extract and clean the token_id 
            token_id = stats.get('token_id', "N/A")
            # Ensure token ID is a clean string without newlines or extra spaces
            if isinstance(token_id, str):
                token_id = token_id.strip()
            
            market_data[display_name] = {
                "probability": round(stats.get('midpoint', 0), 2),
                "bid": round(stats.get('best_bid', 0), 2),
                "ask": round(stats.get('best_ask', 0), 2),
                "spread": round(stats.get('spread', 0) if stats.get('spread') is not None else 0, 2),
                "bid_liquidity": round(stats.get('bid_liquidity', 0), 2),
                "ask_liquidity": round(stats.get('ask_liquidity', 0), 2),
                "liquidity": round(stats.get('total_liquidity', 0), 2),
                "token_id": token_id,
                "market_id": stats.get('market_id', None),
                "original_question": original_question
            }
        
        # Find most likely outcome
        if sorted_markets_for_calculation:
            likely_market = max(sorted_markets_for_calculation, key=lambda x: x[3].get('midpoint', 0))
            most_likely = {
                "range": likely_market[2],
                "probability": round(likely_market[3].get('midpoint', 0), 2)
            }
        else:
            most_likely = {
                "range": "Unknown",
                "probability": 0
            }
        
        # Create the final structured data
        result = {
            "timestamp": datetime.now().isoformat(),
            "event_title": event_title,
            "ranges": ranges,
            "markets": market_data,
            "summary": {
                "expected_value": round(expected_value, 2),
                "total_liquidity": round(total_market_liquidity, 2),
                "most_likely": most_likely
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        return {"error": str(e)}
    finally:
        # Always restore logging level and stdout
        logger.setLevel(original_level)
        logging.getLogger().setLevel(original_level)
        sys.stdout = original_stdout

def display_market_status(stats: Dict[str, Any], refresh: bool = False, quick: bool = False, all_data: bool = False, elapsed_time: float = None, show_token_ids: bool = False) -> None:
    """
    Display the market status in the terminal.
    
    Args:
        stats: The market statistics
        refresh: Whether to clear the screen
        quick: Whether to show minimal information (just main table)
        all_data: Whether to show all available data including extra stats
        elapsed_time: Time taken to fetch and process data (if available)
        show_token_ids: Whether to show token IDs for each market
    """
    event_title = stats.get('event_title', 'Unknown Event')
    timestamp = stats.get('timestamp', 'Unknown Time')
    markets = stats.get('markets', {})
    
    # Clear screen if refreshing and not in quick mode
    if refresh and not quick:
        os.system('cls' if os.name == 'nt' else 'clear')
    
    # Sort markets based on their range
    sorted_markets = []
    for question, stats in markets.items():
        lower, upper = extract_range_value(question)
        display_name = question.replace('Will Elon tweet ', '').strip()
        sorted_markets.append((lower, upper, display_name, stats))
    
    sorted_markets.sort(key=lambda x: x[0])  # Sort by lower bound
    
    # Calculate total market liquidity
    total_market_liquidity = sum(m[3].get('total_liquidity', 0) for m in sorted_markets)
    
    # Quick mode shows minimal header and simplified table
    if quick and not all_data:
        # Ultra-compact display for quick mode
        if not refresh:  # Only show title first time or when not refreshing
            print(f"\n{event_title} - {timestamp}")
            if elapsed_time:
                print(f"Data processed in {elapsed_time:.2f} seconds")
        
        # Print compact table with probabilities only
        header_printed = False
        
        # Show arrows for probability change if we had previous data
        prev_probs = getattr(display_market_status, 'prev_probs', {})
        current_probs = {}
        
        # Very minimal format for just probabilities
        for lower, upper, display_name, stats in sorted_markets:
            midpoint = stats.get('midpoint', 0)
            best_bid = stats.get('best_bid', 0)
            best_ask = stats.get('best_ask', 0)
            spread = stats.get('spread', None)
            liquidity = stats.get('total_liquidity', 0)
            token_id = stats.get('token_id', "N/A")
            current_probs[display_name] = midpoint
            
            # Show header only before first item
            if not header_printed:
                header = "\nRANGE                   PROB      BID      ASK    SPREAD   LIQUIDITY"
                print(header)
                header_printed = True
                
            # Make the display name shorter by removing the date part if it exists
            short_name = display_name.split('April')[0].strip() if 'April' in display_name else display_name
            short_name = short_name.replace('times', '').strip()
            
            # Format spread string
            spread_str = f"{spread:.1f}" if spread is not None else "N/A"
            
            # Format with essential info including bid, ask, spread and liquidity
            print(f"{short_name:<20} {midpoint:>5.1f}%  {best_bid:>5.1f}%  {best_ask:>5.1f}%  {spread_str:>5}  {liquidity:>9.2f}")
        
        # Store current probabilities for next time
        display_market_status.prev_probs = current_probs
        
        # Show just the most likely and expected in a compact format
        likely_market = max(sorted_markets, key=lambda x: x[3].get('midpoint', 0))
        expected_value = calculate_expected_value(sorted_markets)
        
        # Extract just the range part without dates
        likely_range = likely_market[2].split('April')[0].strip() if 'April' in likely_market[2] else likely_market[2]
        likely_range = likely_range.replace('times', '').strip()
        
        print(f"\nMost likely: {likely_range} ({likely_market[3].get('midpoint', 0):.1f}%)")
        print(f"Expected tweets: {expected_value:.1f}")
        print(f"Total market liquidity: {total_market_liquidity:.2f}")
        
        # Display token IDs if requested
        if show_token_ids:
            print("\nToken IDs:")
            for _, _, display_name, stats in sorted_markets:
                short_name = display_name.split('April')[0].strip() if 'April' in display_name else display_name
                short_name = short_name.replace('times', '').strip()
                token_id = stats.get('token_id', "N/A")
                print(f"{short_name:<20}: {token_id}")
    else:
        # Standard mode - full header
        if not quick:
            print("\n" + "=" * 80)
            print(f" POLYMARKET ORDER BOOK STATUS: {event_title}")
            print(f" Data from: {timestamp}")
            if elapsed_time:
                print(f" Data processed in {elapsed_time:.2f} seconds")
            print("=" * 80)
        else:
            print(f"\n{event_title} - {timestamp}")
            if elapsed_time:
                print(f"Data processed in {elapsed_time:.2f} seconds")
            print()
        
        # Print full market data table based on detail level
        if all_data:
            print(f"\n{'RANGE':<20} {'PROB %':<10} {'BID':<8} {'ASK':<8} {'SPREAD':<8} {'BID SIZE':<10} {'ASK SIZE':<10} {'LIQUIDITY':<10}\n")
        else:
            print(f"\n{'RANGE':<20} {'PROB %':<10} {'BID':<8} {'ASK':<8} {'SPREAD':<8} {'LIQUIDITY':<10}\n")
        
        for _, _, display_name, stats in sorted_markets:
            midpoint = stats.get('midpoint', 0)
            best_bid = stats.get('best_bid', 0)
            best_ask = stats.get('best_ask', 0)
            spread = stats.get('spread', None)
            bid_liquidity = stats.get('bid_liquidity', 0)
            ask_liquidity = stats.get('ask_liquidity', 0)
            total_liquidity = stats.get('total_liquidity', 0)
            
            # Format spread string
            spread_str = f"{spread:.1f}" if spread is not None else "N/A"
            
            # Print the row
            if all_data:
                print(f"{display_name:<20} {midpoint:>6.1f}%  {best_bid:>6.1f}%  {best_ask:>6.1f}%  {spread_str:>6}  {bid_liquidity:>9.2f}  {ask_liquidity:>9.2f}  {total_liquidity:>9.2f}")
            else:
                print(f"{display_name:<20} {midpoint:>6.1f}%  {best_bid:>6.1f}%  {best_ask:>6.1f}%  {spread_str:>6}  {total_liquidity:>9.2f}")
    
        if not quick:
            print("\n" + "=" * 80)
            
            # Most likely outcome
            likely_market = max(sorted_markets, key=lambda x: x[3].get('midpoint', 0))
            print(f" Most likely outcome: {likely_market[2]} ({likely_market[3].get('midpoint', 0):.1f}%)")
            
            # Calculate expected value
            expected_value = calculate_expected_value(sorted_markets)
            print(f" Expected tweet count: {expected_value:.1f} tweets")
            
            # Additional statistics for all_data mode
            if all_data:
                print(f" Total markets: {len(sorted_markets)}")
                total_liquidity = sum(m[3].get('total_liquidity', 0) for m in sorted_markets)
                print(f" Total liquidity: {total_liquidity:.2f}")
                
                # Calculate market with tightest spread
                valid_markets = [(name, stats) for _, _, name, stats in sorted_markets if stats.get('spread') is not None]
                if valid_markets:
                    tightest = min(valid_markets, key=lambda x: x[1].get('spread', float('inf')))
                    print(f" Tightest spread: {tightest[0]} ({tightest[1].get('spread', 0):.1f}%)")
            
            print("=" * 80 + "\n")
        
        # Display token IDs if requested
        if show_token_ids:
            print("\nToken IDs:")
            for _, _, display_name, stats in sorted_markets:
                short_name = display_name.split('April')[0].strip() if 'April' in display_name else display_name
                short_name = short_name.replace('times', '').strip()
                token_id = stats.get('token_id', "N/A")
                print(f"{short_name:<20}: {token_id}")

def calculate_expected_value(sorted_markets: List[Tuple]) -> float:
    """Calculate the expected value from the market probabilities."""
    total_prob = sum(m[3].get('midpoint', 0) for m in sorted_markets)
    expected_value = 0
    if total_prob > 0:
        for lower, upper, _, stats in sorted_markets:
            if upper == float('inf'):  # Handle "400 or more" case
                midpoint = 400  # Use minimum value for "or more"
            else:
                midpoint = (lower + upper) / 2
            prob = stats.get('midpoint', 0) / 100  # Convert to probability
            expected_value += midpoint * prob
    return expected_value

def visualize_terminal_chart(stats: Dict[str, Any]) -> None:
    """Generate a simple ASCII chart of market probabilities in the terminal."""
    markets = stats.get('markets', {})
    
    # Sort markets based on their range
    sorted_markets = []
    for question, stats in markets.items():
        lower, upper = extract_range_value(question)
        display_name = question.replace('Will Elon tweet ', '').strip()
        sorted_markets.append((lower, upper, display_name, stats))
    
    sorted_markets.sort(key=lambda x: x[0])  # Sort by lower bound
    
    # Find the market with the highest probability
    max_prob = max(m[3].get('midpoint', 0) for m in sorted_markets)
    scale_factor = 40 / max(max_prob, 1)  # Scale to 40 characters width
    
    print("\nMARKET PROBABILITY CHART (each █ = approximately 2.5%)\n")
    
    for _, _, display_name, stats in sorted_markets:
        midpoint = stats.get('midpoint', 0)
        bar_length = int(midpoint * scale_factor)
        bar = "█" * bar_length
        print(f"{display_name:<20} {midpoint:>5.1f}% | {bar}")
    
    print("")

def show_market_status(refresh: bool = False, interval: int = 0, 
                     quick: bool = False, all_data: bool = False, 
                     visualize: bool = False, show_token_ids: bool = False) -> None:
    """
    Display current market status from the most recent order book data.
    
    Args:
        refresh: If True, refresh the data from Polymarket
        interval: Refresh interval in seconds, 0 for no refresh
        quick: If True, show minimal information for faster viewing
        all_data: If True, show all available data including extra stats
        visualize: If True, include terminal-based visualization
        show_token_ids: If True, show token IDs for each market
    """
    # Start timing the operation
    start_time = time.time()
    
    # Suppress all output if in quick mode
    if quick:
        # Redirect stdout temporarily to suppress fetch_elon_order_book output
        original_stdout = sys.stdout
        if refresh:
            sys.stdout = open(os.devnull, 'w')
    
    # Set logging to critical to suppress most logs in quick mode
    original_level = logger.level
    if quick:
        logger.setLevel(logging.CRITICAL)
        # Also set root logger to critical
        logging.getLogger().setLevel(logging.CRITICAL)
    
    try:
        if refresh:
            # Fetch fresh order book data with minimal output
            output_path = fetch_elon_order_book()
            if not output_path:
                if quick:
                    # Restore stdout before printing error
                    sys.stdout = original_stdout
                logger.error("Failed to fetch fresh order book data.")
                return
            file_path = output_path
        else:
            # Find the most recent order book file
            file_path = find_latest_order_book_file()
            if not file_path:
                logger.warning("No order book data found. Fetching fresh data...")
                # Temporarily suppress output for fetch operation
                if quick:
                    sys.stdout = open(os.devnull, 'w')
                output_path = fetch_elon_order_book()
                if quick:
                    sys.stdout = original_stdout
                if not output_path:
                    logger.error("Failed to fetch order book data.")
                    return
                file_path = output_path
    
        # Restore stdout for quick mode
        if quick and refresh:
            sys.stdout = original_stdout
        
        # Load the order book data
        order_book_data = load_order_book_data(file_path)
        
        # Calculate stats
        stats = calculate_market_stats(order_book_data)
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # If interval is set, continuously update
        if interval > 0:
            try:
                while True:
                    # Display the stats (refresh flag controls whether to clear the screen)
                    display_market_status(stats, refresh=refresh, quick=quick, all_data=all_data, 
                                         elapsed_time=elapsed_time, show_token_ids=show_token_ids)
                    
                    # Show visualization if requested
                    if visualize:
                        visualize_terminal_chart(stats)
                    
                    # Wait for the specified interval
                    if not quick:
                        print(f"Refreshing in {interval} seconds... (Press Ctrl+C to exit)")
                    time.sleep(interval)
                    
                    # Reset timer for the next refresh
                    refresh_start_time = time.time()
                    
                    # Fetch fresh data
                    if quick:
                        sys.stdout = open(os.devnull, 'w')
                    
                    output_path = fetch_elon_order_book()
                    
                    if quick:
                        sys.stdout = original_stdout
                    
                    if output_path:
                        order_book_data = load_order_book_data(output_path)
                        stats = calculate_market_stats(order_book_data)
                        # Update elapsed time for this refresh
                        elapsed_time = time.time() - refresh_start_time
                    else:
                        logger.error("Failed to refresh data. Using previous data.")
            except KeyboardInterrupt:
                print("\nExiting market status view.")
        else:
            # Display the stats once
            display_market_status(stats, refresh=refresh, quick=quick, all_data=all_data, 
                                 elapsed_time=elapsed_time, show_token_ids=show_token_ids)
            
            # Show visualization if requested
            if visualize:
                visualize_terminal_chart(stats)
    finally:
        # Always restore logging level and stdout
        logger.setLevel(original_level)
        logging.getLogger().setLevel(original_level)
        if quick and 'original_stdout' in locals():
            sys.stdout = original_stdout

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Show current Polymarket order book status for Elon Musk tweet markets"
    )
    parser.add_argument(
        "--refresh", 
        action="store_true", 
        help="Fetch fresh data from Polymarket instead of using cached data"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        default=0,
        help="Refresh interval in seconds (0 for no refresh)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Show compact output with probabilities, bid/ask prices, spreads, and liquidity"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all available data including extra statistics"
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Include simple terminal-based visualization of market probabilities"
    )
    parser.add_argument(
        "--token-ids",
        action="store_true",
        help="Display token IDs for each market"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output data in JSON format instead of displaying in terminal"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save the JSON output to specified file instead of printing to console"
    )
    args = parser.parse_args()
    
    # If JSON output is requested, get the data and print it
    if args.json:
        market_data = get_market_data_json(refresh=args.refresh)
        
        # If output file is specified, save to file
        if args.output:
            try:
                with open(args.output, 'w') as f:
                    json.dump(market_data, f, indent=2, ensure_ascii=False)
                print(f"Market data saved to {args.output}")
            except Exception as e:
                print(f"Error saving to file: {e}")
                # Fallback to printing
                print(json.dumps(market_data, indent=2, ensure_ascii=False))
        else:
            # Print with settings to avoid truncation and handle Unicode characters
            try:
                # Try to import the rich library for better JSON formatting
                from rich.console import Console
                from rich.json import JSON
                
                console = Console()
                # Parse and then render to ensure proper formatting
                json_str = json.dumps(market_data, ensure_ascii=False)
                console.print(JSON(json_str))
            except ImportError:
                # Fallback to standard JSON printing if rich is not available
                print(json.dumps(market_data, indent=2, ensure_ascii=False))
    else:
        # Otherwise show the market status in the terminal
        show_market_status(
            refresh=args.refresh, 
            interval=args.interval,
            quick=args.quick,
            all_data=args.all,
            visualize=args.visualize,
            show_token_ids=args.token_ids
        )

if __name__ == "__main__":
    main() 