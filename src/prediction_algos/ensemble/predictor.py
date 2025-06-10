"""
Ensemble predictor combining Neural Prophet, Facebook Prophet, and TimesFM predictions.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Suppress verbose logging from Neural Prophet and Prophet
import logging
logging.getLogger('neuralprophet').setLevel(logging.ERROR)
logging.getLogger('prophet').setLevel(logging.ERROR)
logging.getLogger('cmdstanpy').setLevel(logging.ERROR)
logging.getLogger('pytorch_lightning').setLevel(logging.ERROR)

import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import os
from scipy import stats

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants import TWEET_COUNT_FRAMES, ET_TIMEZONE

from .data_processor import EnsembleTweetDataProcessor
from prediction_algos.neural_prophet import NeuralTweetPredictor, FastNeuralTweetPredictor, EnhancedNeuralTweetPredictor
from prediction_algos.facebook_prophet import TweetPredictor as FacebookTweetPredictor, EnhancedTweetPredictor as EnhancedFacebookTweetPredictor
from prediction_algos.timesfm import TimesFMTweetPredictor, FastTimesFMTweetPredictor, EnhancedTimesFMTweetPredictor


class EnsembleTweetPredictor:
    """Ensemble predictor combining multiple forecasting models with weight control and additional prediction methods."""
    
    def __init__(self, data_path=None, save_plots=True, use_fast_models=False, 
                 neural_prophet_weight=0.15, facebook_prophet_weight=0.40, timesfm_weight=0.40,
                 moving_average_weight=0.025, linear_trend_weight=0.025,
                 include_moving_average=True, include_linear_trend=True):
        """
        Initialize the ensemble predictor.
        
        Args:
            data_path (str): Path to tweet data CSV file
            save_plots (bool): Whether to save prediction plots
            use_fast_models (bool): Whether to use fast versions of individual models
            neural_prophet_weight (float): Weight for Neural Prophet model (0 to exclude)
            facebook_prophet_weight (float): Weight for Facebook Prophet model (0 to exclude)
            timesfm_weight (float): Weight for TimesFM model (0 to exclude)
            moving_average_weight (float): Weight for moving average predictions (0 to exclude)
            linear_trend_weight (float): Weight for linear trend predictions (0 to exclude)
            include_moving_average (bool): Whether to include moving average predictions
            include_linear_trend (bool): Whether to include linear trend predictions
        """
        self.data_processor = EnsembleTweetDataProcessor(data_path)
        self.save_plots = save_plots
        self.use_fast_models = use_fast_models
        self.plots_dir = Path("src/prediction_algos/ensemble/plots")
        
        # Store all weights
        self.raw_weights = {
            'neural_prophet': neural_prophet_weight,
            'facebook_prophet': facebook_prophet_weight,
            'timesfm': timesfm_weight,
            'moving_average': moving_average_weight,
            'linear_trend': linear_trend_weight
        }
        
        # Filter out methods with 0 weight
        active_weights = {k: v for k, v in self.raw_weights.items() if v > 0}
        
        if not active_weights:
            raise ValueError("At least one prediction method must have weight > 0!")
        
        # Normalize weights to sum to 1
        total_weight = sum(active_weights.values())
        self.normalized_weights = {k: v/total_weight for k, v in active_weights.items()}
        
        # Set model weights (only for ML models)
        self.model_weights = {
            'neural_prophet': self.normalized_weights.get('neural_prophet', 0.0),
            'facebook_prophet': self.normalized_weights.get('facebook_prophet', 0.0),
            'timesfm': self.normalized_weights.get('timesfm', 0.0)
        }
        
        # Additional prediction methods
        self.include_moving_average = include_moving_average and moving_average_weight > 0
        self.include_linear_trend = include_linear_trend and linear_trend_weight > 0
        
        # Create plots directory
        if self.save_plots:
            self.plots_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize individual predictors (only for models with weight > 0)
        self.neural_prophet_predictor = None
        self.facebook_prophet_predictor = None
        self.timesfm_predictor = None
        
        # Store individual predictions for analysis
        self.individual_predictions = {}
        
        # Simplified initialization message
        active_methods = [f"{k}: {v:.1%}" for k, v in self.normalized_weights.items()]
        print(f"🎯 Ensemble initialized: {', '.join(active_methods)}")
        
    def prepare_models(self, fast_mode=False):
        """
        Prepare and train all ensemble models (only those with weight > 0).
        
        Args:
            fast_mode (bool): Whether to use fast training mode
        """
        print("🔥 Preparing forecasting models...")
        
        # Determine which models to use
        use_fast = self.use_fast_models or fast_mode
        
        # Only prepare models with weight > 0
        active_models = [model for model, weight in self.model_weights.items() if weight > 0]
        
        model_count = 0
        
        # 1. Neural Prophet Model
        if 'neural_prophet' in active_models:
            try:
                model_count += 1
                print(f"📊 [{model_count}/{len(active_models)}] Neural Prophet...")
                if use_fast:
                    self.neural_prophet_predictor = FastNeuralTweetPredictor(
                        data_path=self.data_processor.data_path,
                        save_plots=False  # Disable individual plots
                    )
                    self.neural_prophet_predictor.prepare_model()
                else:
                    # Use Enhanced Neural Prophet by default
                    self.neural_prophet_predictor = EnhancedNeuralTweetPredictor(
                        data_path=self.data_processor.data_path,
                        save_plots=False
                    )
                    self.neural_prophet_predictor.prepare_model()  # Enhanced Neural Prophet uses prepare_model() not prepare_models()
                
                print("   ✅ Ready")
                
            except Exception as e:
                print(f"   ❌ Enhanced failed: {e}")
                # Fallback to basic Neural Prophet
                try:
                    self.neural_prophet_predictor = NeuralTweetPredictor(
                        data_path=self.data_processor.data_path,
                        save_plots=False
                    )
                    self.neural_prophet_predictor.prepare_model()
                    print("   ✅ Ready (Basic)")
                except Exception as e2:
                    print(f"   ❌ Both failed: {e2}")
                    self.neural_prophet_predictor = None
                    self.model_weights['neural_prophet'] = 0.0
        
        # 2. Facebook Prophet Model
        if 'facebook_prophet' in active_models:
            try:
                model_count += 1
                print(f"📈 [{model_count}/{len(active_models)}] Facebook Prophet...")
                # Use Enhanced Facebook Prophet by default
                self.facebook_prophet_predictor = EnhancedFacebookTweetPredictor(
                    data_path=self.data_processor.data_path,
                    save_plots=False
                )
                self.facebook_prophet_predictor.prepare_models()  # Enhanced model uses prepare_models()
                
                print("   ✅ Ready")
                
            except Exception as e:
                print(f"   ❌ Enhanced failed: {e}")
                # Fallback to basic Prophet
                try:
                    self.facebook_prophet_predictor = FacebookTweetPredictor(
                        data_path=self.data_processor.data_path,
                        save_plots=False
                    )
                    self.facebook_prophet_predictor.prepare_model()
                    print("   ✅ Ready (Basic)")
                except Exception as e2:
                    print(f"   ❌ Both failed: {e2}")
                    self.facebook_prophet_predictor = None
                    self.model_weights['facebook_prophet'] = 0.0
        
        # 3. TimesFM Model
        if 'timesfm' in active_models:
            try:
                model_count += 1
                print(f"🤖 [{model_count}/{len(active_models)}] TimesFM...")
                if use_fast:
                    self.timesfm_predictor = FastTimesFMTweetPredictor(
                        data_path=self.data_processor.data_path,
                        save_plots=False
                    )
                    self.timesfm_predictor.prepare_model()
                else:
                    # Use Enhanced TimesFM by default
                    try:
                        self.timesfm_predictor = EnhancedTimesFMTweetPredictor(
                            data_path=self.data_processor.data_path,
                            save_plots=False
                        )
                        self.timesfm_predictor.prepare_models()  # Enhanced version uses prepare_models()
                    except ImportError:
                        # Fallback to basic TimesFM if enhanced not available
                        self.timesfm_predictor = TimesFMTweetPredictor(
                            data_path=self.data_processor.data_path,
                            save_plots=False
                        )
                        self.timesfm_predictor.prepare_model()
                
                print("   ✅ Ready")
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                self.timesfm_predictor = None
        
        # Renormalize weights after any failures
        self._renormalize_weights()
        
        active_models_final = sum(1 for p in [self.neural_prophet_predictor, 
                                            self.facebook_prophet_predictor, 
                                            self.timesfm_predictor] if p is not None)
        
        print(f"\n🎯 Ensemble ready with {active_models_final}/{len(active_models)} models active")
        print(f"Final model weights: {self.model_weights}")
        
        # Check if we have any prediction methods available
        has_prediction_methods = (active_models_final > 0 or 
                                 self.include_moving_average or 
                                 self.include_linear_trend)
        
        if not has_prediction_methods:
            raise RuntimeError("No models or prediction methods available!")
    
    def _renormalize_weights(self):
        """Renormalize weights after model failures."""
        active_weights = {k: v for k, v in self.model_weights.items() if v > 0}
        
        # Check if corresponding predictor is available
        if self.neural_prophet_predictor is None:
            active_weights.pop('neural_prophet', None)
        if self.facebook_prophet_predictor is None:
            active_weights.pop('facebook_prophet', None)
        if self.timesfm_predictor is None:
            active_weights.pop('timesfm', None)
        
        if active_weights:
            total_weight = sum(active_weights.values())
            # Renormalize
            for model in self.model_weights:
                if model in active_weights:
                    self.model_weights[model] = active_weights[model] / total_weight
                else:
                    self.model_weights[model] = 0.0
    
    def calculate_moving_average_prediction(self, current_time=None, window_days=7):
        """
        Calculate moving average prediction based on historical data.
        
        Args:
            current_time (datetime): Current time for prediction context
            window_days (int): Number of days to use for moving average
            
        Returns:
            dict: Moving average prediction
        """
        df = self.data_processor.load_and_prepare_data()
        
        # Get current week data
        week_data = self.data_processor.get_current_week_data(current_time)
        current_tweets = week_data['current_week_tweets']
        
        # Calculate moving average of weekly tweet counts
        df['week'] = df['ds'].dt.isocalendar().week
        df['year'] = df['ds'].dt.year
        weekly_counts = df.groupby(['year', 'week'])['y'].sum().reset_index()
        
        # Get last N weeks
        recent_weeks = weekly_counts.tail(window_days)['y'].values
        
        if len(recent_weeks) > 0:
            ma_prediction = np.mean(recent_weeks)
        else:
            ma_prediction = df['y'].mean() * 7  # Fallback to daily average * 7
        
        # Adjust for current tweets
        remaining_prediction = max(0, ma_prediction - current_tweets)
        
        return {
            'total_predicted': ma_prediction,
            'current_tweets': current_tweets,
            'predicted_remaining': remaining_prediction,
            'confidence_interval': {
                'lower': ma_prediction * 0.8,
                'upper': ma_prediction * 1.2
            },
            'method': f'{window_days}d_moving_average'
        }
    
    def calculate_linear_trend_prediction(self, current_time=None, trend_days=14):
        """
        Calculate linear trend prediction based on recent data.
        
        Args:
            current_time (datetime): Current time for prediction context
            trend_days (int): Number of days to use for trend calculation
            
        Returns:
            dict: Linear trend prediction
        """
        df = self.data_processor.load_and_prepare_data()
        
        # Get current week data
        week_data = self.data_processor.get_current_week_data(current_time)
        current_tweets = week_data['current_week_tweets']
        
        # Get recent data for trend calculation
        recent_data = df.tail(trend_days).copy()
        
        if len(recent_data) < 3:
            # Fallback to moving average if insufficient data
            return self.calculate_moving_average_prediction(current_time)
        
        # Calculate linear trend
        x = np.arange(len(recent_data))
        y = recent_data['y'].values
        
        # Fit linear regression
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = coeffs
        
        # Project trend for remaining days in week
        days_remaining = week_data['time_remaining'].days + 1
        trend_prediction = slope * days_remaining + intercept * days_remaining
        
        # Total prediction
        total_prediction = current_tweets + max(0, trend_prediction)
        
        # Estimate confidence based on trend variance
        residuals = y - (slope * x + intercept)
        trend_std = np.std(residuals) * np.sqrt(days_remaining)
        
        return {
            'total_predicted': total_prediction,
            'current_tweets': current_tweets,
            'predicted_remaining': max(0, trend_prediction),
            'confidence_interval': {
                'lower': max(current_tweets, total_prediction - 1.96 * trend_std),
                'upper': total_prediction + 1.96 * trend_std
            },
            'method': f'{trend_days}d_linear_trend',
            'slope': slope,
            'daily_trend': slope
        }
    
    def predict_remaining_tweets(self, current_time=None):
        """
        Generate ensemble predictions by combining individual model predictions and additional methods.
        
        Args:
            current_time (datetime): Current time for prediction context
            
        Returns:
            dict: Ensemble prediction results
        """
        # Check if any models are available
        available_models = [p for p in [self.neural_prophet_predictor, 
                                       self.facebook_prophet_predictor, 
                                       self.timesfm_predictor] if p is not None]
        
        if not available_models and not self.include_moving_average and not self.include_linear_trend:
            raise RuntimeError("No models or prediction methods available!")
        
        print("🔮 Generating predictions...")
        
        # Collect individual predictions
        individual_results = {}
        
        # Neural Prophet prediction
        if self.neural_prophet_predictor is not None and self.model_weights['neural_prophet'] > 0:
            try:
                # Check if it's enhanced version
                if hasattr(self.neural_prophet_predictor, 'generate_enhanced_predictions'):
                    neural_pred = self.neural_prophet_predictor.generate_enhanced_predictions(current_time)
                else:
                    neural_pred = self.neural_prophet_predictor.generate_predictions(current_time)
                individual_results['neural_prophet'] = neural_pred
                
                # Extract total_predicted for display (handle nested format)
                if 'prediction_results' in neural_pred:
                    total_pred = neural_pred['prediction_results'].get('total_predicted', 'N/A')
                else:
                    total_pred = neural_pred.get('total_predicted', 'N/A')
                print(f"   📊 Neural Prophet: {total_pred:.1f} tweets" if isinstance(total_pred, (int, float)) else f"   📊 Neural Prophet: {total_pred}")
            except Exception as e:
                print(f"   ❌ Neural Prophet failed: {e}")
        
        # Facebook Prophet prediction
        if self.facebook_prophet_predictor is not None and self.model_weights['facebook_prophet'] > 0:
            try:
                if hasattr(self.facebook_prophet_predictor, 'generate_enhanced_predictions'):
                    # Enhanced version
                    facebook_pred = self.facebook_prophet_predictor.generate_enhanced_predictions(current_time)
                else:
                    # Basic version
                    facebook_pred = self.facebook_prophet_predictor.generate_predictions(current_time)
                individual_results['facebook_prophet'] = facebook_pred
                
                # Extract total_predicted for display
                total_pred = facebook_pred.get('total_predicted', 'N/A')
                print(f"   📈 Facebook Prophet: {total_pred:.1f} tweets" if isinstance(total_pred, (int, float)) else f"   📈 Facebook Prophet: {total_pred}")
            except Exception as e:
                print(f"   ❌ Facebook Prophet failed: {e}")
        
        # TimesFM prediction
        if self.timesfm_predictor is not None and self.model_weights['timesfm'] > 0:
            try:
                # Enhanced TimesFM uses generate_predictions(), not generate_enhanced_predictions()
                if hasattr(self.timesfm_predictor, 'models') and hasattr(self.timesfm_predictor, '_create_ensemble_prediction'):
                    # This is Enhanced TimesFM
                    timesfm_pred = self.timesfm_predictor.generate_predictions(current_time)
                else:
                    # This is basic TimesFM
                    timesfm_pred = self.timesfm_predictor.generate_predictions(current_time)
                individual_results['timesfm'] = timesfm_pred
                
                # Extract total_predicted for display (handle different enhanced formats)
                if 'ensemble_results' in timesfm_pred:
                    # Enhanced TimesFM format: {'ensemble_results': {'total_predicted': ...}}
                    total_pred = timesfm_pred['ensemble_results'].get('total_predicted', 'N/A')
                elif 'prediction_results' in timesfm_pred:
                    # Basic TimesFM format: {'prediction_results': {'total_predicted': ...}}
                    total_pred = timesfm_pred['prediction_results'].get('total_predicted', 'N/A')
                else:
                    # Fallback
                    total_pred = timesfm_pred.get('total_predicted', 'N/A')
                print(f"   🤖 TimesFM: {total_pred:.1f} tweets" if isinstance(total_pred, (int, float)) else f"   🤖 TimesFM: {total_pred}")
            except Exception as e:
                print(f"   ❌ TimesFM failed: {e}")
        
        # Additional prediction methods
        additional_predictions = {}
        
        if self.include_moving_average:
            try:
                ma_pred = self.calculate_moving_average_prediction(current_time)
                additional_predictions['moving_average'] = ma_pred
                print(f"   📊 Moving Average: {ma_pred['total_predicted']:.1f} tweets")
            except Exception as e:
                print(f"   ❌ Moving Average failed: {e}")
        
        if self.include_linear_trend:
            try:
                trend_pred = self.calculate_linear_trend_prediction(current_time)
                additional_predictions['linear_trend'] = trend_pred
                print(f"   📈 Linear Trend: {trend_pred['total_predicted']:.1f} tweets")
            except Exception as e:
                print(f"   ❌ Linear Trend failed: {e}")
        
        # Store individual predictions for analysis
        self.individual_predictions = {**individual_results, **additional_predictions}
        
        if not individual_results and not additional_predictions:
            raise RuntimeError("All predictions failed!")
        
        # Combine predictions using weighted average (main models) + additional methods
        ensemble_prediction = self._combine_predictions(individual_results, additional_predictions, current_time)
        
        print(f"\n🎯 ENSEMBLE RESULT: {ensemble_prediction['total_predicted']:.1f} tweets")
        print(f"   Confidence: {ensemble_prediction['confidence_interval']['lower']:.1f} - {ensemble_prediction['confidence_interval']['upper']:.1f}")
        
        return ensemble_prediction
    
    def _combine_predictions(self, individual_results, additional_predictions, current_time):
        """
        Combine individual model predictions using the normalized weight system.
        
        Args:
            individual_results (dict): Individual model predictions
            additional_predictions (dict): Additional prediction methods
            current_time (datetime): Current time for context
            
        Returns:
            dict: Combined ensemble prediction
        """
        predictions = []
        weights = []
        confidence_intervals = []
        
        # Extract predictions and weights from main models using normalized weights
        for model_name, result in individual_results.items():
            model_weight = self.normalized_weights.get(model_name, 0.0)
            if model_weight > 0:
                # Handle different return formats from individual models
                total_predicted = None
                confidence_interval = None
                
                # Enhanced TimesFM format: {'ensemble_results': {'total_predicted': ...}}
                if 'ensemble_results' in result:
                    total_predicted = result['ensemble_results'].get('total_predicted')
                    if 'confidence_interval' in result['ensemble_results']:
                        ci = result['ensemble_results']['confidence_interval']
                        if isinstance(ci, dict):
                            confidence_interval = (ci['lower'], ci['upper'])
                        else:
                            confidence_interval = ci
                
                # Neural Prophet format: {'prediction_results': {'total_predicted': ...}}
                elif 'prediction_results' in result:
                    total_predicted = result['prediction_results'].get('total_predicted')
                    if 'confidence_interval' in result['prediction_results']:
                        ci = result['prediction_results']['confidence_interval']
                        if isinstance(ci, dict):
                            confidence_interval = (ci['lower'], ci['upper'])
                        else:
                            confidence_interval = ci
                
                # Facebook Prophet Enhanced format: {'total_predicted': ...}
                elif 'total_predicted' in result:
                    total_predicted = result['total_predicted']
                    if 'confidence_interval' in result:
                        ci = result['confidence_interval']
                        if isinstance(ci, dict):
                            confidence_interval = (ci['lower'], ci['upper'])
                        elif isinstance(ci, (list, tuple)) and len(ci) == 2:
                            confidence_interval = ci
                        else:
                            confidence_interval = ci
                
                # If still no total_predicted, skip this model
                if total_predicted is None:
                    print(f"⚠️  Warning: Could not extract total_predicted from {model_name}")
                    continue
                
                predictions.append(total_predicted)
                weights.append(model_weight)
                
                # Handle confidence intervals
                if confidence_interval is None:
                    # Estimate confidence interval as ±10%
                    ci_lower = total_predicted * 0.9
                    ci_upper = total_predicted * 1.1
                    confidence_interval = (ci_lower, ci_upper)
                
                confidence_intervals.append(confidence_interval)
        
        # Add additional prediction methods using normalized weights
        for method_name, result in additional_predictions.items():
            method_weight = self.normalized_weights.get(method_name, 0.0)
            if method_weight > 0:
                total_predicted = result.get('total_predicted')
                confidence_interval = result.get('confidence_interval', {})
                
                if total_predicted is not None:
                    predictions.append(total_predicted)
                    weights.append(method_weight)
                    
                    if isinstance(confidence_interval, dict):
                        ci = (confidence_interval.get('lower', total_predicted * 0.9), 
                              confidence_interval.get('upper', total_predicted * 1.1))
                    else:
                        ci = (total_predicted * 0.9, total_predicted * 1.1)
                    confidence_intervals.append(ci)
        
        if not predictions:
            raise ValueError("No valid predictions to combine!")
        
        # Use weights as-is since they're already normalized
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]  # Re-normalize in case some methods failed
        else:
            weights = [1.0 / len(predictions)] * len(predictions)  # Equal weights fallback
        
        # Weighted average prediction
        ensemble_prediction = sum(p * w for p, w in zip(predictions, weights))
        
        # Combine confidence intervals using weighted average
        lower_bounds = [ci[0] for ci in confidence_intervals]
        upper_bounds = [ci[1] for ci in confidence_intervals]
        
        ensemble_lower = sum(l * w for l, w in zip(lower_bounds, weights))
        ensemble_upper = sum(u * w for u, w in zip(upper_bounds, weights))
        
        # Get current week data for context
        week_data = self.data_processor.get_current_week_data(current_time)
        
        # Build model contributions
        model_contributions = {}
        
        # Add main model contributions
        main_model_names = list(individual_results.keys())
        for i, model in enumerate(main_model_names):
            if i < len(predictions) and model in individual_results:
                model_contributions[model] = {
                    'prediction': predictions[i], 
                    'weight': weights[i],
                    'type': 'main_model'
                }
        
        # Add additional method contributions  
        additional_names = list(additional_predictions.keys())
        main_count = len([m for m in main_model_names if m in individual_results])
        for i, method in enumerate(additional_names):
            pred_index = main_count + i
            if pred_index < len(predictions):
                model_contributions[method] = {
                    'prediction': predictions[pred_index], 
                    'weight': weights[pred_index],
                    'type': 'additional_method'
                }
        
        # Build ensemble result
        ensemble_result = {
            'total_predicted': ensemble_prediction,
            'confidence_interval': {
                'lower': ensemble_lower,
                'upper': ensemble_upper,
                'width': ensemble_upper - ensemble_lower
            },
            'current_tweets': week_data['current_week_tweets'],
            'predicted_remaining': ensemble_prediction - week_data['current_week_tweets'],
            'time_remaining': week_data['time_remaining'],
            'model_contributions': model_contributions,
            'individual_predictions': individual_results,
            'additional_predictions': additional_predictions,
            'ensemble_method': 'weighted_average_normalized'
        }
        
        return ensemble_result
    
    def calculate_ensemble_probabilities(self, ensemble_result):
        """
        Calculate probabilities for each tweet count range using ensemble prediction.
        
        Args:
            ensemble_result (dict): Results from predict_remaining_tweets
            
        Returns:
            dict: Probabilities for each range defined in TWEET_COUNT_FRAMES
        """
        total_predicted = ensemble_result['total_predicted']
        ci_lower = ensemble_result['confidence_interval']['lower']
        ci_upper = ensemble_result['confidence_interval']['upper']
        
        # Estimate standard deviation from confidence interval
        # Assuming 80% CI (±1.28 standard deviations)
        std_estimate = (ci_upper - ci_lower) / (2 * 1.28)
        
        # Handle edge case where std is too small
        if std_estimate < 1.0:
            std_estimate = max(1.0, total_predicted * 0.1)
        
        probabilities = {}
        
        for frame in TWEET_COUNT_FRAMES:
            frame_name = frame['name']
            min_tweets = frame['min']
            max_tweets = frame['max']
            
            if max_tweets == float('inf'):
                # For "X or more" categories
                prob = 1 - stats.norm.cdf(min_tweets - 0.5, total_predicted, std_estimate)
            else:
                # For range categories
                prob_lower = stats.norm.cdf(min_tweets - 0.5, total_predicted, std_estimate)
                prob_upper = stats.norm.cdf(max_tweets + 0.5, total_predicted, std_estimate)
                prob = prob_upper - prob_lower
            
            probabilities[frame_name] = max(0, min(1, prob))
        
        # Normalize probabilities to sum to 1
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            probabilities = {k: v / total_prob for k, v in probabilities.items()}
        
        return probabilities
    
    def generate_predictions(self, current_time=None):
        """
        Generate complete ensemble predictions with probabilities.
        
        Args:
            current_time (datetime): Current time for prediction context
            
        Returns:
            dict: Complete prediction summary
        """
        if all(p is None for p in [self.neural_prophet_predictor,
                                  self.facebook_prophet_predictor,
                                  self.timesfm_predictor]):
            self.prepare_models()
        
        # Get ensemble prediction
        ensemble_result = self.predict_remaining_tweets(current_time)
        
        # Calculate probabilities
        probabilities = self.calculate_ensemble_probabilities(ensemble_result)
        
        # Build complete summary
        summary = {
            'current_tweets': ensemble_result['current_tweets'],
            'predicted_remaining': ensemble_result['predicted_remaining'],
            'total_predicted': ensemble_result['total_predicted'],
            'confidence_interval': ensemble_result['confidence_interval'],
            'time_remaining': ensemble_result['time_remaining'],
            'predictions_by_frame': {
                frame_name: {
                    'probability': prob,
                    'range': f"{TWEET_COUNT_FRAMES[i]['min']}-{TWEET_COUNT_FRAMES[i]['max']}" 
                            if TWEET_COUNT_FRAMES[i]['max'] != float('inf') 
                            else f"{TWEET_COUNT_FRAMES[i]['min']}+",
                    'min': TWEET_COUNT_FRAMES[i]['min'],
                    'max': TWEET_COUNT_FRAMES[i]['max']
                }
                for i, (frame_name, prob) in enumerate(probabilities.items())
            },
            'model_contributions': ensemble_result['model_contributions'],
            'individual_predictions': ensemble_result['individual_predictions'],
            'ensemble_method': 'weighted_average',
            'model_weights': self.model_weights
        }
        
        return summary
    
    def print_prediction_summary(self, prediction_summary):
        """
        Print a simplified ensemble prediction summary.
        
        Args:
            prediction_summary (dict): Results from generate_predictions()
        """
        print("\n" + "="*50)
        print("🔥 ENSEMBLE PREDICTION SUMMARY")
        print("="*50)
        
        print(f"Current tweets: {prediction_summary['current_tweets']}")
        print(f"Total predicted: {prediction_summary['total_predicted']:.1f}")
        print(f"80% Confidence: {prediction_summary['confidence_interval']['lower']:.1f} - {prediction_summary['confidence_interval']['upper']:.1f}")
        
        print(f"\n🤖 MODEL CONTRIBUTIONS:")
        for model, contrib in prediction_summary['model_contributions'].items():
            print(f"   {model}: {contrib['prediction']:.1f} tweets (weight: {contrib['weight']:.3f})")
        
        print(f"\n📊 TOP PROBABILITIES:")
        
        # Sort by probability (descending) and show top 8
        sorted_frames = sorted(
            prediction_summary['predictions_by_frame'].items(),
            key=lambda x: x[1]['probability'],
            reverse=True
        )
        
        for frame_name, frame_data in sorted_frames[:8]:
            prob = frame_data['probability']
            range_str = frame_data['range']
            print(f"{range_str:20s}: {prob*100:5.1f}%")
        
        print("\n" + "="*50)
    
    def plot_predictions(self, prediction_summary, save_path=None):
        """
        Create comprehensive ensemble prediction plots.
        
        Args:
            prediction_summary (dict): Results from generate_predictions()
            save_path (str): Optional custom save path for plots
        """
        if not self.save_plots and save_path is None:
            return
        
        # Create comprehensive plots
        fig = plt.figure(figsize=(20, 16))
        
        # Plot 1: Model Comparison (Top Left)
        ax1 = plt.subplot(3, 3, 1)
        models = list(prediction_summary['model_contributions'].keys())
        predictions = [prediction_summary['model_contributions'][m]['prediction'] for m in models]
        weights = [prediction_summary['model_contributions'][m]['weight'] for m in models]
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1'][:len(models)]
        bars = ax1.bar(models, predictions, color=colors, alpha=0.7)
        
        # Add weight labels
        for i, (bar, weight) in enumerate(zip(bars, weights)):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                    f'w={weight:.2f}', ha='center', va='bottom', fontweight='bold')
        
        ax1.axhline(y=prediction_summary['total_predicted'], color='red', linestyle='--', 
                   label=f'Ensemble: {prediction_summary["total_predicted"]:.1f}')
        ax1.set_title('Model Predictions Comparison')
        ax1.set_ylabel('Predicted Tweets')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Confidence Intervals (Top Center)
        ax2 = plt.subplot(3, 3, 2)
        
        # Extract individual confidence intervals if available
        individual_cis = []
        for model in models:
            if model in prediction_summary['individual_predictions']:
                pred = prediction_summary['individual_predictions'][model]
                
                # Handle different return formats
                total_predicted = None
                confidence_interval = None
                
                # Enhanced TimesFM format: {'ensemble_results': {'total_predicted': ...}}
                if 'ensemble_results' in pred:
                    total_predicted = pred['ensemble_results'].get('total_predicted')
                    if 'confidence_interval' in pred['ensemble_results']:
                        ci = pred['ensemble_results']['confidence_interval']
                        if isinstance(ci, dict):
                            confidence_interval = (ci['lower'], ci['upper'])
                        else:
                            confidence_interval = ci
                
                # Neural Prophet format: {'prediction_results': {'total_predicted': ...}}
                elif 'prediction_results' in pred:
                    total_predicted = pred['prediction_results'].get('total_predicted')
                    if 'confidence_interval' in pred['prediction_results']:
                        ci = pred['prediction_results']['confidence_interval']
                        if isinstance(ci, dict):
                            confidence_interval = (ci['lower'], ci['upper'])
                        else:
                            confidence_interval = ci
                
                # Facebook Prophet Enhanced format: {'total_predicted': ...}
                elif 'total_predicted' in pred:
                    total_predicted = pred['total_predicted']
                    if 'confidence_interval' in pred:
                        ci = pred['confidence_interval']
                        if isinstance(ci, dict):
                            confidence_interval = (ci['lower'], ci['upper'])
                        elif isinstance(ci, (list, tuple)) and len(ci) == 2:
                            confidence_interval = ci
                        else:
                            confidence_interval = ci
                
                if confidence_interval is not None:
                    individual_cis.append(confidence_interval)
                elif total_predicted is not None:
                    # Estimate confidence interval as ±10%
                    individual_cis.append((total_predicted * 0.9, total_predicted * 1.1))
                else:
                    # Fallback
                    individual_cis.append((100, 200))  # Default range
        
        # Plot individual CIs
        y_pos = np.arange(len(models))
        for i, (model, ci) in enumerate(zip(models, individual_cis)):
            ax2.barh(i, ci[1] - ci[0], left=ci[0], alpha=0.6, color=colors[i], 
                    label=f'{model}: [{ci[0]:.0f}, {ci[1]:.0f}]')
        
        # Plot ensemble CI
        ens_ci = prediction_summary['confidence_interval']
        ax2.barh(len(models), ens_ci['upper'] - ens_ci['lower'], left=ens_ci['lower'], 
                alpha=0.8, color='red', label=f'Ensemble: [{ens_ci["lower"]:.0f}, {ens_ci["upper"]:.0f}]')
        
        ax2.set_yticks(list(range(len(models) + 1)))
        ax2.set_yticklabels(models + ['Ensemble'])
        ax2.set_xlabel('Tweet Count')
        ax2.set_title('Confidence Intervals')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Probability Distribution (Top Right)
        ax3 = plt.subplot(3, 3, 3)
        frames = list(prediction_summary['predictions_by_frame'].keys())
        probs = [prediction_summary['predictions_by_frame'][f]['probability'] for f in frames]
        
        # Show top 8 probabilities
        top_indices = np.argsort(probs)[-8:]
        top_frames = [frames[i] for i in top_indices]
        top_probs = [probs[i] for i in top_indices]
        
        colors_prob = plt.cm.viridis(np.linspace(0, 1, len(top_frames)))
        bars = ax3.barh(range(len(top_frames)), top_probs, color=colors_prob)
        ax3.set_yticks(range(len(top_frames)))
        ax3.set_yticklabels(top_frames, fontsize=9)
        ax3.set_xlabel('Probability')
        ax3.set_title('Top 8 Most Likely Ranges')
        ax3.grid(True, alpha=0.3)
        
        # Add probability labels
        for bar, prob in zip(bars, top_probs):
            ax3.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                    f'{prob:.3f}', va='center', fontsize=8)
        
        # Plot 4-6: Individual Model Details (Second Row)
        for i, model in enumerate(models[:3]):
            ax = plt.subplot(3, 3, 4 + i)
            
            if model in prediction_summary['individual_predictions']:
                pred_data = prediction_summary['individual_predictions'][model]
                
                # Handle different return formats to extract values
                total_predicted = None
                current_tweets = None
                predicted_remaining = None
                
                # Enhanced TimesFM format: {'ensemble_results': {'total_predicted': ...}}
                if 'ensemble_results' in pred_data:
                    total_predicted = pred_data['ensemble_results'].get('total_predicted')
                    current_tweets = pred_data['ensemble_results'].get('current_tweets')
                    predicted_remaining = pred_data['ensemble_results'].get('remaining_tweets')
                
                # Neural Prophet format: {'prediction_results': {'total_predicted': ...}}
                elif 'prediction_results' in pred_data:
                    total_predicted = pred_data['prediction_results'].get('total_predicted')
                    current_tweets = pred_data['prediction_results'].get('current_tweets')
                    predicted_remaining = pred_data['prediction_results'].get('remaining_tweets')
                
                # Facebook Prophet Enhanced format: {'total_predicted': ...}
                elif 'total_predicted' in pred_data:
                    total_predicted = pred_data['total_predicted']
                    current_tweets = pred_data.get('current_tweets')
                    predicted_remaining = pred_data.get('predicted_remaining')
                
                # Calculate missing values if needed
                if total_predicted is not None and current_tweets is not None and predicted_remaining is None:
                    predicted_remaining = total_predicted - current_tweets
                elif total_predicted is not None and predicted_remaining is not None and current_tweets is None:
                    current_tweets = total_predicted - predicted_remaining
                
                # Use fallback values if still missing
                if current_tweets is None:
                    current_tweets = prediction_summary.get('current_tweets', 0)
                if total_predicted is None:
                    total_predicted = 150  # Default fallback
                if predicted_remaining is None:
                    predicted_remaining = total_predicted - current_tweets
                
                # Plot prediction vs current
                categories = ['Current', 'Predicted\nRemaining', 'Total']
                values = [current_tweets, predicted_remaining, total_predicted]
                
                bars = ax.bar(categories, values, color=[colors[i], colors[i], 'darkred'], alpha=0.7)
                ax.set_title(f'{model.replace("_", " ").title()} Details')
                ax.set_ylabel('Tweet Count')
                
                # Add value labels
                for bar, value in zip(bars, values):
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                           f'{value:.1f}', ha='center', va='bottom', fontweight='bold')
            
            ax.grid(True, alpha=0.3)
        
        # Plot 7: Time Remaining Context (Bottom Left)
        ax7 = plt.subplot(3, 3, 7)
        time_remaining = prediction_summary['time_remaining']
        
        # Convert to hours for display
        hours_remaining = time_remaining.total_seconds() / 3600
        
        # Create a simple time visualization
        categories = ['Time\nElapsed', 'Time\nRemaining']
        # Assume 7 days total (168 hours)
        total_hours = 168
        elapsed_hours = total_hours - hours_remaining
        
        values = [elapsed_hours, hours_remaining]
        colors_time = ['lightcoral', 'lightblue']
        
        bars = ax7.bar(categories, values, color=colors_time, alpha=0.7)
        ax7.set_title('Time Context')
        ax7.set_ylabel('Hours')
        
        for bar, value in zip(bars, values):
            ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                    f'{value:.1f}h', ha='center', va='bottom', fontweight='bold')
        
        ax7.grid(True, alpha=0.3)
        
        # Plot 8: Ensemble vs Individual Comparison (Bottom Center)
        ax8 = plt.subplot(3, 3, 8)
        
        all_predictions = predictions + [prediction_summary['total_predicted']]
        all_labels = [m.replace('_', ' ').title() for m in models] + ['Ensemble']
        all_colors = colors + ['red']
        
        bars = ax8.bar(all_labels, all_predictions, color=all_colors, alpha=0.7)
        ax8.set_title('Final Comparison')
        ax8.set_ylabel('Predicted Tweets')
        ax8.tick_params(axis='x', rotation=45)
        
        # Highlight ensemble
        bars[-1].set_alpha(0.9)
        bars[-1].set_edgecolor('darkred')
        bars[-1].set_linewidth(2)
        
        ax8.grid(True, alpha=0.3)
        
        # Plot 9: Model Weights (Bottom Right)
        ax9 = plt.subplot(3, 3, 9)
        
        weights_display = [prediction_summary['model_weights'][m] for m in models]
        wedges, texts, autotexts = ax9.pie(weights_display, labels=[m.replace('_', ' ').title() for m in models], 
                                          colors=colors, autopct='%1.1f%%', startangle=90)
        ax9.set_title('Model Weights in Ensemble')
        
        plt.tight_layout()
        
        # Save plot
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        elif self.save_plots:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = self.plots_dir / f"ensemble_prediction_{timestamp}.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 Ensemble plots saved to: {save_path}")
        
        if self.save_plots:
            plt.show()
        else:
            plt.close() 