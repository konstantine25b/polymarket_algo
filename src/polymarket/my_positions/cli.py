#!/usr/bin/env python3
"""
Command-line interface for the Polymarket position tracker with profit/loss calculations.
"""

import argparse
import os
import sys
import logging
from datetime import datetime

from src.polymarket.my_positions.position_tracker import PolymarketPositionTracker

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Track and analyze Polymarket positions with profit/loss calculations')
    
    # Position and trade information
    parser.add_argument('--positions', action='store_true', help='Display basic position summary')
    parser.add_argument('--detailed', action='store_true', help='Display detailed position information')
    parser.add_argument('--positions-table', action='store_true', help='Display current positions as a formatted table with P&L info')
    parser.add_argument('--simple-positions', action='store_true', help='Display a simple list of market IDs and share quantities')
    parser.add_argument('--save-table-image', action='store_true', help='Save the positions table as an image')
    parser.add_argument('--table-image-path', type=str, help='Path for the saved table image')
    parser.add_argument('--trades-table', action='store_true', help='Display all trades grouped by market as tables with P&L metrics')
    parser.add_argument('--market-trades', type=str, metavar='MARKET_ID', help='Display trades for a specific market')
    
    # Visualization options
    parser.add_argument('--visualize', action='store_true', help='Generate all visualizations')
    parser.add_argument('--positions-chart', action='store_true', help='Generate position visualization charts')
    parser.add_argument('--trade-history', action='store_true', help='Generate trade history visualization')
    parser.add_argument('--market-chart', type=str, metavar='MARKET_ID', help='Generate trade chart for a specific market')
    parser.add_argument('--show-plots', action='store_true', help='Show visualization plots interactively')
    
    # Export options
    parser.add_argument('--export-positions', action='store_true', help='Export positions to JSON')
    parser.add_argument('--export-positions-csv', action='store_true', help='Export positions to CSV with P&L information')
    parser.add_argument('--export-trades-csv', action='store_true', help='Export trades by market to CSV with P&L metrics')
    parser.add_argument('--csv-dir', type=str, help='Directory to save CSV files')
    
    # Advanced configuration
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--output-dir', type=str, help='Output directory for generated files')
    parser.add_argument('--clear-cache', action='store_true', help='Clear cached market data')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    return parser.parse_args()

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize the position tracker
    output_dir = args.output_dir if args.output_dir else None
    tracker = PolymarketPositionTracker(
        output_dir=output_dir,
        log_level=log_level
    )
    
    if args.clear_cache and hasattr(tracker, 'clear_market_cache'):
        tracker.clear_market_cache()
        print("Market cache cleared.")
    
    # Display position summaries if requested
    if args.positions or (not any([args.detailed, args.positions_table, args.trades_table, args.market_trades, 
                                  args.visualize, args.positions_chart, args.trade_history, args.market_chart,
                                  args.export_positions, args.export_positions_csv, args.export_trades_csv,
                                  args.save_table_image, args.simple_positions])):
        print("\nPOSITION SUMMARY (with P&L calculations):")
        positions = tracker.get_positions_summary()
        tracker.print_positions_summary(positions)
    
    if args.simple_positions:
        print("\nSIMPLE POSITIONS (Market ID -> Outcome -> Share Quantity):")
        simple_positions = tracker.get_simple_positions()
        for market_id, outcomes in simple_positions.items():
            market_name = tracker.get_market_name(market_id)
            print(f"\n{market_name} ({market_id}):")
            for outcome, quantity in outcomes.items():
                print(f"  {outcome}: {quantity:.6f} shares")
    
    if args.detailed:
        print("\nDETAILED POSITIONS:")
        positions = tracker.get_detailed_positions()
        tracker.print_detailed_positions(positions)
    
    if args.positions_table or args.save_table_image:
        save_image = args.save_table_image
        image_path = args.table_image_path if args.table_image_path else None
        tracker.display_positions_table(save_image=save_image, filename=image_path)
    
    if args.trades_table:
        tracker.display_trades_by_market()
    
    if args.market_trades:
        market_id = args.market_trades
        trades = tracker.get_trades_by_market(market_id)
        print(f"\nTRADES FOR MARKET: {tracker.get_market_name(market_id)} ({market_id})")
        if trades:
            market_trades_df = tracker.trades_to_dataframe(trades)
            if not market_trades_df.empty:
                market_pl_data = tracker.market_gains.get(market_id, {}) if hasattr(tracker, 'market_gains') else {}
                print(market_trades_df[['outcome', 'match_time', 'price', 'size', 'my_side', 'position_impact', 'gain_loss_usd', 'percent_change']])
                
                # Display market P&L summary
                if market_pl_data:
                    realized_pl = market_pl_data.get('realized_pl', 0)
                    unrealized_pl = market_pl_data.get('unrealized_pl', 0)
                    print(f"\nMarket P&L Summary:")
                    print(f"  Realized P&L: ${realized_pl:.2f}")
                    print(f"  Unrealized P&L: ${unrealized_pl:.2f}")
                    print(f"  Total P&L: ${realized_pl + unrealized_pl:.2f}")
            else:
                print("No trade data available for this market.")
        else:
            print("No trades found for this market.")
    
    # Export position data if requested
    if args.export_positions:
        positions = tracker.get_detailed_positions()
        tracker.export_positions(positions)
    
    # Export positions to CSV if requested
    if args.export_positions_csv:
        csv_dir = args.csv_dir if args.csv_dir else None
        if csv_dir:
            # Create custom directory if it doesn't exist
            os.makedirs(csv_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(csv_dir, f"positions_table_{timestamp}.csv")
            tracker.export_positions_table(file_path=file_path)
        else:
            tracker.export_positions_table()
    
    # Export trades to CSV if requested
    if args.export_trades_csv:
        csv_dir = args.csv_dir if args.csv_dir else None
        if csv_dir:
            # Create custom directory if it doesn't exist
            os.makedirs(csv_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(csv_dir, f"trades_by_market_{timestamp}.csv")
            tracker.export_trades_by_market(file_path=file_path)
        else:
            tracker.export_trades_by_market()
    
    # Generate visualizations if requested
    viz_files = []
    
    if args.visualize or args.positions_chart:
        pos_chart = tracker.visualize_positions_chart()
        if pos_chart:
            viz_files.append(pos_chart)
    
    if args.visualize or args.trade_history:
        trade_history = tracker.visualize_trade_history()
        if trade_history:
            viz_files.append(trade_history)
    
    if args.market_chart:
        market_id = args.market_chart
        market_chart = tracker.visualize_market_trades(market_id)
        if market_chart:
            viz_files.append(market_chart)
    
    # Show plots interactively if requested
    if args.show_plots and viz_files:
        try:
            import matplotlib.pyplot as plt
            plt.show()
        except ImportError:
            print("Matplotlib is required to show plots interactively.")
    
    # Print generated file paths
    if viz_files:
        print("\nGenerated visualization files:")
        for f in viz_files:
            print(f"- {f}")

if __name__ == '__main__':
    main() 