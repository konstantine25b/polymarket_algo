#!/usr/bin/env python3
"""
Command-line tool to print all sell opportunities from the comparison table
and execute automatic sell orders for positions that should be sold.
"""

import argparse
import logging
import sys
import pandas as pd
from dotenv import load_dotenv

from .position_seller import PositionSeller
from src.bidding_decision.stats.comparison import generate_comparison_table
from src.constants import POLYMARKET_START_TIME, POLYMARKET_END_TIME

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
    parser.add_argument('--active-market-only', action='store_true',
                         help='Only sell positions for the active market (current time frame)')
    parser.add_argument('--algorithm', type=str, default='prophet',
                         choices=['prophet', 'facebook_prophet', 'enhanced_facebook_prophet', 'neural_prophet', 'enhanced_neural_prophet', 'timesfm', 'enhanced_timesfm', 'ensemble'],
                         help='Prediction algorithm to use (default: prophet)')
    parser.add_argument('--random-seed', type=int, default=42,
                         help='Random seed for reproducible predictions (default: 42)')
    parser.add_argument('--show-eachalgo-distribution', action='store_true',
                         help='Show probability distribution for each individual algorithm (enhanced_facebook_prophet and ensemble only)')
    parser.add_argument('--show-positions', action='store_true',
                         help='Show all current positions before analysis')
    parser.add_argument('--show-active-positions', action='store_true',
                         help='Show positions for active market before analysis')
    
    # Ensemble model weight arguments
    parser.add_argument('--neural-prophet-weight', type=float, default=0.17,
                        help='Weight for Neural Prophet model in ensemble (default: 0.17, set to 0 to exclude)')
    parser.add_argument('--facebook-prophet-weight', type=float, default=0.25,
                        help='Weight for Facebook Prophet model in ensemble (default: 0.25, set to 0 to exclude)')
    parser.add_argument('--timesfm-weight', type=float, default=0.30,
                        help='Weight for TimesFM model in ensemble (default: 0.30, set to 0 to exclude)')
    parser.add_argument('--basic-prophet-weight', type=float, default=0.25,
                        help='Weight for Basic Prophet model in ensemble (default: 0.25, set to 0 to exclude)')
    parser.add_argument('--moving-average-weight', type=float, default=0.015,
                        help='Weight for Moving Average in ensemble (default: 0.015, set to 0 to exclude)')
    parser.add_argument('--linear-trend-weight', type=float, default=0.015,
                        help='Weight for Linear Trend in ensemble (default: 0.015, set to 0 to exclude)')
    
    args = parser.parse_args()
    
    # Set up logging levels based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Display positions if requested (before model training to avoid interruption)
        if args.show_positions or args.show_active_positions:
            from src.polymarket.my_positions.position_tracker import PolymarketPositionTracker
            
            print("\n" + "=" * 80)
            print("📊 CURRENT POSITIONS")
            print("=" * 80)
            
            tracker = PolymarketPositionTracker()
            
            if args.show_positions:
                print("All current positions:")
                positions = tracker.get_simple_positions()
                if positions:
                    for market_id, outcomes in positions.items():
                        market_name = tracker.get_market_name(market_id)
                        print(f"\n🎯 {market_name}")
                        for outcome, quantity in outcomes.items():
                            print(f"   {outcome}: {quantity:.6f} shares")
                else:
                    print("No positions found.")
            
            if args.show_active_positions:
                print("\nActive market positions:")
                active_positions = tracker.get_active_market_positions()
                if active_positions:
                    for market_id, outcomes in active_positions.items():
                        market_name = tracker.get_market_name(market_id)
                        print(f"\n🎯 {market_name}")
                        for outcome, quantity in outcomes.items():
                            print(f"   {outcome}: {quantity:.6f} shares")
                else:
                    print("No active market positions found.")
            
            print("=" * 80 + "\n")
        
        # Create the position seller with debug flag and algorithm parameters
        seller = PositionSeller(
            threshold=args.threshold, 
            sell_below=args.sell_below, 
            debug=args.debug,
            algorithm=args.algorithm,
            random_seed=args.random_seed,
            show_eachalgo_distribution=args.show_eachalgo_distribution,
            neural_prophet_weight=args.neural_prophet_weight,
            facebook_prophet_weight=args.facebook_prophet_weight,
            timesfm_weight=args.timesfm_weight,
            basic_prophet_weight=args.basic_prophet_weight,
            moving_average_weight=args.moving_average_weight,
            linear_trend_weight=args.linear_trend_weight
        )
        
        # Generate the comparison table once - this will be displayed by PositionSeller methods
        # The table display will happen inside get_all_positions_with_stats if no pre-generated table is passed
        all_positions, comparison_df = seller.get_all_positions_with_stats()
        
        # Print all market names for debugging
        print("\nAll market names:")
        for position in all_positions:
            print(f"  {position.get('market_name', 'Unknown')}")
        
        # Filter for active market only if requested
        if args.active_market_only and all_positions:
            # Get the active market time frame from constants
            active_start = POLYMARKET_START_TIME
            active_end = POLYMARKET_END_TIME
            
            # Extract the dates from the constants (format: "YYYY-MM-DD HH:MM:SS")
            active_start_date = active_start.split(" ")[0]
            active_end_date = active_end.split(" ")[0]
            
            # Format the date range for filtering - create multiple possible formats
            active_start_month = active_start_date.split('-')[1]
            active_start_day = active_start_date.split('-')[2]
            active_end_month = active_end_date.split('-')[1]
            active_end_day = active_end_date.split('-')[2]
            
            # Get the month name from the month number
            months = {
                '01': 'January', '02': 'February', '03': 'March', '04': 'April',
                '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                '09': 'September', '10': 'October', '11': 'November', '12': 'December'
            }
            start_month_name = months.get(active_start_month, 'Unknown')
            end_month_name = months.get(active_end_month, 'Unknown')
            
            # Different possible formats for the market name
            # Handle both same-month and cross-month date ranges
            possible_formats = []
            
            if active_start_month == active_end_month:
                # Same month: "June 27–30", "June 27-30"
                possible_formats.extend([
                    f"{start_month_name} {int(active_start_day)}–{int(active_end_day)}",
                    f"{start_month_name} {int(active_start_day)}-{int(active_end_day)}",
                    f"{start_month_name} {active_start_day}–{active_end_day}",
                    f"{start_month_name} {active_start_day}-{active_end_day}"
                ])
            else:
                # Cross-month: "June 27–July 4", "June 27-July 4"
                possible_formats.extend([
                    f"{start_month_name} {int(active_start_day)}–{end_month_name} {int(active_end_day)}",
                    f"{start_month_name} {int(active_start_day)}-{end_month_name} {int(active_end_day)}",
                    f"{start_month_name} {active_start_day}–{end_month_name} {active_end_day}",
                    f"{start_month_name} {active_start_day}-{end_month_name} {active_end_day}"
                ])
            
            # Add "from Month Day to Month Day" format (new market phrasing)
            possible_formats.extend([
                f"from {start_month_name} {int(active_start_day)} to {end_month_name} {int(active_end_day)}",
                f"from {start_month_name} {active_start_day} to {end_month_name} {active_end_day}"
            ])
            
            # Also include the numeric format for fallback
            numeric_format = f"{active_start_month}-{active_start_day}–{active_end_month}-{active_end_day}"
            possible_formats.append(numeric_format)
            
            # Log the active market we're filtering for
            logger.info(f"Filtering for active market only: {numeric_format}")
            print(f"\nFiltering for active market only: {numeric_format}")
            logger.debug(f"Looking for market names containing any of: {possible_formats}")
            
            # Filter positions to only include those from the active market
            filtered_positions = []
            for position in all_positions:
                market_name = position.get('market_name', '')
                # Check if any of the possible formats are in the market name
                is_active_market = any(fmt in market_name for fmt in possible_formats)
                
                if is_active_market:
                    filtered_positions.append(position)
                    logger.debug(f"Keeping position: {market_name}")
                else:
                    logger.debug(f"Filtering out position: {market_name}")
            
            # Log how many positions were filtered out
            logger.info(f"Filtered from {len(all_positions)} to {len(filtered_positions)} positions for active market")
            print(f"Filtered from {len(all_positions)} to {len(filtered_positions)} positions for active market")
            
            # Use the filtered positions
            all_positions = filtered_positions
        
        # Now get only the positions that should be sold from the filtered list
        positions_to_sell = [pos for pos in all_positions if pos.get('should_sell', False)]
        
        if args.auto_sell:
            # Execute all sell orders (with dry run mode if requested) using the pre-generated table
            if positions_to_sell:
                seller.execute_sell_orders(positions_to_sell, dry_run=args.dry_run, comparison_df=comparison_df)
            else:
                print("\nNo positions recommended for selling with threshold {:.1f}%".format(args.threshold))
                if args.sell_below > 0:
                    print(f"or prediction below {args.sell_below}%.")
                
                # If we have active market positions but none to sell, show them anyway
                if all_positions:
                    print("\nActive market positions (not recommended for selling):")
                    for position in all_positions:
                        print(f"  {position['market_name']} - {position['outcome']}: {position['quantity']:.6f} shares")
        else:
            # Just show recommendations
            if positions_to_sell:
                seller.print_sell_recommendations(positions_to_sell)
            else:
                print("\nNo positions recommended for selling with threshold {:.1f}%".format(args.threshold))
                if args.sell_below > 0:
                    print(f"or prediction below {args.sell_below}%.")
                
                # If we have active market positions but none to sell, show them anyway
                if all_positions:
                    print("\nActive market positions (not recommended for selling):")
                    for position in all_positions:
                        print(f"  {position['market_name']} - {position['outcome']}: {position['quantity']:.6f} shares")
        
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