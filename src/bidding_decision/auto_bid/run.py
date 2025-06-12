#!/usr/bin/env python3
"""
Command-line script for running the AutoBidder.
"""

import argparse
import logging
import sys
from typing import Optional
from dotenv import load_dotenv
import os
import pandas as pd

from .bidder import AutoBidder
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
    buy_only_col = [col for col in df.columns if col.startswith('Buy-Only')][0]
    threshold_value = float(buy_only_col.split('(')[1].split('%')[0])
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
    Command-line entry point for the auto-bidder.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Auto-bid on Polymarket opportunities')
    parser.add_argument('--threshold', type=float, default=0.0,
                        help='Minimum opportunity percentage required (default: 0.0)')
    parser.add_argument('--amount', type=float, default=1.0,
                        help='Amount to bid in USDC (default: 1.0)')
    parser.add_argument('--key', type=str,
                        help='Private key for wallet (optional, will use .env if not provided)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Find opportunities but do not place orders')
    parser.add_argument('--no-stats', action='store_true',
                        help='Do not print full statistics table')
    parser.add_argument('--weighted-selection', action='store_true',
                        help='Use weighted selection from multiple opportunities rather than always choosing the best one')
    parser.add_argument('--min-prediction', type=float, default=0.0,
                        help='Only bid on opportunities with prediction percentage at or above this value (default: 0.0)')
    parser.add_argument('--algorithm', type=str, default='prophet',
                        choices=['prophet', 'facebook_prophet', 'enhanced_facebook_prophet', 'neural_prophet', 'enhanced_neural_prophet', 'timesfm', 'enhanced_timesfm', 'ensemble'],
                        help='Prediction algorithm to use (default: prophet)')
    parser.add_argument('--random-seed', type=int, default=42,
                        help='Random seed for reproducible predictions (default: 42)')
    
    args = parser.parse_args()
    
    # Load environment variables if no key is provided
    if not args.key:
        load_dotenv()
        
    # Create the auto-bidder
    bidder = AutoBidder(
        threshold=args.threshold,
        order_amount=args.amount,
        use_weighted_selection=args.weighted_selection,
        min_prediction=args.min_prediction,
        algorithm=args.algorithm,
        random_seed=args.random_seed
    )
    
    try:
        # Connect to Polymarket
        if not bidder.connect(args.key):
            logger.error("Failed to connect to Polymarket. Exiting.")
            sys.exit(1)
        
        # Generate the comparison table once and reuse it
        comparison_df = generate_comparison_table(
            refresh=True,
            use_prophet=True,
            algorithm=args.algorithm,
            threshold=args.threshold,
            silent=args.no_stats,  # Only suppress output if --no-stats is used
            random_seed=args.random_seed
        )
        
        if comparison_df.empty:
            logger.info("No comparison data available. Exiting.")
            sys.exit(0)
        
        # Display stats table if requested
        if not args.no_stats:
            print_stats_table(comparison_df)
        
        # Find the best opportunity using the already-generated comparison table
        opportunity = bidder.find_best_opportunity(comparison_df=comparison_df)
        
        if not opportunity:
            logger.info("No suitable opportunities found. Exiting.")
            sys.exit(0)
        
        # Print opportunity details
        selection_method = "weighted selection" if opportunity.get('selection_method') == 'weighted' else "highest edge"
        total_opps = opportunity.get('total_opportunities', 1)
        
        print("\nSelected Buy Opportunity:")
        print(f"Range: {opportunity['range']}")
        print(f"Prediction: {opportunity['prediction']}%")
        print(f"Market Ask Price: {opportunity['ask']}%")
        print(f"Edge: {opportunity['opportunity']}% (after applying {args.threshold}% threshold)")
        print(f"Token ID: {opportunity['token_id']}")
        print(f"Algorithm: {args.algorithm} (seed: {args.random_seed})")
        
        if total_opps > 1:
            print(f"Selection method: {selection_method} from {total_opps} positive opportunities")
        
        if args.min_prediction > 0:
            print(f"Prediction meets minimum threshold of {args.min_prediction}%")
        
        # Place the order if not a dry run
        if args.dry_run:
            print("\nDRY RUN - No order placed.")
        else:
            print(f"\nPlacing market buy order for {args.amount} USDC...")
            if bidder.place_order(opportunity):
                print("Order placed successfully!")
            else:
                print("Failed to place order. See logs for details.")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperation canceled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 