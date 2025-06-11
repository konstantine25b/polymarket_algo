"""
Basic Neural Prophet predictor for Elon Musk tweet counts.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from neuralprophet import NeuralProphet
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import os
from scipy import stats

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants import TWEET_COUNT_FRAMES, ET_TIMEZONE

from .data_processor import TweetDataProcessor


class NeuralTweetPredictor:
    """Neural Prophet-based tweet count predictor."""
    
    def __init__(self, data_path=None, save_plots=True):
        """
        Initialize the Neural Prophet predictor.
        
        Args:
            data_path (str): Path to tweet data CSV file
            save_plots (bool): Whether to save prediction plots
        """
        self.data_processor = TweetDataProcessor(data_path)
        self.model = None
        self.save_plots = save_plots
        self.plots_dir = Path("src/prediction_algos/neural_prophet/plots")
        self.random_seed = 42  # Default random seed
        
        # Create plots directory
        if self.save_plots:
            self.plots_dir.mkdir(parents=True, exist_ok=True)
    
    def set_random_seed(self, seed):
        """Set random seed for reproducible results."""
        self.random_seed = seed
        
        # Set PyTorch and PyTorch Lightning seeds
        try:
            import torch
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)
            
            # PyTorch Lightning specific settings
            import pytorch_lightning as pl
            pl.seed_everything(seed, workers=True)
            
            # Also set numpy and random for good measure
            np.random.seed(seed)
            import random
            random.seed(seed)
            os.environ['PYTHONHASHSEED'] = str(seed)
        except ImportError:
            # If PyTorch is not available, just set numpy
            np.random.seed(seed)
    
    def prepare_model(self, n_forecasts=1, yearly_seasonality=True, weekly_seasonality=True, 
                     daily_seasonality=False, epochs=50, learning_rate=0.15):
        """
        Prepare and train the Neural Prophet model.
        
        Args:
            n_forecasts (int): Number of steps to forecast ahead
            yearly_seasonality (bool): Whether to include yearly seasonality
            weekly_seasonality (bool): Whether to include weekly seasonality
            daily_seasonality (bool): Whether to include daily seasonality (disabled by default for speed)
            epochs (int): Number of training epochs (default: 50 for normal mode)
            learning_rate (float): Learning rate for training (default: 0.15)
        """
        print("Preparing Neural Prophet model...")
        
        # Set random seed for reproducible training
        self.set_random_seed(self.random_seed)
        
        # Get training data
        train_data = self.data_processor.get_neural_prophet_data()
        
        # Determine mode based on epochs
        if epochs <= 15:
            mode = "ULTRA-FAST"
            print(f"🚀 {mode} MODE: {epochs} epochs, LR={learning_rate}")
        elif epochs <= 30:
            mode = "FAST"
            print(f"⚡ {mode} MODE: {epochs} epochs, LR={learning_rate}")
        else:
            mode = "NORMAL"
            print(f"🔵 {mode} MODE: {epochs} epochs, LR={learning_rate}")
        
        # Initialize Neural Prophet model
        self.model = NeuralProphet(
            n_forecasts=n_forecasts,
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=weekly_seasonality,
            daily_seasonality=daily_seasonality,
            epochs=epochs,
            learning_rate=learning_rate,
            quantiles=[0.1, 0.9],  # Keep confidence intervals
            n_lags=5 if epochs <= 30 else 7,  # More lags for normal mode
            n_changepoints=6 if epochs <= 30 else 10,  # More changepoints for normal mode
            trend_reg=1.5 if epochs <= 30 else 1.0,  # Less regularization for normal mode
            seasonality_reg=1.5 if epochs <= 30 else 1.0,  # Less regularization for normal mode
            normalize='standardize',
            impute_missing=True
        )
        
        print(f"Training {mode} Neural Prophet with {len(train_data)} days of data...")
        if epochs <= 15:
            print("Optimizations: Ultra-fast, minimal features")
        elif epochs <= 30:
            print("Optimizations: Fast, 5 lags, 6 changepoints, no daily seasonality")
        else:
            print("Configuration: Standard, 7 lags, 10 changepoints, enhanced features")
        
        # Train the model
        metrics = self.model.fit(train_data, freq='D')
        
        print(f"{mode} Neural Prophet model training completed!")
        print(f"Final metrics: {metrics.tail(1)}")
        
        return self.model
    
    def predict_remaining_tweets(self, current_time=None):
        """
        Predict remaining tweets for the current prediction period.
        
        Args:
            current_time (datetime): Current time for prediction context
            
        Returns:
            dict: Prediction results including forecasts and confidence intervals
        """
        if self.model is None:
            self.prepare_model()
        
        # Get current week information
        week_data = self.data_processor.get_current_week_data(current_time)
        current_tweets = week_data['current_week_tweets']
        time_remaining = week_data['time_remaining']
        
        print(f"Current tweets: {current_tweets}")
        print(f"Time remaining: {time_remaining}")
        
        # Calculate days remaining (Neural Prophet works with daily forecasts)
        days_remaining = max(1, int(np.ceil(time_remaining.total_seconds() / (24 * 3600))))
        
        print(f"Days to forecast: {days_remaining}")
        
        # Make future dataframe
        future = self.model.make_future_dataframe(
            self.data_processor.get_neural_prophet_data(),
            periods=days_remaining,
            n_historic_predictions=True
        )
        
        # Generate forecast
        forecast = self.model.predict(future)
        
        # Extract predictions for remaining days
        future_forecast = forecast.tail(days_remaining)
        
        # Calculate total remaining tweets
        remaining_tweets = future_forecast['yhat1'].sum()
        
        # Calculate confidence intervals
        if 'yhat1 10.0%-ile' in future_forecast.columns:
            lower_bound = future_forecast['yhat1 10.0%-ile'].sum()
            upper_bound = future_forecast['yhat1 90.0%-ile'].sum()
        else:
            # Fallback: estimate confidence interval from prediction variance
            std_prediction = future_forecast['yhat1'].std()
            lower_bound = remaining_tweets - 1.645 * std_prediction * np.sqrt(days_remaining)
            upper_bound = remaining_tweets + 1.645 * std_prediction * np.sqrt(days_remaining)
        
        total_predicted = current_tweets + remaining_tweets
        total_lower = current_tweets + lower_bound
        total_upper = current_tweets + upper_bound
        
        return {
            'remaining_tweets': remaining_tweets,
            'total_predicted': total_predicted,
            'confidence_interval': {
                'lower': total_lower,
                'upper': total_upper,
                'width': total_upper - total_lower
            },
            'days_remaining': days_remaining,
            'current_tweets': current_tweets,
            'forecast_data': future_forecast,
            'full_forecast': forecast
        }
    
    def calculate_probabilities(self, prediction_results):
        """
        Calculate probabilities for each tweet count range.
        
        Args:
            prediction_results (dict): Results from predict_remaining_tweets
            
        Returns:
            dict: Probabilities for each range defined in TWEET_COUNT_FRAMES
        """
        total_predicted = prediction_results['total_predicted']
        ci_lower = prediction_results['confidence_interval']['lower']
        ci_upper = prediction_results['confidence_interval']['upper']
        
        # Estimate standard deviation from confidence interval
        # Using 80% CI (10th to 90th percentile), so 1.645 * std on each side
        std_estimate = (ci_upper - ci_lower) / (2 * 1.645)
        
        # Use normal distribution for probability calculation
        # (could also use gamma distribution for count data)
        probabilities = {}
        
        for frame in TWEET_COUNT_FRAMES:
            frame_name = frame['name']
            min_tweets = frame['min']
            max_tweets = frame['max']
            
            if max_tweets == float('inf'):  # "X or more" case
                prob = 1 - stats.norm.cdf(min_tweets, loc=total_predicted, scale=std_estimate)
            else:
                prob_lower = stats.norm.cdf(min_tweets, loc=total_predicted, scale=std_estimate)
                prob_upper = stats.norm.cdf(max_tweets + 1, loc=total_predicted, scale=std_estimate)
                prob = prob_upper - prob_lower
            
            probabilities[frame_name] = max(0.001, prob)  # Minimum 0.1% probability
        
        # Normalize probabilities to sum to 1
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            probabilities = {k: v / total_prob for k, v in probabilities.items()}
        
        return probabilities
    
    def generate_predictions(self, current_time=None):
        """
        Generate complete prediction analysis.
        
        Args:
            current_time (datetime): Current time for prediction context
            
        Returns:
            dict: Complete prediction results
        """
        print("=== Neural Prophet Tweet Count Prediction ===")
        
        # Get prediction results
        prediction_results = self.predict_remaining_tweets(current_time)
        
        # Calculate probabilities
        probabilities = self.calculate_probabilities(prediction_results)
        
        # Get current week context
        week_data = self.data_processor.get_current_week_data(current_time)
        
        return {
            'model_type': 'Neural Prophet',
            'prediction_results': prediction_results,
            'probabilities': probabilities,
            'week_context': week_data,
            'predictions_by_frame': {
                frame: {'probability': prob, 'percentage': prob * 100}
                for frame, prob in probabilities.items()
            }
        }
    
    def print_prediction_summary(self, prediction_summary):
        """Print a formatted summary of predictions."""
        results = prediction_summary['prediction_results']
        probabilities = prediction_summary['probabilities']
        week_context = prediction_summary['week_context']
        
        print(f"\n=== NEURAL PROPHET PREDICTION SUMMARY ===")
        print(f"Current time: {week_context['current_time']}")
        print(f"Week period: {week_context['week_start']} to {week_context['week_end']}")
        print(f"Tweets posted so far: {results['current_tweets']}")
        print(f"Time remaining: {week_context['time_remaining']}")
        print(f"Days remaining: {results['days_remaining']}")
        
        print(f"\n=== PREDICTIONS ===")
        print(f"Remaining tweets: {results['remaining_tweets']:.1f}")
        print(f"Total predicted: {results['total_predicted']:.1f}")
        print(f"80% Confidence interval: {results['confidence_interval']['lower']:.1f} - {results['confidence_interval']['upper']:.1f}")
        
        print(f"\n=== ELON MUSK TWEET COUNT PREDICTIONS ===")
        print("=" * 70)
        print(f"Total predicted tweets: {results['total_predicted']:.1f}")
        print(f"80% Confidence interval: {results['confidence_interval']['lower']:.1f} - {results['confidence_interval']['upper']:.1f}")
        
        print(f"\nPROBABILITIES BY TIME FRAME:")
        print("-" * 50)
        
        # Sort by probability (highest first)
        sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
        
        for frame_name, probability in sorted_probs:
            percentage = probability * 100
            print(f"{frame_name:20s}: {probability:8.3f} ({percentage:5.1f}%)")
    
    def plot_predictions(self, prediction_summary, save=None):
        """
        Create visualization plots for the predictions.
        
        Args:
            prediction_summary (dict): Prediction results
            save (str): Optional filename to save plot
        """
        if not self.save_plots:
            return
            
        results = prediction_summary['prediction_results']
        forecast_data = results['full_forecast']
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Neural Prophet Tweet Count Predictions', fontsize=16, fontweight='bold')
        
        # Plot 1: Historical data and forecast
        ax1 = axes[0, 0]
        train_data = self.data_processor.get_neural_prophet_data()
        
        # Plot historical data
        ax1.plot(train_data['ds'], train_data['y'], 'o-', alpha=0.7, label='Historical', markersize=3)
        
        # Plot forecast
        future_data = forecast_data.tail(results['days_remaining'])
        ax1.plot(future_data['ds'], future_data['yhat1'], 'r-', linewidth=2, label='Forecast')
        
        # Add confidence intervals if available
        if 'yhat1 10.0%-ile' in forecast_data.columns:
            ax1.fill_between(future_data['ds'], 
                           future_data['yhat1 10.0%-ile'], 
                           future_data['yhat1 90.0%-ile'], 
                           alpha=0.3, color='red', label='80% CI')
        
        ax1.set_title('Tweet Count Forecast')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Tweet Count')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Probability distribution
        ax2 = axes[0, 1]
        probabilities = prediction_summary['probabilities']
        frames = list(probabilities.keys())
        probs = [probabilities[frame] * 100 for frame in frames]
        
        bars = ax2.bar(range(len(frames)), probs, alpha=0.7, color='skyblue', edgecolor='navy')
        ax2.set_title('Probability Distribution by Range')
        ax2.set_xlabel('Tweet Count Range')
        ax2.set_ylabel('Probability (%)')
        ax2.set_xticks(range(len(frames)))
        ax2.set_xticklabels(frames, rotation=45, ha='right')
        ax2.grid(True, alpha=0.3)
        
        # Add probability labels on bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
        
        # Plot 3: Recent trend (last 30 days)
        ax3 = axes[1, 0]
        recent_data = train_data.tail(30)
        ax3.plot(recent_data['ds'], recent_data['y'], 'o-', color='green', alpha=0.7)
        ax3.set_title('Recent 30-Day Trend')
        ax3.set_xlabel('Date')
        ax3.set_ylabel('Tweet Count')
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Prediction confidence
        ax4 = axes[1, 1]
        
        # Create confidence visualization
        total_pred = results['total_predicted']
        ci_lower = results['confidence_interval']['lower']
        ci_upper = results['confidence_interval']['upper']
        
        # Plot prediction point and confidence interval
        ax4.errorbar([0], [total_pred], 
                    yerr=[[total_pred - ci_lower], [ci_upper - total_pred]], 
                    fmt='ro', markersize=10, capsize=10, capthick=3, linewidth=3)
        
        ax4.set_xlim(-0.5, 0.5)
        ax4.set_ylim(ci_lower - 20, ci_upper + 20)
        ax4.set_title(f'Prediction: {total_pred:.1f} tweets')
        ax4.set_ylabel('Total Tweet Count')
        ax4.set_xticks([])
        ax4.grid(True, alpha=0.3)
        
        # Add text annotations
        ax4.text(0, ci_upper + 10, f'Upper: {ci_upper:.1f}', ha='center', fontweight='bold')
        ax4.text(0, ci_lower - 10, f'Lower: {ci_lower:.1f}', ha='center', fontweight='bold')
        
        plt.tight_layout()
        
        # Save plot
        if save:
            plt.savefig(save, dpi=300, bbox_inches='tight')
        elif self.save_plots:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.plots_dir / f"neural_prophet_prediction_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {filename}")
        
        plt.show() 