#!/usr/bin/env python
"""
Standalone runner script for Polymarket trade analysis.
This script can be executed directly from the command line.
"""

import os
import sys
import json
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Add the parent directory to the path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Import the analyzer and visualizer
from src.polymarket.trade_analysis import PolymarketTradeAnalyzer, PolymarketTradeVisualizer


def format_trade_for_display(trade):
    """Format a trade dictionary into a readable string."""
    # Convert timestamp to readable date
    trade_time = datetime.fromtimestamp(int(trade.get('match_time', 0)))
    formatted_time = trade_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Format the trade details
    market_name = trade.get('market', '')[:8] + '...' if trade.get('market') else 'Unknown'
    side = trade.get('side', 'Unknown')
    outcome = trade.get('outcome', 'Unknown')
    price = float(trade.get('price', 0))
    size = float(trade.get('size', 0))
    total = price * size
    
    return (
        f"Time: {formatted_time} | "
        f"Market: {market_name} | "
        f"Side: {side} | "
        f"Outcome: {outcome} | "
        f"Price: ${price:.2f} | "
        f"Size: {size:.2f} | "
        f"Total: ${total:.2f}"
    )


def calculate_balance(trades_df):
    """Calculate the balance based on trades."""
    if trades_df.empty:
        return 0.0
    
    # Convert price and size to float
    trades_df['price'] = trades_df['price'].astype(float)
    trades_df['size'] = trades_df['size'].astype(float)
    
    # Calculate total value of each trade
    trades_df['total'] = trades_df['price'] * trades_df['size']
    
    # BUY trades decrease balance, SELL trades increase balance
    trades_df['balance_change'] = trades_df.apply(
        lambda row: -row['total'] if row['side'] == 'BUY' else row['total'], 
        axis=1
    )
    
    # Return the sum of all balance changes
    return trades_df['balance_change'].sum()


def plot_balance_history(trades_df, output_dir):
    """Plot the balance history over time."""
    if trades_df.empty or 'match_time' not in trades_df.columns:
        return
    
    # Ensure match_time is datetime
    if not pd.api.types.is_datetime64_dtype(trades_df['match_time']):
        trades_df['match_time'] = pd.to_datetime(trades_df['match_time'])
    
    # Convert price and size to float
    trades_df['price'] = trades_df['price'].astype(float)
    trades_df['size'] = trades_df['size'].astype(float)
    
    # Calculate total value of each trade
    trades_df['total'] = trades_df['price'] * trades_df['size']
    
    # BUY trades decrease balance, SELL trades increase balance
    trades_df['balance_change'] = trades_df.apply(
        lambda row: -row['total'] if row['side'] == 'BUY' else row['total'], 
        axis=1
    )
    
    # Sort by time
    trades_df = trades_df.sort_values('match_time')
    
    # Calculate cumulative balance
    trades_df['cumulative_balance'] = trades_df['balance_change'].cumsum()
    
    # Create figure
    plt.figure(figsize=(12, 6))
    
    # Plot cumulative balance
    plt.plot(trades_df['match_time'], trades_df['cumulative_balance'], 'o-', 
             linewidth=2, markersize=8, color='#3498db')
    
    # Format the plot
    plt.title('Balance History', fontsize=16)
    plt.xlabel('Time', fontsize=14)
    plt.ylabel('Balance (USDC)', fontsize=14)
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # Format dates on x-axis
    plt.gcf().autofmt_xdate()
    
    # Add current balance annotation
    current_balance = trades_df['cumulative_balance'].iloc[-1]
    plt.annotate(f'Current Balance: ${current_balance:.2f}', 
                xy=(0.02, 0.95), xycoords='axes fraction',
                fontsize=12, bbox=dict(boxstyle='round', facecolor='#2c3e50', alpha=0.7))
    
    # Save the plot
    output_path = os.path.join(output_dir, 'balance_history.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Balance history plot saved to {output_path}")
    
    return output_path


def plot_trade_distribution(trades_df, output_dir):
    """Create pie charts showing distribution of trades by outcome and side."""
    if trades_df.empty:
        return
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 1. Distribution by outcome
    if 'outcome' in trades_df.columns:
        outcome_counts = trades_df['outcome'].value_counts()
        ax1.pie(outcome_counts, labels=outcome_counts.index, autopct='%1.1f%%', 
                startangle=90, colors=['#2ecc71', '#e74c3c', '#3498db'])
        ax1.set_title('Trades by Outcome', fontsize=16)
    else:
        ax1.text(0.5, 0.5, 'No outcome data available', ha='center', va='center', fontsize=12)
        ax1.axis('off')
    
    # 2. Distribution by side (BUY/SELL)
    if 'side' in trades_df.columns:
        side_counts = trades_df['side'].value_counts()
        ax2.pie(side_counts, labels=side_counts.index, autopct='%1.1f%%', 
                startangle=90, colors=['#27ae60', '#c0392b'])
        ax2.set_title('Trades by Side', fontsize=16)
    else:
        ax2.text(0.5, 0.5, 'No side data available', ha='center', va='center', fontsize=12)
        ax2.axis('off')
    
    # Add overall title
    plt.suptitle('Trade Distribution', fontsize=18, y=1.05)
    plt.tight_layout()
    
    # Save the plot
    output_path = os.path.join(output_dir, 'trade_distribution.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Trade distribution plot saved to {output_path}")
    return output_path


def create_trade_summary_table(trades_df, output_dir):
    """Create a visual table summarizing trades."""
    if trades_df.empty:
        return
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, len(trades_df) * 0.5 + 2))
    
    # Hide axes
    ax.axis('off')
    
    # Prepare data for table
    # Convert timestamps to readable format
    if 'match_time' in trades_df.columns:
        trades_df['formatted_time'] = trades_df['match_time'].dt.strftime('%Y-%m-%d %H:%M')
    
    # Calculate total values
    trades_df['price'] = trades_df['price'].astype(float)
    trades_df['size'] = trades_df['size'].astype(float)
    trades_df['total_value'] = trades_df['price'] * trades_df['size']
    
    # Limit market ID to first 8 characters
    if 'market' in trades_df.columns:
        trades_df['market_short'] = trades_df['market'].str[:8] + '...'
    
    # Select columns for display
    display_cols = ['formatted_time', 'market_short', 'outcome', 'side', 'price', 'size', 'total_value']
    display_names = ['Time', 'Market', 'Outcome', 'Side', 'Price ($)', 'Size', 'Total ($)']
    
    # Filter columns that exist
    col_indices = [i for i, col in enumerate(display_cols) if col in trades_df.columns]
    display_cols = [display_cols[i] for i in col_indices]
    display_names = [display_names[i] for i in col_indices]
    
    # Get data for table
    table_data = trades_df[display_cols].values.tolist()
    
    # Create table
    table = ax.table(
        cellText=table_data,
        colLabels=display_names,
        loc='center',
        cellLoc='center',
        colColours=['#3498db'] * len(display_names),
        colWidths=[0.15, 0.15, 0.1, 0.1, 0.1, 0.1, 0.1][:len(display_names)]
    )
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    
    # Style header
    for i in range(len(display_names)):
        cell = table._cells[(0, i)]
        cell.set_text_props(weight='bold', color='white')
    
    # Format cells with colors based on side (if side column exists)
    if 'side' in display_cols:
        side_idx = display_cols.index('side')
        for i, row in enumerate(table_data, 1):
            side = row[side_idx]
            cell_color = '#d5f5e3' if side == 'BUY' else '#f5d5d5'  # Light green for BUY, light red for SELL
            for j in range(len(display_cols)):
                cell = table._cells[(i, j)]
                cell.set_facecolor(cell_color)
    
    # Add title
    plt.title('Trade Summary', fontsize=16, pad=20)
    
    # Save the table
    output_path = os.path.join(output_dir, 'trade_summary_table.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Trade summary table saved to {output_path}")
    return output_path


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
        
        # Display all trades
        print("\n=== Your Trades ===")
        for i, trade in enumerate(trades, 1):
            print(f"{i}. {format_trade_for_display(trade)}")
        
        # Convert to pandas DataFrame for analysis
        trades_df = analyzer.get_trades_to_dataframe(trades)
        
        # Calculate and display balance
        balance = calculate_balance(trades_df)
        print(f"\n=== Your Balance ===")
        print(f"Current Balance: ${balance:.2f}")
        
        # Generate balance history plot
        print("\nGenerating balance history plot...")
        balance_plot_path = plot_balance_history(trades_df, output_dir)
        
        # Generate trade distribution pie charts
        print("Generating trade distribution charts...")
        distribution_plot_path = plot_trade_distribution(trades_df, output_dir)
        
        # Generate trade summary table
        print("Generating trade summary table...")
        summary_table_path = create_trade_summary_table(trades_df, output_dir)
        
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