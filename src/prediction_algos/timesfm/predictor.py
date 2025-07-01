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
    print("✅ TimesFM library available")
except ImportError:
    TIMESFM_AVAILABLE = False
    print("⚠️ Warning: timesfm not available. Install with: pip install timesfm")

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
        self.data_path = data_path
        self.save_plots = save_plots
        self.random_seed = 42  # Default seed
        self.model = None
        self.context_len = None
        self.horizon_len = None
        self.num_samples = None
        self.quantiles = None
        self.is_real_model = False  # Track if using real or mock model
        
        # Initialize data processor
        self.data_processor = TweetDataProcessor(data_path)
        
        # Setup plots directory
        self.plots_dir = Path("src/prediction_algos/timesfm/plots")
        if self.save_plots:
            self.plots_dir.mkdir(parents=True, exist_ok=True)
        
        # Check TimesFM availability
        if not TIMESFM_AVAILABLE:
            print("⚠️  TimesFM not available. Using mock predictor for testing.")
    
    def set_random_seed(self, seed):
        """Set random seed for reproducible results."""
        self.random_seed = seed
    
    def prepare_model(self, context_len=64, horizon_len=7, num_samples=100, 
                     quantiles=[0.1, 0.9], model_name="timesfm-1.0-200m-pytorch"):
        """
        Prepare and initialize the TimesFM model.
        
        Args:
            context_len (int): Length of context window (must be <= 512 for 1.0 models, <= 2048 for 2.0 models)
            horizon_len (int): Number of steps to forecast ahead
            num_samples (int): Number of sampling iterations (not used in real model, kept for compatibility)
            quantiles (list): Quantiles for confidence intervals
            model_name (str): TimesFM model variant to use
        """
        print("Preparing TimesFM foundation model...")
        
        # Ensure context_len is multiple of input_patch_len (32)
        context_len = max(32, (context_len // 32) * 32)
        
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
                # Determine model parameters based on model name
                if "2.0" in model_name:
                    max_context = 2048
                    num_layers = 50
                    model_dims = 1280
                    use_positional_embedding = False
                else:
                    max_context = 512
                    num_layers = 20
                    model_dims = 1280
                    use_positional_embedding = True
                
                # Ensure context_len doesn't exceed model limits
                context_len = min(context_len, max_context)
                
                # Create TimesFM model with correct modern API
                hparams = timesfm.TimesFmHparams(
                    backend="gpu" if self._check_gpu() else "cpu",
                    per_core_batch_size=1,  # Set to 1 for single predictions
                    horizon_len=horizon_len,
                    context_len=context_len,
                )
                
                # Add model-specific parameters for 2.0 models
                if "2.0" in model_name:
                    hparams.num_layers = num_layers
                    hparams.use_positional_embedding = use_positional_embedding
                
                checkpoint = timesfm.TimesFmCheckpoint(
                    huggingface_repo_id=f"google/{model_name}"
                )
                
                self.model = timesfm.TimesFm(
                    hparams=hparams,
                    checkpoint=checkpoint
                )
                
                self.is_real_model = True
                print(f"✅ {mode} TimesFM model loaded successfully!")
                print(f"Model: {model_name}")
                print(f"Context length: {context_len} days")
                print(f"Forecast horizon: {horizon_len} days")
                print(f"Backend: {'GPU' if self._check_gpu() else 'CPU'}")
                print(f"Available quantiles: {self.model.quantiles}")
                
            except Exception as e:
                print(f"❌ Error loading TimesFM model: {e}")
                print("Falling back to mock predictor...")
                self.model = self._create_mock_model(context_len, horizon_len, num_samples)
                self.is_real_model = False
        else:
            # Use mock model for testing when TimesFM not available
            self.model = self._create_mock_model(context_len, horizon_len, num_samples)
            self.is_real_model = False
        
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
            def __init__(self, context_len, horizon_len, num_samples, base_seed):
                self.context_len = context_len
                self.horizon_len = horizon_len
                self.num_samples = num_samples
                # Use the seed from the parent predictor instance
                self.base_seed = base_seed
            
            def forecast(self, inputs, freq=None, **kwargs):
                """Mock forecast using simple trend + seasonality."""
                time_series = inputs[0]  # First input
                
                # Set random seed for reproducible results
                # Use context_len and horizon_len as part of seed for different model configs
                seed = self.base_seed + self.context_len + self.horizon_len
                np.random.seed(seed)
                
                # Calculate recent trend
                recent_values = time_series[-7:]  # Last week
                trend = np.mean(np.diff(recent_values)) if len(recent_values) > 1 else 0
                
                # Add weekly seasonality pattern (simplified)
                base_level = np.mean(time_series[-14:]) if len(time_series) >= 14 else np.mean(time_series)
                
                # Generate mean forecast
                mean_forecast = []
                current_level = base_level
                
                for day in range(self.horizon_len):
                    # Add trend
                    current_level += trend * 0.5  # Damped trend
                    
                    # Add weekly seasonality (simplified pattern)
                    weekly_factor = 1 + 0.2 * np.sin(2 * np.pi * day / 7)
                    
                    # Add controlled noise
                    noise_std = np.std(time_series[-30:]) * 0.1 if len(time_series) >= 30 else 1.0
                    noise = np.random.normal(0, noise_std)
                    
                    predicted = max(0, current_level * weekly_factor + noise)
                    mean_forecast.append(predicted)
                
                mean_forecast = np.array(mean_forecast).reshape(1, -1)  # Shape: (1, horizon_len)
                
                # Generate quantile forecasts (mock)
                quantiles = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
                full_forecast = np.zeros((1, self.horizon_len, 1 + len(quantiles)))
                
                # Add mean as first channel
                full_forecast[:, :, 0] = mean_forecast
                
                # Add quantiles with some spread
                std_dev = np.std(time_series[-30:]) * 0.3 if len(time_series) >= 30 else 1.0
                for i, q in enumerate(quantiles):
                    # Use normal distribution quantiles
                    quantile_values = mean_forecast + stats.norm.ppf(q) * std_dev
                    full_forecast[:, :, i + 1] = np.maximum(0, quantile_values)
                
                return mean_forecast, full_forecast
        
        return MockTimesFM(context_len, horizon_len, num_samples, self.random_seed)
    
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
        total_hours_remaining = time_remaining.total_seconds() / 3600
        
        # If less than 1 hour remaining, use fractional day calculation
        if total_hours_remaining < 1:
            # Use fractional day for very short time periods
            days_remaining_exact = time_remaining.total_seconds() / (24 * 3600)
            days_remaining = max(0.01, days_remaining_exact)  # Minimum 0.01 days (14.4 minutes)
            print(f"Time remaining: {total_hours_remaining:.2f} hours ({days_remaining:.3f} days)")
        else:
            # Use the original calculation for longer periods
            days_remaining = max(1, int(np.ceil(time_remaining.total_seconds() / (24 * 3600))))
            print(f"Time remaining: {total_hours_remaining:.2f} hours")
        
        print(f"Days to forecast: {days_remaining}")
        
        # Prepare input data for TimesFM
        input_data = self.data_processor.prepare_timesfm_input(self.context_len)
        time_series = input_data['time_series']
        
        print(f"Using context of {len(time_series)} days for prediction")
        
        # Generate forecast using TimesFM
        try:
            if self.is_real_model:
                # Real TimesFM API returns (mean_forecast, quantile_forecast)
                mean_forecast, quantile_forecast = self.model.forecast(
                    inputs=[time_series],  # List of time series
                    freq=[0]  # High frequency (daily data)
                )
                
                # mean_forecast shape: (1, horizon_len)
                # quantile_forecast shape: (1, horizon_len, num_quantiles)
                
                print(f"🔥 Real TimesFM model used!")
                print(f"Mean forecast shape: {mean_forecast.shape}")
                print(f"Quantile forecast shape: {quantile_forecast.shape}")
                
                # Extract forecasts
                forecasts = mean_forecast[0]  # Remove batch dimension
                
                # Extract quantiles for confidence intervals
                # quantile_forecast contains quantiles directly
                quantile_forecasts = quantile_forecast[0]  # Shape: (horizon_len, num_quantiles)
                
            else:
                # Mock API
                mean_forecast, full_forecast = self.model.forecast(
                    inputs=[time_series]
                )
                
                print(f"🤖 Mock model used (TimesFM not available)")
                print(f"Mean forecast shape: {mean_forecast.shape}")
                print(f"Full forecast shape: {full_forecast.shape}")
                
                forecasts = mean_forecast[0]  # Remove batch dimension
                quantile_forecasts = full_forecast[0, :, 1:]  # Shape: (horizon_len, num_quantiles)
            
            # Take only the days we need and handle fractional days
            if days_remaining < 1:
                # For fractional days, take the first day's forecast and scale it
                if len(forecasts) >= 1:
                    single_day_forecast = forecasts[0]
                    # Scale by the fraction of day remaining
                    remaining_tweets = single_day_forecast * days_remaining
                    
                    # Handle confidence intervals for fractional days
                    if quantile_forecasts.shape[0] >= 1 and quantile_forecasts.shape[1] >= 2:
                        # Real TimesFM: quantiles include mean, use 10th and 90th percentiles
                        if self.is_real_model:
                            # In real TimesFM, quantiles: [0.1, 0.2, 0.3, 0.4, 0.5(mean), 0.6, 0.7, 0.8, 0.9] + mean
                            # So 10th percentile is index 0, 90th percentile is index 8
                            lower_quantile = quantile_forecasts[0, 0] * days_remaining  # 10th percentile
                            upper_quantile = quantile_forecasts[0, 8] * days_remaining  # 90th percentile
                        else:
                            # Mock model format
                            lower_quantile = quantile_forecasts[0, 0] * days_remaining  # 10th percentile
                            upper_quantile = quantile_forecasts[0, 8] * days_remaining  # 90th percentile
                    else:
                        # Fallback to mean +/- std
                        std_estimate = forecasts[0] * 0.3
                        lower_quantile = max(0, remaining_tweets - std_estimate)
                        upper_quantile = remaining_tweets + std_estimate
                else:
                    # Fallback if no forecast available
                    remaining_tweets = 0
                    lower_quantile = 0
                    upper_quantile = 0
            else:
                # Handle full days as before
                days_remaining_int = int(np.ceil(days_remaining))
                if len(forecasts) >= days_remaining_int:
                    relevant_forecasts = forecasts[:days_remaining_int]
                    relevant_quantiles = quantile_forecasts[:days_remaining_int, :]
                else:
                    # Extend if needed
                    remaining_days = days_remaining_int - len(forecasts)
                    last_day_forecast = forecasts[-1] if len(forecasts) > 0 else 0
                    
                    # Handle quantiles shape properly
                    if quantile_forecasts.shape[0] > 0:
                        last_day_quantiles = quantile_forecasts[-1, :]
                    else:
                        # Create appropriate size based on real/mock model
                        q_size = 10 if self.is_real_model else 9
                        last_day_quantiles = np.zeros(q_size)
                    
                    # Extend with last day values
                    extension_forecasts = np.full(remaining_days, last_day_forecast)
                    extension_quantiles = np.tile(last_day_quantiles, (remaining_days, 1))
                    
                    relevant_forecasts = np.concatenate([forecasts, extension_forecasts])
                    relevant_quantiles = np.vstack([quantile_forecasts, extension_quantiles])
                
                # Sum across days
                remaining_tweets = np.sum(relevant_forecasts)
                
                # Sum quantiles across days for confidence intervals
                if relevant_quantiles.shape[1] >= 9:  # Ensure we have enough quantiles
                    if self.is_real_model:
                        # Real TimesFM: use indices 0 and 8 for 10th and 90th percentiles
                        lower_quantile = np.sum(relevant_quantiles[:, 0])  # 10th percentile
                        upper_quantile = np.sum(relevant_quantiles[:, 8])  # 90th percentile
                    else:
                        # Mock model: use indices 0 and 8
                        lower_quantile = np.sum(relevant_quantiles[:, 0])  # 10th percentile
                        upper_quantile = np.sum(relevant_quantiles[:, 8])  # 90th percentile
                else:
                    # Fallback to mean +/- std
                    std_estimate = remaining_tweets * 0.3
                    lower_quantile = max(0, remaining_tweets - std_estimate)
                    upper_quantile = remaining_tweets + std_estimate
            
            # Calculate total predictions
            total_predicted = current_tweets + remaining_tweets
            total_lower = current_tweets + lower_quantile
            total_upper = current_tweets + upper_quantile
            
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
                'forecast_mean': forecasts,
                'forecast_quantiles': quantile_forecasts,
                'model_type': 'Real TimesFM' if self.is_real_model else 'Mock TimesFM'
            }
            
        except Exception as e:
            print(f"❌ Error in forecast generation: {e}")
            print("Falling back to simple prediction...")
            
            # Simple fallback prediction
            recent_avg = np.mean(time_series[-7:]) if len(time_series) >= 7 else np.mean(time_series)
            remaining_tweets = recent_avg * days_remaining
            
            total_predicted = current_tweets + remaining_tweets
            std_estimate = remaining_tweets * 0.3
            
            return {
                'remaining_tweets': remaining_tweets,
                'total_predicted': total_predicted,
                'confidence_interval': {
                    'lower': max(0, total_predicted - std_estimate),
                    'upper': total_predicted + std_estimate,
                    'width': 2 * std_estimate
                },
                'days_remaining': days_remaining,
                'current_tweets': current_tweets,
                'forecast_mean': np.full(int(days_remaining), recent_avg),
                'forecast_quantiles': None,
                'model_type': 'Fallback'
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
        current_tweets = prediction_results['current_tweets']
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
            
            # If the frame's maximum is less than current tweets, it's impossible
            if max_tweets != float('inf') and max_tweets < current_tweets:
                prob = 0.0
            elif max_tweets == float('inf'):  # "X or more" case
                prob = 1 - stats.norm.cdf(min_tweets, loc=total_predicted, scale=std_estimate)
            else:
                prob_lower = stats.norm.cdf(min_tweets, loc=total_predicted, scale=std_estimate)
                prob_upper = stats.norm.cdf(max_tweets + 1, loc=total_predicted, scale=std_estimate)
                prob = prob_upper - prob_lower
            
            # Only apply minimum probability for non-impossible frames
            if max_tweets == float('inf') or max_tweets >= current_tweets:
                probabilities[frame_name] = max(0.001, prob)  # Minimum 0.1% probability for possible frames
            else:
                probabilities[frame_name] = 0.0  # 0% for impossible frames
        
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
        fig.suptitle(f'TimesFM Tweet Count Predictions ({results["model_type"]})', fontsize=16, fontweight='bold')
        
        # Plot 1: Historical data and forecast
        ax1 = axes[0, 0]
        time_series, timestamps = self.data_processor.get_timesfm_data()
        
        # Plot recent historical data (last 60 days)
        recent_data = time_series[-60:]
        recent_timestamps = timestamps[-60:]
        ax1.plot(recent_timestamps, recent_data, 'o-', alpha=0.7, label='Historical', markersize=3)
        
        # Plot forecast
        forecast_mean = results['forecast_mean']
        forecast_quantiles = results.get('forecast_quantiles')
        
        # Create future timestamps
        last_date = timestamps.iloc[-1]
        future_dates = pd.date_range(start=last_date + timedelta(days=1), 
                                   periods=len(forecast_mean), freq='D')
        
        ax1.plot(future_dates, forecast_mean, 'r-', linewidth=2, label='Forecast')
        
        # Add confidence bands if quantiles are available
        if forecast_quantiles is not None and forecast_quantiles.shape[1] >= 9:
            # Use 10th and 90th percentiles for 80% confidence interval
            lower_band = forecast_quantiles[:, 0]  # 10th percentile
            upper_band = forecast_quantiles[:, 8]  # 90th percentile
            ax1.fill_between(future_dates, lower_band, upper_band, 
                            alpha=0.3, color='red', label='80% CI')
        else:
            # Fallback: use simple std-based confidence bands
            std_estimate = np.std(forecast_mean) if len(forecast_mean) > 1 else forecast_mean[0] * 0.3
            lower_band = forecast_mean - std_estimate
            upper_band = forecast_mean + std_estimate
            ax1.fill_between(future_dates, lower_band, upper_band, 
                            alpha=0.3, color='red', label='Est. 80% CI')
        
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
        
        # Plot 3: Forecast uncertainty
        ax3 = axes[1, 0]
        
        if forecast_quantiles is not None and forecast_quantiles.shape[1] >= 9:
            # Use quantiles to show distribution
            median_forecast = forecast_quantiles[:, 4]  # 50th percentile (median)
            q25_forecast = forecast_quantiles[:, 1]     # 20th percentile
            q75_forecast = forecast_quantiles[:, 7]     # 80th percentile
            
            # Create a simple distribution plot
            total_median = np.sum(median_forecast)
            total_q25 = np.sum(q25_forecast)
            total_q75 = np.sum(q75_forecast)
            
            # Generate mock samples based on quantiles
            samples = np.random.normal(total_median, (total_q75 - total_q25) / 1.35, 1000)
            samples = np.maximum(0, samples)  # Ensure non-negative
            
            ax3.hist(samples, bins=20, alpha=0.7, color='coral', edgecolor='darkred')
            ax3.axvline(total_median, color='red', linestyle='--', linewidth=2, 
                       label=f'Median: {total_median:.1f}')
            ax3.set_title('Forecast Distribution (Est. from Quantiles)')
        else:
            # Fallback: show simple statistics
            total_pred = results['total_predicted']
            ci_width = results['confidence_interval']['width']
            
            # Generate mock samples
            samples = np.random.normal(total_pred, ci_width / 3.29, 1000)  # 3.29 for 80% CI
            samples = np.maximum(0, samples)
            
            ax3.hist(samples, bins=20, alpha=0.7, color='coral', edgecolor='darkred')
            ax3.axvline(total_pred, color='red', linestyle='--', linewidth=2, 
                       label=f'Mean: {total_pred:.1f}')
            ax3.set_title('Forecast Distribution (Est. from CI)')
        
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
        ax4.set_ylim(max(0, ci_lower - 20), ci_upper + 20)
        ax4.set_title(f'Prediction: {total_pred:.1f} tweets')
        ax4.set_ylabel('Total Tweet Count')
        ax4.set_xticks([])
        ax4.grid(True, alpha=0.3)
        
        # Add text annotations
        ax4.text(0, ci_upper + 5, f'Upper: {ci_upper:.1f}', ha='center', fontweight='bold')
        ax4.text(0, max(5, ci_lower - 5), f'Lower: {ci_lower:.1f}', ha='center', fontweight='bold')
        
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