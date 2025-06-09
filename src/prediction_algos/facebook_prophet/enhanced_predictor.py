"""
Enhanced predictor with improved forecasting methods for Elon Musk tweet counts.
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
from scipy import stats
from scipy.special import erf
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants import TWEET_COUNT_FRAMES, ET_TIMEZONE

from .data_processor import TweetDataProcessor


class EnhancedTweetPredictor:
    """Enhanced tweet count predictor with multiple forecasting approaches."""
    
    def __init__(self, data_path=None, save_plots=True):
        """
        Initialize the enhanced predictor.
        
        Args:
            data_path (str): Path to tweet data CSV file
            save_plots (bool): Whether to save prediction plots
        """
        self.data_processor = TweetDataProcessor(data_path)
        self.daily_model = None
        self.hourly_model = None
        self.rf_model = None
        self.save_plots = save_plots
        self.plots_dir = Path("src/facebook_prophet/plots")
        
        # Create plots directory
        if self.save_plots:
            self.plots_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_hourly_data(self):
        """Prepare hourly tweet data for more granular predictions."""
        if self.data_processor.raw_data is None:
            self.data_processor.load_data()
        
        # Parse timestamps
        self.data_processor.raw_data['parsed_timestamp'] = self.data_processor.raw_data['created_at'].apply(
            self.data_processor.parse_timestamp
        )
        
        # Remove invalid timestamps
        valid_data = self.data_processor.raw_data.dropna(subset=['parsed_timestamp'])
        
        # Handle timezone-aware operations with ambiguous times
        try:
            # Try to floor to hour bins directly
            valid_data['hour_bin'] = valid_data['parsed_timestamp'].dt.floor('H')
        except Exception as e:
            print(f"Handling timezone ambiguity: {e}")
            # Convert to UTC first to avoid DST issues, then back to ET
            valid_data['utc_timestamp'] = valid_data['parsed_timestamp'].dt.tz_convert('UTC')
            valid_data['hour_bin'] = valid_data['utc_timestamp'].dt.floor('H').dt.tz_convert(ET_TIMEZONE)
        
        hourly_counts = valid_data.groupby('hour_bin').size().reset_index(name='tweet_count')
        
        # Rename for Prophet and remove timezone (Prophet doesn't support timezone-aware data)
        hourly_counts['ds'] = hourly_counts['hour_bin'].dt.tz_localize(None)
        hourly_counts['y'] = hourly_counts['tweet_count']
        
        # Fill missing hours with 0
        start_time = hourly_counts['ds'].min()
        end_time = hourly_counts['ds'].max()
        
        # Create timezone-naive date range
        all_hours = pd.date_range(start=start_time, end=end_time, freq='H')
        
        full_hourly = pd.DataFrame({'ds': all_hours})
        full_hourly = full_hourly.merge(hourly_counts[['ds', 'y']], on='ds', how='left')
        full_hourly['y'] = full_hourly['y'].fillna(0)
        
        return full_hourly[['ds', 'y']]
    
    def analyze_recent_patterns(self, days_back=7):
        """Analyze recent tweeting patterns for trend detection."""
        if self.data_processor.raw_data is None:
            self.data_processor.load_data()
        
        # Get recent data
        cutoff_date = datetime.now(ET_TIMEZONE) - timedelta(days=days_back)
        self.data_processor.raw_data['parsed_timestamp'] = self.data_processor.raw_data['created_at'].apply(
            self.data_processor.parse_timestamp
        )
        
        recent_data = self.data_processor.raw_data[
            self.data_processor.raw_data['parsed_timestamp'] >= cutoff_date
        ].copy()
        
        if len(recent_data) == 0:
            return None
        
        # Daily counts for recent period
        recent_data['date'] = recent_data['parsed_timestamp'].dt.date
        daily_recent = recent_data.groupby('date').size()
        
        # Hourly patterns
        recent_data['hour'] = recent_data['parsed_timestamp'].dt.hour
        hourly_patterns = recent_data.groupby('hour').size()
        
        return {
            'daily_recent': daily_recent,
            'hourly_patterns': hourly_patterns,
            'avg_daily': daily_recent.mean(),
            'std_daily': daily_recent.std(),
            'total_recent': len(recent_data)
        }
    
    def prepare_models(self):
        """Prepare multiple forecasting models."""
        print("Preparing enhanced forecasting models...")
        
        # 1. Daily Prophet model (baseline)
        daily_data = self.data_processor.get_prophet_data()
        self.daily_model = Prophet(
            changepoint_prior_scale=0.1,
            seasonality_prior_scale=20.0,
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
            interval_width=0.8
        )
        self.daily_model.fit(daily_data)
        
        # 2. Hourly Prophet model
        hourly_data = self.prepare_hourly_data()
        print(f"Training hourly model with {len(hourly_data)} hours of data...")
        
        self.hourly_model = Prophet(
            changepoint_prior_scale=0.15,
            seasonality_prior_scale=10.0,
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False,  # Less relevant for hourly data
            interval_width=0.8
        )
        
        # Add custom seasonalities for hourly model
        self.hourly_model.add_seasonality(name='hourly', period=24, fourier_order=8)
        self.hourly_model.fit(hourly_data)
        
        # 3. Random Forest model for ensemble
        self.prepare_rf_model(daily_data)
        
        print("All models prepared successfully!")
    
    def prepare_rf_model(self, daily_data):
        """Prepare Random Forest model with engineered features."""
        # Create features
        df = daily_data.copy()
        df['dayofweek'] = df['ds'].dt.dayofweek
        df['month'] = df['ds'].dt.month
        df['day'] = df['ds'].dt.day
        df['is_weekend'] = (df['dayofweek'] >= 5).astype(int)
        
        # Rolling averages
        df['ma_7'] = df['y'].rolling(7, min_periods=1).mean()
        df['ma_30'] = df['y'].rolling(30, min_periods=1).mean()
        
        # Lag features
        df['lag_1'] = df['y'].shift(1)
        df['lag_7'] = df['y'].shift(7)
        
        # Remove NaN rows
        df = df.dropna()
        
        if len(df) < 50:  # Need sufficient data
            self.rf_model = None
            return
        
        # Features and target
        feature_cols = ['dayofweek', 'month', 'day', 'is_weekend', 'ma_7', 'ma_30', 'lag_1', 'lag_7']
        X = df[feature_cols]
        y = df['y']
        
        # Train Random Forest
        self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.rf_model.fit(X, y)
        
        # Calculate model performance
        y_pred = self.rf_model.predict(X)
        mae = mean_absolute_error(y, y_pred)
        print(f"Random Forest MAE: {mae:.2f}")
    
    def predict_remaining_tweets_enhanced(self, current_time):
        """Enhanced prediction using multiple models and methods."""
        week_data = self.data_processor.get_current_week_data(current_time)
        
        if week_data['time_remaining'].total_seconds() <= 0:
            return {
                'prophet_daily': 0,
                'prophet_hourly': 0,
                'random_forest': 0,
                'pattern_based': 0,
                'ensemble': 0,
                'confidence_interval': (0, 0)
            }
        
        remaining_hours = week_data['time_remaining'].total_seconds() / 3600
        remaining_days = remaining_hours / 24
        
        predictions = {}
        
        # 1. Daily Prophet prediction
        daily_future = self.daily_model.make_future_dataframe(periods=int(np.ceil(remaining_days)))
        daily_forecast = self.daily_model.predict(daily_future)
        daily_pred = daily_forecast.iloc[-1]['yhat'] * remaining_days
        predictions['prophet_daily'] = max(0, daily_pred)
        
        # 2. Hourly Prophet prediction
        hourly_future = self.hourly_model.make_future_dataframe(periods=int(np.ceil(remaining_hours)), freq='H')
        hourly_forecast = self.hourly_model.predict(hourly_future)
        
        # Convert timezone-aware times to naive for comparison with Prophet data
        if hasattr(current_time, 'tz_localize'):
            # pandas Timestamp
            remaining_start_naive = current_time.tz_localize(None) if current_time.tzinfo is None else current_time.tz_convert('UTC').tz_localize(None)
        else:
            # datetime object
            remaining_start_naive = current_time.replace(tzinfo=None) if current_time.tzinfo is not None else current_time
        
        if hasattr(week_data['week_end'], 'tz_localize'):
            # pandas Timestamp
            remaining_end_naive = week_data['week_end'].tz_localize(None) if week_data['week_end'].tzinfo is None else week_data['week_end'].tz_convert('UTC').tz_localize(None)
        else:
            # datetime object
            remaining_end_naive = week_data['week_end'].replace(tzinfo=None) if week_data['week_end'].tzinfo is not None else week_data['week_end']
        
        # Filter hourly predictions for remaining period
        hourly_remaining = hourly_forecast[
            (hourly_forecast['ds'] >= remaining_start_naive) & 
            (hourly_forecast['ds'] <= remaining_end_naive)
        ]
        hourly_pred = hourly_remaining['yhat'].sum()
        predictions['prophet_hourly'] = max(0, hourly_pred)
        
        # 3. Pattern-based prediction using recent data
        recent_patterns = self.analyze_recent_patterns(days_back=14)
        if recent_patterns:
            # Use recent average scaled by remaining time
            pattern_pred = recent_patterns['avg_daily'] * remaining_days
            predictions['pattern_based'] = max(0, pattern_pred)
        else:
            predictions['pattern_based'] = predictions['prophet_daily']
        
        # 4. Random Forest prediction (if available)
        if self.rf_model is not None:
            try:
                # Create features for prediction
                pred_date = current_time + timedelta(days=remaining_days/2)  # Mid-point
                features = np.array([[
                    pred_date.weekday(),  # dayofweek
                    pred_date.month,      # month
                    pred_date.day,        # day
                    1 if pred_date.weekday() >= 5 else 0,  # is_weekend
                    recent_patterns['avg_daily'] if recent_patterns else 40,  # ma_7 approx
                    40,  # ma_30 approx
                    recent_patterns['avg_daily'] if recent_patterns else 40,  # lag_1 approx
                    40   # lag_7 approx
                ]])
                
                rf_pred = self.rf_model.predict(features)[0] * remaining_days
                predictions['random_forest'] = max(0, rf_pred)
            except:
                predictions['random_forest'] = predictions['prophet_daily']
        else:
            predictions['random_forest'] = predictions['prophet_daily']
        
        # 5. Ensemble prediction (weighted average)
        weights = {
            'prophet_daily': 0.3,
            'prophet_hourly': 0.4,  # Give more weight to hourly model
            'pattern_based': 0.2,
            'random_forest': 0.1
        }
        
        ensemble_pred = sum(predictions[model] * weight for model, weight in weights.items())
        predictions['ensemble'] = ensemble_pred
        
        # Calculate confidence interval using prediction variance
        pred_values = list(predictions.values())
        pred_std = np.std(pred_values)
        lower_bound = ensemble_pred - 1.96 * pred_std
        upper_bound = ensemble_pred + 1.96 * pred_std
        
        predictions['confidence_interval'] = (max(0, lower_bound), upper_bound)
        
        return predictions
    
    def calculate_enhanced_probabilities(self, current_tweets, remaining_predictions):
        """Calculate probabilities using mixture of distributions."""
        total_predicted = current_tweets + remaining_predictions['ensemble']
        lower_bound, upper_bound = remaining_predictions['confidence_interval']
        total_lower = current_tweets + lower_bound
        total_upper = current_tweets + upper_bound
        
        # Use different distribution types for better modeling
        predictions_list = [
            remaining_predictions['prophet_daily'],
            remaining_predictions['prophet_hourly'], 
            remaining_predictions['pattern_based'],
            remaining_predictions['random_forest']
        ]
        
        # Fit gamma distribution to the predictions (better for count data)
        pred_array = np.array([current_tweets + p for p in predictions_list])
        pred_array = pred_array[pred_array > 0]  # Gamma distribution needs positive values
        
        if len(pred_array) > 1:
            try:
                # Fit gamma distribution
                alpha, loc, scale = stats.gamma.fit(pred_array, floc=0)
                
                # Calculate probabilities using gamma distribution
                probabilities = {}
                for frame in TWEET_COUNT_FRAMES:
                    frame_name = frame['name']
                    min_tweets = frame['min']
                    max_tweets = frame['max']
                    
                    if max_tweets == float('inf'):
                        prob = 1 - stats.gamma.cdf(min_tweets - 0.5, alpha, scale=scale)
                    else:
                        prob_lower = stats.gamma.cdf(min_tweets - 0.5, alpha, scale=scale)
                        prob_upper = stats.gamma.cdf(max_tweets + 0.5, alpha, scale=scale)
                        prob = prob_upper - prob_lower
                    
                    probabilities[frame_name] = {
                        'probability': max(0, min(1, prob)),
                        'range': f"{min_tweets}-{max_tweets}" if max_tweets != float('inf') else f"{min_tweets}+",
                        'min': min_tweets,
                        'max': max_tweets
                    }
                
            except:
                # Fallback to normal distribution
                probabilities = self._fallback_normal_probabilities(total_predicted, total_lower, total_upper)
        else:
            # Fallback to normal distribution
            probabilities = self._fallback_normal_probabilities(total_predicted, total_lower, total_upper)
        
        # Normalize probabilities
        total_prob = sum(pred['probability'] for pred in probabilities.values())
        if total_prob > 0:
            for frame_name in probabilities:
                probabilities[frame_name]['probability'] /= total_prob
        
        return probabilities
    
    def _fallback_normal_probabilities(self, total_predicted, total_lower, total_upper):
        """Fallback normal distribution probability calculation."""
        std_dev = (total_upper - total_lower) / 4
        
        probabilities = {}
        for frame in TWEET_COUNT_FRAMES:
            frame_name = frame['name']
            min_tweets = frame['min']
            max_tweets = frame['max']
            
            if max_tweets == float('inf'):
                prob = 1 - self._normal_cdf(min_tweets - 0.5, total_predicted, std_dev)
            else:
                prob_lower = self._normal_cdf(min_tweets - 0.5, total_predicted, std_dev)
                prob_upper = self._normal_cdf(max_tweets + 0.5, total_predicted, std_dev)
                prob = prob_upper - prob_lower
            
            probabilities[frame_name] = {
                'probability': max(0, min(1, prob)),
                'range': f"{min_tweets}-{max_tweets}" if max_tweets != float('inf') else f"{min_tweets}+",
                'min': min_tweets,
                'max': max_tweets
            }
        
        return probabilities
    
    def _normal_cdf(self, x, mean, std):
        """Calculate cumulative distribution function of normal distribution."""
        if std <= 0:
            return 1.0 if x >= mean else 0.0
        return 0.5 * (1 + erf((x - mean) / (std * np.sqrt(2))))
    
    def generate_enhanced_predictions(self, current_time=None):
        """Generate enhanced predictions using multiple models."""
        if any(model is None for model in [self.daily_model, self.hourly_model]):
            self.prepare_models()
        
        week_data = self.data_processor.get_current_week_data(current_time)
        current_tweets = week_data['current_week_tweets']
        
        print(f"\n=== Enhanced Prediction Analysis ===")
        print(f"Current time: {week_data['current_time']}")
        print(f"Week period: {week_data['week_start']} to {week_data['week_end']}")
        print(f"Tweets posted so far: {current_tweets}")
        print(f"Time remaining: {week_data['time_remaining']}")
        
        # Get predictions from all models
        remaining_predictions = self.predict_remaining_tweets_enhanced(week_data['current_time'])
        
        print(f"\n=== Model Predictions (Remaining Tweets) ===")
        for model_name, prediction in remaining_predictions.items():
            if model_name != 'confidence_interval':
                print(f"{model_name:15s}: {prediction:6.1f}")
        
        ci = remaining_predictions['confidence_interval']
        total_predicted = current_tweets + remaining_predictions['ensemble']
        total_ci = (current_tweets + ci[0], current_tweets + ci[1])
        
        print(f"\n=== Final Predictions ===")
        print(f"Ensemble remaining: {remaining_predictions['ensemble']:.1f}")
        print(f"Total predicted: {total_predicted:.1f}")
        print(f"95% CI: {total_ci[0]:.1f} - {total_ci[1]:.1f}")
        
        # Calculate enhanced probabilities
        probabilities = self.calculate_enhanced_probabilities(current_tweets, remaining_predictions)
        
        return {
            'current_tweets': current_tweets,
            'predictions_breakdown': remaining_predictions,
            'total_predicted': total_predicted,
            'confidence_interval': total_ci,
            'time_remaining': week_data['time_remaining'],
            'predictions_by_frame': probabilities
        }
    
    def print_enhanced_summary(self, predictions_summary):
        """Print enhanced prediction summary."""
        print("\n" + "="*70)
        print("ENHANCED ELON MUSK TWEET COUNT PREDICTIONS")
        print("="*70)
        
        print(f"Current tweets this week: {predictions_summary['current_tweets']}")
        
        # Show breakdown of different models
        breakdown = predictions_summary['predictions_breakdown']
        print(f"\nModel Predictions (Remaining Tweets):")
        print(f"  Daily Prophet    : {breakdown['prophet_daily']:6.1f}")
        print(f"  Hourly Prophet   : {breakdown['prophet_hourly']:6.1f}")
        print(f"  Pattern-based    : {breakdown['pattern_based']:6.1f}")
        print(f"  Random Forest    : {breakdown['random_forest']:6.1f}")
        print(f"  Ensemble Average : {breakdown['ensemble']:6.1f}")
        
        print(f"\nTotal predicted tweets: {predictions_summary['total_predicted']:.1f}")
        ci = predictions_summary['confidence_interval']
        print(f"95% Confidence interval: {ci[0]:.1f} - {ci[1]:.1f}")
        print(f"Time remaining: {predictions_summary['time_remaining']}")
        
        print(f"\nPROBABILITIES BY TIME FRAME:")
        print("-" * 50)
        
        # Sort by probability descending
        sorted_frames = sorted(predictions_summary['predictions_by_frame'].items(), 
                             key=lambda x: x[1]['probability'], reverse=True)
        
        for frame_name, data in sorted_frames:
            prob = data['probability']
            print(f"{frame_name:20s}: {prob:7.3f} ({prob*100:5.1f}%)")
        
        print("-" * 50)
        print(f"{'TOTAL':20s}: {sum(d['probability'] for d in predictions_summary['predictions_by_frame'].values()):7.3f} (100.0%)")
        print("="*70) 