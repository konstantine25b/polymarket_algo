"""
Facebook Prophet predictor for Elon Musk tweet count forecasting.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from prophet import Prophet
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import os
from scipy.special import erf

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants import TWEET_COUNT_FRAMES, ET_TIMEZONE

from .data_processor import TweetDataProcessor


class TweetPredictor:
    """Facebook Prophet-based tweet count predictor for Polymarket time frames."""
    
    def __init__(self, data_path=None, save_plots=True):
        """
        Initialize the tweet predictor.
        
        Args:
            data_path (str): Path to tweet data CSV file
            save_plots (bool): Whether to save prediction plots
        """
        self.data_processor = TweetDataProcessor(data_path)
        self.model = None
        self.forecast = None
        self.save_plots = save_plots
        self.plots_dir = Path("src/facebook_prophet/plots")
        self.random_seed = None
        
        # Create plots directory
        if self.save_plots:
            self.plots_dir.mkdir(parents=True, exist_ok=True)
    
    def set_random_seed(self, seed):
        """
        Set random seed for reproducible results.
        
        Args:
            seed (int): Random seed value
        """
        self.random_seed = seed
        np.random.seed(seed)
        # Note: Prophet doesn't have built-in random seed control,
        # but this helps with any numpy operations we do
    
    def prepare_model(self, changepoint_prior_scale=0.05, seasonality_prior_scale=10.0):
        """
        Prepare and fit the Prophet model.
        
        Args:
            changepoint_prior_scale (float): Flexibility of trend changes
            seasonality_prior_scale (float): Strength of seasonality
        """
        # Get processed data
        df = self.data_processor.get_prophet_data()
        
        # Initialize Prophet model with parameters optimized for tweet data
        self.model = Prophet(
            changepoint_prior_scale=changepoint_prior_scale,
            seasonality_prior_scale=seasonality_prior_scale,
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
            interval_width=0.95
        )
        
        # Fit the model
        print("Training Prophet model...")
        self.model.fit(df)
        print("Model training completed!")
        
        return self.model
    
    def generate_predictions(self, current_time=None):
        """
        Generate predictions for all tweet count time frames.
        
        Args:
            current_time (datetime): Current time for prediction context
            
        Returns:
            dict: Predictions for each time frame with probabilities
        """
        if self.model is None:
            self.prepare_model()
        
        # Get current week context
        week_data = self.data_processor.get_current_week_data(current_time)
        
        current_tweets = week_data['current_week_tweets']
        time_remaining = week_data['time_remaining']
        total_duration = week_data['total_week_duration']
        
        print(f"\n=== Current Week Status ===")
        print(f"Current time: {week_data['current_time']}")
        print(f"Week period: {week_data['week_start']} to {week_data['week_end']}")
        print(f"Tweets posted so far: {current_tweets}")
        print(f"Time remaining: {time_remaining}")
        
        # Calculate daily prediction for remaining period
        if time_remaining.total_seconds() > 0:
            remaining_days = time_remaining.total_seconds() / (24 * 3600)
            
            # Create future dataframe for prediction
            future = self.model.make_future_dataframe(periods=max(1, int(np.ceil(remaining_days))))
            forecast = self.model.predict(future)
            
            # Get the latest prediction (most recent forecast)
            latest_prediction = forecast.iloc[-1]['yhat']
            prediction_lower = forecast.iloc[-1]['yhat_lower']
            prediction_upper = forecast.iloc[-1]['yhat_upper']
            
            # Scale prediction based on remaining time
            predicted_remaining_tweets = latest_prediction * remaining_days
            
            # For confidence intervals, we need to be more careful
            # The uncertainty doesn't scale linearly with time for tweet counts
            # Use a more conservative approach for confidence intervals
            daily_uncertainty = (prediction_upper - prediction_lower) / 2
            
            # Scale uncertainty by square root of remaining days (more realistic for count data)
            scaled_uncertainty = daily_uncertainty * np.sqrt(remaining_days)
            
            predicted_remaining_lower = predicted_remaining_tweets - scaled_uncertainty
            predicted_remaining_upper = predicted_remaining_tweets + scaled_uncertainty
            
            # Ensure lower bound is not negative for tweet counts
            predicted_remaining_lower = max(0, predicted_remaining_lower)
            
        else:
            # No time remaining
            predicted_remaining_tweets = 0
            predicted_remaining_lower = 0
            predicted_remaining_upper = 0
        
        # Calculate total predicted tweets for the week
        total_predicted = current_tweets + predicted_remaining_tweets
        total_predicted_lower = current_tweets + predicted_remaining_lower
        total_predicted_upper = current_tweets + predicted_remaining_upper
        
        print(f"Predicted remaining tweets: {predicted_remaining_tweets:.1f}")
        print(f"Total predicted tweets for week: {total_predicted:.1f} ({total_predicted_lower:.1f} - {total_predicted_upper:.1f})")
        
        # Calculate probabilities for each time frame
        predictions = {}
        
        # Use a reasonable standard deviation for tweet count predictions
        # Based on typical tweet count variability (around 15-20% of the prediction)
        std_dev = max(10, total_predicted * 0.15)  # Minimum 10 tweets std dev, or 15% of prediction
        
        for frame in TWEET_COUNT_FRAMES:
            frame_name = frame['name']
            min_tweets = frame['min']
            max_tweets = frame['max']
            
            # Calculate probability using normal distribution
            if max_tweets == float('inf'):
                # For "X or more" categories
                prob = 1 - self._normal_cdf(min_tweets - 0.5, total_predicted, std_dev)
            else:
                # For range categories
                prob_lower = self._normal_cdf(min_tweets - 0.5, total_predicted, std_dev)
                prob_upper = self._normal_cdf(max_tweets + 0.5, total_predicted, std_dev)
                prob = prob_upper - prob_lower
            
            predictions[frame_name] = {
                'probability': max(0, min(1, prob)),  # Clamp between 0 and 1
                'range': f"{min_tweets}-{max_tweets}" if max_tweets != float('inf') else f"{min_tweets}+",
                'min': min_tweets,
                'max': max_tweets
            }
        
        # Normalize probabilities to sum to 1
        total_prob = sum(pred['probability'] for pred in predictions.values())
        if total_prob > 0:
            for frame_name in predictions:
                predictions[frame_name]['probability'] /= total_prob
        
        # Store forecast for plotting
        if time_remaining.total_seconds() > 0:
            self.forecast = forecast
        
        # Add summary information
        summary = {
            'current_tweets': current_tweets,
            'predicted_remaining': predicted_remaining_tweets,
            'total_predicted': total_predicted,
            'confidence_interval': (total_predicted_lower, total_predicted_upper),
            'time_remaining': time_remaining,
            'predictions_by_frame': predictions
        }
        
        return summary
    
    def _normal_cdf(self, x, mean, std):
        """Calculate cumulative distribution function of normal distribution."""
        if std <= 0:
            return 1.0 if x >= mean else 0.0
        return 0.5 * (1 + erf((x - mean) / (std * np.sqrt(2))))
    
    def plot_predictions(self, predictions_summary, save_path=None):
        """
        Plot the prediction results.
        
        Args:
            predictions_summary (dict): Results from generate_predictions()
            save_path (str): Optional custom save path for plots
        """
        if not self.save_plots and save_path is None:
            return
        
        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Plot 1: Historical tweet counts and forecast
        if self.forecast is not None:
            df = self.data_processor.get_prophet_data()
            
            ax1.plot(df['ds'], df['y'], 'o-', label='Historical Daily Tweets', alpha=0.7)
            
            # Plot forecast for last few days
            forecast_recent = self.forecast.tail(30)
            ax1.plot(forecast_recent['ds'], forecast_recent['yhat'], 
                    'r-', label='Prophet Forecast', linewidth=2)
            ax1.fill_between(forecast_recent['ds'], 
                           forecast_recent['yhat_lower'], 
                           forecast_recent['yhat_upper'], 
                           alpha=0.3, color='red', label='Uncertainty')
            
            ax1.set_title('Tweet Count Forecast')
            ax1.set_xlabel('Date')
            ax1.set_ylabel('Daily Tweet Count')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        # Plot 2: Time frame probabilities
        frames = list(predictions_summary['predictions_by_frame'].keys())
        probs = [predictions_summary['predictions_by_frame'][f]['probability'] for f in frames]
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(frames)))
        bars = ax2.bar(range(len(frames)), probs, color=colors)
        ax2.set_title('Probability by Tweet Count Range')
        ax2.set_xlabel('Tweet Count Range')
        ax2.set_ylabel('Probability')
        ax2.set_xticks(range(len(frames)))
        ax2.set_xticklabels(frames, rotation=45, ha='right')
        ax2.grid(True, alpha=0.3)
        
        # Add probability labels on bars
        for bar, prob in zip(bars, probs):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{prob:.3f}', ha='center', va='bottom', fontsize=9)
        
        # Plot 3: Current status
        current = predictions_summary['current_tweets']
        predicted = predictions_summary['total_predicted']
        remaining = predictions_summary['predicted_remaining']
        
        categories = ['Current\nTweets', 'Predicted\nRemaining', 'Total\nPredicted']
        values = [current, remaining, predicted]
        colors_status = ['blue', 'orange', 'green']
        
        bars = ax3.bar(categories, values, color=colors_status, alpha=0.7)
        ax3.set_title('Tweet Count Status')
        ax3.set_ylabel('Number of Tweets')
        ax3.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{value:.1f}', ha='center', va='bottom', fontweight='bold')
        
        # Plot 4: Top 5 most likely time frames
        sorted_frames = sorted(predictions_summary['predictions_by_frame'].items(), 
                             key=lambda x: x[1]['probability'], reverse=True)
        top_5 = sorted_frames[:5]
        
        top_frames = [f[0] for f in top_5]
        top_probs = [f[1]['probability'] for f in top_5]
        
        colors_top = plt.cm.viridis(np.linspace(0, 1, len(top_5)))
        bars = ax4.barh(range(len(top_5)), top_probs, color=colors_top)
        ax4.set_title('Top 5 Most Likely Ranges')
        ax4.set_xlabel('Probability')
        ax4.set_yticks(range(len(top_5)))
        ax4.set_yticklabels(top_frames)
        ax4.grid(True, alpha=0.3)
        
        # Add probability labels
        for i, (bar, prob) in enumerate(zip(bars, top_probs)):
            width = bar.get_width()
            ax4.text(width + 0.01, bar.get_y() + bar.get_height()/2.,
                    f'{prob:.3f}', ha='left', va='center', fontweight='bold')
        
        plt.tight_layout()
        
        # Save the plot
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        elif self.save_plots:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = self.plots_dir / f"tweet_predictions_{timestamp}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        
        plt.show()
    
    def print_prediction_summary(self, predictions_summary):
        """Print a formatted summary of predictions."""
        print("\n" + "="*60)
        print("ELON MUSK TWEET COUNT PREDICTIONS")
        print("="*60)
        
        print(f"Current tweets this week: {predictions_summary['current_tweets']}")
        print(f"Predicted remaining tweets: {predictions_summary['predicted_remaining']:.1f}")
        print(f"Total predicted tweets: {predictions_summary['total_predicted']:.1f}")
        
        ci = predictions_summary['confidence_interval']
        print(f"95% Confidence interval: {ci[0]:.1f} - {ci[1]:.1f}")
        print(f"Time remaining: {predictions_summary['time_remaining']}")
        
        print("\nPROBABILITIES BY TIME FRAME:")
        print("-"*40)
        
        # Sort by probability descending
        sorted_frames = sorted(predictions_summary['predictions_by_frame'].items(), 
                             key=lambda x: x[1]['probability'], reverse=True)
        
        for frame_name, data in sorted_frames:
            prob = data['probability']
            print(f"{frame_name:20s}: {prob:7.3f} ({prob*100:5.1f}%)")
        
        print("-"*40)
        print(f"{'TOTAL':20s}: {sum(d['probability'] for d in predictions_summary['predictions_by_frame'].values()):7.3f} (100.0%)")
        print("="*60) 