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


def display_positions(trades_data, analyzer):
    """
    Display position information using the new identify_positions functionality.
    
    Args:
        trades_data (list): List of trade data dictionaries.
        analyzer (PolymarketTradeAnalyzer): The trade analyzer instance.
    """
    print("\n=== Position Analysis ===")
    positions = analyzer.identify_positions(trades_data)
    
    if isinstance(positions, dict) and positions.get('error'):
        print(f"Error: {positions['error']}")
        return
    
    # Display position information
    position_count = len(positions)
    open_positions = sum(1 for p in positions.values() if p['status'] == 'open')
    closed_positions = sum(1 for p in positions.values() if p['status'] == 'closed')
    
    print(f"Found {position_count} positions ({open_positions} open, {closed_positions} closed)")
    print("\n=== Position Details ===")
    
    # Display each position
    for idx, (key, position) in enumerate(positions.items(), 1):
        status_color = "\033[92m" if position['status'] == 'closed' else "\033[93m"  # Green for closed, yellow for open
        reset_color = "\033[0m"
        
        # Format entry/exit times - Fix for timestamp objects
        if 'first_trade_time' in position:
            if isinstance(position['first_trade_time'], (int, float)):
                first_trade = datetime.fromtimestamp(position['first_trade_time'])
            else:
                # Handle pandas Timestamp objects
                first_trade = position['first_trade_time']
        else:
            first_trade = "N/A"
            
        if 'last_trade_time' in position:
            if isinstance(position['last_trade_time'], (int, float)):
                last_trade = datetime.fromtimestamp(position['last_trade_time'])
            else:
                # Handle pandas Timestamp objects
                last_trade = position['last_trade_time']
        else:
            last_trade = "N/A"
        
        # Display basic position info
        print(f"{idx}. Market: {position['market_id_short']} | Outcome: {position['outcome']} | "
              f"Status: {status_color}{position['status'].upper()}{reset_color}")
        
        print(f"   Entry: {first_trade} | Exit: {last_trade if position['status'] == 'closed' else 'OPEN'}")
        print(f"   Buy Volume: {position['buy_volume']:.2f} @ Avg Price: ${position['avg_buy_price']:.4f}")
        print(f"   Sell Volume: {position['sell_volume']:.2f} @ Avg Price: ${position['avg_sell_price']:.4f}")
        print(f"   Net Position: {position['net_position']:.2f}")
        
        # Show PnL for closed positions
        if position['status'] == 'closed' and 'realized_pnl' in position:
            pnl_color = "\033[92m" if position['realized_pnl'] >= 0 else "\033[91m"  # Green for profit, red for loss
            print(f"   Realized PnL: {pnl_color}${position['realized_pnl']:.4f}{reset_color}")
        
        print("")  # Empty line between positions
    
    return positions


def analyze_positions_only():
    """
    Standalone function to run only position analysis without other trade data.
    This provides a focused view of just position PnL information.
    """
    print("=== Polymarket Position Analysis ===")
    
    try:
        # Initialize the analyzer
        print("Initializing trade analyzer...")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plots')
        os.makedirs(output_dir, exist_ok=True)
        
        analyzer = PolymarketTradeAnalyzer(output_dir=output_dir)
        
        # Get trades for the current wallet
        print("\nRetrieving your trades...")
        trades = analyzer.get_trades_by_maker()
        
        if not trades:
            print("No trades found for your wallet address.")
            return
        
        print(f"Found {len(trades)} trades. Analyzing positions...")
        
        # Perform position analysis
        positions = display_positions(trades, analyzer)
        
        # Show total PnL summary
        closed_positions = [p for p in positions.values() if p['status'] == 'closed' and 'realized_pnl' in p]
        if closed_positions:
            total_realized_pnl = sum(p['realized_pnl'] for p in closed_positions)
            pnl_color = "\033[92m" if total_realized_pnl >= 0 else "\033[91m"
            reset_color = "\033[0m"
            print(f"\n=== PnL Summary ===")
            print(f"Total Realized PnL: {pnl_color}${total_realized_pnl:.4f}{reset_color}")
            print(f"Closed Positions: {len(closed_positions)}")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main function to run the Polymarket trade analysis."""
    print("=== Polymarket Trade Analysis ===")
    
    try:
        # Initialize the analyzer
        print("Initializing trade analyzer...")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plots')
        os.makedirs(output_dir, exist_ok=True)
        
        analyzer = PolymarketTradeAnalyzer(output_dir=output_dir)
        
        # Get trades for the current wallet
        print("\nRetrieving your maker trades...")
        trades = analyzer.get_trades_by_maker()
        
        if not trades:
            print("No trades found for your wallet address.")
            return
        
        print(f"Found {len(trades)} trades.")
        
        # Convert to DataFrame for analysis
        trades_df = analyzer.get_trades_to_dataframe(trades)
        
        # Display trades
        print("\n=== Your Trades ===")
        for i, trade in enumerate(trades, 1):
            print(f"{i}. {format_trade_for_display(trade)}")
        
        # Calculate and display balance
        balance = calculate_balance(trades_df)
        print(f"\n=== Your Balance ===")
        print(f"Current Balance: ${balance:.2f}")
        
        # Generate balance history plot
        print("\nGenerating balance history plot...")
        plot_balance_history(trades_df, output_dir)
        
        # Generate trade distribution charts
        print("Generating trade distribution charts...")
        plot_trade_distribution(trades_df, output_dir)
        
        # Generate trade summary table
        print("Generating trade summary table...")
        create_trade_summary_table(trades_df, output_dir)
        
        # Generate comprehensive analysis
        print("\nGenerating comprehensive analysis...")
        analysis = analyzer.get_comprehensive_analysis(trades)
        print("\n=== Analysis Results ===")
        print(json.dumps(analysis, indent=2))
        
        # Generate visualizations
        print("\nGenerating visualizations...")
        try:
            visualizer = PolymarketTradeVisualizer(output_dir=output_dir)
            
            # Create price history chart
            print("Creating price history chart...")
            visualizer.plot_price_history(trades_df)
            
            # Create volume distribution chart
            print("Creating volume distribution chart...")
            visualizer.plot_volume_by_outcome(trades_df)
            
            # Create price distribution chart
            print("Creating price distribution chart...")
            visualizer.plot_price_distribution(trades_df)
            
            # Create trading activity heatmap
            print("Creating trading activity heatmap...")
            visualizer.plot_trading_heatmap(trades_df)
            
            # Create full dashboard
            print("Creating full dashboard...")
            visualizer.create_dashboard(trades_df)
            
            print(f"\nVisualization files have been created in the '{output_dir}' directory.")
            print("Open the PNG files in any image viewer to see the visualizations.")
        
        except Exception as viz_error:
            print(f"ERROR during visualization: {str(viz_error)}")
            print("Analysis completed, but some visualizations failed to generate.")
        
        # Display position analysis
        print("\nPerforming position analysis...")
        display_positions(trades, analyzer)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check if we're running the positions-only command
    if len(sys.argv) > 1 and sys.argv[1] == "positions":
        analyze_positions_only()
    else:
        main() 