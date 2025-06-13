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

# Set all relevant loggers to CRITICAL level to suppress everything
loggers_to_suppress = [
    'neuralprophet',
    'prophet', 
    'cmdstanpy',
    'pytorch_lightning',
    'pytorch_lightning.utilities.rank_zero',
    'pytorch_lightning.accelerators.gpu',
    'pytorch_lightning.callbacks',
    'pytorch_lightning.core',
    'pytorch_lightning.utilities.distributed',
    'pytorch_lightning.accelerators',
    'pytorch_lightning.trainer',
    'pytorch_lightning.utilities.warnings',
    'NP.config',
    'NP.forecaster',
    'NP.df_utils',
    'NP.data.processing',
    'NP.data.splitting'
]

for logger_name in loggers_to_suppress:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    logging.getLogger(logger_name).disabled = True

# Suppress warnings
warnings.filterwarnings('ignore')
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=RuntimeWarning)

# Suppress matplotlib warnings
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import os
from scipy import stats
import contextlib
import io

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants import TWEET_COUNT_FRAMES, ET_TIMEZONE

from .data_processor import EnsembleTweetDataProcessor
from prediction_algos.neural_prophet import NeuralTweetPredictor, FastNeuralTweetPredictor, EnhancedNeuralTweetPredictor
from prediction_algos.facebook_prophet import TweetPredictor as FacebookTweetPredictor, EnhancedTweetPredictor as EnhancedFacebookTweetPredictor
from prediction_algos.timesfm import TimesFMTweetPredictor, FastTimesFMTweetPredictor, EnhancedTimesFMTweetPredictor

# Import basic prophet from polymarket_predictor
from src.polymarket_predictor.prophet_prediction import predict_with_prophet

# Suppress TensorFlow/PyTorch warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['PYTHONWARNINGS'] = 'ignore'

@contextlib.contextmanager
def suppress_stdout_stderr():
    """Context manager to suppress all stdout and stderr output."""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = devnull
            sys.stderr = devnull
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

class EnsembleTweetPredictor:
    """Ensemble predictor combining multiple forecasting models with weight control and additional prediction methods."""
    
    def __init__(self, data_path=None, save_plots=True, use_fast_models=False, 
                 neural_prophet_weight=0.17, facebook_prophet_weight=0.25, timesfm_weight=0.30,
                 basic_prophet_weight=0.25, moving_average_weight=0.015, linear_trend_weight=0.015,
                 include_basic_prophet=True, include_moving_average=True, include_linear_trend=True,
                 random_seed=42):
        """
        Initialize the ensemble predictor.
        
        Args:
            data_path (str): Path to tweet data CSV file
            save_plots (bool): Whether to save prediction plots
            use_fast_models (bool): Whether to use fast versions of individual models
            neural_prophet_weight (float): Weight for Neural Prophet model (0 to exclude)
            facebook_prophet_weight (float): Weight for Facebook Prophet model (0 to exclude)
            timesfm_weight (float): Weight for TimesFM model (0 to exclude)
            basic_prophet_weight (float): Weight for Basic Prophet model (0 to exclude)
            moving_average_weight (float): Weight for moving average predictions (0 to exclude)
            linear_trend_weight (float): Weight for linear trend predictions (0 to exclude)
            include_basic_prophet (bool): Whether to include basic prophet predictions
            include_moving_average (bool): Whether to include moving average predictions
            include_linear_trend (bool): Whether to include linear trend predictions
            random_seed (int): Random seed for reproducible results
        """
        self.data_processor = EnsembleTweetDataProcessor(data_path)
        self.save_plots = save_plots
        self.use_fast_models = use_fast_models
        self.random_seed = random_seed
        self.plots_dir = Path("src/prediction_algos/ensemble/plots")
        
        # Store all weights
        self.raw_weights = {
            'neural_prophet': neural_prophet_weight,
            'facebook_prophet': facebook_prophet_weight,
            'timesfm': timesfm_weight,
            'basic_prophet': basic_prophet_weight,
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
            'timesfm': self.normalized_weights.get('timesfm', 0.0),
            'basic_prophet': self.normalized_weights.get('basic_prophet', 0.0)
        }
        
        # Additional prediction methods
        self.include_basic_prophet = include_basic_prophet and basic_prophet_weight > 0
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
        print("🔥 Preparing models...")
        
        # Determine which models to use
        use_fast = self.use_fast_models or fast_mode
        
        # Only prepare models with weight > 0 (basic prophet doesn't need preparation)
        active_models = [model for model, weight in self.model_weights.items() 
                        if weight > 0 and model != 'basic_prophet']
        
        # 1. Neural Prophet Model
        if 'neural_prophet' in active_models:
            try:
                print("📊 Neural Prophet...", end=" ", flush=True)
                if use_fast:
                    with suppress_stdout_stderr():
                        self.neural_prophet_predictor = FastNeuralTweetPredictor(
                            data_path=self.data_processor.data_path,
                            save_plots=False  # Disable individual plots
                        )
                        # Set random seed if supported
                        if hasattr(self.neural_prophet_predictor, 'set_random_seed'):
                            self.neural_prophet_predictor.set_random_seed(self.random_seed)
                        self.neural_prophet_predictor.prepare_model()
                    print("✅ (Fast)")
                else:
                    # Use Basic Neural Prophet by default (faster, shows progress)
                    print("") # New line for progress display
                    self.neural_prophet_predictor = NeuralTweetPredictor(
                        data_path=self.data_processor.data_path,
                        save_plots=False
                    )
                    # Set random seed if supported
                    if hasattr(self.neural_prophet_predictor, 'set_random_seed'):
                        self.neural_prophet_predictor.set_random_seed(self.random_seed)
                    # Don't suppress output so we can see epoch progress
                    self.neural_prophet_predictor.prepare_model()
                    print("✅ Neural Prophet ready")
                
            except Exception as e:
                print("❌ Basic failed, trying Enhanced...", end=" ", flush=True)
                # Fallback to Enhanced Neural Prophet
                try:
                    with suppress_stdout_stderr():
                        self.neural_prophet_predictor = EnhancedNeuralTweetPredictor(
                            data_path=self.data_processor.data_path,
                            save_plots=False,
                            random_seed=self.random_seed
                        )
                        self.neural_prophet_predictor.prepare_models()  # Enhanced Neural Prophet uses prepare_models() (plural)
                    print("✅ (Enhanced)")
                except Exception as e2:
                    print(f"❌ Failed")
                    self.neural_prophet_predictor = None
                    self.model_weights['neural_prophet'] = 0.0
        
        # 2. Facebook Prophet Model
        if 'facebook_prophet' in active_models:
            try:
                print("📈 Facebook Prophet...", end=" ", flush=True)
                with suppress_stdout_stderr():
                    # Use Enhanced Facebook Prophet by default
                    self.facebook_prophet_predictor = EnhancedFacebookTweetPredictor(
                        data_path=self.data_processor.data_path,
                        save_plots=False,
                        random_seed=self.random_seed
                    )
                    self.facebook_prophet_predictor.prepare_models()  # Enhanced model uses prepare_models()
                
                print("✅")
                
            except Exception as e:
                print("❌ Enhanced failed, trying basic...", end=" ", flush=True)
                # Fallback to basic Prophet
                try:
                    with suppress_stdout_stderr():
                        self.facebook_prophet_predictor = FacebookTweetPredictor(
                            data_path=self.data_processor.data_path,
                            save_plots=False
                        )
                        # Set random seed if supported
                        if hasattr(self.facebook_prophet_predictor, 'set_random_seed'):
                            self.facebook_prophet_predictor.set_random_seed(self.random_seed)
                        self.facebook_prophet_predictor.prepare_model()
                    print("✅ (Basic)")
                except Exception as e2:
                    print(f"❌ Failed")
                    self.facebook_prophet_predictor = None
                    self.model_weights['facebook_prophet'] = 0.0
        
        # 3. TimesFM Model
        if 'timesfm' in active_models:
            try:
                print("🤖 TimesFM...", end=" ", flush=True)
                with suppress_stdout_stderr():
                    if use_fast:
                        self.timesfm_predictor = FastTimesFMTweetPredictor(
                            data_path=self.data_processor.data_path,
                            save_plots=False
                        )
                        # Set random seed if supported
                        if hasattr(self.timesfm_predictor, 'set_random_seed'):
                            self.timesfm_predictor.set_random_seed(self.random_seed)
                        self.timesfm_predictor.prepare_model()
                    else:
                        # Use Enhanced TimesFM by default
                        try:
                            self.timesfm_predictor = EnhancedTimesFMTweetPredictor(
                                data_path=self.data_processor.data_path,
                                save_plots=False,
                                random_seed=self.random_seed
                            )
                            self.timesfm_predictor.prepare_models()  # Enhanced version uses prepare_models()
                        except ImportError:
                            # Fallback to basic TimesFM if enhanced not available
                            self.timesfm_predictor = TimesFMTweetPredictor(
                                data_path=self.data_processor.data_path,
                                save_plots=False
                            )
                            # Set random seed if supported
                            if hasattr(self.timesfm_predictor, 'set_random_seed'):
                                self.timesfm_predictor.set_random_seed(self.random_seed)
                            self.timesfm_predictor.prepare_model()
                
                print("✅")
                
            except Exception as e:
                print(f"❌ Failed")
                self.timesfm_predictor = None
        
        # 4. Basic Prophet (doesn't need preparation)
        if self.include_basic_prophet and self.model_weights.get('basic_prophet', 0) > 0:
            print("🔮 Basic Prophet: ✅ (Ready)")
        
        # Renormalize weights after any failures
        self._renormalize_weights()
        
        active_models_final = sum(1 for p in [self.neural_prophet_predictor, 
                                            self.facebook_prophet_predictor, 
                                            self.timesfm_predictor] if p is not None)
        
        # Add basic prophet to count if active
        if self.include_basic_prophet and self.model_weights.get('basic_prophet', 0) > 0:
            active_models_final += 1
        
        print(f"🎯 {active_models_final}/{len([m for m in self.model_weights.keys() if self.model_weights[m] > 0])} models ready")
        
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
        # Basic prophet is always available if enabled, no need to check predictor
        
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
        
        # Check if basic prophet is available
        basic_prophet_available = (self.include_basic_prophet and 
                                 self.model_weights.get('basic_prophet', 0) > 0)
        
        if not available_models and not basic_prophet_available and not self.include_moving_average and not self.include_linear_trend:
            raise RuntimeError("No models or prediction methods available!")
        
        print("🔮 Generating predictions...")
        
        # Collect individual predictions
        individual_results = {}
        
        # Neural Prophet prediction
        if self.neural_prophet_predictor is not None and self.model_weights['neural_prophet'] > 0:
            try:
                with suppress_stdout_stderr():
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
                print(f"   📊 Neural Prophet: {total_pred:.1f}" if isinstance(total_pred, (int, float)) else f"   📊 Neural Prophet: {total_pred}")
            except Exception as e:
                print(f"   ❌ Neural Prophet failed")
        
        # Facebook Prophet prediction
        if self.facebook_prophet_predictor is not None and self.model_weights['facebook_prophet'] > 0:
            try:
                with suppress_stdout_stderr():
                    if hasattr(self.facebook_prophet_predictor, 'generate_enhanced_predictions'):
                        # Enhanced version
                        facebook_pred = self.facebook_prophet_predictor.generate_enhanced_predictions(current_time)
                    else:
                        # Basic version
                        facebook_pred = self.facebook_prophet_predictor.generate_predictions(current_time)
                individual_results['facebook_prophet'] = facebook_pred
                
                # Extract total_predicted for display
                total_pred = facebook_pred.get('total_predicted', 'N/A')
                print(f"   📈 Facebook Prophet: {total_pred:.1f}" if isinstance(total_pred, (int, float)) else f"   📈 Facebook Prophet: {total_pred}")
            except Exception as e:
                print(f"   ❌ Facebook Prophet failed")
        
        # TimesFM prediction
        if self.timesfm_predictor is not None and self.model_weights['timesfm'] > 0:
            try:
                with suppress_stdout_stderr():
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
                print(f"   🤖 TimesFM: {total_pred:.1f}" if isinstance(total_pred, (int, float)) else f"   🤖 TimesFM: {total_pred}")
            except Exception as e:
                print(f"   ❌ TimesFM failed")
        
        # Basic Prophet prediction (from polymarket_predictor)
        if self.include_basic_prophet and self.model_weights.get('basic_prophet', 0) > 0:
            try:
                # Use raw data directly - basic prophet expects original format
                # Load raw CSV data if available
                import pandas as pd
                
                if self.data_processor.data_path:
                    # Load raw data directly
                    df = pd.read_csv(self.data_processor.data_path)
                    
                    # Handle the custom timestamp format: 2024:04:18:18:41:57
                    if 'created_at' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['created_at']):
                        # Convert custom format to standard format
                        df['created_at'] = df['created_at'].str.replace(':', '-', n=2).str.replace(':', ' ', n=1)
                        df['created_at'] = pd.to_datetime(df['created_at'])
                    
                    # Add created_at_dt column if not present
                    if 'created_at_dt' not in df.columns and 'created_at' in df.columns:
                        df['created_at_dt'] = df['created_at']
                else:
                    # Fallback: convert from ensemble format if no raw data path
                    df_standard = self.data_processor.load_and_prepare_data()
                    df = pd.DataFrame()
                    df['created_at'] = df_standard['ds'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    df['created_at_dt'] = df_standard['ds']
                    # Add other columns that might be expected
                    for col in df_standard.columns:
                        if col not in ['ds', 'created_at', 'created_at_dt']:
                            df[col] = df_standard[col]
                
                # Parse time parameters
                from datetime import datetime
                from constants import POLYMARKET_START_TIME, POLYMARKET_END_TIME
                
                if current_time is None:
                    current_time = datetime.now(ET_TIMEZONE)
                
                # Parse the constant strings to datetime objects
                polymarket_start = ET_TIMEZONE.localize(
                    datetime.strptime(POLYMARKET_START_TIME, "%Y-%m-%d %H:%M:%S"), 
                    is_dst=None
                )
                polymarket_end = ET_TIMEZONE.localize(
                    datetime.strptime(POLYMARKET_END_TIME, "%Y-%m-%d %H:%M:%S"), 
                    is_dst=None
                )
                
                # Get current tweet count
                week_data = self.data_processor.get_current_week_data(current_time)
                current_tweet_count = week_data['current_week_tweets']
                
                # Import TWEET_COUNT_FRAMES for basic prophet
                from constants import TWEET_COUNT_FRAMES
                
                # Run basic prophet prediction with raw data
                basic_prophet_result = predict_with_prophet(
                    df=df,
                    polymarket_start=polymarket_start,
                    polymarket_end=polymarket_end,
                    count_frames=TWEET_COUNT_FRAMES,
                    current_tweet_count=current_tweet_count,
                    num_simulations=5000,
                    current_time=current_time,
                    random_seed=self.random_seed
                )
                
                # Convert to standard format
                if 'error' not in basic_prophet_result:
                    basic_prophet_pred = {
                        'total_predicted': basic_prophet_result['expected_count'],
                        'current_tweets': current_tweet_count,
                        'predicted_remaining': basic_prophet_result['expected_count'] - current_tweet_count,
                        'confidence_interval': {
                            'lower': basic_prophet_result['confidence_interval'][0],
                            'upper': basic_prophet_result['confidence_interval'][1]
                        },
                        'frame_probabilities': basic_prophet_result['frame_probabilities'],  # Preserve native probabilities
                        'method': 'basic_prophet'
                    }
                    individual_results['basic_prophet'] = basic_prophet_pred
                    print(f"   🔮 Basic Prophet: {basic_prophet_result['expected_count']:.1f}")
                else:
                    print(f"   ❌ Basic Prophet failed: {basic_prophet_result['error']}")
                    
            except Exception as e:
                print(f"   ❌ Basic Prophet failed: {str(e)}")
        
        # Additional prediction methods
        additional_predictions = {}
        
        if self.include_moving_average:
            try:
                ma_pred = self.calculate_moving_average_prediction(current_time)
                additional_predictions['moving_average'] = ma_pred
                print(f"   📊 Moving Average: {ma_pred['total_predicted']:.1f}")
            except Exception as e:
                print(f"   ❌ Moving Average failed")
        
        if self.include_linear_trend:
            try:
                trend_pred = self.calculate_linear_trend_prediction(current_time)
                additional_predictions['linear_trend'] = trend_pred
                print(f"   📈 Linear Trend: {trend_pred['total_predicted']:.1f}")
            except Exception as e:
                print(f"   ❌ Linear Trend failed")
        
        # Store individual predictions for analysis
        self.individual_predictions = {**individual_results, **additional_predictions}
        
        if not individual_results and not additional_predictions:
            raise RuntimeError("All predictions failed!")
        
        # Combine predictions using weighted average (main models) + additional methods
        ensemble_prediction = self._combine_predictions(individual_results, additional_predictions, current_time)
        
        print(f"🎯 ENSEMBLE: {ensemble_prediction['total_predicted']:.1f} tweets ({ensemble_prediction['confidence_interval']['lower']:.1f}-{ensemble_prediction['confidence_interval']['upper']:.1f})")
        
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
                
                # Basic Prophet format: simple dict with 'total_predicted' at top level
                if model_name == 'basic_prophet':
                    total_predicted = result.get('total_predicted')
                    if 'confidence_interval' in result:
                        ci = result['confidence_interval']
                        if isinstance(ci, dict):
                            confidence_interval = (ci['lower'], ci['upper'])
                        else:
                            confidence_interval = ci
                
                # Enhanced TimesFM format: {'ensemble_results': {'total_predicted': ...}}
                elif 'ensemble_results' in result:
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
        Calculate probabilities for each tweet count range using weighted combination of individual model probabilities.
        
        Args:
            ensemble_result (dict): Results from predict_remaining_tweets
            
        Returns:
            dict: Probabilities for each range defined in TWEET_COUNT_FRAMES
        """
        # Extract probabilities from individual models
        model_probabilities = {}
        
        for model_name, result in ensemble_result.get('individual_predictions', {}).items():
            model_weight = self.normalized_weights.get(model_name, 0.0)
            if model_weight > 0:
                probs = None
                
                # Basic Prophet: has native frame_probabilities 
                if model_name == 'basic_prophet' and 'frame_probabilities' in result:
                    # Convert percentages to probabilities (0-1 range)
                    probs = {frame: prob/100.0 for frame, prob in result['frame_probabilities'].items()}
                
                # Other models: check for probabilities in their standard format
                elif 'probabilities' in result:
                    probs = result['probabilities']
                elif 'predictions_by_frame' in result:
                    probs = {frame: data['probability'] for frame, data in result['predictions_by_frame'].items()}
                
                if probs:
                    model_probabilities[model_name] = probs
        
        # Initialize ensemble probabilities to 0 for all frames
        ensemble_probabilities = {}
        for frame in TWEET_COUNT_FRAMES:
            ensemble_probabilities[frame['name']] = 0.0
        
        # Weight and combine model probabilities
        total_weight = 0.0
        for model_name, probs in model_probabilities.items():
            model_weight = self.normalized_weights.get(model_name, 0.0)
            total_weight += model_weight
            
            for frame_name, prob in probs.items():
                if frame_name in ensemble_probabilities:
                    ensemble_probabilities[frame_name] += prob * model_weight
        
        # Normalize by total weight if we have any model probabilities
        if total_weight > 0:
            for frame_name in ensemble_probabilities:
                ensemble_probabilities[frame_name] /= total_weight
        else:
            # If no model probabilities available, fall back to equal distribution
            # This should rarely happen in practice
            num_frames = len(TWEET_COUNT_FRAMES)
            for frame_name in ensemble_probabilities:
                ensemble_probabilities[frame_name] = 1.0 / num_frames
        
        # Final normalization to ensure probabilities sum to 1
        total_prob = sum(ensemble_probabilities.values())
        if total_prob > 0:
            ensemble_probabilities = {k: v / total_prob for k, v in ensemble_probabilities.items()}
        
        return ensemble_probabilities
    
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
                frame['name']: {
                    'probability': probabilities.get(frame['name'], 0.0),  # Show ALL frames, even 0%
                    'range': f"{frame['min']}-{frame['max']}" 
                            if frame['max'] != float('inf') 
                            else f"{frame['min']}+",
                    'min': frame['min'],
                    'max': frame['max']
                }
                for frame in TWEET_COUNT_FRAMES  # Use TWEET_COUNT_FRAMES to ensure all frames are included
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