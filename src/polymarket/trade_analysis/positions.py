#!/usr/bin/env python
"""
Standalone script for Polymarket position analysis.
This script focuses only on position tracking and PnL calculations.
"""

import os
import sys
from datetime import datetime
import traceback
import requests
import time
import argparse
import json
import subprocess

# Add the parent directory to the path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Import the analyzer and constants
from src.polymarket.trade_analysis import PolymarketTradeAnalyzer
from src.constants import POLYMARKET_START_TIME, POLYMARKET_END_TIME


def get_market_name(market_id):
    """
    Fetch market name from Polymarket API.
    
    Args:
        market_id (str): Market ID to fetch information for.
    
    Returns:
        str: Market name or None if not found.
    """
    api_endpoints = [
        f"https://clob.polymarket.com/markets/{market_id}",
        f"https://polymarket.com/api/markets/{market_id}",
        f"https://polymarket.com/api/v2/markets/{market_id}",
        f"https://gamma-api.polymarket.com/markets/{market_id}"
    ]
    
    for endpoint in api_endpoints:
        try:
            # Add headers to appear as a browser request
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json",
                "Referer": "https://polymarket.com/"
            }
            
            response = requests.get(endpoint, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Try different potential field names for the market name
                for field in ['title', 'name', 'question', 'marketName', 'market_name', 'description']:
                    if field in data:
                        return data[field]
                
                # If the data has a 'data' field, check inside it
                if 'data' in data:
                    data_obj = data['data']
                    for field in ['title', 'name', 'question', 'marketName', 'market_name', 'description']:
                        if field in data_obj:
                            return data_obj[field]
                
                # Return any data we got if we couldn't find a name field
                return str(data)[:50] + "..."
        except Exception as e:
            continue
    
    # If all endpoints fail, return a shortened version of the market ID
    return f"{market_id[:10]}..."


def get_market_data_from_order_book():
    """
    Get comprehensive market data directly from the order book module.
    
    Returns:
        dict: Dictionary containing market data with prices and token IDs
    """
    try:
        # Build the command to run with JSON output
        cmd = ["python", "-m", "src.polymarket.order_book.show_market_status", "--json", "--refresh"]
        
        # Run the command and capture the output
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the JSON output
        try:
            market_data = json.loads(result.stdout)
            print(f"Successfully fetched data for {len(market_data.get('markets', {}))} markets")
            return market_data
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from order book output: {e}")
            # Try to extract JSON part if there's extra text
            stdout = result.stdout
            json_start = stdout.find('{')
            json_end = stdout.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                json_str = stdout[json_start:json_end+1]
                try:
                    market_data = json.loads(json_str)
                    print(f"Successfully extracted JSON for {len(market_data.get('markets', {}))} markets")
                    return market_data
                except json.JSONDecodeError:
                    print("Failed to extract valid JSON")
            
            return {}
    except subprocess.CalledProcessError as e:
        print(f"Error running order book command: {e}")
        print(f"Command output: {e.stderr}")
        return {}


def get_order_book_data(refresh=True):
    """
    Get order book data from the Polymarket order book module.
    
    Args:
        refresh: Whether to fetch fresh data
        
    Returns:
        Dict containing market data
    """
    try:
        # Build the command to run
        cmd = ["python", "-m", "src.polymarket.order_book.show_market_status", "--json"]
        if refresh:
            cmd.append("--refresh")
        
        # Run the command and capture the output
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the JSON output
        market_data = json.loads(result.stdout)
        return market_data
    except subprocess.CalledProcessError as e:
        print(f"Error running market command: {e}")
        print(f"Command output: {e.stderr}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing market JSON: {e}")
        return {}


def find_market_data_by_id(market_id, order_book_data):
    """
    Find market data for a specific market ID in the order book data.
    
    Args:
        market_id (str): The market ID to find
        order_book_data (dict): The order book data
        
    Returns:
        tuple: (bid_price, ask_price) or (0, 0) if not found
    """
    # Check if we have market data
    if not order_book_data or 'markets' not in order_book_data:
        print(f"No market data available or missing 'markets' key")
        return 0, 0
        
    # Debug info
    print(f"Looking for market ID: {market_id}")
    print(f"Available markets: {len(order_book_data['markets'])} ranges")
    
    # First, try direct market ID match
    for range_name, market_info in order_book_data['markets'].items():
        market_id_in_data = market_info.get('market_id')
        if market_id_in_data and market_id_in_data.lower() == market_id.lower():
            print(f"Found exact match for market ID in '{range_name}'")
            bid_price = market_info.get('bid', 0)
            ask_price = market_info.get('ask', 0)
            return bid_price, ask_price
    
    # Second, try token ID match (sometimes the market ID is embedded in the token ID)
    for range_name, market_info in order_book_data['markets'].items():
        token_id = market_info.get('token_id')
        if token_id and (market_id.lower() in token_id.lower()):
            print(f"Found market ID in token ID for '{range_name}'")
            bid_price = market_info.get('bid', 0)
            ask_price = market_info.get('ask', 0)
            return bid_price, ask_price
    
    # Third, try partial matches on either ID
    for range_name, market_info in order_book_data['markets'].items():
        market_id_in_data = market_info.get('market_id', '')
        token_id = market_info.get('token_id', '')
        
        # Get first 10 chars of each for comparison
        market_id_prefix = market_id[:10].lower()
        data_market_id_prefix = market_id_in_data[:10].lower() if market_id_in_data else ''
        
        if (data_market_id_prefix and market_id_prefix == data_market_id_prefix) or \
           (token_id and market_id_prefix in token_id.lower()):
            print(f"Found partial match for market ID in '{range_name}'")
            bid_price = market_info.get('bid', 0)
            ask_price = market_info.get('ask', 0)
            return bid_price, ask_price
    
    # If not found, print debug info and return zeros
    print(f"Could not find market data for ID: {market_id}")
    return 0, 0


def get_market_names_and_prices_for_positions(positions):
    """
    Fetch market names and current prices for all positions.
    
    Args:
        positions (dict): Dictionary of positions with market IDs.
    
    Returns:
        tuple: (market_names, market_bid_prices, market_ask_prices) dictionaries
    """
    market_names = {}
    market_bid_prices = {}
    market_ask_prices = {}
    
    # First, identify all unique markets and determine which ones are active
    all_market_ids = set()
    active_market_ids = set()
    
    for key, position in positions.items():
        market_id = position['market_id']
        all_market_ids.add(market_id)
        
        # Try to get the market name
        if market_id not in market_names:
            market_name = get_market_name(market_id)
            market_names[market_id] = market_name
            
            # Check if this is an active market
            if is_active_market(market_name):
                active_market_ids.add(market_id)
    
    print(f"Found {len(all_market_ids)} unique markets, {len(active_market_ids)} are active")
    
    # If we have any active markets and positions, only fetch data for those
    market_ids_to_process = active_market_ids if len(active_market_ids) > 0 else all_market_ids
    
    # Get market data directly from the order book module
    print("Fetching market data from order book...")
    order_book_data = get_market_data_from_order_book()
    
    # Create a mapping from range names to price data
    market_ranges_data = {}
    if 'markets' in order_book_data:
        for range_name, market_info in order_book_data['markets'].items():
            # Clean up the range name (e.g., "100–124  May 23–30?" -> "100–124")
            clean_range = range_name.split()[0] if ' ' in range_name else range_name
            
            market_ranges_data[clean_range] = {
                'bid': market_info.get('bid', 0) / 100.0,  # Convert to decimal
                'ask': market_info.get('ask', 0) / 100.0,  # Convert to decimal
                'token_id': market_info.get('token_id', None),
                'original_name': range_name
            }
            
            # Also store with the full name as key for alternative matching
            market_ranges_data[range_name] = {
                'bid': market_info.get('bid', 0) / 100.0,
                'ask': market_info.get('ask', 0) / 100.0,
                'token_id': market_info.get('token_id', None),
                'original_name': range_name
            }
    
    # Process each market ID to assign prices
    for market_id in market_ids_to_process:
        market_name = market_names[market_id]
        
        # Initialize prices to zero
        bid_price = 0
        ask_price = 0
        matched_range = None
        
        # Try to match the market name to a range in our data
        for range_name, data in market_ranges_data.items():
            if range_name in market_name:
                bid_price = data['bid']
                ask_price = data['ask']
                matched_range = data['original_name']
                print(f"Found prices for '{range_name}' in '{market_name}'")
                print(f"  Bid: {bid_price:.4f}, Ask: {ask_price:.4f}")
                break
        
        # If no match by range name, try matching parts
        if matched_range is None:
            # Extract ranges like "100-124" or "100–124" from the market name
            import re
            range_pattern = r'(\d+)[-–](\d+)'
            matches = re.search(range_pattern, market_name)
            
            if matches:
                range_text = f"{matches.group(1)}–{matches.group(2)}"
                alt_range_text = f"{matches.group(1)}-{matches.group(2)}"
                
                for range_name, data in market_ranges_data.items():
                    if range_text in range_name or alt_range_text in range_name:
                        bid_price = data['bid']
                        ask_price = data['ask']
                        matched_range = data['original_name']
                        print(f"Found prices by range pattern '{range_text}' in '{range_name}'")
                        print(f"  Bid: {bid_price:.4f}, Ask: {ask_price:.4f}")
                        break
        
        # If still no match, try "less than" or "or more" patterns
        if matched_range is None:
            if "less than" in market_name.lower():
                for range_name, data in market_ranges_data.items():
                    if "less than" in range_name.lower():
                        bid_price = data['bid']
                        ask_price = data['ask']
                        matched_range = data['original_name']
                        print(f"Found prices for 'less than' in '{range_name}'")
                        print(f"  Bid: {bid_price:.4f}, Ask: {ask_price:.4f}")
                        break
            
            elif "or more" in market_name.lower() or "350" in market_name:
                for range_name, data in market_ranges_data.items():
                    if "or more" in range_name.lower() or range_name.startswith("350"):
                        bid_price = data['bid']
                        ask_price = data['ask']
                        matched_range = data['original_name']
                        print(f"Found prices for '350 or more' in '{range_name}'")
                        print(f"  Bid: {bid_price:.4f}, Ask: {ask_price:.4f}")
                        break
        
        # Store the prices
        market_bid_prices[market_id] = bid_price
        market_ask_prices[market_id] = ask_price
        
        match_status = "MATCHED" if matched_range else "NO MATCH"
        print(f"Final prices for {market_name} ({match_status}): Bid={bid_price:.4f}, Ask={ask_price:.4f}")
    
    return market_names, market_bid_prices, market_ask_prices


def is_active_market(market_name):
    """
    Determine if a market is active based on the date range in constants.py.
    
    Args:
        market_name (str): The market name to check.
        
    Returns:
        bool: True if the market is active, False otherwise.
    """
    # Extract the dates from the constants (format: "YYYY-MM-DD HH:MM:SS")
    active_start_date = POLYMARKET_START_TIME.split(" ")[0]
    active_end_date = POLYMARKET_END_TIME.split(" ")[0]
    
    # Format the date range for pattern matching
    active_start_month = active_start_date.split('-')[1]
    active_start_day = active_start_date.split('-')[2]
    active_end_month = active_end_date.split('-')[1]
    active_end_day = active_end_date.split('-')[2]
    
    # Create patterns to match for active market
    patterns = [
        f"May {active_start_day}–{active_end_day}",
        f"May {int(active_start_day)}–{int(active_end_day)}",
        f"May {active_start_day}-{active_end_day}",
        f"May {int(active_start_day)}-{int(active_end_day)}",
        f"{active_start_month}-{active_start_day}–{active_end_month}-{active_end_day}"
    ]
    
    # Check if this market matches the active market pattern
    for pattern in patterns:
        if pattern in market_name and "Will Elon tweet" in market_name:
            return True
            
    return False


def is_market_finished(market_name):
    """
    Determine if a market is finished based on the date range.
    
    Args:
        market_name (str): The market name to check.
        
    Returns:
        bool: True if the market is finished, False otherwise.
    """
    # Extract the current date
    current_date = datetime.now()
    
    # Try to extract date from market name
    if 'May' in market_name:
        # Examples: "May 2–9", "May 16–23", etc.
        try:
            parts = market_name.split('May ')[1].split('–')
            end_day = int(parts[1].split(' ')[0])
            end_month = 5  # May
            end_year = current_date.year
            
            # If the current date is past the market end date, it's finished
            market_end_date = datetime(end_year, end_month, end_day)
            return current_date > market_end_date
        except:
            pass
            
    # Default to not finished if we can't determine
    return False


def calculate_position_performance(position, bid_price, ask_price, is_finished=False):
    """
    Calculate performance metrics for a position.
    
    Args:
        position (dict): Position data
        bid_price (float): Current bid price
        ask_price (float): Current ask price
        is_finished (bool): Whether the market is finished
        
    Returns:
        dict: Performance metrics
    """
    # Initialize performance data
    performance = {
        'roi': 0,
        'unrealized_pnl': 0,
        'total_pnl': 0,
        'status': 'Unknown'
    }
    
    # For closed positions
    if position['status'] == 'closed':
        if 'realized_pnl' in position:
            performance['total_pnl'] = position['realized_pnl']
            
            # Calculate ROI
            total_cost = position['avg_buy_price'] * position['buy_volume']
            if total_cost > 0:
                performance['roi'] = (position['realized_pnl'] / total_cost) * 100
                
            performance['status'] = 'Closed'
        return performance
    
    # For finished markets that are still open in our records
    if is_finished:
        # For "Yes" outcomes in finished markets that didn't resolve to "Yes"
        performance['unrealized_pnl'] = -1 * position['avg_buy_price'] * position['net_position']
        performance['total_pnl'] = performance['unrealized_pnl']
        
        # If we also have partial sells
        if position['sell_volume'] > 0:
            partial_realized_pnl = (position['avg_sell_price'] - position['avg_buy_price']) * position['sell_volume']
            performance['total_pnl'] += partial_realized_pnl
            
        # Calculate ROI
        total_cost = position['avg_buy_price'] * position['buy_volume']
        if total_cost > 0:
            performance['roi'] = (performance['total_pnl'] / total_cost) * 100
            
        performance['status'] = 'Expired'
        return performance
    
    # For open positions with remaining shares
    if position['net_position'] > 0:
        # Use current ask price for mark-to-market if available
        price_to_use = ask_price if ask_price > 0 else position['avg_buy_price']
        
        # Calculate unrealized PnL based on current market price
        performance['unrealized_pnl'] = (price_to_use - position['avg_buy_price']) * position['net_position']
        
        # Add any partial realized PnL from sells
        partial_realized_pnl = 0
        if position['sell_volume'] > 0:
            partial_realized_pnl = (position['avg_sell_price'] - position['avg_buy_price']) * position['sell_volume']
            
        performance['total_pnl'] = performance['unrealized_pnl'] + partial_realized_pnl
        
        # Calculate ROI
        total_cost = position['avg_buy_price'] * position['buy_volume']
        if total_cost > 0:
            performance['roi'] = (performance['total_pnl'] / total_cost) * 100
            
        # Determine status based on performance
        if performance['total_pnl'] > 0:
            performance['status'] = 'Profitable'
        elif performance['total_pnl'] < 0:
            performance['status'] = 'Loss'
        else:
            performance['status'] = 'Breakeven'
            
    return performance


def display_positions(trades_data, analyzer, active_only=False):
    """
    Display position information using the identify_positions functionality.
    
    Args:
        trades_data (list): List of trade data dictionaries.
        analyzer (PolymarketTradeAnalyzer): The trade analyzer instance.
        active_only (bool): Whether to show only active market positions.
    """
    print("\n=== Position Analysis ===")
    positions = analyzer.identify_positions(trades_data)
    
    if isinstance(positions, dict) and positions.get('error'):
        print(f"Error: {positions['error']}")
        return
    
    # First get market names for all positions to identify active ones
    print("Getting market names...")
    market_names = {}
    active_position_keys = []
    
    for key, position in positions.items():
        market_id = position['market_id']
        if market_id not in market_names:
            market_name = get_market_name(market_id)
            market_names[market_id] = market_name
            
        # Check if this is an active market position
        if is_active_market(market_names[market_id]):
            active_position_keys.append(key)
    
    # Filter for active markets if requested
    if active_only and active_position_keys:
        active_positions = {}
        for key in active_position_keys:
            active_positions[key] = positions[key]
        
        positions = active_positions
        print(f"Filtered to {len(positions)} active market positions")
    
    # Now get market names and prices for the positions we're displaying
    print("Fetching market names and current prices...")
    market_names, market_bid_prices, market_ask_prices = get_market_names_and_prices_for_positions(positions)
    
    # Display position information
    position_count = len(positions)
    if position_count == 0:
        print("No positions found.")
        return
    
    open_positions = sum(1 for p in positions.values() if p['status'] == 'open')
    closed_positions = sum(1 for p in positions.values() if p['status'] == 'closed')
    
    print(f"Found {position_count} positions ({open_positions} open, {closed_positions} closed)")
    print("\n=== Position Details ===")
    
    # Track totals for portfolio summary
    total_realized_pnl = 0
    total_unrealized_pnl = 0
    total_partial_pnl = 0
    total_portfolio_value = 0
    total_remaining_shares = 0
    
    # Display each position
    for idx, (key, position) in enumerate(positions.items(), 1):
        status_color = "\033[92m" if position['status'] == 'closed' else "\033[93m"  # Green for closed, yellow for open
        reset_color = "\033[0m"
        
        # Format entry/exit times - Handle both timestamp objects and integers
        if 'first_trade_time' in position:
            if isinstance(position['first_trade_time'], (int, float)):
                first_trade = datetime.fromtimestamp(position['first_trade_time'])
            else:
                # Handle pandas Timestamp objects
                first_trade = position['first_trade_time']
        else:
            first_trade = "N/A"
            
        if 'last_trade_time' in position:
            if isinstance(position['last_trade_time'], (int, float)):
                last_trade = datetime.fromtimestamp(position['last_trade_time'])
            else:
                # Handle pandas Timestamp objects
                last_trade = position['last_trade_time']
        else:
            last_trade = "N/A"
        
        # Get market name and current prices
        market_id = position['market_id']
        market_name = market_names.get(market_id, position['market_id_short'])
        current_bid_price = market_bid_prices.get(market_id, 0)
        current_ask_price = market_ask_prices.get(market_id, 0)
        
        # Get remaining shares
        remaining_shares = position['net_position']
        total_remaining_shares += remaining_shares
        
        # Check if market is finished
        is_finished = is_market_finished(market_name)
        
        # Calculate position performance
        performance = calculate_position_performance(
            position, 
            current_bid_price, 
            current_ask_price,
            is_finished
        )
        
        # Update portfolio totals
        if position['status'] == 'closed' and 'realized_pnl' in position:
            total_realized_pnl += position['realized_pnl']
        elif position['status'] == 'open' and position['sell_volume'] > 0:
            partial_pnl = (position['avg_sell_price'] - position['avg_buy_price']) * position['sell_volume']
            total_partial_pnl += partial_pnl
            total_unrealized_pnl += performance['unrealized_pnl']
        else:
            total_unrealized_pnl += performance['unrealized_pnl']
        
        # Calculate portfolio value
        if remaining_shares > 0 and (current_ask_price > 0 or current_bid_price > 0):
            # Use ask price for mark-to-market if available, otherwise use bid price
            price_to_use = current_ask_price if current_ask_price > 0 else current_bid_price
            position_value = remaining_shares * price_to_use
            total_portfolio_value += position_value
        
        # Set colors based on performance
        perf_color = "\033[92m" if performance['total_pnl'] > 0 else "\033[91m"  # Green for profit, red for loss
        if performance['total_pnl'] == 0:
            perf_color = "\033[90m"  # Gray for breakeven
            
        status_display = f"{status_color}{position['status'].upper()}{reset_color}"
        if performance['status'] != 'Unknown':
            status_display += f" ({perf_color}{performance['status']}{reset_color})"
        
        # Display basic position info with market name
        print(f"{idx}. Market: {market_name}")
        print(f"   ID: {position['market_id']}")
        print(f"   Outcome: {position['outcome']} | Status: {status_display}")
        
        if is_finished:
            print(f"   {reset_color}Market Status: FINISHED{reset_color}")
            
        print(f"   Entry: {first_trade} | Exit: {last_trade if position['status'] == 'closed' else 'OPEN'}")
        print(f"   Buy Volume: {position['buy_volume']:.2f} @ Avg Price: ${position['avg_buy_price']:.4f}")
        print(f"   Sell Volume: {position['sell_volume']:.2f} @ Avg Price: ${position['avg_sell_price']:.4f}")
        
        # Display current prices
        bid_color = "\033[96m"  # Cyan
        ask_color = "\033[94m"  # Blue
        print(f"   {bid_color}Current Bid Price (Selling): ${current_bid_price:.4f}{reset_color}")
        print(f"   {ask_color}Current Ask Price (Market): ${current_ask_price:.4f}{reset_color}")
        
        # Highlight remaining shares
        shares_color = "\033[96m" if remaining_shares > 0 else "\033[90m"  # Cyan for positive, gray for zero
        print(f"   {shares_color}Remaining Shares: {remaining_shares:.2f}{reset_color}")
        
        # Calculate and show unrealized value
        if position['status'] == 'open' and remaining_shares > 0:
            # Use current market price (ask) for value if available, otherwise use bid price
            price_to_use = current_ask_price if current_ask_price > 0 else current_bid_price
            price_source = "Market (Ask)" if current_ask_price > 0 else "Bid"
            
            if price_to_use > 0:
                unrealized_value = remaining_shares * price_to_use
                print(f"   {shares_color}Est. Value at {price_source} Price: ${unrealized_value:.4f}{reset_color}")
        
        # Show PnL information
        if performance['unrealized_pnl'] != 0:
            unrealized_color = "\033[92m" if performance['unrealized_pnl'] > 0 else "\033[91m"
            print(f"   Unrealized PnL: {unrealized_color}${performance['unrealized_pnl']:.4f}{reset_color}")
            
        if position['status'] == 'closed' and 'realized_pnl' in position:
            pnl_color = "\033[92m" if position['realized_pnl'] >= 0 else "\033[91m"
            print(f"   Realized PnL: {pnl_color}${position['realized_pnl']:.4f}{reset_color}")
        
        if position['status'] == 'open' and position['buy_volume'] > 0 and position['sell_volume'] > 0:
            partial_realized_pnl = (position['avg_sell_price'] - position['avg_buy_price']) * position['sell_volume']
            pnl_color = "\033[92m" if partial_realized_pnl >= 0 else "\033[91m"
            print(f"   Partial Realized PnL: {pnl_color}${partial_realized_pnl:.4f}{reset_color}")
        
        # Show total PnL and ROI for the position
        print(f"   {perf_color}Total PnL: ${performance['total_pnl']:.4f} (ROI: {performance['roi']:.2f}%){reset_color}")
        
        # Show potential PnL if sold at current bid price
        if position['status'] == 'open' and remaining_shares > 0 and current_bid_price > 0:
            potential_pnl = (current_bid_price - position['avg_buy_price']) * remaining_shares
            pnl_color = "\033[92m" if potential_pnl >= 0 else "\033[91m"
            print(f"   Potential PnL if Sold Now: {pnl_color}${potential_pnl:.4f}{reset_color}")
        
        print("")  # Empty line between positions
    
    # Calculate total PnL
    total_pnl = total_realized_pnl + total_partial_pnl + total_unrealized_pnl
    
    # Display portfolio summary with colors
    realized_color = "\033[92m" if total_realized_pnl >= 0 else "\033[91m"
    unrealized_color = "\033[92m" if total_unrealized_pnl >= 0 else "\033[91m"
    total_color = "\033[92m" if total_pnl >= 0 else "\033[91m"
    reset_color = "\033[0m"
    
    print(f"\n=== Portfolio Summary ===")
    print(f"Total Realized PnL: {realized_color}${total_realized_pnl + total_partial_pnl:.4f}{reset_color}")
    print(f"  - From Closed Positions: {realized_color}${total_realized_pnl:.4f}{reset_color}")
    print(f"  - From Partial Sells: {realized_color}${total_partial_pnl:.4f}{reset_color}")
    print(f"Total Unrealized PnL: {unrealized_color}${total_unrealized_pnl:.4f}{reset_color}")
    print(f"Total PnL (Realized + Unrealized): {total_color}${total_pnl:.4f}{reset_color}")
    print(f"Portfolio Value: ${total_portfolio_value:.4f}")
    print(f"Total Remaining Shares: {total_remaining_shares:.2f}")
    print(f"Closed Positions: {closed_positions}")
    print(f"Open Positions: {open_positions}")
    
    return positions


def main():
    """Main function to run Polymarket position analysis."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Polymarket Position Analysis")
    parser.add_argument("--active", "-a", action="store_true", help="Show only active market positions")
    args = parser.parse_args()
    
    print("=== Polymarket Position Analysis ===")
    
    try:
        # Initialize the analyzer
        print("Initializing trade analyzer...")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plots')
        os.makedirs(output_dir, exist_ok=True)
        
        analyzer = PolymarketTradeAnalyzer(output_dir=output_dir)
        
        # Get trades for the current wallet
        print("\nRetrieving your trades...")
        trades = analyzer.get_trades_by_maker()
        
        if not trades:
            print("No trades found for your wallet address.")
            return
        
        print(f"Found {len(trades)} trades. Analyzing positions...")
        
        # Perform position analysis
        display_positions(trades, analyzer, active_only=args.active)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    main() 