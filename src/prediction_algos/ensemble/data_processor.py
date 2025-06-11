"""
Data processor for ensemble tweet predictions.
Coordinates data processing for Neural Prophet, Facebook Prophet, and TimesFM models.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants import DEFAULT_DATA_PATH, ET_TIMEZONE, POLYMARKET_START_TIME, POLYMARKET_END_TIME
from prediction_algos.neural_prophet.data_processor import TweetDataProcessor as NeuralProphetDataProcessor
from prediction_algos.facebook_prophet.data_processor import TweetDataProcessor as FacebookProphetDataProcessor
from prediction_algos.timesfm.data_processor import TweetDataProcessor as TimesFMDataProcessor


class EnsembleTweetDataProcessor:
    """Data processor that coordinates all model-specific data processors."""
    
    def __init__(self, data_path=None):
        """
        Initialize the ensemble data processor.
        
        Args:
            data_path (str): Path to tweet data CSV file
        """
        self.data_path = data_path or DEFAULT_DATA_PATH
        
        # Initialize individual data processors
        self.neural_prophet_processor = NeuralProphetDataProcessor(data_path)
        self.facebook_prophet_processor = FacebookProphetDataProcessor(data_path)
        self.timesfm_processor = TimesFMDataProcessor(data_path)
        
        # Load raw data once and share it
        self.raw_data = None
        self.load_data()
    
    def load_data(self):
        """Load and validate tweet data."""
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Tweet data file not found: {self.data_path}")
        
        print(f"Loading tweet data from {self.data_path}")
        
        # Load the raw data
        self.raw_data = pd.read_csv(self.data_path)
        
        print(f"Loaded {len(self.raw_data)} tweets")
        
        # Share raw data with individual processors
        self.neural_prophet_processor.raw_data = self.raw_data.copy()
        self.facebook_prophet_processor.raw_data = self.raw_data.copy()
        self.timesfm_processor.raw_data = self.raw_data.copy()
        
        return self.raw_data
    
    def get_neural_prophet_data(self):
        """Get data formatted for Neural Prophet."""
        return self.neural_prophet_processor.get_neural_prophet_data()
    
    def get_facebook_prophet_data(self):
        """Get data formatted for Facebook Prophet."""
        return self.facebook_prophet_processor.get_prophet_data()
    
    def get_timesfm_data(self):
        """Get data formatted for TimesFM."""
        return self.timesfm_processor.get_timesfm_data()
    
    def get_current_week_data(self, current_time=None):
        """
        Get current week information from any of the processors.
        
        Args:
            current_time (datetime): Current time for analysis
            
        Returns:
            dict: Current week status information
        """
        # Use Facebook Prophet processor as it has the most comprehensive implementation
        return self.facebook_prophet_processor.get_current_week_data(current_time)
    
    def analyze_data_quality(self):
        """
        Analyze data quality and compatibility across all models.
        
        Returns:
            dict: Data quality analysis
        """
        analysis = {
            'total_tweets': len(self.raw_data) if self.raw_data is not None else 0,
            'date_range': None,
            'missing_timestamps': 0,
            'data_quality_score': 0.0,
            'model_compatibility': {
                'neural_prophet': True,
                'facebook_prophet': True,
                'timesfm': True
            }
        }
        
        if self.raw_data is None or len(self.raw_data) == 0:
            analysis['data_quality_score'] = 0.0
            return analysis
        
        try:
            # Check date range
            if 'created_at' in self.raw_data.columns:
                # Parse timestamps using Facebook Prophet processor method
                parsed_timestamps = self.raw_data['created_at'].apply(
                    self.facebook_prophet_processor.parse_timestamp
                )
                valid_timestamps = parsed_timestamps.dropna()
                
                if len(valid_timestamps) > 0:
                    analysis['date_range'] = {
                        'start': valid_timestamps.min(),
                        'end': valid_timestamps.max(),
                        'span_days': (valid_timestamps.max() - valid_timestamps.min()).days
                    }
                    analysis['missing_timestamps'] = len(self.raw_data) - len(valid_timestamps)
            
            # Calculate quality score
            if analysis['missing_timestamps'] == 0:
                analysis['data_quality_score'] = 1.0
            else:
                analysis['data_quality_score'] = 1.0 - (analysis['missing_timestamps'] / len(self.raw_data))
            
            # Test model compatibility
            try:
                neural_data = self.get_neural_prophet_data()
                analysis['model_compatibility']['neural_prophet'] = len(neural_data) > 0
            except Exception:
                analysis['model_compatibility']['neural_prophet'] = False
            
            try:
                prophet_data = self.get_facebook_prophet_data()
                analysis['model_compatibility']['facebook_prophet'] = len(prophet_data) > 0
            except Exception:
                analysis['model_compatibility']['facebook_prophet'] = False
            
            try:
                timesfm_data = self.get_timesfm_data()
                analysis['model_compatibility']['timesfm'] = len(timesfm_data) > 0
            except Exception:
                analysis['model_compatibility']['timesfm'] = False
        
        except Exception as e:
            print(f"Warning: Data quality analysis failed: {e}")
            analysis['data_quality_score'] = 0.5  # Partial score if analysis fails
        
        return analysis
    
    def get_validation_data_splits(self, validation_days=7):
        """
        Get train/validation splits for ensemble model evaluation.
        
        Args:
            validation_days (int): Number of days to use for validation
            
        Returns:
            dict: Train and validation data for each model type
        """
        validation_cutoff = datetime.now(ET_TIMEZONE) - timedelta(days=validation_days)
        
        splits = {
            'neural_prophet': {'train': None, 'val': None},
            'facebook_prophet': {'train': None, 'val': None},
            'timesfm': {'train': None, 'val': None}
        }
        
        try:
            # Neural Prophet splits
            neural_data = self.get_neural_prophet_data()
            neural_train = neural_data[neural_data['ds'] < validation_cutoff]
            neural_val = neural_data[neural_data['ds'] >= validation_cutoff]
            splits['neural_prophet'] = {'train': neural_train, 'val': neural_val}
            
            # Facebook Prophet splits
            prophet_data = self.get_facebook_prophet_data()
            prophet_train = prophet_data[prophet_data['ds'] < validation_cutoff]
            prophet_val = prophet_data[prophet_data['ds'] >= validation_cutoff]
            splits['facebook_prophet'] = {'train': prophet_train, 'val': prophet_val}
            
            # TimesFM splits
            timesfm_data = self.get_timesfm_data()
            timesfm_train = timesfm_data[timesfm_data['ds'] < validation_cutoff]
            timesfm_val = timesfm_data[timesfm_data['ds'] >= validation_cutoff]
            splits['timesfm'] = {'train': timesfm_train, 'val': timesfm_val}
            
        except Exception as e:
            print(f"Warning: Failed to create validation splits: {e}")
        
        return splits
    
    def load_and_prepare_data(self):
        """
        Load and prepare data in a standardized format for additional prediction methods.
        
        Returns:
            pd.DataFrame: Data with columns 'ds' (datetime) and 'y' (tweet count)
        """
        return self.get_facebook_prophet_data()  # Uses standard ds/y format
    
    def get_ensemble_summary(self):
        """
        Get a summary of data preparation for ensemble modeling.
        
        Returns:
            dict: Summary of data status for ensemble
        """
        summary = {
            'data_path': self.data_path,
            'total_records': len(self.raw_data) if self.raw_data is not None else 0,
            'data_quality': self.analyze_data_quality(),
            'model_data_sizes': {},
            'ready_for_ensemble': False
        }
        
        try:
            # Get data sizes for each model
            neural_data = self.get_neural_prophet_data()
            summary['model_data_sizes']['neural_prophet'] = len(neural_data)
            
            prophet_data = self.get_facebook_prophet_data()
            summary['model_data_sizes']['facebook_prophet'] = len(prophet_data)
            
            timesfm_data = self.get_timesfm_data()
            summary['model_data_sizes']['timesfm'] = len(timesfm_data)
            
            # Check if ready for ensemble
            min_size = min(summary['model_data_sizes'].values())
            all_compatible = all(summary['data_quality']['model_compatibility'].values())
            summary['ready_for_ensemble'] = min_size >= 30 and all_compatible
            
        except Exception as e:
            print(f"Warning: Failed to generate ensemble summary: {e}")
        
        return summary 