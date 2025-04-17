# src/polymarket/market_scanner.py

import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from tabulate import tabulate

from src.polymarket.clob_utils import ClobUtils

def scan_rewarded_markets(verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Scan for markets with rewards enabled.
    
    Args:
        verbose: Whether to print detailed information
        
    Returns:
        List of rewarded markets
    """
    clob = ClobUtils()
    
    print("Scanning for markets with rewards...")
    markets = clob.fetch_all_rewarded_markets()
    
    if verbose:
        print(f"Found {len(markets)} markets with rewards")
        
        # Display top 5 markets
        top_markets = markets[:5]
        for idx, market in enumerate(top_markets):
            condition_id = market.get("condition_id", "")
            tokens = market.get("tokens", [])
            rewards = market.get("rewards", {})
            
            print(f"\n{idx+1}. Market Condition ID: {condition_id}")
            
            # Print token information
            if tokens:
                print("  Tokens:")
                for token in tokens:
                    token_id = token.get("token_id", "")
                    outcome = token.get("outcome", "")
                    print(f"    - {outcome}: {token_id}")
            
            # Print reward information
            if rewards:
                print("  Rewards:")
                print(f"    - Min Size: {rewards.get('min_size', 0)}")
                print(f"    - Max Spread: {rewards.get('max_spread', 0)}")
                print(f"    - In-Game Multiplier: {rewards.get('in_game_multiplier', 0)}")
                print(f"    - Reward Epoch: {rewards.get('reward_epoch', 0)}")
                
                # Print date range if available
                start_date = rewards.get("event_start_date", "")
                end_date = rewards.get("event_end_date", "")
                if start_date and end_date:
                    print(f"    - Event Period: {start_date} to {end_date}")
    
    return markets

def find_most_liquid_markets(top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Find the most liquid markets based on order book depth.
    
    Args:
        top_n: Number of top markets to return
        
    Returns:
        List of the most liquid markets with their liquidity metrics
    """
    clob = ClobUtils()
    
    print("Fetching all markets...")
    markets = clob.fetch_all_markets()
    print(f"Found {len(markets)} total markets")
    
    # Extract tokens from markets
    tokens = clob.extract_tokens_from_markets(markets)
    
    if not tokens:
        print("No valid token pairs found. Unable to analyze markets.")
        return []
    
    # Calculate liquidity for each market
    liquidity_metrics = []
    
    print(f"Analyzing order books for {min(20, len(tokens))} markets...")
    for idx, (condition_id, token_data) in enumerate(list(tokens.items())[:20]):  # Limit to 20 for demo
        yes_token_id = token_data.get("yes_token_id")
        
        if not yes_token_id:
            print(f"Skipping market {condition_id}: No YES token ID found")
            continue
        
        print(f"Analyzing market {idx+1}/20: {condition_id}")
        print(f"YES token ID: {yes_token_id}")
        
        try:
            # Try to get order book directly first
            order_book = clob.get_order_book_direct(yes_token_id)
            
            # If that doesn't work, try through the client
            if not order_book or not order_book.get("bids") and not order_book.get("asks"):
                print(f"  Direct API failed. Trying through client...")
                order_book = clob.get_order_book(yes_token_id)
            
            # If both methods fail, get midpoint and generate synthetic data
            if not order_book or not order_book.get("bids") and not order_book.get("asks"):
                print(f"  Both order book methods failed. Generating synthetic data...")
                midpoint = clob.get_midpoint_direct(yes_token_id)
                if midpoint <= 0:
                    midpoint = 0.5  # Default if midpoint retrieval fails
                
                order_book = clob.generate_synthetic_order_book(yes_token_id, midpoint)
                print(f"  Using synthetic data with midpoint: {midpoint:.4f}")
            
            # Format order book data
            formatted = clob.format_order_book(order_book)
            data_source = "Synthetic" if formatted.get("is_synthetic", True) else "Real"
            print(f"  Order book data source: {data_source}")
            
            # Calculate liquidity metrics
            buy_orders = formatted.get("buy_orders", [])
            sell_orders = formatted.get("sell_orders", [])
            
            buy_liquidity = sum(order.get("total", 0) for order in buy_orders)
            sell_liquidity = sum(order.get("total", 0) for order in sell_orders)
            total_liquidity = buy_liquidity + sell_liquidity
            
            # Calculate spread
            best_bid = max([order.get("price", 0) for order in buy_orders]) if buy_orders else 0
            best_ask = min([order.get("price", 0) for order in sell_orders]) if sell_orders else 100
            
            spread = best_ask - best_bid if best_bid > 0 and best_ask < 100 else None
            spread_pct = (spread / best_bid * 100) if spread is not None and best_bid > 0 else None
            
            # Store metrics
            liquidity_metrics.append({
                "condition_id": condition_id,
                "token_id": yes_token_id,
                "outcome": token_data.get("yes_outcome", "YES"),
                "buy_liquidity": buy_liquidity,
                "sell_liquidity": sell_liquidity,
                "total_liquidity": total_liquidity,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": spread,
                "spread_pct": spread_pct,
                "is_synthetic": formatted.get("is_synthetic", True)
            })
            
            # Debug output
            print(f"  Buy liquidity: ${buy_liquidity:.2f}, Sell liquidity: ${sell_liquidity:.2f}")
            print(f"  Best bid: {best_bid:.2f}%, Best ask: {best_ask:.2f}%")
            if spread is not None:
                print(f"  Spread: {spread:.2f}% ({spread_pct:.2f}%)")
            
        except Exception as e:
            print(f"  Error analyzing market {condition_id}: {e}")
            continue
    
    # Sort by total liquidity
    liquidity_metrics.sort(key=lambda x: x.get("total_liquidity", 0), reverse=True)
    
    # Get top N
    top_markets = liquidity_metrics[:top_n]
    
    # Print results
    print("\nTop Liquid Markets:")
    
    table_data = []
    for idx, market in enumerate(top_markets):
        spread_str = f"{market.get('spread', 0):.2f} ({market.get('spread_pct', 0):.2f}%)" if market.get('spread') else "N/A"
        data_source = "📊 Synthetic" if market.get("is_synthetic", True) else "🔍 Real"
        
        table_data.append([
            idx + 1,
            market.get("condition_id", "")[:10] + "...",
            f"${market.get('buy_liquidity', 0):.2f}",
            f"${market.get('sell_liquidity', 0):.2f}",
            f"${market.get('total_liquidity', 0):.2f}",
            f"{market.get('best_bid', 0):.2f}%",
            f"{market.get('best_ask', 0):.2f}%",
            spread_str,
            data_source
        ])
    
    headers = ["#", "Market ID", "Buy Liquidity", "Sell Liquidity", "Total Liquidity", "Best Bid", "Best Ask", "Spread", "Data Source"]
    print(tabulate(table_data, headers=headers, tablefmt="pipe"))
    
    return top_markets

def analyze_market(condition_id: str) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of a single market.
    
    Args:
        condition_id: The condition ID of the market to analyze
        
    Returns:
        Dictionary containing analysis results
    """
    clob = ClobUtils()
    
    print(f"Analyzing market: {condition_id}")
    
    # Get market details
    market = clob.get_market(condition_id=condition_id)
    
    if not market:
        # Try to get market through Polymarket API
        print("Market not found via CLOB API. Attempting to use Polymarket API...")
        all_markets = clob.fetch_polymarket_markets()
        market = next((m for m in all_markets if m.get("condition_id") == condition_id), None)
        
        if not market:
            print("Market not found through either API.")
            return {}
    
    # Extract tokens
    tokens = []
    for token in market.get("tokens", []):
        tokens.append({
            "token_id": token.get("token_id", ""),
            "outcome": token.get("outcome", "")
        })
    
    yes_token = next((t for t in tokens if t.get("outcome", "").upper() == "YES"), None)
    no_token = next((t for t in tokens if t.get("outcome", "").upper() == "NO"), None)
    
    if not yes_token or not no_token:
        print("Could not identify YES and NO tokens")
        return {}
    
    yes_token_id = yes_token.get("token_id", "")
    no_token_id = no_token.get("token_id", "")
    
    print(f"Found YES token: {yes_token_id}")
    print(f"Found NO token: {no_token_id}")
    
    # Get order books - try direct API first, then client, then generate synthetic
    yes_order_book = None
    yes_is_synthetic = True
    
    print("Fetching YES token order book...")
    try:
        # Try direct API first
        yes_order_book = clob.get_order_book_direct(yes_token_id)
        if yes_order_book and (yes_order_book.get("bids") or yes_order_book.get("asks")):
            yes_is_synthetic = False
            print("✅ Got real YES order book via direct API")
        else:
            # Try through client
            print("Direct API failed. Trying through client...")
            yes_order_book = clob.get_order_book(yes_token_id)
            if yes_order_book and (yes_order_book.get("bids") or yes_order_book.get("asks")):
                yes_is_synthetic = False
                print("✅ Got real YES order book via client")
            else:
                # Generate synthetic
                print("Both methods failed. Generating synthetic YES order book...")
                yes_midpoint = clob.get_midpoint_direct(yes_token_id)
                if yes_midpoint <= 0:
                    yes_midpoint = 0.5
                yes_order_book = clob.generate_synthetic_order_book(yes_token_id, yes_midpoint)
                print(f"Using synthetic YES data with midpoint: {yes_midpoint:.4f}")
    except Exception as e:
        print(f"Error fetching YES order book: {e}")
        # Generate synthetic as fallback
        yes_midpoint = 0.5
        print("Generating synthetic YES order book due to error...")
        yes_order_book = clob.generate_synthetic_order_book(yes_token_id, yes_midpoint)
    
    # Do the same for NO token
    no_order_book = None
    no_is_synthetic = True
    
    print("Fetching NO token order book...")
    try:
        # Try direct API first
        no_order_book = clob.get_order_book_direct(no_token_id)
        if no_order_book and (no_order_book.get("bids") or no_order_book.get("asks")):
            no_is_synthetic = False
            print("✅ Got real NO order book via direct API")
        else:
            # Try through client
            print("Direct API failed. Trying through client...")
            no_order_book = clob.get_order_book(no_token_id)
            if no_order_book and (no_order_book.get("bids") or no_order_book.get("asks")):
                no_is_synthetic = False
                print("✅ Got real NO order book via client")
            else:
                # Generate synthetic
                print("Both methods failed. Generating synthetic NO order book...")
                no_midpoint = clob.get_midpoint_direct(no_token_id)
                if no_midpoint <= 0:
                    no_midpoint = 0.5
                no_order_book = clob.generate_synthetic_order_book(no_token_id, no_midpoint)
                print(f"Using synthetic NO data with midpoint: {no_midpoint:.4f}")
    except Exception as e:
        print(f"Error fetching NO order book: {e}")
        # Generate synthetic as fallback
        no_midpoint = 0.5
        print("Generating synthetic NO order book due to error...")
        no_order_book = clob.generate_synthetic_order_book(no_token_id, no_midpoint)
    
    # Format order books
    formatted_yes = clob.format_order_book(yes_order_book)
    formatted_yes["is_synthetic"] = yes_is_synthetic
    
    formatted_no = clob.format_order_book(no_order_book)
    formatted_no["is_synthetic"] = no_is_synthetic
    
    # Get midpoint prices - use previously obtained values if they exist
    if 'yes_midpoint' in locals():
        yes_midpoint_val = yes_midpoint
    else:
        yes_midpoint_val = clob.get_midpoint_direct(yes_token_id)
        if yes_midpoint_val <= 0:
            buy_price = clob.get_price_direct(yes_token_id, "buy")
            sell_price = clob.get_price_direct(yes_token_id, "sell")
            if buy_price > 0 and sell_price > 0:
                yes_midpoint_val = (buy_price + sell_price) / 2
            else:
                yes_midpoint_val = 0.5
    
    if 'no_midpoint' in locals():
        no_midpoint_val = no_midpoint
    else:
        no_midpoint_val = clob.get_midpoint_direct(no_token_id)
        if no_midpoint_val <= 0:
            buy_price = clob.get_price_direct(no_token_id, "buy")
            sell_price = clob.get_price_direct(no_token_id, "sell")
            if buy_price > 0 and sell_price > 0:
                no_midpoint_val = (buy_price + sell_price) / 2
            else:
                no_midpoint_val = 0.5
    
    # Get spreads
    try:
        yes_spread = clob.get_spread(yes_token_id)
    except Exception:
        yes_spread = {}
    
    try:
        no_spread = clob.get_spread(no_token_id)
    except Exception:
        no_spread = {}
    
    # Calculate market metrics
    analysis = {
        "condition_id": condition_id,
        "market": market,
        "yes_token": yes_token,
        "no_token": no_token,
        "yes_order_book": formatted_yes,
        "no_order_book": formatted_no,
        "yes_midpoint": yes_midpoint_val,
        "no_midpoint": no_midpoint_val,
        "yes_spread": yes_spread,
        "no_spread": no_spread,
        "metrics": {}
    }
    
    # Calculate additional metrics
    yes_buy_liquidity = sum(order.get("total", 0) for order in formatted_yes.get("buy_orders", []))
    yes_sell_liquidity = sum(order.get("total", 0) for order in formatted_yes.get("sell_orders", []))
    yes_total_liquidity = yes_buy_liquidity + yes_sell_liquidity
    
    no_buy_liquidity = sum(order.get("total", 0) for order in formatted_no.get("buy_orders", []))
    no_sell_liquidity = sum(order.get("total", 0) for order in formatted_no.get("sell_orders", []))
    no_total_liquidity = no_buy_liquidity + no_sell_liquidity
    
    total_market_liquidity = yes_total_liquidity + no_total_liquidity
    
    # Calculate YES token metrics
    yes_buy_orders = formatted_yes.get("buy_orders", [])
    yes_sell_orders = formatted_yes.get("sell_orders", [])
    
    yes_best_bid = max([order.get("price", 0) for order in yes_buy_orders]) if yes_buy_orders else 0
    yes_best_ask = min([order.get("price", 0) for order in yes_sell_orders]) if yes_sell_orders else 100
    
    yes_spread_val = yes_best_ask - yes_best_bid if yes_best_bid > 0 and yes_best_ask < 100 else None
    yes_spread_pct = (yes_spread_val / yes_best_bid * 100) if yes_spread_val is not None and yes_best_bid > 0 else None
    
    # Check for arbitrage opportunity
    market_sum = yes_midpoint_val + no_midpoint_val
    arbitrage_opportunity = None
    
    if market_sum < 0.98:
        arbitrage_opportunity = f"🔍 Potential long arbitrage: YES + NO = {market_sum:.4f}, profit = {(1-market_sum)*100:.2f}%"
    elif market_sum > 1.02:
        arbitrage_opportunity = f"🔍 Potential short arbitrage: YES + NO = {market_sum:.4f}, profit = {(market_sum-1)*100:.2f}%"
    
    # Store metrics
    analysis["metrics"] = {
        "yes_buy_liquidity": yes_buy_liquidity,
        "yes_sell_liquidity": yes_sell_liquidity,
        "yes_total_liquidity": yes_total_liquidity,
        "no_buy_liquidity": no_buy_liquidity,
        "no_sell_liquidity": no_sell_liquidity,
        "no_total_liquidity": no_total_liquidity,
        "total_market_liquidity": total_market_liquidity,
        "yes_best_bid": yes_best_bid,
        "yes_best_ask": yes_best_ask,
        "yes_spread": yes_spread_val,
        "yes_spread_pct": yes_spread_pct,
        "market_sum": market_sum,
        "arbitrage_opportunity": arbitrage_opportunity,
        "yes_is_synthetic": yes_is_synthetic,
        "no_is_synthetic": no_is_synthetic
    }
    
    # Print analysis results
    print("\nMarket Analysis Results:")
    print(f"  Condition ID: {condition_id}")
    
    if market.get("market"):
        print(f"  Question: {market.get('market', {}).get('question', 'Unknown')}")
    elif market.get("question"):
        print(f"  Question: {market.get('question')}")
    
    print(f"\n  YES Token ID: {yes_token.get('token_id', '')}")
    print(f"  YES Midpoint: {yes_midpoint_val:.4f} ({yes_midpoint_val*100:.2f}%)")
    print(f"  YES Liquidity: ${yes_total_liquidity:.2f} (Buy: ${yes_buy_liquidity:.2f}, Sell: ${yes_sell_liquidity:.2f})")
    
    if yes_spread_val is not None:
        print(f"  YES Spread: {yes_spread_val:.2f}% ({yes_spread_pct:.2f}%)")
    
    print(f"\n  NO Token ID: {no_token.get('token_id', '')}")
    print(f"  NO Midpoint: {no_midpoint_val:.4f} ({no_midpoint_val*100:.2f}%)")
    print(f"  NO Liquidity: ${no_total_liquidity:.2f} (Buy: ${no_buy_liquidity:.2f}, Sell: ${no_sell_liquidity:.2f})")
    
    print(f"\n  Total Market Liquidity: ${total_market_liquidity:.2f}")
    print(f"  Market Sum (YES + NO): {market_sum:.4f}")
    
    if arbitrage_opportunity:
        print(f"\n  {arbitrage_opportunity}")
    
    # Print order book summary
    print("\nYES Order Book Summary:")
    print(f"  Data Source: {'📊 Synthetic' if yes_is_synthetic else '🔍 Real'}")
    
    if yes_buy_orders:
        print("  Top 5 Buy Orders:")
        buy_table = tabulate(
            [[f"{order.get('price', 0):.2f}%", f"{order.get('size', 0):.2f}", f"${order.get('total', 0):.2f}"] 
             for order in yes_buy_orders[:5]],
            headers=["Price", "Size", "Total"],
            tablefmt="simple"
        )
        print("  " + buy_table.replace("\n", "\n  "))
    else:
        print("  No buy orders found")
    
    if yes_sell_orders:
        print("\n  Top 5 Sell Orders:")
        sell_table = tabulate(
            [[f"{order.get('price', 0):.2f}%", f"{order.get('size', 0):.2f}", f"${order.get('total', 0):.2f}"] 
             for order in yes_sell_orders[:5]],
            headers=["Price", "Size", "Total"],
            tablefmt="simple"
        )
        print("  " + sell_table.replace("\n", "\n  "))
    else:
        print("  No sell orders found")
    
    return analysis

def save_market_analysis(analysis: Dict[str, Any], output_dir: str = "src/polymarket/data/analysis") -> str:
    """
    Save market analysis results to a JSON file.
    
    Args:
        analysis: The analysis results
        output_dir: Directory to save the file
        
    Returns:
        Path to the saved file
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    condition_id = analysis.get("condition_id", "unknown")
    timestamp = int(time.time())
    filename = f"{condition_id}_{timestamp}.json"
    filepath = output_path / filename
    
    # Save to JSON file
    with open(filepath, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\nAnalysis saved to {filepath}")
    return str(filepath)

def main():
    """CLI entry point for the Market Scanner."""
    parser = argparse.ArgumentParser(description="Polymarket Market Scanner")
    
    # Add command-line arguments
    parser.add_argument("--rewarded", action="store_true",
                        help="Scan for markets with rewards")
    parser.add_argument("--liquid", action="store_true",
                        help="Find most liquid markets")
    parser.add_argument("--market", type=str,
                        help="Analyze a specific market by condition ID")
    parser.add_argument("--top", type=int, default=10,
                        help="Number of top markets to return (default: 10)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print detailed information")
    parser.add_argument("--save", action="store_true",
                        help="Save analysis results to a file")
    
    args = parser.parse_args()
    
    if args.rewarded:
        scan_rewarded_markets(verbose=args.verbose)
    
    if args.liquid:
        find_most_liquid_markets(top_n=args.top)
    
    if args.market:
        analysis = analyze_market(args.market)
        if args.save and analysis:
            save_market_analysis(analysis)
    
    # If no command provided, show help
    if not (args.rewarded or args.liquid or args.market):
        parser.print_help()

if __name__ == "__main__":
    main() 