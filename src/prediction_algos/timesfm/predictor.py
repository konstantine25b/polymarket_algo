"""
TimesFM (Time Series Foundation Model) predictor for Elon Musk tweet counts.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    import timesfm
    TIMESFM_AVAILABLE = True
except ImportError:
    TIMESFM_AVAILABLE = False
    print("Warning: timesfm not available. Install with: pip install timesfm")

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


class TimesFMTweetPredictor:
    """TimesFM-based tweet count predictor."""
    
    def __init__(self, data_path=None, save_plots=True):
        """
        Initialize the TimesFM predictor.
        
        Args:
            data_path (str): Path to tweet data CSV file
            save_plots (bool): Whether to save prediction plots
        """
        self.data_processor = TweetDataProcessor(data_path)
        self.model = None
        self.save_plots = save_plots
        self.plots_dir = Path("src/prediction_algos/timesfm/plots")
        
        # Create plots directory
        if self.save_plots:
            self.plots_dir.mkdir(parents=True, exist_ok=True)
        
        # Check TimesFM availability
        if not TIMESFM_AVAILABLE:
            print("⚠️  TimesFM not available. Using mock predictor for testing.")
    
    def prepare_model(self, context_len=64, horizon_len=7, num_samples=100, 
                     quantiles=[0.1, 0.9], model_name="timesfm-1.0-200m"):
        """
        Prepare and initialize the TimesFM model.
        
        Args:
            context_len (int): Length of context window (default: 64 for normal mode)
            horizon_len (int): Number of steps to forecast ahead
            num_samples (int): Number of sampling iterations (default: 100)
            quantiles (list): Quantiles for confidence intervals
            model_name (str): TimesFM model variant to use
        """
        print("Preparing TimesFM foundation model...")
        
        # Determine mode based on context_len and num_samples
        if context_len <= 32 and num_samples <= 10:
            mode = "ULTRA-FAST"
            print(f"🚀 {mode} MODE: context_len={context_len}, samples={num_samples}")
        elif context_len <= 48 and num_samples <= 50:
            mode = "FAST"
            print(f"⚡ {mode} MODE: context_len={context_len}, samples={num_samples}")
        else:
            mode = "NORMAL"
            print(f"🔵 {mode} MODE: context_len={context_len}, samples={num_samples}")
        
        if TIMESFM_AVAILABLE:
            try:
                # Initialize TimesFM model
                self.model = timesfm.TimesFm(
                    context_len=context_len,
                    horizon_len=horizon_len,
                    input_patch_len=32,  # Standard patch length
                    output_patch_len=128,  # Standard output patch length
                    num_layers=20,  # Foundation model depth
                    model_dims=1280,  # Model dimensions
                    backend="gpu" if self._check_gpu() else "cpu"
                )
                
                # Load pre-trained weights
                self.model.load_from_checkpoint(repo_id=f"google/{model_name}")
                
                print(f"{mode} TimesFM model loaded successfully!")
                print(f"Model: {model_name}")
                print(f"Context length: {context_len} days")
                print(f"Forecast horizon: {horizon_len} days")
                print(f"Sampling iterations: {num_samples}")
                
            except Exception as e:
                print(f"Error loading TimesFM model: {e}")
                print("Falling back to mock predictor...")
                self.model = self._create_mock_model(context_len, horizon_len, num_samples)
        else:
            # Use mock model for testing when TimesFM not available
            self.model = self._create_mock_model(context_len, horizon_len, num_samples)
        
        self.context_len = context_len
        self.horizon_len = horizon_len
        self.num_samples = num_samples
        self.quantiles = quantiles
        
        return self.model
    
    def _check_gpu(self):
        """Check if GPU is available for acceleration."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def _create_mock_model(self, context_len, horizon_len, num_samples):
        """Create a mock model for testing when TimesFM is not available."""
        
        class MockTimesFM:
            def __init__(self, context_len, horizon_len, num_samples):
                self.context_len = context_len
                self.horizon_len = horizon_len
                self.num_samples = num_samples
            
            def forecast(self, inputs, num_samples=None):
                """Mock forecast using simple trend + seasonality."""
                time_series = inputs[0]  # First input
                samples = num_samples or self.num_samples
                
                # Calculate recent trend
                recent_values = time_series[-7:]  # Last week
                trend = np.mean(np.diff(recent_values)) if len(recent_values) > 1 else 0
                
                # Add weekly seasonality pattern (simplified)
                base_level = np.mean(time_series[-14:]) if len(time_series) >= 14 else np.mean(time_series)
                
                # Generate forecasts with some randomness
                forecasts = []
                for _ in range(samples):
                    forecast = []
                    current_level = base_level
                    
                    for day in range(self.horizon_len):
                        # Add trend
                        current_level += trend * 0.5  # Damped trend
                        
                        # Add weekly seasonality (simplified pattern)
                        weekly_factor = 1 + 0.2 * np.sin(2 * np.pi * day / 7)
                        
                        # Add noise
                        noise = np.random.normal(0, np.std(time_series[-30:]) * 0.3)
                        
                        predicted = max(0, current_level * weekly_factor + noise)
                        forecast.append(predicted)
                    
                    forecasts.append(forecast)
                
                return np.array(forecasts)  # Shape: (num_samples, horizon_len)
        
        return MockTimesFM(context_len, horizon_len, num_samples)
    
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
        
        # Calculate days remaining
        days_remaining = max(1, int(np.ceil(time_remaining.total_seconds() / (24 * 3600))))
        print(f"Days to forecast: {days_remaining}")
        
        # Prepare input data for TimesFM
        input_data = self.data_processor.prepare_timesfm_input(self.context_len)
        time_series = input_data['time_series']
        
        print(f"Using context of {len(time_series)} days for prediction")
        
        # Generate forecast using TimesFM
        if TIMESFM_AVAILABLE and hasattr(self.model, 'forecast'):
            # Real TimesFM API
            forecasts = self.model.forecast(
                inputs=[time_series.reshape(1, -1)],  # Batch format
                num_samples=self.num_samples
            )
            # forecasts shape: (num_samples, horizon_len)
            forecasts = forecasts[0]  # Remove batch dimension
        else:
            # Mock API
            forecasts = self.model.forecast(
                inputs=[time_series],
                num_samples=self.num_samples
            )
        
        # Take only the days we need
        if forecasts.shape[1] >= days_remaining:
            relevant_forecasts = forecasts[:, :days_remaining]
        else:
            # Extend if needed
            remaining_days = days_remaining - forecasts.shape[1]
            last_day_forecasts = forecasts[:, -1:]
            extension = np.repeat(last_day_forecasts, remaining_days, axis=1)
            relevant_forecasts = np.concatenate([forecasts, extension], axis=1)
        
        # Calculate statistics
        remaining_tweets = np.mean(np.sum(relevant_forecasts, axis=1))
        
        # Calculate confidence intervals using quantiles
        total_forecasts = np.sum(relevant_forecasts, axis=1)
        lower_bound = np.quantile(total_forecasts, self.quantiles[0])
        upper_bound = np.quantile(total_forecasts, self.quantiles[1])
        
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
            'forecast_samples': relevant_forecasts,
            'forecast_mean': np.mean(relevant_forecasts, axis=0),
            'forecast_std': np.std(relevant_forecasts, axis=0)
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
        print("=== TimesFM Tweet Count Prediction ===")
        
        # Get prediction results
        prediction_results = self.predict_remaining_tweets(current_time)
        
        # Calculate probabilities
        probabilities = self.calculate_probabilities(prediction_results)
        
        # Get current week context
        week_data = self.data_processor.get_current_week_data(current_time)
        
        return {
            'model_type': 'TimesFM Foundation Model',
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
        
        print(f"\n=== TIMESFM PREDICTION SUMMARY ===")
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
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('TimesFM Tweet Count Predictions', fontsize=16, fontweight='bold')
        
        # Plot 1: Historical data and forecast
        ax1 = axes[0, 0]
        time_series, timestamps = self.data_processor.get_timesfm_data()
        
        # Plot recent historical data (last 60 days)
        recent_data = time_series[-60:]
        recent_timestamps = timestamps[-60:]
        ax1.plot(recent_timestamps, recent_data, 'o-', alpha=0.7, label='Historical', markersize=3)
        
        # Plot forecast
        forecast_mean = results['forecast_mean']
        forecast_std = results['forecast_std']
        
        # Create future timestamps
        last_date = timestamps.iloc[-1]
        future_dates = pd.date_range(start=last_date + timedelta(days=1), 
                                   periods=len(forecast_mean), freq='D')
        
        ax1.plot(future_dates, forecast_mean, 'r-', linewidth=2, label='Forecast')
        
        # Add confidence bands
        lower_band = forecast_mean - 1.645 * forecast_std
        upper_band = forecast_mean + 1.645 * forecast_std
        ax1.fill_between(future_dates, lower_band, upper_band, 
                        alpha=0.3, color='red', label='90% CI')
        
        ax1.set_title('Tweet Count Forecast (TimesFM)')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Tweet Count')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Probability distribution
        ax2 = axes[0, 1]
        probabilities = prediction_summary['probabilities']
        frames = list(probabilities.keys())
        probs = [probabilities[frame] * 100 for frame in frames]
        
        bars = ax2.bar(range(len(frames)), probs, alpha=0.7, color='lightcoral', edgecolor='darkred')
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
        
        # Plot 3: Forecast uncertainty (samples distribution)
        ax3 = axes[1, 0]
        forecast_samples = results['forecast_samples']
        total_samples = np.sum(forecast_samples, axis=1)
        
        ax3.hist(total_samples, bins=20, alpha=0.7, color='coral', edgecolor='darkred')
        ax3.axvline(np.mean(total_samples), color='red', linestyle='--', linewidth=2, 
                   label=f'Mean: {np.mean(total_samples):.1f}')
        ax3.set_title('Forecast Distribution (Foundation Model Samples)')
        ax3.set_xlabel('Remaining Tweets')
        ax3.set_ylabel('Frequency')
        ax3.legend()
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
            filename = self.plots_dir / f"timesfm_prediction_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {filename}")
        
        plt.show() 