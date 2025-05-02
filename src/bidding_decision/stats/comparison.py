"""
Comparison tool for Polymarket predictions and order book data.
"""

import os
import json
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import logging
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_prediction_data(prophet: bool = True) -> Dict[str, Any]:
    """
    Get prediction data from the polymarket_predictor module.
    
    Args:
        prophet: Whether to use the Prophet algorithm
        
    Returns:
        Dict containing prediction data
    """
    try:
        # Build the command to run
        cmd = ["python", "-m", "src.polymarket_predictor", "--json"]
        if prophet:
            cmd.append("--prophet")
        
        # Try with --brief flag first
        try:
            # Add brief flag and run the command
            brief_cmd = cmd + ["--brief"]
            result = subprocess.run(brief_cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            # If --brief fails, try without it
            logger.warning("Brief flag not recognized, trying without --brief")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Find the JSON data in the output (it might have other text before/after)
        json_start = result.stdout.find('{')
        json_end = result.stdout.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = result.stdout[json_start:json_end]
            # Parse the JSON output
            prediction_data = json.loads(json_str)
            return prediction_data
        else:
            logger.error("Could not find valid JSON in output")
            return {}
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running prediction command: {e}")
        logger.error(f"Command output: {e.stderr}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing prediction JSON: {e}")
        logger.error(f"Output: {result.stdout}")
        return {}

def get_market_data(refresh: bool = True) -> Dict[str, Any]:
    """
    Get order book data from the Polymarket order book module.
    
    Args:
        refresh: Whether to fetch fresh data
        
    Returns:
        Dict containing market data
    """
    try:
        # Build the command to run
        cmd = ["python", "-m", "src.polymarket.order_book.show_market_status", "--json"]
        if refresh:
            cmd.append("--refresh")
        
        # Run the command and capture the output
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the JSON output
        market_data = json.loads(result.stdout)
        return market_data
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running market command: {e}")
        logger.error(f"Command output: {e.stderr}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing market JSON: {e}")
        return {}

def normalize_range_name(range_name: str) -> str:
    """
    Normalize range names to ensure consistent formatting between data sources.
    
    Args:
        range_name: Original range name
    
    Returns:
        Normalized range name
    """
    # Convert to lowercase for case-insensitive comparison
    name = range_name.lower()
    
    # Handle "less than X" format
    if "less than" in name:
        return "less than 100"  # Common format for both sources
    
    # Handle "X or more" format
    if "or more" in name:
        return "400 or more"  # Common format for both sources
    
    # Strip any "Will Elon tweet" prefix and dates
    if "will elon tweet" in name:
        name = name.replace("will elon tweet", "").strip()
    
    # Remove any date ranges (e.g., "April 25–May 2")
    if "april" in name or "may" in name:
        # Find the position of "April" or any month
        month_pos = min([p for p in [name.find(m) for m in ["april", "may", "june", "july"]] if p >= 0], default=-1)
        if month_pos >= 0:
            name = name[:month_pos].strip()
    
    # Remove " times" suffix if present
    name = name.replace(" times", "").strip()
    
    # Extract just the numeric range part
    if "–" in name or "-" in name:
        # Split by any dash character
        separator = "–" if "–" in name else "-"
        parts = name.split(separator)
        
        if len(parts) == 2:
            start, end = parts
            # Try to convert to numbers to ensure it's a valid range
            try:
                start_num = int(start.strip())
                end_num = int(end.strip())
                # Return in standard format with en dash
                return f"{start_num}–{end_num}"
            except ValueError:
                pass
    
    # If all else fails, return the original name
    return range_name

def generate_comparison_table(
    prediction_data: Optional[Dict[str, Any]] = None, 
    market_data: Optional[Dict[str, Any]] = None,
    refresh: bool = True,
    use_prophet: bool = True,
    output_path: Optional[str] = None,
    threshold: float = 0.0
) -> pd.DataFrame:
    """
    Generate a comparison table between prediction and market data.
    
    Args:
        prediction_data: Prediction data (fetched if None)
        market_data: Market data (fetched if None)
        refresh: Whether to refresh market data
        use_prophet: Whether to use Prophet for predictions
        output_path: Path to save the comparison table CSV
        threshold: Minimum opportunity percentage to include in results
        
    Returns:
        DataFrame with comparison data
    """
    # Fetch data if not provided
    if prediction_data is None:
        prediction_data = get_prediction_data(prophet=use_prophet)
    
    if market_data is None:
        market_data = get_market_data(refresh=refresh)
    
    # Check if we have valid data
    if not prediction_data or not market_data:
        logger.error("Failed to get valid data for comparison")
        return pd.DataFrame()
    
    # Get frame probabilities from prediction
    pred_probs = prediction_data.get('frame_probabilities', {})
    
    # Get market probabilities, asks, and bids from order book
    market_probs = {}
    market_asks = {}
    market_bids = {}
    for range_name, details in market_data.get('markets', {}).items():
        # Normalize the range name to match between data sources
        norm_name = normalize_range_name(range_name)
        market_probs[norm_name] = details.get('probability', 0)
        market_asks[norm_name] = details.get('ask', 0)
        market_bids[norm_name] = details.get('bid', 0)
    
    # Normalize prediction range names as well
    normalized_pred_probs = {}
    for range_name, prob in pred_probs.items():
        norm_name = normalize_range_name(range_name)
        normalized_pred_probs[norm_name] = prob
    
    # Create comparison table
    comparison_data = []
    
    # Get all unique range names from both sources
    all_ranges = set(list(normalized_pred_probs.keys()) + list(market_probs.keys()))
    
    for range_name in sorted(all_ranges):
        pred_prob = normalized_pred_probs.get(range_name, 0)
        market_prob = market_probs.get(range_name, 0)
        market_ask = market_asks.get(range_name, 0)
        market_bid = market_bids.get(range_name, 0)
        
        # Calculate spread (gap between ask and bid)
        spread = market_ask - market_bid if market_ask > 0 and market_bid > 0 else 0
        
        # Calculate differences using ask price instead of market price
        diff = pred_prob - market_ask
        opportunity = abs(diff)
        
        # Calculate spread-adjusted opportunity
        spread_adj_opportunity = max(0, opportunity - spread)
        
        # Calculate fully adjusted opportunity (spread + threshold)
        fully_adj_opportunity = max(0, opportunity - spread - threshold)
        
        # Skip rows that don't meet the threshold
        if opportunity < threshold and range_name != 'EXPECTED VALUE':
            continue
        
        comparison_data.append({
            'Range': range_name,
            'Prediction (%)': pred_prob,
            'Market (%)': market_prob,
            'Bid (%)': market_bid,
            'Ask (%)': market_ask,
            'Spread (%)': spread,
            'Difference (%)': diff,
            'Opportunity (%)': opportunity,
            'Spread-Adj. Opp. (%)': spread_adj_opportunity,
            f'Full-Adj. Opp. ({threshold}%)': fully_adj_opportunity
        })
    
    # Create DataFrame
    df = pd.DataFrame(comparison_data)
    
    # Calculate expected values
    pred_ev = prediction_data.get('summary', {}).get('expected_value', 0)
    market_ev = market_data.get('summary', {}).get('expected_value', 0)
    ev_diff = pred_ev - market_ev
    
    # Add summary row
    summary_row = pd.DataFrame([{
        'Range': 'EXPECTED VALUE',
        'Prediction (%)': pred_ev,
        'Market (%)': market_ev,
        'Bid (%)': None,  # No Bid for expected value
        'Ask (%)': None,  # No Ask for expected value
        'Spread (%)': None,  # No Spread for expected value
        'Difference (%)': ev_diff,
        'Opportunity (%)': abs(ev_diff),
        'Spread-Adj. Opp. (%)': abs(ev_diff),  # No spread for expected value
        f'Full-Adj. Opp. ({threshold}%)': max(0, abs(ev_diff) - threshold)
    }])
    
    df = pd.concat([df, summary_row], ignore_index=True)
    
    # Save to file if requested
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Comparison table saved to {output_path}")
    
    return df

def visualize_comparison(
    comparison_df: Optional[pd.DataFrame] = None,
    prediction_data: Optional[Dict[str, Any]] = None, 
    market_data: Optional[Dict[str, Any]] = None,
    refresh: bool = True,
    use_prophet: bool = True,
    threshold: float = 0.0,
    output_path: Optional[str] = None
) -> None:
    """
    Visualize the comparison between prediction and market data.
    
    Args:
        comparison_df: Comparison DataFrame (generated if None)
        prediction_data: Prediction data (fetched if comparison_df is None)
        market_data: Market data (fetched if comparison_df is None)
        refresh: Whether to refresh market data
        use_prophet: Whether to use Prophet for predictions
        threshold: Minimum opportunity percentage to include in results
        output_path: Path to save visualization
    """
    # Generate comparison table if not provided
    if comparison_df is None:
        comparison_df = generate_comparison_table(
            prediction_data, market_data, 
            refresh=refresh, 
            use_prophet=use_prophet,
            threshold=threshold
        )
    
    if comparison_df.empty:
        logger.error("No data to visualize")
        return
    
    # Filter out the expected value row for plotting
    plot_df = comparison_df[comparison_df['Range'] != 'EXPECTED VALUE'].copy()
    
    if plot_df.empty:
        logger.error("No data points to visualize after filtering")
        return
    
    # Create figure with subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 18))
    
    # Plot the comparison
    ranges = plot_df['Range']
    x = np.arange(len(ranges))
    width = 0.2  # Narrower bars to fit all series
    
    # First subplot: Prediction vs Market vs Bid vs Ask
    bars1 = ax1.bar(x - 1.5*width, plot_df['Prediction (%)'], width, label='Prediction')
    bars2 = ax1.bar(x - 0.5*width, plot_df['Market (%)'], width, label='Market')
    bars3 = ax1.bar(x + 0.5*width, plot_df['Bid (%)'], width, label='Bid Price')
    bars4 = ax1.bar(x + 1.5*width, plot_df['Ask (%)'], width, label='Ask Price')
    
    ax1.set_xlabel('Range')
    ax1.set_ylabel('Probability (%)')
    ax1.set_title('Prediction vs Market, Bid, Ask Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(ranges, rotation=45, ha='right')
    ax1.legend()
    
    # Second subplot: Spread visualization
    bars_spread = ax2.bar(x, plot_df['Spread (%)'], width, label='Bid-Ask Spread')
    
    # Color the spread bars based on size
    for i, bar in enumerate(bars_spread):
        intensity = min(1.0, plot_df['Spread (%)'].iloc[i] / plot_df['Spread (%)'].max() if plot_df['Spread (%)'].max() > 0 else 0)
        bar.set_color(plt.cm.Oranges(0.5 + intensity/2))
    
    ax2.set_xlabel('Range')
    ax2.set_ylabel('Spread (%)')
    ax2.set_title('Bid-Ask Spread by Range')
    ax2.set_xticks(x)
    ax2.set_xticklabels(ranges, rotation=45, ha='right')
    ax2.legend()
    
    # Third subplot: Opportunities and Adjusted Opportunities
    full_adj_opp_col = f'Full-Adj. Opp. ({threshold}%)'
    
    # Create grouped bar chart for opportunities
    bars_opp = ax3.bar(x - width, plot_df['Opportunity (%)'], width, label='Raw Opportunity')
    bars_spread_adj = ax3.bar(x, plot_df['Spread-Adj. Opp. (%)'], width, label='After Spread')
    bars_full_adj = ax3.bar(x + width, plot_df[full_adj_opp_col], width, label=f'After Spread + {threshold}%')
    
    # Color the bars based on opportunity size
    for i in range(len(plot_df)):
        # Raw opportunity bars in blue
        intensity_opp = min(1.0, plot_df['Opportunity (%)'].iloc[i] / plot_df['Opportunity (%)'].max() if plot_df['Opportunity (%)'].max() > 0 else 0)
        bars_opp[i].set_color(plt.cm.Blues(0.5 + intensity_opp/2))
        
        # Spread-adjusted opportunity bars in green
        intensity_spread_adj = min(1.0, plot_df['Spread-Adj. Opp. (%)'].iloc[i] / plot_df['Spread-Adj. Opp. (%)'].max() if plot_df['Spread-Adj. Opp. (%)'].max() > 0 else 0)
        bars_spread_adj[i].set_color(plt.cm.Greens(0.5 + intensity_spread_adj/2))
        
        # Fully-adjusted opportunity bars in red
        intensity_full_adj = min(1.0, plot_df[full_adj_opp_col].iloc[i] / plot_df[full_adj_opp_col].max() if plot_df[full_adj_opp_col].max() > 0 else 0)
        bars_full_adj[i].set_color(plt.cm.Reds(0.5 + intensity_full_adj/2))
    
    ax3.set_xlabel('Range')
    ax3.set_ylabel('Opportunity (%)')
    ax3.set_title(f'Trading Opportunities (Raw, Spread-Adjusted, and Fully-Adjusted)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(ranges, rotation=45, ha='right')
    ax3.legend()
    
    # Add a 'buy' or 'sell' annotation to the top 3 fully adjusted opportunities
    adj_opps = plot_df[full_adj_opp_col]
    if adj_opps.max() > 0:  # Only if there are opportunities above threshold
        top_opps = adj_opps.nlargest(3)
        for opp in top_opps:
            if opp > 0:  # Only annotate non-zero opportunities
                idx = adj_opps[adj_opps == opp].index[0]
                row = plot_df.iloc[idx]
                diff = row['Difference (%)']
                
                position = (idx, opp + 0.5)
                action = "BUY" if diff > 0 else "SELL"
                price = row['Ask (%)'] if diff > 0 else row['Bid (%)']
                spread = row['Spread (%)']
                
                ax3.annotate(
                    f"{action} at {price:.2f}% (Spread: {spread:.2f}%, Edge: {opp:.2f}%)",
                    position, 
                    xytext=(0, 5),
                    textcoords='offset points',
                    ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5)
                )
    
    # Add expected values as text
    ev_row = comparison_df[comparison_df['Range'] == 'EXPECTED VALUE'].iloc[0]
    fig.text(
        0.5, 0.02,
        f"Expected Values: Prediction = {ev_row['Prediction (%)']:.2f}, " + 
        f"Market = {ev_row['Market (%)']:.2f}, " + 
        f"Difference = {ev_row['Difference (%)']:.2f}",
        ha='center', fontsize=12, bbox=dict(facecolor='yellow', alpha=0.2)
    )
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path)
        logger.info(f"Visualization saved to {output_path}")
    else:
        plt.show()

def enhanced_visualization(
    comparison_df: pd.DataFrame,
    threshold: float = 0.0,
    output_path: Optional[str] = None
) -> None:
    """
    Create an enhanced visualization with multiple informative charts.
    
    Args:
        comparison_df: Comparison DataFrame
        threshold: Minimum opportunity percentage to highlight
        output_path: Path to save visualization
    """
    if comparison_df.empty:
        logger.error("No data to visualize")
        return
    
    # Filter out the expected value row for plotting
    plot_df = comparison_df[comparison_df['Range'] != 'EXPECTED VALUE'].copy()
    
    if plot_df.empty:
        logger.error("No data points to visualize after filtering")
        return
    
    # Create a larger figure with multiple subplots
    fig = plt.figure(figsize=(20, 15))
    fig.suptitle(f'Market vs Prediction Analysis (Threshold: {threshold}%)', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    # Define grid layout
    gs = plt.GridSpec(3, 2, figure=fig, height_ratios=[1, 1, 1.2], wspace=0.25, hspace=0.35)
    
    # 1. Probability Comparison - Upper Left
    ax1 = fig.add_subplot(gs[0, 0])
    _plot_probability_comparison(ax1, plot_df)
    
    # 2. Bid-Ask Spread - Upper Right
    ax2 = fig.add_subplot(gs[0, 1])
    _plot_bid_ask_spread(ax2, plot_df)
    
    # 3. Trading Opportunities - Middle Left
    ax3 = fig.add_subplot(gs[1, 0])
    full_adj_opp_col = f'Full-Adj. Opp. ({threshold}%)'
    _plot_trading_opportunities(ax3, plot_df, full_adj_opp_col, threshold)
    
    # 4. Expected Value - Middle Right
    ax4 = fig.add_subplot(gs[1, 1])
    ev_row = comparison_df[comparison_df['Range'] == 'EXPECTED VALUE'].iloc[0]
    _plot_expected_value(ax4, ev_row, threshold)
    
    # 5. Detailed Recommendations - Bottom Full Width
    ax5 = fig.add_subplot(gs[2, :])
    _plot_detailed_recommendations(ax5, plot_df, full_adj_opp_col, threshold)
    
    # Add timestamp and information
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plt.figtext(0.01, 0.01, f"Generated: {timestamp}", fontsize=8)
    plt.figtext(0.99, 0.01, "Source: Polymarket Order Book & Prophet Predictions", 
                fontsize=8, ha='right')
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"Enhanced visualization saved to {output_path}")
    else:
        plt.show()

def _plot_probability_comparison(ax, df):
    """Plot probability comparison chart"""
    ranges = df['Range']
    x = np.arange(len(ranges))
    width = 0.25
    
    bars1 = ax.bar(x - width, df['Prediction (%)'], width, label='Prediction', color='#4285F4')
    bars2 = ax.bar(x, df['Market (%)'], width, label='Market', color='#34A853')
    
    # Add value labels on the bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 1:  # Only show labels for bars with height > 1%
                ax.text(
                    bar.get_x() + bar.get_width()/2.,
                    height + 1,
                    f'{height:.1f}%',
                    ha='center', va='bottom',
                    fontsize=8, rotation=0
                )
    
    ax.set_xlabel('Range')
    ax.set_ylabel('Probability (%)')
    ax.set_title('Prediction vs Market Probabilities')
    ax.set_xticks(x - width/2)
    ax.set_xticklabels(ranges, rotation=45, ha='right')
    ax.legend(loc='upper right')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Highlight top predicted range
    max_pred_idx = df['Prediction (%)'].argmax()
    ax.get_xticklabels()[max_pred_idx].set_color('red')
    ax.get_xticklabels()[max_pred_idx].set_fontweight('bold')

def _plot_bid_ask_spread(ax, df):
    """Plot bid-ask spread chart"""
    ranges = df['Range']
    x = np.arange(len(ranges))
    width = 0.25
    
    bars1 = ax.bar(x - width, df['Bid (%)'], width, label='Bid', color='#FBBC05')
    bars2 = ax.bar(x, df['Ask (%)'], width, label='Ask', color='#EA4335')
    
    # Calculate and plot spread as a line
    spreads = df['Ask (%)'] - df['Bid (%)']
    ax2 = ax.twinx()
    ax2.plot(x, spreads, 'k--', label='Spread', linewidth=1.5, alpha=0.6)
    ax2.set_ylabel('Spread (%)')
    
    ax.set_xlabel('Range')
    ax.set_ylabel('Price (%)')
    ax.set_title('Bid-Ask Prices and Spreads')
    ax.set_xticks(x - width/2)
    ax.set_xticklabels(ranges, rotation=45, ha='right')
    
    # Combine legends
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc='upper right')
    
    ax.grid(axis='y', linestyle='--', alpha=0.3)

def _plot_trading_opportunities(ax, df, full_adj_opp_col, threshold):
    """Plot trading opportunities chart"""
    # Sort by adjusted opportunity
    sorted_df = df.sort_values(by=full_adj_opp_col, ascending=False).copy()
    
    # Only show rows with meaningful opportunities
    display_df = sorted_df[sorted_df[full_adj_opp_col] > 0]
    if display_df.empty:
        display_df = sorted_df.head(3)  # Show at least top 3 if none above threshold
    
    ranges = display_df['Range']
    x = np.arange(len(ranges))
    width = 0.35
    
    # Create grouped bar chart for opportunities
    bars_raw = ax.bar(x - width/2, display_df['Opportunity (%)'], width, 
                      label='Raw Opportunity', color='#4285F4', alpha=0.7)
    bars_spread_adj = ax.bar(x + width/2, display_df[full_adj_opp_col], width, 
                      label=f'After Spread + {threshold}% Threshold', color='#34A853')
    
    # Add value labels
    for bars in [bars_raw, bars_spread_adj]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width()/2.,
                    height + 0.5,
                    f'{height:.1f}%',
                    ha='center', va='bottom',
                    fontsize=9
                )
    
    # Add buy/sell annotations
    for i, (_, row) in enumerate(display_df.iterrows()):
        if row[full_adj_opp_col] > 0:
            action = "BUY" if row['Difference (%)'] > 0 else "SELL"
            ax.annotate(
                f"{action}",
                (i, 0),
                xytext=(0, -20),
                textcoords='offset points',
                ha='center', va='center',
                fontsize=12, fontweight='bold',
                color='white', bbox=dict(boxstyle="round,pad=0.3", 
                                         fc='#EA4335' if action == 'SELL' else '#34A853', 
                                         ec="none")
            )
    
    ax.set_xlabel('Range')
    ax.set_ylabel('Opportunity (%)')
    ax.set_title('Top Trading Opportunities')
    ax.set_xticks(x)
    ax.set_xticklabels(ranges, rotation=0)
    ax.legend(loc='upper right')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Set y-axis to start at 0
    ax.set_ylim(bottom=0)

def _plot_expected_value(ax, ev_row, threshold):
    """Plot expected value comparison"""
    labels = ['Prediction', 'Market']
    values = [ev_row['Prediction (%)'], ev_row['Market (%)']]
    diff = ev_row['Difference (%)']
    abs_diff = abs(diff)
    adj_diff = max(0, abs_diff - threshold)
    
    # Create the bar chart
    bars = ax.bar(labels, values, color=['#4285F4', '#34A853'])
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2.,
            height + 1,
            f'{height:.2f}',
            ha='center', va='bottom',
            fontsize=10
        )
    
    # Add difference annotation
    direction = '↑' if diff > 0 else '↓'
    color = '#34A853' if diff > 0 else '#EA4335'
    
    ax.annotate(
        f"Difference: {diff:.2f} {direction}",
        xy=(0.5, max(values) * 0.6),
        xytext=(0.5, max(values) * 0.6),
        textcoords='axes fraction',
        ha='center',
        fontsize=12,
        fontweight='bold',
        color=color
    )
    
    # Add adjusted opportunity if significant
    if adj_diff > 0:
        ax.annotate(
            f"Adjusted Opportunity: {adj_diff:.2f}%",
            xy=(0.5, max(values) * 0.5),
            xytext=(0.5, max(values) * 0.5),
            textcoords='axes fraction',
            ha='center',
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc='#FBBC05', ec="none", alpha=0.3)
        )
    
    ax.set_title('Expected Value Comparison')
    ax.set_ylabel('Expected Tweet Count')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Add a recommendation if there's a significant difference
    if abs_diff > threshold:
        action = "HIGHER" if diff > 0 else "LOWER"
        ax.text(
            0.5, 0.05,
            f"Prediction is {action} than market",
            transform=ax.transAxes,
            ha='center',
            fontsize=11,
            bbox=dict(boxstyle="round,pad=0.3", fc='#FBBC05', ec="none", alpha=0.3)
        )

def _plot_detailed_recommendations(ax, df, full_adj_opp_col, threshold):
    """Plot detailed recommendations chart"""
    # Find top opportunities
    df_filtered = df[df[full_adj_opp_col] > 0].copy()
    
    if df_filtered.empty:
        ax.text(
            0.5, 0.5,
            "No significant trading opportunities found above threshold",
            ha='center', va='center',
            fontsize=14, fontweight='bold',
            transform=ax.transAxes
        )
        ax.set_title("Trading Recommendations")
        ax.axis('off')
        return
    
    # Sort by adjusted opportunity
    df_sorted = df_filtered.sort_values(by=full_adj_opp_col, ascending=False)
    
    # Take top 5 or all if less
    top_opps = df_sorted.head(5)
    
    # Create table data
    table_data = []
    for _, row in top_opps.iterrows():
        action = "BUY" if row['Difference (%)'] > 0 else "SELL"
        price = row['Ask (%)'] if action == "BUY" else row['Bid (%)']
        spread = row['Spread (%)']
        edge = row[full_adj_opp_col]
        pred = row['Prediction (%)']
        market = row['Market (%)']
        spread_adj = row['Spread-Adj. Opp. (%)']
        
        table_data.append([
            row['Range'],
            action,
            f"{price:.2f}%",
            f"{spread:.2f}%",  # Added spread column
            f"{pred:.2f}%",
            f"{market:.2f}%",
            f"{row['Difference (%)']:.2f}%",
            f"{spread_adj:.2f}%",  # Added spread-adjusted column
            f"{edge:.2f}%"
        ])
    
    # Create the table
    columns = ['Range', 'Action', 'Price', 'Spread', 'Prediction', 'Market', 'Difference', 'After Spread', f'Final Edge ({threshold}%)']
    colors = []
    
    for row in table_data:
        if row[1] == "BUY":
            colors.append(['w', 'w', '#C8E6C9', '#FFF9C4', 'w', 'w', 'w', '#E3F2FD', 'w'])  # Green for BUY
        else:
            colors.append(['w', 'w', '#FFCDD2', '#FFF9C4', 'w', 'w', 'w', '#E3F2FD', 'w'])  # Red for SELL
    
    table = ax.table(
        cellText=table_data,
        colLabels=columns,
        loc='center',
        cellLoc='center',
        colColours=['#F5F5F5'] * len(columns),
        cellColours=colors
    )
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    
    # Add a title
    ax.set_title("Detailed Trading Recommendations", fontsize=14, fontweight='bold', pad=20)
    
    # Add a summary text
    top_action = table_data[0][1]
    top_range = table_data[0][0]
    top_price = table_data[0][2]
    top_spread = table_data[0][3]
    top_edge = table_data[0][8]
    
    summary_text = (
        f"Best Opportunity: {top_action} {top_range} at {top_price}\n"
        f"with {top_edge} edge (after {top_spread} spread and {threshold}% threshold)"
    )
    
    ax.text(
        0.5, 0.9,
        summary_text,
        ha='center', va='center',
        fontsize=14, fontweight='bold',
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.5", fc='#FFF9C4', ec="none")
    )
    
    ax.axis('off')

def initialize_directories():
    """Create necessary directories for output files."""
    # Create output directory for CSV files
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create subdirectory for visualizations
    viz_dir = os.path.join(output_dir, 'viz')
    os.makedirs(viz_dir, exist_ok=True)
    
    return output_dir, viz_dir

def main():
    """Command line entry point"""
    import argparse
    
    # Set pandas display options to show all columns
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.float_format', '{:.2f}'.format)
    pd.set_option('display.precision', 2)
    
    # Initialize directories
    output_dir, viz_dir = initialize_directories()
    
    parser = argparse.ArgumentParser(description='Compare prediction and market data')
    parser.add_argument('--output', type=str, help='Path to save the comparison table CSV')
    parser.add_argument('--no-refresh', action='store_true', help='Do not refresh market data')
    parser.add_argument('--no-prophet', action='store_true', help='Do not use Prophet for predictions')
    parser.add_argument('--visualize', action='store_true', help='Generate visualization')
    parser.add_argument('--viz-output', type=str, help='Path to save visualization')
    parser.add_argument('--threshold', type=float, default=0.0, help='Minimum opportunity percentage (0-100) to include in results')
    parser.add_argument('--enhanced-viz', action='store_true', help='Generate enhanced visualization with more details')
    
    args = parser.parse_args()
    
    # Set default output paths if not specified
    if args.output is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = os.path.join(output_dir, f'comparison_{timestamp}.csv')
    
    if args.visualize and args.viz_output is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        args.viz_output = os.path.join(viz_dir, f'comparison_{timestamp}.png')
    
    try:
        # Generate comparison table
        df = generate_comparison_table(
            refresh=not args.no_refresh,
            use_prophet=not args.no_prophet,
            output_path=args.output,
            threshold=args.threshold
        )
        
        # Print the table
        if not df.empty:
            print("\nComparison Table:")
            print(df.to_string(index=False))
            
            # Find the largest adjusted opportunity
            data_rows = df[df['Range'] != 'EXPECTED VALUE']
            full_adj_opp_col = f'Full-Adj. Opp. ({args.threshold}%)'
            
            if not data_rows.empty:
                # Find the index of the max adjusted opportunity
                max_adj_idx = data_rows[full_adj_opp_col].idxmax()
                max_opp_row = data_rows.loc[max_adj_idx]
                
                # Only show if there's a meaningful opportunity
                if max_opp_row[full_adj_opp_col] > 0:
                    print("\nBest Trading Opportunity:")
                    print(f"Range: {max_opp_row['Range']}")
                    print(f"Prediction: {max_opp_row['Prediction (%)']}%")
                    print(f"Market: {max_opp_row['Market (%)']}%")
                    print(f"Bid: {max_opp_row['Bid (%)']}%")
                    print(f"Ask: {max_opp_row['Ask (%)']}%")
                    print(f"Spread: {max_opp_row['Spread (%)']}%")
                    print(f"Difference: {max_opp_row['Difference (%)']}%")
                    print(f"Opportunity: {max_opp_row['Opportunity (%)']}%")
                    print(f"Spread-Adjusted Opportunity: {max_opp_row['Spread-Adj. Opp. (%)']}%")
                    print(f"Fully-Adjusted Opportunity: {max_opp_row[full_adj_opp_col]}%")
                    
                    # Trading recommendation with specific price
                    if max_opp_row['Difference (%)'] > 0:
                        print(f"Recommendation: BUY {max_opp_row['Range']} at {max_opp_row['Ask (%)']}% (prediction: {max_opp_row['Prediction (%)']}%)")
                        print(f"Edge: {max_opp_row[full_adj_opp_col]}% after spread and {args.threshold}% threshold")
                    else:
                        print(f"Recommendation: SELL {max_opp_row['Range']} at {max_opp_row['Bid (%)']}% (prediction: {max_opp_row['Prediction (%)']}%)")
                        print(f"Edge: {max_opp_row[full_adj_opp_col]}% after spread and {args.threshold}% threshold")
                else:
                    print("\nNo significant trading opportunities found above the threshold.")
                    print(f"Try lowering the threshold (currently set to {args.threshold}%)")
            else:
                print("No data available for comparison. Please check the logs for errors.")
        else:
            print("No data available for comparison. Please check the logs for errors.")
        
        # Generate visualization if requested
        if args.visualize and not df.empty:
            if args.enhanced_viz:
                enhanced_visualization(
                    comparison_df=df,
                    output_path=args.viz_output,
                    threshold=args.threshold
                )
            else:
                visualize_comparison(
                    comparison_df=df,
                    output_path=args.viz_output,
                    threshold=args.threshold
                )
            print(f"\nVisualization saved to: {args.viz_output}")
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        print(f"Error: {str(e)}")
        print("Please check the logs for more details.")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 