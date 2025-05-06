#!/usr/bin/env python
import os
import argparse
import logging
import sys
from datetime import datetime
from .position_tracker import PolymarketPositionTracker
import pandas as pd

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Track and analyze your Polymarket positions based on trade history.'
    )
    
    parser.add_argument('--market', '-m', type=str, 
                        help='Filter positions by specific market ID')
    parser.add_argument('--output', '-o', type=str, default='output',
                        help='Directory to save output files (default: output)')
    parser.add_argument('--save', '-s', action='store_true',
                        help='Save results to a JSON file')
    parser.add_argument('--filename', '-f', type=str,
                        help='Custom filename for saved results (implies --save)')
    parser.add_argument('--key', '-k', type=str,
                        help='Wallet private key (if not set in .env)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    
    # Table Options
    table_group = parser.add_argument_group('Table Options')
    table_group.add_argument('--positions-table', action='store_true',
                        help='Display current positions as a formatted table')
    table_group.add_argument('--trades-table', action='store_true',
                        help='Display all trades grouped by market as tables')
    table_group.add_argument('--export-positions-csv', action='store_true',
                        help='Export positions to a CSV file')
    table_group.add_argument('--export-trades-csv', action='store_true',
                        help='Export trades by market to a CSV file')
    table_group.add_argument('--csv-dir', type=str,
                        help='Directory to save CSV files (default: output/tables)')
    
    # Visualization Options
    viz_group = parser.add_argument_group('Visualization Options')
    viz_group.add_argument('--visualize', '-viz', action='store_true',
                        help='Generate all visualizations of position data and trade history')
    viz_group.add_argument('--show-plots', action='store_true',
                        help='Display visualization plots interactively')
    viz_group.add_argument('--positions-chart', action='store_true',
                        help='Generate a bubble chart visualization of current positions')
    viz_group.add_argument('--trade-history', action='store_true',
                        help='Visualize your complete trade history')
    viz_group.add_argument('--market-trades', type=str, metavar='MARKET_ID',
                        help='Visualize trades for a specific market')
    
    return parser.parse_args()

def main():
    """Main function to run the CLI."""
    args = parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    
    # Configure pandas to display full data
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)  # Add this to show full market IDs
    pd.set_option('display.expand_frame_repr', False)
    
    try:
        print("Connecting to Polymarket...")
        
        # Initialize the position tracker
        tracker = PolymarketPositionTracker(
            output_dir=args.output,
            log_level=log_level,
            key=args.key
        )
        
        # Get position data
        if args.market:
            print(f"Analyzing positions for market: {args.market}")
            trades = tracker.get_trades_by_market(args.market)
            if not trades:
                print("No trades found for this market ID.")
                return 0
                
            df = tracker.trades_to_dataframe(trades)
            positions = tracker.calculate_positions(df)
            result = {
                'wallet_address': tracker.wallet_address,
                'market_id': args.market,
                'total_trades': len(trades),
                'positions': positions,
                'last_updated': datetime.now().isoformat()
            }
        else:
            print("Analyzing all positions...")
            result = tracker.get_detailed_positions()
            if not result or (isinstance(result, dict) and result.get('error')):
                print("No positions found.")
                return 0
        
        # Print summary
        print("\nPosition Summary:\n")
        tracker.print_positions_summary(result)
        
        # Display positions as table if requested
        if args.positions_table:
            tracker.display_positions_table(result)
            
        # Display trades table if requested
        if args.trades_table:
            # For market-specific analysis, use only those trades
            if args.market:
                trades = tracker.get_trades_by_market(args.market)
                tracker.display_trades_by_market(trades)
            else:
                # Otherwise get all trades
                tracker.display_trades_by_market()
        
        # Export positions to CSV if requested
        if args.export_positions_csv:
            print("\nExporting positions to CSV...")
            csv_filepath = None
            
            if args.csv_dir:
                # Create custom directory if specified
                os.makedirs(args.csv_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_filepath = os.path.join(args.csv_dir, f"positions_table_{timestamp}.csv")
                
            positions_csv = tracker.export_positions_table(result, filepath=csv_filepath)
            if positions_csv:
                print(f"Positions exported to: {positions_csv}")
            else:
                print("Failed to export positions to CSV.")
                
        # Export trades to CSV if requested
        if args.export_trades_csv:
            print("\nExporting trades to CSV...")
            csv_filepath = None
            
            if args.csv_dir:
                # Create custom directory if specified
                os.makedirs(args.csv_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_filepath = os.path.join(args.csv_dir, f"trades_by_market_{timestamp}.csv")
            
            # For market-specific analysis, use only those trades
            if args.market:
                trades = tracker.get_trades_by_market(args.market)
                trades_csv = tracker.export_trades_by_market(trades, filepath=csv_filepath)
            else:
                # Otherwise export all trades
                trades_csv = tracker.export_trades_by_market(filepath=csv_filepath)
                
            if trades_csv:
                print(f"Trades exported to: {trades_csv}")
            else:
                print("Failed to export trades to CSV.")
        
        # Save to file if requested
        if args.save or args.filename:
            print("\nSaving position data...")
            filename = args.filename
            filepath = tracker.save_positions_to_file(result, filename)
            if filepath:
                print(f"Results saved to: {filepath}")
            else:
                print("Failed to save results to file.")
        
        # Generate visualizations based on options
        viz_files = {}
        
        # Option: Visualize trades for a specific market
        if args.market_trades:
            print(f"\nGenerating trade visualization for market: {args.market_trades[:8]}...")
            market_viz_files = tracker.visualize_market_trades(
                market_id=args.market_trades,
                save=True,
                show=args.show_plots
            )
            viz_files.update(market_viz_files)
        
        # Option: Visualize complete trade history
        if args.trade_history:
            print("\nGenerating complete trade history visualization...")
            trades_list = tracker.get_my_trades()
            trades_df = tracker.trades_to_dataframe(trades_list)
            if not trades_df.empty:
                trade_history_files = tracker.visualize_trade_history(
                    trades_df=trades_df,
                    save=True,
                    show=args.show_plots
                )
                viz_files.update(trade_history_files)
            else:
                print("No trades found to visualize.")
                
        # Option: Generate positions chart
        if args.positions_chart:
            print("\nGenerating positions chart...")
            position_chart_files = tracker.visualize_positions_chart(
                positions=result,
                save=True,
                show=args.show_plots
            )
            viz_files.update(position_chart_files)
        
        # Option: Generate all visualizations
        if args.visualize:
            print("\nGenerating all position and trade visualizations...")
            all_viz_files = tracker.visualize_positions(
                positions=result,
                save=True,
                show=args.show_plots
            )
            viz_files.update(all_viz_files)
            
        # Print visualization results
        if viz_files:
            print(f"\nCreated {len(viz_files)} visualizations:")
            for viz_name, viz_path in viz_files.items():
                print(f"  - {viz_name}: {viz_path}")
        elif args.visualize or args.trade_history or args.positions_chart or args.market_trades:
            print("\nNo visualizations were generated.")
                
        print("\nDone!")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 1
    except ValueError as e:
        print(f"\nConfiguration error: {e}")
        if "WALLET_PRIVATE_KEY" in str(e):
            print("\nMake sure you have set the WALLET_PRIVATE_KEY in your .env file or provided it with --key")
        return 1
    except ConnectionError as e:
        print(f"\nConnection error: {e}")
        print("\nMake sure you have a working internet connection and Polymarket API is accessible.")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 