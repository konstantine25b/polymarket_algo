#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Import custom modules
from src.polymarket.trade_analysis.trade_analyzer import PolymarketTradeAnalyzer
from src.polymarket.trade_analysis.visualizer import PolymarketTradeVisualizer

def load_trades_from_file(filepath):
    """
    Load trade data from a JSON file.
    
    Args:
        filepath (str): Path to the JSON file containing trade data.
        
    Returns:
        list: List of trade dictionaries.
    """
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found")
        return []
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Handle different formats (direct list or nested in a key)
        if isinstance(data, list):
            trades = data
        elif isinstance(data, dict) and 'trades' in data:
            trades = data['trades']
        elif isinstance(data, dict) and 'data' in data:
            trades = data['data']
        else:
            # Try to find a list in the data
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    trades = value
                    print(f"Found trades under key: {key}")
                    break
            else:
                print("Error: Could not find trade data in the file")
                return []
        
        print(f"Loaded {len(trades)} trades from {filepath}")
        return trades
    
    except Exception as e:
        print(f"Error loading trades from file: {e}")
        return []

def create_output_dir(output_base, market_name=None):
    """
    Create an output directory for analysis results and visualizations.
    
    Args:
        output_base (str): Base directory for outputs.
        market_name (str, optional): Name of the market for directory naming.
        
    Returns:
        str: Path to the created output directory.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create directory name
    if market_name:
        # Clean market name for directory name
        market_name_clean = ''.join(c for c in market_name if c.isalnum() or c in '_ -').replace(' ', '_')
        dir_name = f"{market_name_clean}_{timestamp}"
    else:
        dir_name = f"analysis_{timestamp}"
    
    # Create full path
    output_dir = os.path.join(output_base, dir_name)
    
    # Create directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    return output_dir

def run_analysis(trades, market_name=None, output_dir='output'):
    """
    Run full analysis on trade data.
    
    Args:
        trades (list): List of trade dictionaries.
        market_name (str, optional): Name of the market for reporting.
        output_dir (str): Directory to save output files.
        
    Returns:
        dict: Analysis results.
    """
    # Create the analyzer
    analyzer = PolymarketTradeAnalyzer(output_dir=output_dir)
    
    # Run the analysis
    print(f"Running analysis on {len(trades)} trades...")
    results = analyzer.analyze_all(trades, market_name=market_name, create_visualizations=True)
    
    # Print summary
    print("\n===== ANALYSIS SUMMARY =====")
    if 'price' in results and 'summary' in results['price']:
        print("\n" + results['price']['summary'])
    
    if 'volume' in results and 'summary' in results['volume']:
        print("\n" + results['volume']['summary'])
    
    if 'patterns' in results and 'summary' in results['patterns']:
        print("\n" + results['patterns']['summary'])
    
    # Print visualization files
    if 'visualizations' in results and 'files' in results['visualizations']:
        print("\n===== VISUALIZATION FILES =====")
        for viz_type, filepath in results['visualizations']['files'].items():
            print(f"- {viz_type}: {filepath}")
    
    return results

def visualize_only(trades, market_name=None, output_dir='output'):
    """
    Only create visualizations without detailed analysis.
    
    Args:
        trades (list): List of trade dictionaries.
        market_name (str, optional): Name of the market for visualizations.
        output_dir (str): Directory to save output files.
    """
    # Convert trades to DataFrame
    df = pd.DataFrame(trades)
    
    # Convert datatypes
    if 'match_time' in df.columns:
        df['match_time'] = pd.to_datetime(df['match_time'])
    
    numeric_cols = ['price', 'size']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Create visualizer
    visualizer = PolymarketTradeVisualizer(
        theme='dark_background',
        output_dir=output_dir,
        dpi=300
    )
    
    # Generate visualizations
    print("Creating visualizations...")
    
    visualizer.plot_price_history(df=df, market_name=market_name)
    print("- Created price history chart")
    
    visualizer.plot_price_distribution(df=df)
    print("- Created price distribution chart")
    
    if 'outcome' in df.columns and 'size' in df.columns:
        visualizer.plot_volume_distribution(df=df, by='outcome')
        print("- Created volume by outcome chart")
    
    if 'side' in df.columns and 'size' in df.columns:
        visualizer.plot_volume_distribution(df=df, by='side')
        print("- Created volume by side chart")
    
    visualizer.plot_trade_heatmap(df=df)
    print("- Created trading activity heatmap")
    
    visualizer.create_dashboard(df=df, market_name=market_name)
    print("- Created comprehensive dashboard")
    
    print(f"\nAll visualizations saved to {output_dir}/ directory")

def main():
    """Main function to parse arguments and run the script."""
    parser = argparse.ArgumentParser(description='Analyze Polymarket trade data and generate visualizations.')
    
    parser.add_argument('--input', '-i', 
                        required=True,
                        help='Input JSON file containing trade data')
    
    parser.add_argument('--market', '-m',
                        help='Name of the market (for visualization titles)')
    
    parser.add_argument('--output', '-o',
                        default='output',
                        help='Base directory for output files (default: output)')
    
    parser.add_argument('--viz-only',
                        action='store_true',
                        help='Only generate visualizations without detailed analysis')
    
    args = parser.parse_args()
    
    # Load trade data
    trades = load_trades_from_file(args.input)
    if not trades:
        return
    
    # Create output directory
    output_dir = create_output_dir(args.output, args.market)
    
    # Run analysis or visualization
    if args.viz_only:
        visualize_only(trades, args.market, output_dir)
    else:
        run_analysis(trades, args.market, output_dir)
        
    print(f"\nAll outputs saved to: {output_dir}")
    print("Done!")

if __name__ == "__main__":
    # Ensure proper environment
    load_dotenv()
    
    # Run main function
    main() 