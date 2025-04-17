# src/polymarket/visualization.py

import os
import re
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path

class Visualization:
    """Class for visualizing Polymarket data."""
    
    def __init__(self):
        """Initialize the visualization module with default style settings."""
        # Set default style for matplotlib
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Define a color palette
        self.colors = [
            '#1f77b4',  # Blue
            '#ff7f0e',  # Orange
            '#2ca02c',  # Green
            '#d62728',  # Red
            '#9467bd',  # Purple
            '#8c564b',  # Brown
            '#e377c2',  # Pink
            '#7f7f7f',  # Gray
            '#bcbd22',  # Olive
            '#17becf'   # Teal
        ]
    
    def extract_range_value(self, question: str) -> Optional[Tuple[float, float]]:
        """
        Extract the numerical range from a question.
        For questions like "Will Elon tweet 125–149 times April 11–18?",
        returns the range (125, 149).
        
        Args:
            question: The market question.
            
        Returns:
            A tuple of (min, max) values if found, or None if no range is found.
        """
        # Look for patterns like "100–124", "100-124", "100+"
        range_match = re.search(r'(\d+)[–-](\d+)', question)
        if range_match:
            min_val = float(range_match.group(1))
            max_val = float(range_match.group(2))
            return (min_val, max_val)
        
        # Look for patterns like "400 or more", "400+"
        plus_match = re.search(r'(\d+)[\s+]*(or more|\+)', question)
        if plus_match:
            min_val = float(plus_match.group(1))
            return (min_val, float('inf'))
        
        # Look for patterns like "less than 100"
        less_match = re.search(r'less than (\d+)', question)
        if less_match:
            max_val = float(less_match.group(1))
            return (0, max_val)
            
        return None
    
    def sort_by_range(self, market_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort market data by range values extracted from questions.
        
        Args:
            market_data: The market data to sort.
            
        Returns:
            The sorted market data.
        """
        # Group outcomes by question
        question_groups = {}
        for item in market_data:
            question = item.get("question", "")
            if question not in question_groups:
                question_groups[question] = []
            question_groups[question].append(item)
        
        # For each question, extract range and add to data
        all_data = []
        for question, items in question_groups.items():
            range_val = self.extract_range_value(question)
            if range_val:
                min_val, max_val = range_val
                for item in items:
                    item_copy = item.copy()
                    item_copy["range_min"] = min_val
                    item_copy["range_max"] = max_val if max_val != float('inf') else min_val + 50
                    all_data.append(item_copy)
            else:
                # If no range is found, just add the item as is
                all_data.extend(items)
        
        # Sort by range minimum
        all_data.sort(key=lambda x: x.get("range_min", 0) if "range_min" in x else float('inf'))
        
        return all_data
    
    def plot_market_probabilities(self, market_data: List[Dict[str, Any]], 
                                 event_title: str) -> Figure:
        """
        Create a visualization of market probabilities.
        
        Args:
            market_data: List of market data dictionaries
            event_title: Title of the event
            
        Returns:
            matplotlib Figure object
        """
        # Create figure and axes
        fig, ax = plt.subplots(figsize=(14, 10))  # Larger figure size for better visibility
        
        # Sort markets by question text
        sorted_markets = sorted(market_data, key=lambda x: x.get('question', ''))
        
        # Check if we have any market data
        if not sorted_markets:
            ax.text(0.5, 0.5, "No market data available", 
                  ha='center', va='center', fontsize=14, transform=ax.transAxes)
            ax.set_title(f'{event_title} - Market Probabilities', fontsize=14, pad=20)
            return fig
        
        # Collect all percentages to determine y-axis range
        all_percentages = []
        
        # Plot each market's probability
        for i, market in enumerate(sorted_markets):
            question = market.get('question', f'Question {i+1}')
            price = market.get('price', None)
            percentage = market.get('percentage', None)
            outcome = market.get('outcome', '')
            
            # For API data format, we have 'price' and 'percentage' directly in the market object
            if price is not None and percentage is not None:
                # Only show YES outcomes to avoid duplication
                if outcome.lower() == 'yes':
                    all_percentages.append(percentage)
                    
                    # Calculate bar positions
                    bar_width = 0.8
                    x_position = i
                    
                    # Plot bar
                    color_idx = i % len(self.colors)
                    bar = ax.bar(x_position, percentage, width=bar_width,
                                label=question, color=self.colors[color_idx], alpha=0.7)
                    
                    # Add percentage label on top of bar
                    ax.text(x_position, percentage + 2, f'{percentage:.1f}%',
                           ha='center', va='bottom', fontsize=10, fontweight='bold')
                    
                    # Add market question below bar
                    ax.text(x_position, -5, question, ha='center', va='top',
                           rotation=45, fontsize=10)
            
            # For the legacy format with 'outcomes'
            else:
                outcomes = market.get('outcomes', [])
                if not outcomes:
                    continue
                
                # Sort outcomes by probability (descending)
                outcomes = sorted(outcomes, key=lambda x: x.get('probability', 0), reverse=True)
                
                # Get labels and probabilities
                labels = [outcome.get('value', f'Outcome {j+1}') for j, outcome in enumerate(outcomes)]
                probabilities = [outcome.get('probability', 0) for outcome in outcomes]
                
                # Convert probabilities from decimals to percentages
                probabilities = [prob * 100 for prob in probabilities]
                all_percentages.extend(probabilities)
                
                # Calculate bar positions
                bar_width = 0.8
                x_positions = np.arange(len(labels)) + (i * (len(labels) + 2))
                
                # Plot bars
                color_idx = i % len(self.colors)
                bars = ax.bar(x_positions, probabilities, width=bar_width, 
                             label=question, color=self.colors[color_idx], alpha=0.7)
                
                # Add percentage labels on top of bars
                for bar, prob in zip(bars, probabilities):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                           f'{prob:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
                
                # Add outcome labels below bars
                for j, (pos, label) in enumerate(zip(x_positions, labels)):
                    ax.text(pos, -5, label, ha='center', va='top', 
                           rotation=45, fontsize=10)
        
        # Set title and labels
        ax.set_title(f'{event_title} - Market Probabilities', fontsize=16, pad=20)
        ax.set_ylabel('Probability (%)', fontsize=14)
        
        # Remove x-axis ticks and labels (we add our own)
        ax.set_xticks([])
        
        # Add grid lines
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add legend
        if len(sorted_markets) > 1:
            ax.legend(loc='upper right', fontsize=10)
        
        # Set y-axis limits properly based on the actual data
        if all_percentages:
            max_percentage = max(all_percentages)
            # Add 15% padding above the highest percentage for labels
            y_max = max_percentage * 1.15
            # Ensure y_max is at least 100% for cases where percentages are small
            y_max = max(y_max, 100)
            ax.set_ylim(bottom=-10, top=y_max)
        else:
            # Default if no percentages
            ax.set_ylim(bottom=-10, top=100)
            
        # Safely set the container heights if they exist
        try:
            if ax.containers and len(ax.containers) > 0 and len(ax.containers[0]) > 0:
                # No need to set y-axis limits here since we already did it above
                pass
        except (IndexError, ValueError):
            # If there's an error with containers, we've already set default limits above
            pass
        
        # Format y-axis as percentage
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        
        # Adjust layout with more bottom margin for rotated labels
        plt.subplots_adjust(bottom=0.3)
        
        return fig
    
    def plot_comparison(self, current_data: List[Dict[str, Any]], 
                       previous_data: List[Dict[str, Any]],
                       event_title: str) -> Figure:
        """
        Create a comparison visualization between current and previous market data.
        
        Args:
            current_data: Current market data
            previous_data: Previous market data for comparison
            event_title: Title of the event
            
        Returns:
            matplotlib Figure object
        """
        # Create figure and axes
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Check if we have any data
        if not current_data:
            ax.text(0.5, 0.5, "No current market data available", 
                  ha='center', va='center', fontsize=14, transform=ax.transAxes)
            ax.set_title(f'{event_title} - Comparison', fontsize=16, pad=20)
            return fig
        
        # Sort markets by question text
        current_markets = sorted(current_data, key=lambda x: x.get('question', ''))
        
        # Create a mapping for previous data
        prev_markets_map = {m.get('question', ''): m for m in previous_data}
        
        # Plot changes for each market
        bar_group_width = 2.5  # Width for each group of bars
        group_spacing = 2      # Space between different market questions
        
        x_offset = 0  # Keep track of x-position
        tick_positions = []    # To store positions for x-ticks
        tick_labels = []       # To store labels for x-ticks
        
        for i, current_market in enumerate(current_markets):
            question = current_market.get('question', f'Question {i+1}')
            
            # Handle direct price/percentage format
            if 'price' in current_market and 'outcome' in current_market:
                # Only process YES outcomes
                if current_market.get('outcome', '').lower() != 'yes':
                    continue
                
                # Current data
                current_prob = current_market.get('percentage', 0)
                
                # Previous data - try to find matching market
                prev_prob = 0
                for prev_item in previous_data:
                    if (prev_item.get('question') == question and 
                        prev_item.get('outcome', '').lower() == 'yes'):
                        prev_prob = prev_item.get('percentage', 0)
                        break
                
                # Position for this market
                x_pos = x_offset
                
                # Plot bars
                color_idx = i % len(self.colors)
                
                # Plot current probability bar
                ax.bar(x_pos, current_prob, width=1.0, 
                      color=self.colors[color_idx], alpha=0.8,
                      label=f'Current' if i == 0 else "")
                
                # Plot previous probability bar (if exists)
                if prev_prob > 0:
                    ax.bar(x_pos + 1.0, prev_prob, width=1.0, 
                          color=self.colors[color_idx], alpha=0.4,
                          label=f'Previous' if i == 0 else "")
                
                # Add percentage labels
                ax.text(x_pos + 0.5, current_prob + 1, f'{current_prob:.1f}%', 
                       ha='center', va='bottom', fontsize=9)
                
                if prev_prob > 0:
                    ax.text(x_pos + 1.5, prev_prob + 1, f'{prev_prob:.1f}%', 
                           ha='center', va='bottom', fontsize=9)
                    
                    # Add change indicator
                    change = current_prob - prev_prob
                    change_color = 'green' if change > 0 else 'red' if change < 0 else 'gray'
                    change_sign = '+' if change > 0 else ''
                    ax.text(x_pos + 0.75, max(current_prob, prev_prob) + 5, 
                           f'{change_sign}{change:.1f}%', ha='center', 
                           color=change_color, fontweight='bold', fontsize=10)
                
                # Add market label
                tick_positions.append(x_pos + 0.5)
                tick_labels.append(question)
                
                # Update offset for next market
                x_offset += bar_group_width + group_spacing
                
            else:
                # Handle legacy format with 'outcomes'
                current_outcomes = current_market.get('outcomes', [])
                
                # Try to find this market in previous data
                prev_market = prev_markets_map.get(question, {})
                prev_outcomes = prev_market.get('outcomes', [])
                
                # Create mapping of outcome values to their probabilities
                current_probs = {o.get('value', ''): o.get('probability', 0) for o in current_outcomes}
                prev_probs = {o.get('value', ''): o.get('probability', 0) for o in prev_outcomes}
                
                # Get all unique outcome values
                all_outcomes = sorted(set(list(current_probs.keys()) + list(prev_probs.keys())))
                
                # Skip if no outcomes
                if not all_outcomes:
                    continue
                    
                # Add market question as a section label
                ax.text(x_offset + (len(all_outcomes) * bar_group_width) / 2, 105, 
                       question, ha='center', fontsize=12, fontweight='bold')
                
                # Plot each outcome's current and previous probabilities
                for j, outcome in enumerate(all_outcomes):
                    # Current position
                    x_pos = x_offset + j * bar_group_width
                    
                    # Get probabilities (convert to percentage)
                    current_prob = current_probs.get(outcome, 0) * 100
                    prev_prob = prev_probs.get(outcome, 0) * 100
                    
                    # Calculate change
                    change = current_prob - prev_prob
                    
                    # Plot bars
                    color_idx = i % len(self.colors)
                    
                    # Plot current probability bar
                    ax.bar(x_pos, current_prob, width=1.0, 
                          color=self.colors[color_idx], alpha=0.8,
                          label=f'Current' if i == 0 and j == 0 else "")
                    
                    # Plot previous probability bar (if exists)
                    if prev_prob > 0:
                        ax.bar(x_pos + 1.0, prev_prob, width=1.0, 
                              color=self.colors[color_idx], alpha=0.4,
                              label=f'Previous' if i == 0 and j == 0 else "")
                    
                    # Add percentage labels on top of bars
                    ax.text(x_pos + 0.5, current_prob + 1, f'{current_prob:.1f}%', 
                           ha='center', va='bottom', fontsize=9)
                    
                    if prev_prob > 0:
                        ax.text(x_pos + 1.5, prev_prob + 1, f'{prev_prob:.1f}%', 
                               ha='center', va='bottom', fontsize=9)
                    
                    # Add change indicator
                    if prev_prob > 0:
                        change_color = 'green' if change > 0 else 'red' if change < 0 else 'gray'
                        change_sign = '+' if change > 0 else ''
                        ax.text(x_pos + 0.75, max(current_prob, prev_prob) + 5, 
                               f'{change_sign}{change:.1f}%', ha='center', 
                               color=change_color, fontweight='bold', fontsize=10)
                    
                    # Add outcome label
                    tick_positions.append(x_pos + 0.5)
                    tick_labels.append(outcome)
                
                # Update x_offset for next market group
                x_offset += len(all_outcomes) * bar_group_width + group_spacing
        
        # Set title and labels
        ax.set_title(f'{event_title}', fontsize=16, pad=20)
        ax.set_ylabel('Probability (%)', fontsize=12)
        
        # Set x-axis ticks and labels
        if tick_positions:
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=10)
        
        # Add legend
        ax.legend(loc='upper right', fontsize=10)
        
        # Set y-axis limits
        ax.set_ylim(bottom=0, top=110)  # Leave room for labels
        
        # Add grid lines
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Adjust layout
        plt.tight_layout()
        
        return fig
    
    def save_plot(self, fig: Figure, output_path: Union[str, Path]) -> None:
        """
        Save the figure to a file.
        
        Args:
            fig: The matplotlib Figure to save
            output_path: Path where the plot should be saved
            
        Returns:
            None
        """
        # Make sure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the figure
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)  # Close the figure to free memory
    
    def plot_order_book(self, order_frames: Dict[str, Dict[str, List[Dict[str, float]]]], 
                      event_title: str) -> Dict[str, Figure]:
        """
        Create visualizations of order book data showing buy and sell orders.
        
        Args:
            order_frames: Dictionary of market questions to order book data
            event_title: Title of the event
            
        Returns:
            Dictionary mapping market questions to figure objects
        """
        figures = {}
        
        # Process each market in the order frames
        for question, data in order_frames.items():
            # Create a new figure for this market
            fig, ax = plt.subplots(figsize=(12, 8))
            
            buy_orders = data.get('buy_orders', [])
            sell_orders = data.get('sell_orders', [])
            
            # Sort orders by price
            buy_orders = sorted(buy_orders, key=lambda x: x['price'], reverse=True)
            sell_orders = sorted(sell_orders, key=lambda x: x['price'])
            
            # Prepare data for plotting
            buy_prices = [order['price'] for order in buy_orders]
            buy_sizes = [order['size'] for order in buy_orders]
            sell_prices = [order['price'] for order in sell_orders]
            sell_sizes = [order['size'] for order in sell_orders]
            
            # Create bar plots for buy orders (in green)
            if buy_prices:
                ax.bar(buy_prices, buy_sizes, width=0.4, color='green', alpha=0.6, label='Buy Orders')
                
                # Add value labels above bars
                for price, size in zip(buy_prices, buy_sizes):
                    ax.text(price, size + 1, f'{size:.1f}', ha='center', va='bottom', fontsize=9)
            
            # Create bar plots for sell orders (in red)
            if sell_prices:
                ax.bar(sell_prices, sell_sizes, width=0.4, color='red', alpha=0.6, label='Sell Orders')
                
                # Add value labels above bars
                for price, size in zip(sell_prices, sell_sizes):
                    ax.text(price, size + 1, f'{size:.1f}', ha='center', va='bottom', fontsize=9)
            
            # Calculate market metrics
            if buy_orders and sell_orders:
                best_bid = buy_orders[0]['price']
                best_ask = sell_orders[0]['price']
                spread = best_ask - best_bid
                mid_price = (best_bid + best_ask) / 2
                
                # Highlight the spread area
                if best_bid < best_ask:  # Normal spread
                    ax.axvspan(best_bid, best_ask, alpha=0.2, color='yellow', label=f'Spread: {spread:.1f}¢')
                    
                    # Add vertical lines for best bid and ask
                    ax.axvline(x=best_bid, color='green', linestyle='--', alpha=0.7)
                    ax.axvline(x=best_ask, color='red', linestyle='--', alpha=0.7)
                    
                    # Add text annotations
                    y_max = ax.get_ylim()[1]
                    ax.text(best_bid, y_max * 0.9, f'Best Bid\n{best_bid:.1f}¢', 
                            ha='right', va='top', color='green', fontweight='bold')
                    ax.text(best_ask, y_max * 0.9, f'Best Ask\n{best_ask:.1f}¢', 
                            ha='left', va='top', color='red', fontweight='bold')
                
            # Set title and labels
            ax.set_title(f'Order Book: {question}', fontsize=14, pad=20)
            ax.set_xlabel('Price (¢)', fontsize=12)
            ax.set_ylabel('Size (contracts)', fontsize=12)
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.6)
            
            # Add legend
            ax.legend(loc='upper right')
            
            # Adjust y-axis to show all data plus some margin
            y_values = buy_sizes + sell_sizes
            if y_values:
                max_y = max(y_values)
                ax.set_ylim(0, max_y * 1.2)  # Add 20% margin
            else:
                # Set default y-limits if no data
                ax.set_ylim(0, 10)
            
            # Format price axis as currency
            ax.xaxis.set_major_formatter(mtick.StrMethodFormatter('{x:.1f}¢'))
            
            # Add event title as a text above the plot
            plt.figtext(0.5, 0.99, f'{event_title}', ha='center', fontsize=16, fontweight='bold')
            
            # Adjust layout
            plt.tight_layout(rect=[0, 0, 1, 0.97])  # Leave space at top for title
            
            # Store the figure
            figures[question] = fig
        
        return figures