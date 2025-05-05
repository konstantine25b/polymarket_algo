#!/usr/bin/env python
"""
Standalone runner script for Polymarket trade analysis.
This script can be executed directly from the command line.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add the parent directory to the path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Import the analyzer and visualizer
from src.polymarket.trade_analysis import PolymarketTradeAnalyzer, PolymarketTradeVisualizer


def main():
    """Main function to run the Polymarket trade analysis."""
    print("=== Polymarket Trade Analysis ===")
    
    # Load environment variables (including WALLET_PRIVATE_KEY)
    load_dotenv()
    
    if not os.getenv("WALLET_PRIVATE_KEY"):
        print("ERROR: WALLET_PRIVATE_KEY environment variable not found.")
        print("Please create a .env file with your private key or set it in your environment.")
        print("Example .env file content: WALLET_PRIVATE_KEY=0x123abc...")
        return
    
    try:
        # Determine the script location to save output files in the same directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "plots")
        
        # Initialize the analyzer with credentials from .env
        print("Initializing trade analyzer...")
        analyzer = PolymarketTradeAnalyzer(output_dir=output_dir)
        
        # Get your trades (where you are the maker)
        print("\nRetrieving your maker trades...")
        trades = analyzer.get_trades_by_maker()
        
        if not trades:
            print("No maker trades found for your account.")
            print("\nWould you like to try retrieving trades where you are the taker? (y/n)")
            choice = input().lower()
            if choice in ('y', 'yes'):
                # Try getting trades for the connected wallet (not as maker but as participant)
                print("Retrieving trades for your wallet...")
                # Use the market parameter to get all trades for any market
                # (this is a workaround as the API doesn't have a direct method for this)
                trades = analyzer.client.get_trades()
                if not trades:
                    print("No trades found for your wallet.")
                    return
            else:
                return
        
        print(f"Found {len(trades)} trades.")
        
        # Convert to pandas DataFrame for analysis
        trades_df = analyzer.get_trades_to_dataframe(trades)
        
        # Get comprehensive analysis
        print("\nGenerating comprehensive analysis...")
        analysis = analyzer.get_comprehensive_analysis(trades)
        
        # Pretty print the analysis results
        print("\n=== Analysis Results ===")
        print(json.dumps(analysis, indent=2, default=str))
        
        # Create an output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Initialize the visualizer with the output directory
        print("\nGenerating visualizations...")
        visualizer = PolymarketTradeVisualizer(output_dir=output_dir)
        
        # Create visualizations - using matplotlib by default (use_plotly=False)
        try:
            # Price history chart
            print("Creating price history chart...")
            visualizer.plot_price_history(trades_df, save_file=True)
            
            # Volume distribution
            print("Creating volume distribution chart...")
            visualizer.plot_volume_distribution(trades_df, by='outcome', save_file=True)
            
            # Price distribution
            print("Creating price distribution chart...")
            visualizer.plot_price_distribution(trades_df, save_file=True)
            
            # Trading activity heatmap
            print("Creating trading activity heatmap...")
            visualizer.plot_trade_heatmap(trades_df, save_file=True)
            
            # Full dashboard - requires plotly
            print("Creating full dashboard...")
            visualizer.create_dashboard(trades_df, save_file=True)
            
            print(f"\nVisualization files have been created in the '{output_dir}' directory.")
            print("Open the PNG files in any image viewer to see the visualizations.")
        except Exception as viz_error:
            print(f"ERROR during visualization: {str(viz_error)}")
            print("Analysis completed, but some visualizations failed to generate.")
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Make sure your WALLET_PRIVATE_KEY is valid")
        print("2. Check your internet connection")
        print("3. Ensure the Polymarket API is accessible")
        print("\nStacktrace for debugging:")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main() 