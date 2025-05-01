#!/usr/bin/env python3
"""
Visualize Polymarket order book data.
This script generates visualizations for order book data, 
including price distribution and order depth charts.
"""

import os
import json
import argparse
import logging
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.axes import Axes

# Import from project
from src.constants import DATA_DIR, PLOTS_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_output_dirs() -> Path:
    """Create the necessary output directories for plots."""
    # Create base plots directory
    plots_dir = PLOTS_DIR / "order_book"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    return plots_dir

def load_order_book_data(file_path: str) -> Dict[str, Any]:
    """Load order book data from a JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

def find_latest_order_book_file() -> Optional[str]:
    """Find the most recent order book data file."""
    # Get the path for stored order book data
    json_dir = DATA_DIR / "order_book" / "json"
    
    # Find all JSON files
    json_files = glob.glob(str(json_dir / "*.json"))
    
    if not json_files:
        logger.error("No order book data files found.")
        return None
    
    # Get the most recent file based on modification time
    latest_file = max(json_files, key=os.path.getmtime)
    logger.info(f"Using most recent order book data: {latest_file}")
    
    return latest_file

def plot_order_book_depth(ax: Axes, buy_orders: List[Dict], sell_orders: List[Dict], market_name: str) -> None:
    """
    Plot the order book depth chart for a single market.
    
    Args:
        ax: Matplotlib axes to plot on
        buy_orders: List of buy orders with price and size
        sell_orders: List of sell orders with price and size
        market_name: Name of the market for the title
    """
    # Extract prices and sizes
    buy_prices = [order['price'] for order in buy_orders]
    buy_sizes = [order['size'] for order in buy_orders]
    sell_prices = [order['price'] for order in sell_orders]
    sell_sizes = [order['size'] for order in sell_orders]
    
    # Calculate cumulative sizes
    buy_cumulative = np.cumsum(buy_sizes)
    sell_cumulative = np.cumsum(sell_sizes)
    
    # Plot buy orders (bids) in green
    if buy_prices and buy_cumulative.size > 0:
        ax.step(buy_prices, buy_cumulative, where='post', color='green', label='Bids')
        ax.fill_between(buy_prices, 0, buy_cumulative, step='post', alpha=0.2, color='green')
    
    # Plot sell orders (asks) in red
    if sell_prices and sell_cumulative.size > 0:
        ax.step(sell_prices, sell_cumulative, where='post', color='red', label='Asks')
        ax.fill_between(sell_prices, 0, sell_cumulative, step='post', alpha=0.2, color='red')
    
    # Set chart properties
    ax.set_title(f"Order Book Depth: {market_name}", fontsize=10)
    ax.set_xlabel("Price (%)")
    ax.set_ylabel("Cumulative Size")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Set x-axis to show percentage with % sign
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.1f}%'))

def plot_price_histogram(ax: Axes, buy_orders: List[Dict], sell_orders: List[Dict], market_name: str) -> None:
    """
    Plot a histogram of order prices for a single market.
    
    Args:
        ax: Matplotlib axes to plot on
        buy_orders: List of buy orders with price and size
        sell_orders: List of sell orders with price and size
        market_name: Name of the market for the title
    """
    # Extract prices and sizes for weighting
    buy_prices = [order['price'] for order in buy_orders]
    buy_weights = [order['size'] for order in buy_orders]
    sell_prices = [order['price'] for order in sell_orders]
    sell_weights = [order['size'] for order in sell_orders]
    
    # Determine bins based on the range of prices
    all_prices = buy_prices + sell_prices
    if not all_prices:
        ax.text(0.5, 0.5, "No order data available", ha='center', va='center')
        ax.set_title(f"Price Distribution: {market_name}", fontsize=10)
        return
        
    min_price = min(all_prices) - 1
    max_price = max(all_prices) + 1
    bins = np.linspace(min_price, max_price, 20)
    
    # Plot histograms
    if buy_prices:
        ax.hist(buy_prices, bins=bins, weights=buy_weights, alpha=0.5, color='green', label='Bids')
    if sell_prices:
        ax.hist(sell_prices, bins=bins, weights=sell_weights, alpha=0.5, color='red', label='Asks')
    
    # Set chart properties
    ax.set_title(f"Price Distribution: {market_name}", fontsize=10)
    ax.set_xlabel("Price (%)")
    ax.set_ylabel("Total Size")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Set x-axis to show percentage with % sign
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.1f}%'))

def visualize_all_markets(order_book_data: Dict[str, Any], output_dir: Path) -> List[str]:
    """
    Generate visualization plots for all markets in the order book data.
    
    Args:
        order_book_data: The order book data dictionary
        output_dir: Directory to save the plots
        
    Returns:
        List of paths to the generated plot files
    """
    # Extract the questions (markets) from the order book data
    questions = order_book_data.get('questions', {})
    event_title = order_book_data.get('event_title', 'Polymarket Order Book')
    timestamp = order_book_data.get('timestamp', datetime.now().isoformat())
    
    # Parse the timestamp
    try:
        dt = datetime.fromisoformat(timestamp)
        timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        timestamp_str = timestamp
    
    # List to store all generated file paths
    generated_files = []
    
    # Create plot for each market
    for question, market_data in questions.items():
        # Extract order data
        buy_orders = market_data.get('buy_orders', [])
        sell_orders = market_data.get('sell_orders', [])
        
        # Sort orders by price
        buy_orders = sorted(buy_orders, key=lambda x: x['price'], reverse=True)
        sell_orders = sorted(sell_orders, key=lambda x: x['price'])
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Clean up the question for display
        display_name = question.replace('Will Elon tweet ', '')
        
        # Plot order book depth
        plot_order_book_depth(ax1, buy_orders, sell_orders, display_name)
        
        # Plot price histogram
        plot_price_histogram(ax2, buy_orders, sell_orders, display_name)
        
        # Add a title to the figure
        fig.suptitle(f"{event_title} - {timestamp_str}", fontsize=12)
        fig.tight_layout()
        
        # Save the figure
        filename = f"orderbook_{display_name.replace(' ', '_').replace('?', '').replace('-', '_')}.png"
        output_path = output_dir / filename
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Saved visualization for {display_name} to {output_path}")
        generated_files.append(str(output_path))
        
    # Create a combined visualization of all market midpoints
    if questions:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Extract midpoint prices for each market
        market_names = []
        yes_probabilities = []
        
        for question, market_data in questions.items():
            # Calculate midpoint from order book
            buy_orders = sorted(market_data.get('buy_orders', []), key=lambda x: x['price'], reverse=True)
            sell_orders = sorted(market_data.get('sell_orders', []), key=lambda x: x['price'])
            
            if buy_orders and sell_orders:
                best_bid = buy_orders[0]['price']
                best_ask = sell_orders[0]['price']
                midpoint = (best_bid + best_ask) / 2
            elif buy_orders:
                midpoint = buy_orders[0]['price']
            elif sell_orders:
                midpoint = sell_orders[0]['price']
            else:
                continue
                
            # Clean up the question for display
            display_name = question.replace('Will Elon tweet ', '')
            
            market_names.append(display_name)
            yes_probabilities.append(midpoint)
        
        # Sort by probabilities
        sorted_indices = np.argsort(yes_probabilities)
        sorted_names = [market_names[i] for i in sorted_indices]
        sorted_probs = [yes_probabilities[i] for i in sorted_indices]
        
        # Plot horizontal bar chart
        bars = ax.barh(sorted_names, sorted_probs, color='skyblue')
        
        # Add value labels
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height()/2, 
                    f'{sorted_probs[i]:.1f}%', va='center')
        
        # Set chart properties
        ax.set_title(f"{event_title} - Market Probabilities - {timestamp_str}")
        ax.set_xlabel("Probability (%)")
        ax.set_xlim(0, 100)
        ax.grid(True, alpha=0.3)
        
        # Save the figure
        filename = "orderbook_all_markets_summary.png"
        output_path = output_dir / filename
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Saved summary visualization to {output_path}")
        generated_files.append(str(output_path))
        
    return generated_files

def visualize_order_book(file_path: Optional[str] = None) -> List[str]:
    """
    Generate visualizations for Polymarket order book data.
    
    Args:
        file_path: Path to the order book data file. If None, uses the most recent file.
        
    Returns:
        List of file paths to the generated plots.
    """
    # If no file path provided, find the most recent one
    if file_path is None:
        file_path = find_latest_order_book_file()
        if file_path is None:
            return []
    
    # Load the order book data
    try:
        order_book_data = load_order_book_data(file_path)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading order book data: {e}")
        return []
    
    # Create output directory for plots
    output_dir = create_output_dirs()
    
    # Generate the visualizations
    return visualize_all_markets(order_book_data, output_dir)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Visualize Polymarket order book data")
    parser.add_argument("--file", type=str, help="Path to order book data file")
    args = parser.parse_args()
    
    generated_files = visualize_order_book(args.file)
    
    if generated_files:
        logger.info(f"Generated {len(generated_files)} visualization files.")
    else:
        logger.warning("No visualizations were generated.")

if __name__ == "__main__":
    main() 