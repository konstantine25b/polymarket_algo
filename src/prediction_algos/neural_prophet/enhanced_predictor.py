"""
Enhanced Neural Prophet predictor with improved forecasting methods for Elon Musk tweet counts.
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
from scipy.special import erf
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants import TWEET_COUNT_FRAMES, ET_TIMEZONE

from .data_processor import TweetDataProcessor


class EnhancedNeuralTweetPredictor:
    """Enhanced tweet count predictor with multiple Neural Prophet model configurations."""
    
    def __init__(self, data_path=None, save_plots=True, random_seed=42):
        """
        Initialize the enhanced Neural Prophet predictor.
        
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
        self.rf_model = None
        self.save_plots = save_plots
        self.random_seed = random_seed
        self.plots_dir = Path("src/prediction_algos/neural_prophet/plots")
        
        # Create plots directory
        if self.save_plots:
            self.plots_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_hourly_data(self):
        """Prepare hourly tweet data for more granular predictions."""
        return self.data_processor.get_neural_prophet_hourly_data()
    
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
        """Prepare multiple Neural Prophet forecasting models with optimized training times."""
        print("Preparing fast Neural Prophet forecasting models...")
        
        # 1. Daily Neural Prophet model (baseline) - REDUCED EPOCHS
        daily_data = self.data_processor.get_neural_prophet_data()
        print(f"Training daily Neural Prophet with {len(daily_data)} days of data...")
        
        self.daily_model = NeuralProphet(
            n_forecasts=1,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=True,
            epochs=50,  # REDUCED from 100
            learning_rate=0.15,  # INCREASED for faster convergence
            quantiles=[0.1, 0.9],
            n_lags=5,  # REDUCED from 7
            n_changepoints=8,  # REDUCED from 10
            trend_reg=1.0,
            seasonality_reg=1.0,
            normalize='standardize',
            impute_missing=True
        )
        self.daily_model.fit(daily_data, freq='D')
        
        # 2. Hourly Neural Prophet model - SIMPLIFIED
        hourly_data = self.prepare_hourly_data()
        print(f"Training hourly Neural Prophet with {len(hourly_data)} hours of data...")
        
        self.hourly_model = NeuralProphet(
            n_forecasts=1,
            yearly_seasonality=False,  # DISABLED for speed
            weekly_seasonality=True,
            daily_seasonality=True,
            epochs=40,  # REDUCED from 150
            learning_rate=0.1,  # INCREASED for faster convergence
            quantiles=[0.1, 0.9],
            n_lags=12,  # REDUCED from 24
            n_changepoints=8,  # REDUCED from 15
            trend_reg=1.0,  # INCREASED for stability
            seasonality_reg=2.0,
            normalize='standardize',
            impute_missing=True
        )
        self.hourly_model.fit(hourly_data, freq='H')
        
        # 3. Random Forest model for ensemble
        self.prepare_rf_model(daily_data)
        
        # 4. Conservative model (more stable, less sensitive) - SIMPLIFIED
        self.prepare_conservative_model(daily_data)
        
        # 5. Aggressive model (more sensitive to recent changes) - SIMPLIFIED
        self.prepare_aggressive_model(daily_data)
        
        print("All fast Neural Prophet models prepared successfully!")
    
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
        """Prepare Conservative Neural Prophet model (faster training)."""
        print("Training conservative Neural Prophet model...")
        
        self.conservative_model = NeuralProphet(
            n_forecasts=1,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,  # DISABLED for speed
            epochs=30,  # REDUCED from 80
            learning_rate=0.1,  # INCREASED for faster convergence
            quantiles=[0.05, 0.95],
            n_lags=3,  # REDUCED from 5
            n_changepoints=5,  # SAME
            trend_reg=2.0,
            seasonality_reg=3.0,
            normalize='standardize',
            impute_missing=True
        )
        self.conservative_model.fit(daily_data, freq='D')
        print("Conservative Neural Prophet model trained")
    
    def prepare_aggressive_model(self, daily_data):
        """Prepare Aggressive Neural Prophet model (faster training)."""
        print("Training aggressive Neural Prophet model...")
        
        self.aggressive_model = NeuralProphet(
            n_forecasts=1,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,  # DISABLED for speed
            epochs=40,  # REDUCED from 120
            learning_rate=0.2,  # INCREASED for faster convergence
            quantiles=[0.1, 0.9],
            n_lags=7,  # REDUCED from 10
            n_changepoints=12,  # REDUCED from 20
            trend_reg=0.5,  # INCREASED for stability
            seasonality_reg=1.0,  # INCREASED for stability
            normalize='standardize',
            impute_missing=True
        )
        self.aggressive_model.fit(daily_data, freq='D')
        print("Aggressive Neural Prophet model trained")
    
    def predict_remaining_tweets_enhanced(self, current_time):
        """Generate predictions from all models and create ensemble."""
        if self.daily_model is None:
            self.prepare_models()
        
        # Get current week information
        week_data = self.data_processor.get_current_week_data(current_time)
        current_tweets = week_data['current_week_tweets']
        time_remaining = week_data['time_remaining']
        
        # Calculate forecast periods
        days_remaining = max(1, int(np.ceil(time_remaining.total_seconds() / (24 * 3600))))
        hours_remaining = max(1, int(np.ceil(time_remaining.total_seconds() / 3600)))
        
        predictions = {}
        
        # 1. Daily Neural Prophet
        try:
            daily_data = self.data_processor.get_neural_prophet_data()
            daily_future = self.daily_model.make_future_dataframe(daily_data, periods=days_remaining)
            daily_forecast = self.daily_model.predict(daily_future)
            daily_remaining = daily_forecast.tail(days_remaining)['yhat1'].sum()
            predictions['neural_daily'] = max(0, daily_remaining)
        except Exception as e:
            print(f"Daily Neural Prophet error: {e}")
            predictions['neural_daily'] = 0
        
        # 2. Hourly Neural Prophet (aggregate to daily equivalent)
        try:
            hourly_data = self.prepare_hourly_data()
            hourly_future = self.hourly_model.make_future_dataframe(hourly_data, periods=hours_remaining)
            hourly_forecast = self.hourly_model.predict(hourly_future)
            hourly_remaining = hourly_forecast.tail(hours_remaining)['yhat1'].sum()
            predictions['neural_hourly'] = max(0, hourly_remaining)
        except Exception as e:
            print(f"Hourly Neural Prophet error: {e}")
            predictions['neural_hourly'] = 0
        
        # 3. Conservative Neural Prophet
        try:
            conservative_future = self.conservative_model.make_future_dataframe(daily_data, periods=days_remaining)
            conservative_forecast = self.conservative_model.predict(conservative_future)
            conservative_remaining = conservative_forecast.tail(days_remaining)['yhat1'].sum()
            predictions['conservative_neural'] = max(0, conservative_remaining)
        except Exception as e:
            print(f"Conservative Neural Prophet error: {e}")
            predictions['conservative_neural'] = 0
        
        # 4. Aggressive Neural Prophet
        try:
            aggressive_future = self.aggressive_model.make_future_dataframe(daily_data, periods=days_remaining)
            aggressive_forecast = self.aggressive_model.predict(aggressive_future)
            aggressive_remaining = aggressive_forecast.tail(days_remaining)['yhat1'].sum()
            predictions['aggressive_neural'] = max(0, aggressive_remaining)
        except Exception as e:
            print(f"Aggressive Neural Prophet error: {e}")
            predictions['aggressive_neural'] = 0
        
        # 5. Pattern-based prediction (14-day recent average)
        try:
            recent_patterns = self.analyze_recent_patterns(days_back=14)
            if recent_patterns and recent_patterns['avg_daily'] > 0:
                pattern_remaining = recent_patterns['avg_daily'] * (time_remaining.total_seconds() / (24 * 3600))
                predictions['pattern_based'] = max(0, pattern_remaining)
            else:
                predictions['pattern_based'] = 0
        except Exception as e:
            print(f"Pattern-based prediction error: {e}")
            predictions['pattern_based'] = 0
        
        # 6. Random Forest prediction
        if self.rf_model:
            try:
                # Create future features for RF prediction
                future_dates = pd.date_range(
                    start=datetime.now(ET_TIMEZONE), 
                    periods=days_remaining, 
                    freq='D'
                )
                
                rf_predictions = []
                for date in future_dates:
                    features = {
                        'dayofweek': date.dayofweek,
                        'month': date.month,
                        'day': date.day,
                        'is_weekend': 1 if date.dayofweek >= 5 else 0,
                        'ma_7': daily_data['y'].tail(7).mean(),
                        'ma_30': daily_data['y'].tail(30).mean(),
                        'lag_1': daily_data['y'].iloc[-1],
                        'lag_7': daily_data['y'].iloc[-7] if len(daily_data) >= 7 else daily_data['y'].iloc[0]
                    }
                    
                    X_pred = pd.DataFrame([features])
                    pred = self.rf_model.predict(X_pred)[0]
                    rf_predictions.append(max(0, pred))
                
                predictions['random_forest'] = sum(rf_predictions)
            except Exception as e:
                print(f"Random Forest prediction error: {e}")
                predictions['random_forest'] = 0
        else:
            predictions['random_forest'] = 0
        
        return predictions, current_tweets, time_remaining, days_remaining
    
    def detect_current_activity_mode(self, current_time):
        """Detect current activity mode for adaptive ensemble weighting."""
        try:
            # Analyze recent tweet rates
            if self.data_processor.raw_data is None:
                self.data_processor.load_data()
            
            # Parse timestamps
            self.data_processor.raw_data['parsed_timestamp'] = self.data_processor.raw_data['created_at'].apply(
                self.data_processor.parse_timestamp
            )
            valid_data = self.data_processor.raw_data.dropna(subset=['parsed_timestamp'])
            
            # Current time handling
            if current_time is None:
                current_time = datetime.now(ET_TIMEZONE)
            elif current_time.tzinfo is None:
                current_time = ET_TIMEZONE.localize(current_time)
            
            # Calculate recent rates
            cutoff_6h = current_time - timedelta(hours=6)
            cutoff_24h = current_time - timedelta(hours=24)
            cutoff_3d = current_time - timedelta(days=3)
            
            tweets_6h = len(valid_data[valid_data['parsed_timestamp'] >= cutoff_6h])
            tweets_24h = len(valid_data[valid_data['parsed_timestamp'] >= cutoff_24h])
            tweets_3d = len(valid_data[valid_data['parsed_timestamp'] >= cutoff_3d])
            
            rate_6h = tweets_6h / 6.0
            rate_24h = tweets_24h / 24.0
            rate_3d = tweets_3d / 72.0
            
            # Determine activity mode
            if rate_6h > 3.0 or tweets_24h > 50:
                return "high_activity", 1.3
            elif rate_6h < 1.0 and tweets_24h < 20:
                return "low_activity", 0.8
            elif rate_24h > rate_3d * 1.5:
                return "increasing_activity", 1.15
            else:
                return "normal_activity", 1.0
                
        except Exception as e:
            print(f"Activity detection error: {e}")
            return "normal_activity", 1.0
    
    def calculate_adaptive_weights(self, current_time):
        """Calculate adaptive ensemble weights based on current activity (FAST VERSION)."""
        activity_mode, activity_multiplier = self.detect_current_activity_mode(current_time)
        
        # Base weights for 6 models (4 neural + 2 support)
        base_weights = {
            'neural_daily': 0.30,      # INCREASED - Reliable daily patterns
            'neural_hourly': 0.35,     # INCREASED - Granular hourly patterns  
            'pattern_based': 0.25,     # Key recent trend analysis
            'aggressive_neural': 0.20, # INCREASED - Sensitive to changes
            'conservative_neural': 0.05, # Stable baseline
            'random_forest': 0.05      # Feature backup
        }
        
        # Adjust weights based on activity mode
        if activity_mode == "high_activity":
            base_weights['pattern_based'] = 0.35
            base_weights['aggressive_neural'] = 0.30
            base_weights['neural_daily'] = 0.25
            base_weights['neural_hourly'] = 0.30
        elif activity_mode == "low_activity":
            base_weights['conservative_neural'] = 0.15
            base_weights['neural_daily'] = 0.45
            base_weights['pattern_based'] = 0.20
            base_weights['neural_hourly'] = 0.30
        elif activity_mode == "increasing_activity":
            base_weights['aggressive_neural'] = 0.25
            base_weights['pattern_based'] = 0.30
        
        # Normalize weights to sum to 1
        total_weight = sum(base_weights.values())
        if total_weight > 0:
            base_weights = {k: v / total_weight for k, v in base_weights.items()}
        
        return base_weights, activity_mode, activity_multiplier
    
    def calculate_enhanced_probabilities(self, current_tweets, remaining_predictions):
        """Calculate probabilities with ensemble predictions and bias correction."""
        # Calculate ensemble weights
        weights, activity_mode, activity_multiplier = self.calculate_adaptive_weights(None)
        
        # Calculate weighted ensemble prediction
        ensemble_prediction = sum(
            remaining_predictions.get(model, 0) * weight 
            for model, weight in weights.items()
        )
        
        # Apply activity multiplier
        ensemble_prediction *= activity_multiplier
        
        # Calculate total predicted tweets
        total_predicted = current_tweets + ensemble_prediction
        
        # Bias correction (similar to Facebook Prophet enhanced)
        if current_tweets > 70:  # Late in prediction week
            # Calculate probability of <150 to check if bias correction needed
            temp_std = max(8.0, ensemble_prediction * 0.15)  # Temporary std estimate
            prob_under_150 = stats.norm.cdf(150, loc=total_predicted, scale=temp_std)
            
            if prob_under_150 > 0.08:  # Too high for realistic scenario
                bias = 4 + (prob_under_150 - 0.08) * 25
                total_predicted += bias + 1
        
        # Calculate ensemble uncertainty
        prediction_values = list(remaining_predictions.values())
        if len(prediction_values) > 1:
            model_uncertainty = np.std(prediction_values)
        else:
            model_uncertainty = 5.0
        
        # Base uncertainty with smart calibration
        base_uncertainty = max(model_uncertainty, 4.0)
        
        # Activity-based uncertainty adjustment
        if activity_mode == "high_activity":
            uncertainty_factor = 1.4
        elif activity_mode == "low_activity":
            uncertainty_factor = 0.7
        else:
            uncertainty_factor = 1.0
        
        final_uncertainty = base_uncertainty * uncertainty_factor * 0.6
        
        # Calculate probabilities using mixture distribution
        probabilities = {}
        normal_weight = 0.70
        t_weight = 0.30
        t_df = 4
        
        for frame in TWEET_COUNT_FRAMES:
            frame_name = frame['name']
            min_tweets = frame['min']
            max_tweets = frame['max']
            
            if max_tweets == float('inf'):  # "X or more" case
                prob_normal = 1 - stats.norm.cdf(min_tweets, loc=total_predicted, scale=final_uncertainty)
                prob_t = 1 - stats.t.cdf(min_tweets, df=t_df, loc=total_predicted, scale=final_uncertainty)
            else:
                prob_normal_lower = stats.norm.cdf(min_tweets, loc=total_predicted, scale=final_uncertainty)
                prob_normal_upper = stats.norm.cdf(max_tweets + 1, loc=total_predicted, scale=final_uncertainty)
                prob_normal = prob_normal_upper - prob_normal_lower
                
                prob_t_lower = stats.t.cdf(min_tweets, df=t_df, loc=total_predicted, scale=final_uncertainty)
                prob_t_upper = stats.t.cdf(max_tweets + 1, df=t_df, loc=total_predicted, scale=final_uncertainty)
                prob_t = prob_t_upper - prob_t_lower
            
            # Mixture probability
            prob = normal_weight * prob_normal + t_weight * prob_t
            probabilities[frame_name] = max(0.001, prob)  # Minimum 0.1% probability
        
        # Normalize probabilities
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            probabilities = {k: v / total_prob for k, v in probabilities.items()}
        
        return probabilities, total_predicted, final_uncertainty, activity_mode, weights
    
    def generate_enhanced_predictions(self, current_time=None):
        """Generate enhanced predictions using Neural Prophet ensemble."""
        print("=== Enhanced Neural Prophet Prediction Analysis ===")
        
        # Get predictions from all models
        remaining_predictions, current_tweets, time_remaining, days_remaining = self.predict_remaining_tweets_enhanced(current_time)
        
        # Calculate ensemble probabilities
        probabilities, total_predicted, uncertainty, activity_mode, weights = self.calculate_enhanced_probabilities(
            current_tweets, remaining_predictions
        )
        
        # Get current week context
        week_data = self.data_processor.get_current_week_data(current_time)
        
        # Calculate confidence intervals
        ci_lower = total_predicted - 1.645 * uncertainty
        ci_upper = total_predicted + 1.645 * uncertainty
        
        return {
            'model_type': 'Enhanced Neural Prophet',
            'prediction_results': {
                'remaining_tweets': total_predicted - current_tweets,
                'total_predicted': total_predicted,
                'confidence_interval': {
                    'lower': ci_lower,
                    'upper': ci_upper,
                    'width': ci_upper - ci_lower
                },
                'current_tweets': current_tweets,
                'days_remaining': days_remaining,
                'uncertainty': uncertainty
            },
            'predictions_breakdown': remaining_predictions,
            'ensemble_weights': weights,
            'activity_mode': activity_mode,
            'probabilities': probabilities,
            'week_context': week_data,
            'predictions_by_frame': {
                frame: {'probability': prob, 'percentage': prob * 100}
                for frame, prob in probabilities.items()
            }
        }
    
    def print_enhanced_summary(self, predictions_summary):
        """Print a comprehensive summary of enhanced predictions."""
        results = predictions_summary['prediction_results']
        breakdown = predictions_summary['predictions_breakdown']
        weights = predictions_summary['ensemble_weights']
        probabilities = predictions_summary['probabilities']
        week_context = predictions_summary['week_context']
        activity_mode = predictions_summary['activity_mode']
        
        print(f"Current time: {week_context['current_time']}")
        print(f"Week period: {week_context['week_start']} to {week_context['week_end']}")
        print(f"Tweets posted so far: {results['current_tweets']}")
        print(f"Time remaining: {week_context['time_remaining']}")
        print()
        
        print("=== Neural Prophet Model Predictions (Remaining Tweets) ===")
        for model_name, prediction in breakdown.items():
            model_display = model_name.replace('_', ' ').title()
            weight = weights.get(model_name, 0) * 100
            print(f"{model_display:20s}: {prediction:6.1f} (weight: {weight:4.1f}%)")
        
        print(f"\n=== Activity Detection ===")
        print(f"Current mode: {activity_mode}")
        
        print(f"\n=== Final Enhanced Predictions ===")
        print(f"Total predicted: {results['total_predicted']:.1f}")
        print(f"90% CI: {results['confidence_interval']['lower']:.1f} - {results['confidence_interval']['upper']:.1f}")
        
        print(f"\nENHANCED NEURAL PROPHET TWEET COUNT PREDICTIONS")
        print("=" * 75)
        print(f"Fast Neural Prophet Models (Remaining Tweets):")
        for model_name, prediction in breakdown.items():
            model_display = model_name.replace('_', ' ').title()
            print(f"  {model_display:20s}: {prediction:6.1f}")
        
        print(f"\nTotal predicted tweets: {results['total_predicted']:.1f}")
        print(f"90% Confidence interval: {results['confidence_interval']['lower']:.1f} - {results['confidence_interval']['upper']:.1f}")
        
        print(f"\nPROBABILITIES BY TIME FRAME:")
        print("-" * 50)
        
        # Sort by probability (highest first)
        sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
        
        for frame_name, probability in sorted_probs:
            percentage = probability * 100
            print(f"{frame_name:20s}: {probability:8.3f} ({percentage:5.1f}%)")
        
        print(f"\nActivity mode: {activity_mode}")
        print(f"Fast Neural Prophet ensemble (4 neural + 2 support models) optimized for speed.")
    
    def plot_enhanced_predictions(self, prediction_summary, save=None):
        """Create enhanced visualization plots."""
        if not self.save_plots:
            return
            
        results = prediction_summary['prediction_results']
        breakdown = prediction_summary['predictions_breakdown']
        probabilities = prediction_summary['probabilities']
        
        # Create comprehensive plots
        fig, axes = plt.subplots(2, 3, figsize=(20, 12))
        fig.suptitle('Enhanced Neural Prophet Tweet Count Predictions', fontsize=16, fontweight='bold')
        
        # Plot 1: Model comparison
        ax1 = axes[0, 0]
        models = list(breakdown.keys())
        predictions = [breakdown[model] for model in models]
        colors = plt.cm.Set3(np.linspace(0, 1, len(models)))
        
        bars = ax1.bar(range(len(models)), predictions, color=colors, alpha=0.8)
        ax1.set_title('Neural Prophet Model Predictions')
        ax1.set_xlabel('Models')
        ax1.set_ylabel('Remaining Tweets')
        ax1.set_xticks(range(len(models)))
        ax1.set_xticklabels([m.replace('_', '\n') for m in models], rotation=45, ha='right')
        ax1.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=9)
        
        # Plot 2: Probability distribution
        ax2 = axes[0, 1]
        frames = list(probabilities.keys())
        probs = [probabilities[frame] * 100 for frame in frames]
        
        bars2 = ax2.bar(range(len(frames)), probs, alpha=0.7, color='lightcoral', edgecolor='darkred')
        ax2.set_title('Enhanced Probability Distribution')
        ax2.set_xlabel('Tweet Count Range')
        ax2.set_ylabel('Probability (%)')
        ax2.set_xticks(range(len(frames)))
        ax2.set_xticklabels(frames, rotation=45, ha='right')
        ax2.grid(True, alpha=0.3)
        
        # Add probability labels
        for i, bar in enumerate(bars2):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
        
        # Plot 3: Historical data trend
        ax3 = axes[0, 2]
        train_data = self.data_processor.get_neural_prophet_data()
        recent_data = train_data.tail(60)  # Last 60 days
        ax3.plot(recent_data['ds'], recent_data['y'], 'o-', color='blue', alpha=0.7, markersize=3)
        ax3.set_title('Recent 60-Day Trend')
        ax3.set_xlabel('Date')
        ax3.set_ylabel('Tweet Count')
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Confidence intervals
        ax4 = axes[1, 0]
        total_pred = results['total_predicted']
        ci_lower = results['confidence_interval']['lower']
        ci_upper = results['confidence_interval']['upper']
        
        ax4.errorbar([0], [total_pred], 
                    yerr=[[total_pred - ci_lower], [ci_upper - total_pred]], 
                    fmt='go', markersize=12, capsize=15, capthick=4, linewidth=4)
        
        ax4.set_xlim(-0.5, 0.5)
        ax4.set_ylim(ci_lower - 30, ci_upper + 30)
        ax4.set_title(f'Enhanced Prediction: {total_pred:.1f}')
        ax4.set_ylabel('Total Tweet Count')
        ax4.set_xticks([])
        ax4.grid(True, alpha=0.3)
        
        # Plot 5: Model weights
        ax5 = axes[1, 1]
        weights = prediction_summary['ensemble_weights']
        weight_models = list(weights.keys())
        weight_values = [weights[model] * 100 for model in weight_models]
        
        ax5.pie(weight_values, labels=[m.replace('_', '\n') for m in weight_models], autopct='%1.1f%%', startangle=90)
        ax5.set_title('Enhanced Ensemble Weights')
        
        # Plot 6: Activity analysis
        ax6 = axes[1, 2]
        activity_mode = prediction_summary['activity_mode']
        
        # Simple activity indicator
        activity_colors = {
            'high_activity': 'red',
            'increasing_activity': 'orange', 
            'normal_activity': 'green',
            'low_activity': 'blue'
        }
        
        ax6.bar([0], [1], color=activity_colors.get(activity_mode, 'gray'), alpha=0.7)
        ax6.set_xlim(-0.5, 0.5)
        ax6.set_ylim(0, 1.2)
        ax6.set_title(f'Activity: {activity_mode.replace("_", " ").title()}')
        ax6.set_xticks([])
        ax6.set_yticks([])
        
        plt.tight_layout()
        
        # Save plot
        if save:
            plt.savefig(save, dpi=300, bbox_inches='tight')
        elif self.save_plots:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.plots_dir / f"enhanced_neural_prophet_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Enhanced plot saved to: {filename}")
        
        plt.show() 