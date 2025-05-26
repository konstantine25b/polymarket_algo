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


def get_market_bid_price(market_id, asset_id=None):
    """
    Fetch current bid price for a market from Polymarket API.
    
    Args:
        market_id (str): Market ID to fetch information for.
        asset_id (str, optional): Asset ID for the specific outcome.
    
    Returns:
        float: Current bid price or 0 if not found.
    """
    try:
        # First try the orderbook endpoint
        api_url = f"https://polymarket.com/api/order-books?marketId={market_id}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://polymarket.com/"
        }
        
        response = requests.get(api_url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Extract the highest bid price
            buy_orders = data.get('buyOrders', [])
            if buy_orders:
                # Sort by price in descending order
                buy_orders.sort(key=lambda x: float(x.get('price', 0)), reverse=True)
                highest_bid = buy_orders[0]
                return float(highest_bid.get('price', 0))
        
        # If the first method fails, try the direct market endpoint
        api_url = f"https://polymarket.com/api/markets/{market_id}"
        response = requests.get(api_url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'bids' in data['data']:
                bids = data['data']['bids']
                if bids:
                    # Sort by price in descending order
                    bids.sort(key=lambda x: float(x.get('price', 0)), reverse=True)
                    highest_bid = bids[0]
                    return float(highest_bid.get('price', 0))
    except Exception as e:
        pass
    
    return 0


def get_market_names_and_prices_for_positions(positions):
    """
    Fetch market names and current bid prices for all positions.
    
    Args:
        positions (dict): Dictionary of positions with market IDs.
    
    Returns:
        tuple: (market_names, market_prices) dictionaries
    """
    market_names = {}
    market_prices = {}
    
    for key, position in positions.items():
        market_id = position['market_id']
        if market_id not in market_names:
            # Try to get the market name
            market_name = get_market_name(market_id)
            market_names[market_id] = market_name
            
            # Try to get the current bid price
            bid_price = get_market_bid_price(market_id)
            market_prices[market_id] = bid_price
            
            # Add a small delay to avoid hitting rate limits
            time.sleep(0.2)
    
    return market_names, market_prices


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
    
    # Get market names and prices for all positions
    print("Fetching market names and current bid prices...")
    market_names, market_prices = get_market_names_and_prices_for_positions(positions)
    
    # Filter for active markets if requested
    if active_only:
        active_positions = {}
        for key, position in positions.items():
            market_id = position['market_id']
            market_name = market_names.get(market_id, "")
            if is_active_market(market_name):
                active_positions[key] = position
        
        positions = active_positions
        print(f"Filtered to {len(positions)} active market positions")
    
    # Display position information
    position_count = len(positions)
    if position_count == 0:
        print("No positions found.")
        return
    
    open_positions = sum(1 for p in positions.values() if p['status'] == 'open')
    closed_positions = sum(1 for p in positions.values() if p['status'] == 'closed')
    
    print(f"Found {position_count} positions ({open_positions} open, {closed_positions} closed)")
    print("\n=== Position Details ===")
    
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
        
        # Get market name and current bid price
        market_id = position['market_id']
        market_name = market_names.get(market_id, position['market_id_short'])
        current_bid_price = market_prices.get(market_id, 0)
        
        # Get remaining shares
        remaining_shares = position['net_position']
        
        # Display basic position info with market name
        print(f"{idx}. Market: {market_name}")
        print(f"   ID: {position['market_id']}")
        print(f"   Outcome: {position['outcome']} | Status: {status_color}{position['status'].upper()}{reset_color}")
        
        print(f"   Entry: {first_trade} | Exit: {last_trade if position['status'] == 'closed' else 'OPEN'}")
        print(f"   Buy Volume: {position['buy_volume']:.2f} @ Avg Price: ${position['avg_buy_price']:.4f}")
        print(f"   Sell Volume: {position['sell_volume']:.2f} @ Avg Price: ${position['avg_sell_price']:.4f}")
        
        # Display current bid price
        bid_color = "\033[96m"  # Cyan
        print(f"   {bid_color}Current Bid Price: ${current_bid_price:.4f}{reset_color}")
        
        # Highlight remaining shares
        shares_color = "\033[96m" if remaining_shares > 0 else "\033[90m"  # Cyan for positive, gray for zero
        print(f"   {shares_color}Remaining Shares: {remaining_shares:.2f}{reset_color}")
        
        # Calculate and show unrealized value at current bid price
        if position['status'] == 'open' and remaining_shares > 0:
            # Use current bid price if available, otherwise use last sell price
            price_to_use = current_bid_price if current_bid_price > 0 else position['avg_sell_price']
            price_source = "Current Bid" if current_bid_price > 0 else "Last Sell"
            
            if price_to_use > 0:
                unrealized_value = remaining_shares * price_to_use
                print(f"   {shares_color}Est. Value at {price_source} Price: ${unrealized_value:.4f}{reset_color}")
        
        # Show PnL for closed positions
        if position['status'] == 'closed' and 'realized_pnl' in position:
            pnl_color = "\033[92m" if position['realized_pnl'] >= 0 else "\033[91m"  # Green for profit, red for loss
            print(f"   Realized PnL: {pnl_color}${position['realized_pnl']:.4f}{reset_color}")
        
        # If partially closed (some buys and sells but still open)
        if position['status'] == 'open' and position['buy_volume'] > 0 and position['sell_volume'] > 0:
            # Calculate partial realized PnL on the portion that was sold
            partial_realized_pnl = (position['avg_sell_price'] - position['avg_buy_price']) * position['sell_volume']
            pnl_color = "\033[92m" if partial_realized_pnl >= 0 else "\033[91m"
            print(f"   Partial Realized PnL: {pnl_color}${partial_realized_pnl:.4f}{reset_color}")
            
            # Calculate potential PnL if sold at current bid price
            if remaining_shares > 0 and current_bid_price > 0:
                potential_pnl = (current_bid_price - position['avg_buy_price']) * remaining_shares
                pnl_color = "\033[92m" if potential_pnl >= 0 else "\033[91m"
                print(f"   Potential PnL at Current Bid: {pnl_color}${potential_pnl:.4f}{reset_color}")
        
        print("")  # Empty line between positions
    
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
        positions = display_positions(trades, analyzer, active_only=args.active)
        
        if not positions:
            return
        
        # Show total PnL summary
        closed_positions = [p for p in positions.values() if p['status'] == 'closed' and 'realized_pnl' in p]
        partial_positions = [p for p in positions.values() if p['status'] == 'open' and p['sell_volume'] > 0]
        
        total_realized_pnl = 0
        
        # Calculate total realized PnL from closed positions
        if closed_positions:
            closed_pnl = sum(p['realized_pnl'] for p in closed_positions)
            total_realized_pnl += closed_pnl
        
        # Calculate partial realized PnL from open positions that have some sells
        partial_realized_pnl = 0
        if partial_positions:
            for p in partial_positions:
                partial_pnl = (p['avg_sell_price'] - p['avg_buy_price']) * p['sell_volume']
                partial_realized_pnl += partial_pnl
            total_realized_pnl += partial_realized_pnl
        
        # Calculate remaining shares across all positions
        remaining_shares = sum(p['net_position'] for p in positions.values() if p['status'] == 'open')
        
        # Display summary
        pnl_color = "\033[92m" if total_realized_pnl >= 0 else "\033[91m"
        reset_color = "\033[0m"
        print(f"\n=== Portfolio Summary ===")
        print(f"Total Realized PnL: {pnl_color}${total_realized_pnl:.4f}{reset_color}")
        print(f"  - From Closed Positions: ${sum(p['realized_pnl'] for p in closed_positions):.4f}")
        print(f"  - From Partial Sells: ${partial_realized_pnl:.4f}")
        print(f"Total Remaining Shares: {remaining_shares:.2f}")
        print(f"Closed Positions: {len(closed_positions)}")
        print(f"Open Positions: {len(positions) - len(closed_positions)}")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    main() 