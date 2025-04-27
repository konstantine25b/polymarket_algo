import os
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

from src.constants import PREDICTOR_PLOTS_DIR

def plot_monte_carlo_simulation(simulations: np.ndarray, 
                              tweet_count: int, 
                              final_prediction: float, 
                              confidence_interval: tuple, 
                              count_frames: List[Dict[str, any]], 
                              frame_probabilities: Dict[str, float]) -> str:
    """
    Generate and save a visualization of the Monte Carlo simulations
    
    Args:
        simulations: Array of simulation results
        tweet_count: Current tweet count
        final_prediction: Final prediction value
        confidence_interval: Tuple of (lower, upper) confidence interval
        count_frames: List of count frame dictionaries
        frame_probabilities: Dictionary mapping frames to probabilities
        
    Returns:
        str: Path to the saved plot
    """
    try:
        plt.figure(figsize=(12, 8))
        
        # Create histogram of simulations
        n, bins, patches = plt.hist(simulations, bins=30, alpha=0.6, color='skyblue', density=True)
        
        # Add KDE for smooth distribution
        sns.kdeplot(simulations, color='darkblue', lw=2)
        
        # Add vertical lines for key values
        plt.axvline(x=tweet_count, color='red', linestyle='-', label=f'Current count: {tweet_count}', linewidth=2)
        plt.axvline(x=final_prediction, color='green', linestyle='--', label=f'Prediction: {final_prediction:.1f}', linewidth=2)
        
        # Add CI
        plt.axvline(x=confidence_interval[0], color='orange', linestyle=':', label=f'95% CI: {confidence_interval[0]:.1f} - {confidence_interval[1]:.1f}', linewidth=1.5)
        plt.axvline(x=confidence_interval[1], color='orange', linestyle=':', linewidth=1.5)
        
        # Add frame boundaries
        for frame in count_frames:
            if frame["min"] >= tweet_count and frame["min"] <= confidence_interval[1] + 50:
                plt.axvline(x=frame["min"], color='gray', linestyle='-', alpha=0.3, linewidth=1)
        
        plt.title('Monte Carlo Simulation of Final Tweet Count', fontsize=16)
        plt.xlabel('Total Tweets', fontsize=14)
        plt.ylabel('Probability Density', fontsize=14)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Add text annotation for most likely frames
        y_pos = 0.85
        plt.text(0.02, y_pos, "Most likely outcomes:", transform=plt.gca().transAxes, fontsize=12, 
                bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        
        # Sort frames by probability
        sorted_by_prob = sorted(frame_probabilities.items(), key=lambda x: x[1], reverse=True)
        
        for i, (frame_name, probability) in enumerate(sorted_by_prob[:3]):
            y_pos -= 0.05
            plt.text(0.02, y_pos, f"{i+1}. {frame_name}: {probability:.1f}%", 
                    transform=plt.gca().transAxes, fontsize=12, 
                    bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.3'))
        
        # Create the plots directory if it doesn't exist
        os.makedirs(PREDICTOR_PLOTS_DIR, exist_ok=True)
        
        # Save to the predictor plots directory
        plot_path = os.path.join(PREDICTOR_PLOTS_DIR, 'tweet_prediction.png')
        plt.tight_layout()
        plt.savefig(plot_path)
        plt.close()
        print(f"\nVisualization saved to: {plot_path}")
        
        return plot_path
        
    except Exception as e:
        print(f"Warning: Could not generate visualization: {e}")
        return ""

def plot_historical_trends(df: pd.DataFrame, start_time, end_time, tweet_count, prediction) -> str:
    """
    Generate and save a visualization of historical tweet trends
    
    Args:
        df: DataFrame containing tweet data
        start_time: Start time of the prediction window
        end_time: End time of the prediction window
        tweet_count: Current tweet count
        prediction: Predicted final tweet count
    
    Returns:
        str: Path to the saved plot
    """
    try:
        # Prepare daily data
        df['date'] = df['created_at_dt'].dt.date
        daily_counts = df.groupby('date').size().reset_index(name='count')
        daily_counts['date'] = pd.to_datetime(daily_counts['date'])
        daily_counts = daily_counts.sort_values('date')
        
        # Calculate moving averages
        daily_counts['MA_7'] = daily_counts['count'].rolling(window=7).mean()
        daily_counts['MA_30'] = daily_counts['count'].rolling(window=30).mean()
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        # Plot daily counts as points
        plt.scatter(daily_counts['date'], daily_counts['count'], s=10, color='gray', alpha=0.5, label='Daily Tweets')
        
        # Plot moving averages
        plt.plot(daily_counts['date'], daily_counts['MA_7'], color='blue', linewidth=2, label='7-day MA')
        plt.plot(daily_counts['date'], daily_counts['MA_30'], color='red', linewidth=2, label='30-day MA')
        
        # Add vertical lines for prediction window
        plt.axvline(x=start_time, color='green', linestyle='--', label='Prediction Window', linewidth=1.5)
        plt.axvline(x=end_time, color='green', linestyle='--', linewidth=1.5)
        
        # Add horizontal line for the prediction
        plt.axhline(y=prediction/((end_time - start_time).days), color='purple', linestyle='-', 
                   label=f'Required Daily Rate: {prediction/((end_time - start_time).days):.1f}', linewidth=2)
        
        plt.title('Historical Tweet Frequency and Prediction Window', fontsize=16)
        plt.xlabel('Date', fontsize=14)
        plt.ylabel('Tweets per Day', fontsize=14)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Format x-axis dates
        plt.gcf().autofmt_xdate()
        
        # Create the plots directory if it doesn't exist
        os.makedirs(PREDICTOR_PLOTS_DIR, exist_ok=True)
        
        # Save to the predictor plots directory
        plot_path = os.path.join(PREDICTOR_PLOTS_DIR, 'historical_trends.png')
        plt.tight_layout()
        plt.savefig(plot_path)
        plt.close()
        print(f"\nHistorical trend visualization saved to: {plot_path}")
        
        return plot_path
        
    except Exception as e:
        print(f"Warning: Could not generate historical trends visualization: {e}")
        return "" 