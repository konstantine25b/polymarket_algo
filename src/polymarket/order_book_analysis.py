# src/polymarket/order_book_analysis.py

import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import argparse
from typing import Dict, List, Any, Optional, Tuple

from src.polymarket.api_client import PolymarketAPIClient
from src.polymarket.visualization import Visualization

class OrderBookAnalyzer:
    """A tool for analyzing Polymarket order book data."""
    
    def __init__(self, data_dir: Path = Path("src/polymarket/data")):
        """
        Initialize the analyzer.
        
        Args:
            data_dir: Directory containing order book data
        """
        self.data_dir = data_dir
        self.order_book_dir = data_dir / "order_books"
        self.visualization = Visualization()

    def load_order_book(self, file_path: str) -> Dict[str, Any]:
        """
        Load order book data from a JSON file.
        
        Args:
            file_path: Path to the order book JSON file
            
        Returns:
            The order book data
        """
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading order book file: {e}")
            return {}
    
    def calculate_market_liquidity(self, order_frames: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate liquidity metrics for each market.
        
        Args:
            order_frames: The order book data
            
        Returns:
            Dictionary mapping market questions to liquidity metrics
        """
        liquidity_metrics = {}
        
        for question, data in order_frames.items():
            # Calculate buy and sell liquidity
            buy_orders = data.get("buy_orders", [])
            sell_orders = data.get("sell_orders", [])
            is_synthetic = data.get("is_synthetic", True)
            
            buy_liquidity = sum(order.get("total", 0) for order in buy_orders)
            sell_liquidity = sum(order.get("total", 0) for order in sell_orders)
            total_liquidity = buy_liquidity + sell_liquidity
            
            # Calculate depth (how many orders within 5% of best price)
            best_bid = max([order.get("price", 0) for order in buy_orders]) if buy_orders else 0
            best_ask = min([order.get("price", 0) for order in sell_orders]) if sell_orders else 100
            
            bid_depth_5pct = sum(
                order.get("total", 0) for order in buy_orders 
                if order.get("price", 0) >= best_bid * 0.95
            )
            ask_depth_5pct = sum(
                order.get("total", 0) for order in sell_orders 
                if order.get("price", 0) <= best_ask * 1.05
            )
            
            # Calculate the spread
            spread = best_ask - best_bid if best_bid > 0 and best_ask < 100 else None
            spread_pct = (spread / best_bid * 100) if spread is not None and best_bid > 0 else None
            
            # Combined liquidity score: total liquidity weighted by inverse of spread
            # Higher liquidity and lower spread = better score
            liquidity_score = total_liquidity / (spread if spread and spread > 0 else 100)
            
            liquidity_metrics[question] = {
                "buy_liquidity": buy_liquidity,
                "sell_liquidity": sell_liquidity,
                "total_liquidity": total_liquidity,
                "bid_depth_5pct": bid_depth_5pct,
                "ask_depth_5pct": ask_depth_5pct,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": spread,
                "spread_pct": spread_pct,
                "liquidity_score": liquidity_score,
                "is_synthetic": is_synthetic
            }
        
        return liquidity_metrics

    def detect_price_manipulation(self, order_frames: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect potential price manipulation patterns in order book.
        
        Args:
            order_frames: The order book data
            
        Returns:
            List of potential manipulation flags
        """
        manipulation_flags = []
        
        for question, data in order_frames.items():
            buy_orders = data.get("buy_orders", [])
            sell_orders = data.get("sell_orders", [])
            
            # Check for large orders that could move the market
            if buy_orders:
                largest_buy = max(buy_orders, key=lambda x: x.get("size", 0))
                largest_buy_pct = largest_buy.get("size", 0) / sum(o.get("size", 0) for o in buy_orders) * 100
                
                if largest_buy_pct > 70:  # One order is >70% of all buy orders
                    manipulation_flags.append({
                        "market": question,
                        "type": "large_buy_concentration",
                        "details": f"One buy order represents {largest_buy_pct:.1f}% of all buy orders",
                        "price": largest_buy.get("price"),
                        "size": largest_buy.get("size")
                    })
            
            if sell_orders:
                largest_sell = max(sell_orders, key=lambda x: x.get("size", 0))
                largest_sell_pct = largest_sell.get("size", 0) / sum(o.get("size", 0) for o in sell_orders) * 100
                
                if largest_sell_pct > 70:  # One order is >70% of all sell orders
                    manipulation_flags.append({
                        "market": question,
                        "type": "large_sell_concentration",
                        "details": f"One sell order represents {largest_sell_pct:.1f}% of all sell orders",
                        "price": largest_sell.get("price"),
                        "size": largest_sell.get("size")
                    })
            
            # Check for abnormal spread
            if buy_orders and sell_orders:
                best_bid = max([order.get("price", 0) for order in buy_orders])
                best_ask = min([order.get("price", 0) for order in sell_orders])
                spread = best_ask - best_bid
                spread_pct = (spread / best_bid * 100) if best_bid > 0 else 0
                
                if spread_pct > 20:  # Spread > 20%
                    manipulation_flags.append({
                        "market": question,
                        "type": "abnormal_spread",
                        "details": f"Abnormal spread of {spread_pct:.1f}% between best bid and ask",
                        "best_bid": best_bid,
                        "best_ask": best_ask
                    })
            
            # Check for large gaps in price levels (potential price manipulation)
            if len(buy_orders) > 1:
                buy_prices = sorted([order.get("price", 0) for order in buy_orders], reverse=True)
                max_gap = max([buy_prices[i] - buy_prices[i+1] for i in range(len(buy_prices)-1)])
                max_gap_pct = (max_gap / buy_prices[-1] * 100) if buy_prices[-1] > 0 else 0
                
                if max_gap_pct > 15:  # Gap > 15%
                    manipulation_flags.append({
                        "market": question,
                        "type": "large_buy_gap",
                        "details": f"Large gap of {max_gap_pct:.1f}% in buy order prices",
                        "max_gap": max_gap
                    })
            
            if len(sell_orders) > 1:
                sell_prices = sorted([order.get("price", 0) for order in sell_orders])
                max_gap = max([sell_prices[i+1] - sell_prices[i] for i in range(len(sell_prices)-1)])
                max_gap_pct = (max_gap / sell_prices[0] * 100) if sell_prices[0] > 0 else 0
                
                if max_gap_pct > 15:  # Gap > 15%
                    manipulation_flags.append({
                        "market": question,
                        "type": "large_sell_gap",
                        "details": f"Large gap of {max_gap_pct:.1f}% in sell order prices",
                        "max_gap": max_gap
                    })
        
        return manipulation_flags

    def compare_order_books(self, 
                            current_book: Dict[str, Dict[str, Any]], 
                            previous_book: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Compare two order books to detect changes.
        
        Args:
            current_book: Current order book data
            previous_book: Previous order book data
            
        Returns:
            Dictionary of changes for each market
        """
        changes = {}
        
        # Get common markets in both order books
        common_markets = set(current_book.keys()) & set(previous_book.keys())
        
        for market in common_markets:
            current_data = current_book[market]
            previous_data = previous_book[market]
            
            # Calculate changes in best bid/ask
            current_best_bid = max([o.get("price", 0) for o in current_data.get("buy_orders", [])]) if current_data.get("buy_orders") else 0
            previous_best_bid = max([o.get("price", 0) for o in previous_data.get("buy_orders", [])]) if previous_data.get("buy_orders") else 0
            
            current_best_ask = min([o.get("price", 0) for o in current_data.get("sell_orders", [])]) if current_data.get("sell_orders") else 100
            previous_best_ask = min([o.get("price", 0) for o in previous_data.get("sell_orders", [])]) if previous_data.get("sell_orders") else 100
            
            bid_change = current_best_bid - previous_best_bid
            ask_change = current_best_ask - previous_best_ask
            
            # Calculate changes in liquidity
            current_buy_liquidity = sum(o.get("total", 0) for o in current_data.get("buy_orders", []))
            previous_buy_liquidity = sum(o.get("total", 0) for o in previous_data.get("buy_orders", []))
            
            current_sell_liquidity = sum(o.get("total", 0) for o in current_data.get("sell_orders", []))
            previous_sell_liquidity = sum(o.get("total", 0) for o in previous_data.get("sell_orders", []))
            
            buy_liquidity_change = current_buy_liquidity - previous_buy_liquidity
            sell_liquidity_change = current_sell_liquidity - previous_sell_liquidity
            
            # Store changes
            changes[market] = {
                "bid_change": bid_change,
                "bid_change_pct": (bid_change / previous_best_bid * 100) if previous_best_bid > 0 else 0,
                "ask_change": ask_change,
                "ask_change_pct": (ask_change / previous_best_ask * 100) if previous_best_ask > 0 else 0,
                "buy_liquidity_change": buy_liquidity_change,
                "buy_liquidity_change_pct": (buy_liquidity_change / previous_buy_liquidity * 100) if previous_buy_liquidity > 0 else 0,
                "sell_liquidity_change": sell_liquidity_change,
                "sell_liquidity_change_pct": (sell_liquidity_change / previous_sell_liquidity * 100) if previous_sell_liquidity > 0 else 0
            }
        
        return changes

    def plot_order_book_depth(self, order_frames: Dict[str, Dict[str, Any]], market_question: str) -> None:
        """
        Plot order book depth chart for a specific market.
        
        Args:
            order_frames: Order book data
            market_question: The market question to plot
        """
        if market_question not in order_frames:
            print(f"Market '{market_question}' not found in order book data")
            return
        
        data = order_frames[market_question]
        buy_orders = sorted(data.get("buy_orders", []), key=lambda x: x.get("price", 0), reverse=True)
        sell_orders = sorted(data.get("sell_orders", []), key=lambda x: x.get("price", 0))
        is_synthetic = data.get("is_synthetic", True)
        
        # Calculate cumulative amounts
        buy_prices = [order.get("price", 0) for order in buy_orders]
        buy_amounts = [order.get("size", 0) for order in buy_orders]
        buy_cumulative = np.cumsum(buy_amounts)
        
        sell_prices = [order.get("price", 0) for order in sell_orders]
        sell_amounts = [order.get("size", 0) for order in sell_orders]
        sell_cumulative = np.cumsum(sell_amounts)
        
        # Create depth chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if buy_prices:
            ax.step(buy_prices, buy_cumulative, 'g-', where='post', label='Bids')
            ax.fill_between(buy_prices, buy_cumulative, step="post", alpha=0.2, color='green')
        
        if sell_prices:
            ax.step(sell_prices, sell_cumulative, 'r-', where='post', label='Asks')
            ax.fill_between(sell_prices, sell_cumulative, step="post", alpha=0.2, color='red')
        
        # Add data source to title
        data_source = "SYNTHETIC DATA" if is_synthetic else "Real Market Data"
        ax.set_title(f"Order Book Depth Chart: {market_question}\n({data_source})")
        
        # Add warning if synthetic
        if is_synthetic:
            ax.text(0.5, 0.02, 
                    "⚠️ WARNING: This data is synthetic and does not represent actual market liquidity ⚠️",
                    horizontalalignment='center',
                    color='red',
                    transform=ax.transAxes,
                    bbox=dict(facecolor='lightyellow', alpha=0.8, boxstyle='round,pad=0.5'))
        
        ax.set_xlabel("Price (%)")
        ax.set_ylabel("Cumulative Size")
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Add best bid/ask annotation
        best_bid = max(buy_prices) if buy_prices else 0
        best_ask = min(sell_prices) if sell_prices else 100
        
        if best_bid > 0:
            ax.axvline(x=best_bid, color='green', linestyle='--', alpha=0.7)
            ax.text(best_bid, 0, f"Best Bid: {best_bid:.1f}%", color='green', 
                    rotation=90, verticalalignment='bottom')
        
        if best_ask < 100:
            ax.axvline(x=best_ask, color='red', linestyle='--', alpha=0.7)
            ax.text(best_ask, 0, f"Best Ask: {best_ask:.1f}%", color='red', 
                    rotation=90, verticalalignment='bottom')
        
        plt.tight_layout()
        plt.show()

    def analyze_order_book(self, event_slug: str, visualize: bool = False) -> None:
        """
        Perform a comprehensive analysis of order book data for an event.
        
        Args:
            event_slug: The event slug to analyze
            visualize: Whether to generate visualizations
        """
        # First, fetch current order book data
        order_frames = PolymarketAPIClient.get_order_frames(event_slug)
        
        if not order_frames:
            print("No order book data available for this event.")
            return
        
        # Calculate liquidity metrics
        liquidity_metrics = self.calculate_market_liquidity(order_frames)
        
        # Detect potential manipulation
        manipulation_flags = self.detect_price_manipulation(order_frames)
        
        # Check if all data is synthetic
        all_synthetic = all(metrics.get("is_synthetic", True) for _, metrics in liquidity_metrics.items())
        some_synthetic = any(metrics.get("is_synthetic", True) for _, metrics in liquidity_metrics.items())
        
        # Print analysis results
        print("\n========== ORDER BOOK ANALYSIS ==========")
        print(f"Event: {event_slug}")
        print(f"Markets analyzed: {len(order_frames)}")
        
        if all_synthetic:
            print("\n⚠️ WARNING: All order book data is synthetic!")
            print("This data is generated based on real market prices but does not reflect")
            print("actual market liquidity. Do not use for trading decisions.")
        elif some_synthetic:
            print("\n⚠️ NOTE: Some markets use synthetic order book data.")
            print("Markets with synthetic data are marked with [SYNTHETIC] below.")
        
        # Print liquidity metrics for each market
        print("\n----- LIQUIDITY METRICS -----")
        for question, metrics in liquidity_metrics.items():
            synthetic_tag = "[SYNTHETIC]" if metrics.get("is_synthetic", True) else "[REAL DATA]"
            print(f"\nMarket: {question} {synthetic_tag}")
            print(f"  Best Bid: {metrics['best_bid']:.1f}%")
            print(f"  Best Ask: {metrics['best_ask']:.1f}%")
            if metrics['spread'] is not None:
                print(f"  Spread: {metrics['spread']:.1f}% ({metrics['spread_pct']:.1f}%)")
            print(f"  Buy Liquidity: ${metrics['buy_liquidity']:.2f}")
            print(f"  Sell Liquidity: ${metrics['sell_liquidity']:.2f}")
            print(f"  Total Liquidity: ${metrics['total_liquidity']:.2f}")
            print(f"  Liquidity Score: {metrics['liquidity_score']:.2f}")
        
        # Print manipulation flags if any
        if manipulation_flags:
            print("\n----- POTENTIAL MARKET ISSUES -----")
            for flag in manipulation_flags:
                market = flag['market']
                is_synthetic = liquidity_metrics.get(market, {}).get("is_synthetic", True)
                
                if is_synthetic:
                    print(f"\nMarket: {flag['market']} [SYNTHETIC - IGNORE WARNINGS]")
                    print(f"  ⚠️ Issue Type: {flag['type']} (based on synthetic data)")
                    print(f"  ⚠️ Details: {flag['details']}")
                    print(f"  ⚠️ Note: This issue is detected in synthetic data and may not reflect actual market conditions.")
                else:
                    print(f"\nMarket: {flag['market']}")
                    print(f"  Issue Type: {flag['type']}")
                    print(f"  Details: {flag['details']}")
        else:
            print("\n----- POTENTIAL MARKET ISSUES -----")
            print("No potential market issues detected.")
        
        # Generate visualizations if requested
        if visualize:
            print("\n----- GENERATING VISUALIZATIONS -----")
            for question in order_frames.keys():
                is_synthetic = liquidity_metrics.get(question, {}).get("is_synthetic", True)
                data_type = "synthetic" if is_synthetic else "real"
                print(f"\nGenerating depth chart for: {question} ({data_type} data)")
                self.plot_order_book_depth(order_frames, question)

def main():
    """CLI entry point for the Order Book Analyzer."""
    parser = argparse.ArgumentParser(description="Polymarket Order Book Analysis Tool")
    
    parser.add_argument("--slug", type=str, required=True,
                        help="Slug of the Polymarket event to analyze")
    parser.add_argument("--visualize", action="store_true",
                        help="Generate and display visualizations")
    
    args = parser.parse_args()
    
    analyzer = OrderBookAnalyzer()
    analyzer.analyze_order_book(args.slug, args.visualize)

if __name__ == "__main__":
    main() 