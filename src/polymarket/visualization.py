# src/polymarket/visualization.py

import os
import re
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from typing import List, Dict, Any, Optional, Tuple

class MarketVisualizer:
    """Handles visualization of market data."""
    
    def __init__(self, output_dir: str = "plots"):
        """
        Initialize the visualizer.
        
        Args:
            output_dir: Directory for saving plot images.
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
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
    
    def plot_market_probabilities(self, 
                                  market_data: List[Dict[str, Any]], 
                                  event_title: str, 
                                  event_slug: str) -> str:
        """
        Create a bar chart of market probabilities.
        
        Args:
            market_data: The market data to visualize.
            event_title: The title of the event.
            event_slug: The event slug from the URL.
            
        Returns:
            The path to the saved plot image.
        """
        if not market_data:
            print("No data to visualize.")
            return ""
        
        # Sort data by range values
        sorted_data = self.sort_by_range(market_data)
        
        # Filter for "Yes" outcomes only to avoid duplicates
        yes_data = [item for item in sorted_data if item.get("outcome") == "Yes"]
        
        if not yes_data:
            print("No 'Yes' outcomes found to visualize.")
            return ""
        
        # Set up the figure
        plt.figure(figsize=(12, 8))
        
        # Extract values for plotting
        questions = [self._format_question(item.get("question", "Unknown")) for item in yes_data]
        percentages = [item.get("percentage", 0) or 0 for item in yes_data]  # Handle None values
        
        # Create the bar chart
        bars = plt.bar(range(len(yes_data)), percentages, color='skyblue')
        
        # Add percentage labels on top of bars
        for i, (bar, percentage) in enumerate(zip(bars, percentages)):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{percentage:.1f}%',
                    ha='center', va='bottom', fontsize=9)
        
        # Configure the chart
        plt.title(f"Market Probabilities: {event_title}", fontsize=14)
        plt.xlabel("Market Range", fontsize=12)
        plt.ylabel("Probability (%)", fontsize=12)
        plt.xticks(range(len(yes_data)), questions, rotation=45, ha='right', fontsize=9)
        plt.ylim(0, max(percentages) * 1.2 if percentages else 100)  # Add some headroom
        
        # Format y-axis as percentage
        plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the plot
        filename = f"{event_slug}_probabilities.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300)
        plt.close()
        
        print(f"Plot saved to {filepath}")
        return filepath
    
    def _format_question(self, question: str) -> str:
        """
        Format the question for display in the chart.
        
        Args:
            question: The question to format.
            
        Returns:
            The formatted question.
        """
        # Extract the range part only, e.g. "Will Elon tweet 125–149 times..." -> "125–149"
        range_match = re.search(r'(\d+[–-]\d+|\d+\+|less than \d+|\d+ or more)', question)
        if range_match:
            return range_match.group(1)
        
        # Truncate long questions
        if len(question) > 20:
            return question[:17] + "..."
        
        return question
    
    def plot_market_comparison(self, 
                              current_data: List[Dict[str, Any]], 
                              previous_data: List[Dict[str, Any]], 
                              event_title: str, 
                              event_slug: str) -> str:
        """
        Create a comparison chart between current and previous market data.
        
        Args:
            current_data: The current market data.
            previous_data: The previous market data.
            event_title: The title of the event.
            event_slug: The event slug from the URL.
            
        Returns:
            The path to the saved plot image.
        """
        if not current_data or not previous_data:
            print("Insufficient data for comparison.")
            return ""
        
        # Sort data by range values
        current_sorted = self.sort_by_range(current_data)
        previous_sorted = self.sort_by_range(previous_data)
        
        # Filter for "Yes" outcomes
        current_yes = [item for item in current_sorted if item.get("outcome") == "Yes"]
        previous_yes = [item for item in previous_sorted if item.get("outcome") == "Yes"]
        
        if not current_yes or not previous_yes:
            print("No 'Yes' outcomes found for comparison.")
            return ""
        
        # Create a mapping of questions to data for easier lookup
        prev_data_map = {item.get("question", ""): item for item in previous_yes}
        
        # Filter current data to include only questions that exist in both datasets
        common_data = []
        for item in current_yes:
            question = item.get("question", "")
            if question in prev_data_map:
                common_data.append({
                    "question": question,
                    "current": item.get("percentage", 0) or 0,
                    "previous": prev_data_map[question].get("percentage", 0) or 0,
                    "range_min": item.get("range_min", 0)
                })
        
        if not common_data:
            print("No common questions found for comparison.")
            return ""
        
        # Sort by range minimum
        common_data.sort(key=lambda x: x.get("range_min", 0))
        
        # Set up the figure
        plt.figure(figsize=(12, 8))
        
        # Extract values for plotting
        questions = [self._format_question(item["question"]) for item in common_data]
        current_percentages = [item["current"] for item in common_data]
        previous_percentages = [item["previous"] for item in common_data]
        
        # Set width of bars
        bar_width = 0.35
        indices = range(len(common_data))
        
        # Create the bar chart
        plt.bar([i - bar_width/2 for i in indices], previous_percentages, 
                bar_width, label='Previous', color='lightgray')
        current_bars = plt.bar([i + bar_width/2 for i in indices], current_percentages, 
                              bar_width, label='Current', color='skyblue')
        
        # Add percentage labels on current bars
        for i, (bar, curr, prev) in enumerate(zip(current_bars, current_percentages, previous_percentages)):
            height = bar.get_height()
            change = curr - prev
            change_str = f"+{change:.1f}%" if change > 0 else f"{change:.1f}%"
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{curr:.1f}% ({change_str})',
                    ha='center', va='bottom', fontsize=8, color='black' if abs(change) < 5 else 'red' if change < 0 else 'green')
        
        # Configure the chart
        plt.title(f"Market Probability Changes: {event_title}", fontsize=14)
        plt.xlabel("Market Range", fontsize=12)
        plt.ylabel("Probability (%)", fontsize=12)
        plt.xticks(indices, questions, rotation=45, ha='right', fontsize=9)
        plt.legend()
        
        # Format y-axis as percentage
        plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the plot
        filename = f"{event_slug}_comparison.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300)
        plt.close()
        
        print(f"Comparison plot saved to {filepath}")
        return filepath 