#!/usr/bin/env python
"""
Example script demonstrating basic usage of the Polymarket trade analysis tools.
This shows how to retrieve, analyze, and visualize your Polymarket trade data.
"""

import os
import json
import sys
from dotenv import load_dotenv

# Fix imports based on how the script is run
try:
    # When run as a module
    from .trade_analyzer import PolymarketTradeAnalyzer
    from .visualizer import PolymarketTradeVisualizer
except ImportError:
    # When run directly
    sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from src.polymarket.trade_analysis.trade_analyzer import PolymarketTradeAnalyzer
    from src.polymarket.trade_analysis.visualizer import PolymarketTradeVisualizer


def main():
    """Main function to run the example."""
    print("=== Polymarket Trade Analysis Example ===")
    
    # Load environment variables (including WALLET_PRIVATE_KEY)
    load_dotenv()
    
    if not os.getenv("WALLET_PRIVATE_KEY"):
        print("ERROR: WALLET_PRIVATE_KEY environment variable not found.")
        print("Please create a .env file with your private key or set it in your environment.")
        return
    
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "plots")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Initialize the analyzer with credentials from .env
        print("Initializing trade analyzer...")
        analyzer = PolymarketTradeAnalyzer(output_dir=output_dir)
        
        # Get your trades (where you are the maker)
        print("Retrieving your maker trades...")
        trades = analyzer.get_trades_by_maker()
        
        if not trades:
            print("No maker trades found for your account.")
            return
        
        print(f"Found {len(trades)} trades.")
        
        # Convert to pandas DataFrame for analysis
        trades_df = analyzer.get_trades_to_dataframe(trades)
        
        # Get comprehensive analysis
        print("\nGenerating comprehensive analysis...")
        analysis = analyzer.get_comprehensive_analysis(trades)
        
        # Convert non-serializable objects to strings for JSON serialization
        def json_serializable(obj):
            """Helper function for JSON serialization of complex objects."""
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)
        
        # Pretty print the analysis results
        print("\n=== Analysis Results ===")
        print(json.dumps(analysis, indent=2, default=json_serializable))
        
        # Initialize the visualizer with the output directory
        visualizer = PolymarketTradeVisualizer(output_dir=output_dir)
        
        # Create visualizations
        print("\nGenerating visualizations...")
        
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
            
            # Full dashboard
            print("Creating full dashboard...")
            visualizer.create_dashboard(trades_df, save_file=True)
            
            print(f"\nVisualization files have been created in the '{output_dir}' directory.")
            print("Open the PNG files in any image viewer to see the visualizations.")
        
        except Exception as viz_error:
            print(f"ERROR during visualization: {str(viz_error)}")
            print("Analysis completed, but visualization creation failed.")
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main() 