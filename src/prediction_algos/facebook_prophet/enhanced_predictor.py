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
import random

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants import TWEET_COUNT_FRAMES, ET_TIMEZONE

from .data_processor import TweetDataProcessor


class EnhancedTweetPredictor:
    """Enhanced tweet count predictor with multiple Prophet model configurations."""
    
    def __init__(self, data_path=None, save_plots=True, random_seed=42):
        """
        Initialize the enhanced predictor.
        
        Args:
            data_path (str): Path to tweet data CSV file
            save_plots (bool): Whether to save prediction plots
            random_seed (int): Random seed for reproducible results
        """
        self.data_processor = TweetDataProcessor(data_path)
        self.daily_model = None
        self.hourly_model = None
        self.conservative_model = None
        self.aggressive_model = None
        self.weekly_focused_model = None
        self.rf_model = None
        self.save_plots = save_plots
        self.random_seed = random_seed
        self.plots_dir = Path("src/facebook_prophet/plots")
        
        # Set global random seeds for reproducibility
        np.random.seed(random_seed)
        random.seed(random_seed)
        
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
        
        # 4. Conservative model
        self.prepare_conservative_model(daily_data)
        
        # 5. Aggressive model
        self.prepare_aggressive_model(daily_data)
        
        # 6. Weekly focused model
        self.prepare_weekly_focused_model(daily_data)
        
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
        self.rf_model = RandomForestRegressor(n_estimators=100, random_state=self.random_seed)
        self.rf_model.fit(X, y)
        
        # Calculate model performance
        y_pred = self.rf_model.predict(X)
        mae = mean_absolute_error(y, y_pred)
        print(f"Random Forest MAE: {mae:.2f}")
    
    def prepare_conservative_model(self, daily_data):
        """Prepare Conservative Prophet model (less sensitive to recent changes)."""
        self.conservative_model = Prophet(
            changepoint_prior_scale=0.05,  # Less flexible to changes
            seasonality_prior_scale=10.0,  # Lower seasonality influence
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
            interval_width=0.9  # Wider confidence intervals
        )
        self.conservative_model.fit(daily_data)
        print("Conservative model trained")
    
    def prepare_aggressive_model(self, daily_data):
        """Prepare Aggressive Prophet model (more sensitive to recent changes)."""
        self.aggressive_model = Prophet(
            changepoint_prior_scale=0.2,   # More flexible to changes
            seasonality_prior_scale=30.0,  # Higher seasonality influence
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
            interval_width=0.8
        )
        self.aggressive_model.fit(daily_data)
        print("Aggressive model trained")
    
    def prepare_weekly_focused_model(self, daily_data):
        """Prepare Weekly-focused Prophet model (emphasizes weekly patterns)."""
        self.weekly_focused_model = Prophet(
            changepoint_prior_scale=0.1,
            seasonality_prior_scale=15.0,
            daily_seasonality=False,  # Focus on weekly patterns
            weekly_seasonality=True,
            yearly_seasonality=False,
            interval_width=0.8
        )
        # Add custom weekly seasonality components
        self.weekly_focused_model.add_seasonality(name='bi_weekly', period=14, fourier_order=4)
        self.weekly_focused_model.fit(daily_data)
        print("Weekly-focused model trained")
    
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
        
        # 1. Daily Prophet prediction - FIX: Generate forecasts for each remaining day
        daily_future = self.daily_model.make_future_dataframe(periods=int(np.ceil(remaining_days)))
        daily_forecast = self.daily_model.predict(daily_future)
        
        # FIX: Sum predictions for each remaining day instead of multiplying one day
        current_date = current_time.date()
        end_date = week_data['week_end'].date()
        
        # Convert daily forecast to timezone-naive for date comparison
        daily_forecast['ds_date'] = daily_forecast['ds'].dt.date
        
        # Sum predictions for remaining days only
        remaining_forecast = daily_forecast[daily_forecast['ds_date'] > current_date]
        daily_pred = remaining_forecast['yhat'].sum()
        
        # Fix confidence interval - sum the individual day uncertainties properly
        daily_uncertainties = (remaining_forecast['yhat_upper'] - remaining_forecast['yhat_lower']) / 2
        # For independent daily predictions, uncertainty scales with sqrt of number of days
        total_daily_uncertainty = np.sqrt(np.sum(daily_uncertainties**2))
        daily_lower = max(0, daily_pred - total_daily_uncertainty)
        daily_upper = daily_pred + total_daily_uncertainty
        
        predictions['prophet_daily'] = max(0, daily_pred)
        predictions['prophet_daily_ci'] = (daily_lower, daily_upper)
        
        # 2. Hourly Prophet prediction - Keep existing logic but ensure proper aggregation
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
        
        # Fix hourly confidence interval - use proper uncertainty aggregation
        hourly_uncertainties = (hourly_remaining['yhat_upper'] - hourly_remaining['yhat_lower']) / 2
        # For independent hourly predictions, uncertainty scales with sqrt of number of hours
        total_hourly_uncertainty = np.sqrt(np.sum(hourly_uncertainties**2))
        hourly_lower = max(0, hourly_pred - total_hourly_uncertainty)
        hourly_upper = hourly_pred + total_hourly_uncertainty
        
        predictions['prophet_hourly'] = max(0, hourly_pred)
        predictions['prophet_hourly_ci'] = (hourly_lower, hourly_upper)
        
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
        
        # 5. Conservative Prophet prediction - FIX: Same as daily prophet
        conservative_future = self.conservative_model.make_future_dataframe(periods=int(np.ceil(remaining_days)))
        conservative_forecast = self.conservative_model.predict(conservative_future)
        
        # FIX: Sum predictions for remaining days
        conservative_forecast['ds_date'] = conservative_forecast['ds'].dt.date
        remaining_conservative = conservative_forecast[conservative_forecast['ds_date'] > current_date]
        conservative_pred = remaining_conservative['yhat'].sum()
        
        # Fix conservative confidence interval scaling
        conservative_uncertainties = (remaining_conservative['yhat_upper'] - remaining_conservative['yhat_lower']) / 2
        total_conservative_uncertainty = np.sqrt(np.sum(conservative_uncertainties**2))
        conservative_lower = max(0, conservative_pred - total_conservative_uncertainty)
        conservative_upper = conservative_pred + total_conservative_uncertainty
        
        predictions['conservative_prophet'] = max(0, conservative_pred)
        predictions['conservative_prophet_ci'] = (conservative_lower, conservative_upper)
        
        # 6. Aggressive Prophet prediction - FIX: Same as daily prophet
        aggressive_future = self.aggressive_model.make_future_dataframe(periods=int(np.ceil(remaining_days)))
        aggressive_forecast = self.aggressive_model.predict(aggressive_future)
        
        # FIX: Sum predictions for remaining days
        aggressive_forecast['ds_date'] = aggressive_forecast['ds'].dt.date
        remaining_aggressive = aggressive_forecast[aggressive_forecast['ds_date'] > current_date]
        aggressive_pred = remaining_aggressive['yhat'].sum()
        
        # Fix aggressive confidence interval scaling
        aggressive_uncertainties = (remaining_aggressive['yhat_upper'] - remaining_aggressive['yhat_lower']) / 2
        total_aggressive_uncertainty = np.sqrt(np.sum(aggressive_uncertainties**2))
        aggressive_lower = max(0, aggressive_pred - total_aggressive_uncertainty)
        aggressive_upper = aggressive_pred + total_aggressive_uncertainty
        
        predictions['aggressive_prophet'] = max(0, aggressive_pred)
        predictions['aggressive_prophet_ci'] = (aggressive_lower, aggressive_upper)
        
        # 7. Weekly-focused Prophet prediction - FIX: Same as daily prophet
        weekly_future = self.weekly_focused_model.make_future_dataframe(periods=int(np.ceil(remaining_days)))
        weekly_forecast = self.weekly_focused_model.predict(weekly_future)
        
        # FIX: Sum predictions for remaining days
        weekly_forecast['ds_date'] = weekly_forecast['ds'].dt.date
        remaining_weekly = weekly_forecast[weekly_forecast['ds_date'] > current_date]
        weekly_pred = remaining_weekly['yhat'].sum()
        
        # Fix weekly confidence interval scaling
        weekly_uncertainties = (remaining_weekly['yhat_upper'] - remaining_weekly['yhat_lower']) / 2
        total_weekly_uncertainty = np.sqrt(np.sum(weekly_uncertainties**2))
        weekly_lower = max(0, weekly_pred - total_weekly_uncertainty)
        weekly_upper = weekly_pred + total_weekly_uncertainty
        
        predictions['weekly_prophet'] = max(0, weekly_pred)
        predictions['weekly_prophet_ci'] = (weekly_lower, weekly_upper)
        
        # 8. Ensemble prediction (adaptive weighted average based on activity)
        adaptive_weights, activity_info = self.calculate_adaptive_weights(week_data['current_time'])
        
        ensemble_pred = sum(predictions[model] * weight for model, weight in adaptive_weights.items())
        
        # FIX: Reduce activity multiplier impact and add sanity check
        activity_multiplier = activity_info['multiplier']
        
        # Sanity check: If activity multiplier would make prediction unreasonably low, cap it
        if activity_multiplier < 1.0 and ensemble_pred * activity_multiplier < 20 * remaining_days:
            print(f"Activity multiplier {activity_multiplier:.2f} too aggressive, using 0.9 instead")
            activity_multiplier = 0.9
        
        ensemble_pred *= activity_multiplier
        
        predictions['ensemble'] = ensemble_pred
        predictions['activity_mode'] = activity_info['mode']
        predictions['activity_multiplier'] = activity_multiplier
        
        # Calculate improved confidence interval using Prophet CIs
        prophet_models = ['prophet_daily', 'prophet_hourly', 'conservative_prophet', 
                         'aggressive_prophet', 'weekly_prophet']
        
        # Weighted average of Prophet confidence intervals
        ensemble_lower = sum(predictions[f'{model}_ci'][0] * adaptive_weights[model] 
                           for model in prophet_models if f'{model}_ci' in predictions)
        ensemble_upper = sum(predictions[f'{model}_ci'][1] * adaptive_weights[model] 
                           for model in prophet_models if f'{model}_ci' in predictions)
        
        # Add ensemble variance to account for model disagreement
        pred_values = [predictions[model] for model in prophet_models if model in predictions]
        ensemble_variance = np.var(pred_values) if len(pred_values) > 1 else 0
        
        # Expand CI based on ensemble variance
        ci_expansion = 1.96 * np.sqrt(ensemble_variance)
        final_lower = max(0, ensemble_lower - ci_expansion)
        final_upper = ensemble_upper + ci_expansion
        
        predictions['confidence_interval'] = (final_lower, final_upper)
        predictions['time_remaining'] = week_data['time_remaining']  # Add for probability calc
        
        return predictions
    
    def calculate_enhanced_probabilities(self, current_tweets, remaining_predictions):
        """Calculate probabilities using simplified normal distribution."""
        total_predicted = current_tweets + remaining_predictions['ensemble']
        
        # Use a reasonable standard deviation for tweet count predictions
        # Based on typical tweet count variability (around 15-20% of the prediction)
        # Enhanced version uses slightly more uncertainty due to ensemble complexity
        std_dev = max(10, total_predicted * 0.12)  # Minimum 10 tweets std dev, or 12% of prediction
        
        probabilities = {}
        for frame in TWEET_COUNT_FRAMES:
            frame_name = frame['name']
            min_tweets = frame['min']
            max_tweets = frame['max']
            
            # Calculate probability using normal distribution
            if max_tweets == float('inf'):
                # For "X or more" categories
                prob = 1 - stats.norm.cdf(min_tweets - 0.5, loc=total_predicted, scale=std_dev)
            else:
                # For range categories
                prob_lower = stats.norm.cdf(min_tweets - 0.5, loc=total_predicted, scale=std_dev)
                prob_upper = stats.norm.cdf(max_tweets + 0.5, loc=total_predicted, scale=std_dev)
                prob = prob_upper - prob_lower
            
            probabilities[frame_name] = {
                'probability': max(0, min(1, prob)),
                'range': f"{min_tweets}-{max_tweets}" if max_tweets != float('inf') else f"{min_tweets}+",
                'min': min_tweets,
                'max': max_tweets
            }
        
        # Normalize probabilities to ensure they sum to 1
        total_prob = sum(pred['probability'] for pred in probabilities.values())
        if total_prob > 0:
            for frame_name in probabilities:
                probabilities[frame_name]['probability'] /= total_prob
        
        return probabilities
    
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
            if model_name not in ['confidence_interval', 'time_remaining', 'activity_mode', 'activity_multiplier'] and not model_name.endswith('_ci'):
                print(f"{model_name:15s}: {prediction:6.1f}")
        
        # Show activity detection
        activity_mode = remaining_predictions.get('activity_mode', 'normal_activity')
        activity_mult = remaining_predictions.get('activity_multiplier', 1.0)
        print(f"\n=== Activity Detection ===")
        print(f"Current mode: {activity_mode}")
        print(f"Activity multiplier: {activity_mult:.2f}")
        
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
        print(f"  Daily Prophet      : {breakdown['prophet_daily']:6.1f}")
        print(f"  Hourly Prophet     : {breakdown['prophet_hourly']:6.1f}")
        print(f"  Conservative Prophet: {breakdown['conservative_prophet']:6.1f}")
        print(f"  Aggressive Prophet : {breakdown['aggressive_prophet']:6.1f}")
        print(f"  Weekly Prophet     : {breakdown['weekly_prophet']:6.1f}")
        print(f"  Pattern-based      : {breakdown['pattern_based']:6.1f}")
        print(f"  Random Forest      : {breakdown['random_forest']:6.1f}")
        print(f"  Ensemble Average   : {breakdown['ensemble']:6.1f}")
        
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
    
    def detect_current_activity_mode(self, current_time):
        """Detect if Elon is in high/normal/low activity mode based on recent patterns."""
        if self.data_processor.raw_data is None:
            self.data_processor.load_data()
        
        # Parse timestamps if not already done
        if 'parsed_timestamp' not in self.data_processor.raw_data.columns:
            self.data_processor.raw_data['parsed_timestamp'] = self.data_processor.raw_data['created_at'].apply(
                self.data_processor.parse_timestamp
            )
        
        # Get tweets from last 6 hours, 24 hours, and 3 days
        now = current_time
        last_6h = now - timedelta(hours=6)
        last_24h = now - timedelta(hours=24) 
        last_3d = now - timedelta(days=3)
        
        tweets_6h = len(self.data_processor.raw_data[
            self.data_processor.raw_data['parsed_timestamp'] >= last_6h
        ])
        
        tweets_24h = len(self.data_processor.raw_data[
            self.data_processor.raw_data['parsed_timestamp'] >= last_24h
        ])
        
        tweets_3d = len(self.data_processor.raw_data[
            self.data_processor.raw_data['parsed_timestamp'] >= last_3d
        ])
        
        # Calculate rates
        rate_6h = tweets_6h / 6.0    # tweets per hour last 6h
        rate_24h = tweets_24h / 24.0  # tweets per hour last 24h  
        rate_3d = tweets_3d / 72.0    # tweets per hour last 3d
        
        # Determine activity mode
        if rate_6h > 3.0 or tweets_24h > 50:
            mode = "high_activity"
            multiplier = 1.3
        elif rate_6h < 1.0 and tweets_24h < 20:
            mode = "low_activity" 
            multiplier = 0.8
        elif rate_24h > rate_3d * 1.5:
            mode = "increasing_activity"
            multiplier = 1.15
        else:
            mode = "normal_activity"
            multiplier = 1.0
        
        return {
            'mode': mode,
            'multiplier': multiplier,
            'rate_6h': rate_6h,
            'rate_24h': rate_24h,
            'rate_3d': rate_3d,
            'tweets_6h': tweets_6h,
            'tweets_24h': tweets_24h
        }
    
    def calculate_adaptive_weights(self, current_time):
        """Calculate adaptive weights based on recent model performance and activity."""
        activity = self.detect_current_activity_mode(current_time)
        
        # Base weights - FIX: Reduce weekly prophet weight significantly since it performs poorly
        base_weights = {
            'prophet_daily': 0.30,
            'pattern_based': 0.30, 
            'aggressive_prophet': 0.15,
            'prophet_hourly': 0.15,
            'conservative_prophet': 0.05,
            'weekly_prophet': 0.03,   # Reduced from 0.01 to 0.03 but still minimal impact
            'random_forest': 0.02     # Increased slightly
        }
        
        # Adjust based on activity mode - FIX: Be less aggressive with low activity adjustments
        if activity['mode'] == "high_activity":
            # Boost pattern-based and aggressive models
            base_weights['pattern_based'] = 0.35
            base_weights['aggressive_prophet'] = 0.20
            base_weights['prophet_daily'] = 0.25
            base_weights['prophet_hourly'] = 0.15
            base_weights['conservative_prophet'] = 0.03
            base_weights['weekly_prophet'] = 0.01
            base_weights['random_forest'] = 0.01
        elif activity['mode'] == "low_activity":
            # FIX: Be less aggressive - don't heavily penalize recent patterns
            base_weights['conservative_prophet'] = 0.10  # Reduced from 0.15
            base_weights['prophet_daily'] = 0.35       # Increased from 0.40
            base_weights['pattern_based'] = 0.25       # Kept reasonable
            base_weights['aggressive_prophet'] = 0.12   # Reduced from 0.15
            base_weights['prophet_hourly'] = 0.15      # Increased 
            base_weights['weekly_prophet'] = 0.02
            base_weights['random_forest'] = 0.01
        elif activity['mode'] == "increasing_activity":
            # Balanced but slightly aggressive
            base_weights['pattern_based'] = 0.35
            base_weights['aggressive_prophet'] = 0.18
            base_weights['prophet_daily'] = 0.27
            base_weights['prophet_hourly'] = 0.15
            base_weights['conservative_prophet'] = 0.03
            base_weights['weekly_prophet'] = 0.01
            base_weights['random_forest'] = 0.01
        
        return base_weights, activity
    
    def calculate_individual_algorithm_probabilities(self, current_tweets, remaining_predictions):
        """Calculate probabilities for each individual algorithm."""
        individual_probabilities = {}
        
        # List of algorithms to analyze
        algorithms = [
            ('prophet_daily', 'Daily Prophet'),
            ('prophet_hourly', 'Hourly Prophet'), 
            ('conservative_prophet', 'Conservative Prophet'),
            ('aggressive_prophet', 'Aggressive Prophet'),
            ('weekly_prophet', 'Weekly Prophet'),
            ('pattern_based', 'Pattern-based'),
            ('random_forest', 'Random Forest')
        ]
        
        for algo_key, algo_name in algorithms:
            if algo_key in remaining_predictions:
                total_predicted = current_tweets + remaining_predictions[algo_key]
                
                # Use same standard deviation calculation as ensemble but slightly reduced for individual models
                std_dev = max(8, total_predicted * 0.10)  # 10% for individual models
                
                probabilities = {}
                for frame in TWEET_COUNT_FRAMES:
                    frame_name = frame['name']
                    min_tweets = frame['min']
                    max_tweets = frame['max']
                    
                    # Calculate probability using normal distribution
                    if max_tweets == float('inf'):
                        prob = 1 - stats.norm.cdf(min_tweets - 0.5, loc=total_predicted, scale=std_dev)
                    else:
                        prob_lower = stats.norm.cdf(min_tweets - 0.5, loc=total_predicted, scale=std_dev)
                        prob_upper = stats.norm.cdf(max_tweets + 0.5, loc=total_predicted, scale=std_dev)
                        prob = prob_upper - prob_lower
                    
                    probabilities[frame_name] = max(0, min(1, prob))
                
                # Normalize probabilities
                total_prob = sum(probabilities.values())
                if total_prob > 0:
                    for frame_name in probabilities:
                        probabilities[frame_name] /= total_prob
                
                individual_probabilities[algo_name] = {
                    'total_predicted': total_predicted,
                    'probabilities': probabilities
                }
        
        return individual_probabilities
    
    def print_individual_algorithm_distributions(self, predictions_summary):
        """Print probability distributions for each individual algorithm."""
        current_tweets = predictions_summary['current_tweets']
        remaining_predictions = predictions_summary['predictions_breakdown']
        
        # Calculate individual probabilities
        individual_probs = self.calculate_individual_algorithm_probabilities(current_tweets, remaining_predictions)
        
        print("\n" + "="*100)
        print("INDIVIDUAL ALGORITHM PROBABILITY DISTRIBUTIONS")
        print("="*100)
        
        # Get top 6 most likely frames for display
        ensemble_probs = predictions_summary['predictions_by_frame']
        top_frames = sorted(ensemble_probs.items(), key=lambda x: x[1]['probability'], reverse=True)[:6]
        top_frame_names = [frame[0] for frame in top_frames]
        
        # Print header
        print(f"{'Algorithm':<20s} {'Total':<6s}", end="")
        for frame_name in top_frame_names:
            print(f" {frame_name:<12s}", end="")
        print()
        print("-" * 100)
        
        # Print each algorithm's distribution
        for algo_name, data in individual_probs.items():
            total_pred = data['total_predicted']
            probs = data['probabilities']
            
            print(f"{algo_name:<20s} {total_pred:<6.1f}", end="")
            for frame_name in top_frame_names:
                prob = probs.get(frame_name, 0)
                print(f" {prob*100:<12.1f}", end="")
            print()
        
        # Print ensemble for comparison
        ensemble_total = predictions_summary['total_predicted']
        print(f"{'Ensemble (Final)':<20s} {ensemble_total:<6.1f}", end="")
        for frame_name in top_frame_names:
            prob = ensemble_probs[frame_name]['probability']
            print(f" {prob*100:<12.1f}", end="")
        print()
        
        print("-" * 100)
        print("Values show: Total predicted tweets, then probability percentages for top categories")
        print("="*100) 