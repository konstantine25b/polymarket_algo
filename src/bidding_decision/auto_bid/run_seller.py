#!/usr/bin/env python3
"""
Command-line script for running the PositionSeller to identify positions to sell.
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
    """
    Command-line entry point for the position seller.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Identify which positions should be sold based on comparison data')
    parser.add_argument('--threshold', type=float, default=0.0,
                        help='Minimum opportunity percentage required (default: 0.0)')
    parser.add_argument('--no-stats', action='store_true',
                        help='Do not print full statistics table')
    parser.add_argument('--verbose', '-v', action='store_true', 
                        help='Enable verbose logging')
    parser.add_argument('--sell-only', action='store_true',
                        help='Show only positions to sell, not all positions')
    parser.add_argument('--auto-sell', action='store_true',
                        help='Automatically execute sell orders for recommended positions')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be sold but don\'t execute actual sell orders')
    
    args = parser.parse_args()
    
    # Set logging level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)
    
    # Create the position seller
    seller = PositionSeller(threshold=args.threshold)
    
    try:
        # Generate the comparison table directly for displaying full stats
        comparison_df = None
        if not args.no_stats:
            comparison_df = generate_comparison_table(
                refresh=True,
                use_prophet=True,
                threshold=args.threshold
            )
            
            if not comparison_df.empty:
                print_stats_table(comparison_df)
        
        # Retrieve all positions with stats
        all_positions, _ = seller.get_all_positions_with_stats()
        
        # Get positions to sell
        positions_to_sell = [pos for pos in all_positions if pos['should_sell']]
        
        # Execute automatic selling if requested
        if args.auto_sell:
            seller.execute_sell_orders(positions_to_sell, dry_run=args.dry_run)
        # Display positions based on command line option
        elif args.sell_only:
            # Get and print only positions to sell
            seller.print_sell_recommendations(positions_to_sell)
            
            if not positions_to_sell:
                print("\nNo positions recommended for selling at this time.")
            else:
                print(f"\nFound {len(positions_to_sell)} positions to sell based on current market conditions.")
        else:
            # Print all positions with recommendations
            seller.print_all_positions(all_positions)
            
            # Count positions to sell for the summary
            if positions_to_sell:
                print(f"\nFound {len(positions_to_sell)} positions to sell out of {len(all_positions)} total positions.")
    
    except KeyboardInterrupt:
        print("\nOperation canceled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 