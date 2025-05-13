#!/usr/bin/env python3
"""
Command-line tool to print all sell opportunities from the comparison table
and execute automatic sell orders for positions that should be sold.
"""

import argparse
import logging
import sys
import pandas as pd

from .position_seller import PositionSeller
from src.bidding_decision.stats.comparison import generate_comparison_table

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_stats_table(df):
    """
    Print the full stats comparison table.
    
    Args:
        df: DataFrame with comparison data
    """
    # Set pandas display options to show all columns
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.float_format', '{:.2f}'.format)
    pd.set_option('display.precision', 2)
    
    # Determine which columns to show in the main display
    display_cols = [col for col in df.columns if col not in ['Token ID', 'Market ID']]
    
    print("\nComparison Table:")
    print(df[display_cols].to_string(index=False))
    
    # Show the threshold being used
    sell_only_col = [col for col in df.columns if col.startswith('Sell-Only')][0]
    threshold_value = float(sell_only_col.split('(')[1].split('%')[0])
    print(f"\nUsing threshold: {threshold_value}%")
    
    # Show token IDs in a cleaner format
    print("\nToken IDs:")
    data_rows = df[df['Range'] != 'EXPECTED VALUE']
    for _, row in data_rows.iterrows():
        if 'Token ID' in row and row['Token ID']:
            print(f"{row['Range']}: {row['Token ID']}")
    
    # Get expected value info
    ev_row = df[df['Range'] == 'EXPECTED VALUE'].iloc[0]
    print("\nExpected Values:")
    print(f"Prediction: {ev_row['Pred (%)']}%")
    print(f"Market: {ev_row['Mkt (%)']}%")
    print(f"Difference: {ev_row['Diff (%)']}%")

def main():
    """Main entry point for the auto seller."""
    parser = argparse.ArgumentParser(description='Identify positions to sell and execute sell orders')
    parser.add_argument('--threshold', type=float, default=0.0,
                        help='Minimum opportunity percentage (default: 0.0)')
    parser.add_argument('--auto-sell', action='store_true',
                        help='Automatically execute sell orders for recommended positions')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be sold but don\'t execute actual sell orders')
    parser.add_argument('--no-stats', action='store_true',
                        help='Don\'t show the full statistical comparison table')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--sell-below', type=float, default=0.0,
                        help='Sell positions with prediction below this percentage (default: 0.0)')
    parser.add_argument('--debug', action='store_true',
                        help='Show detailed debugging information')
    
    args = parser.parse_args()
    
    # Set up logging levels based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create the position seller with debug flag
        seller = PositionSeller(threshold=args.threshold, sell_below=args.sell_below, debug=args.debug)
        
        # Get all recommended positions to sell
        positions_to_sell = seller.get_positions_to_sell()
        
        if args.auto_sell:
            # Execute all sell orders (with dry run mode if requested)
            seller.execute_sell_orders(positions_to_sell, dry_run=args.dry_run)
        else:
            # Just show recommendations
            seller.print_sell_recommendations(positions_to_sell)
        
        # Log the number of positions found
        num_positions = len(positions_to_sell)
        if num_positions > 0:
            logger.info(f"Found {num_positions} positions to sell")
        else:
            logger.info("No positions found to sell")
            
        # Always return 0 for success
        return 0
    
    except Exception as e:
        logger.error(f"Error in auto-seller: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 