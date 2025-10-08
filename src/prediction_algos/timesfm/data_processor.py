"""
Data processor for TimesFM tweet count predictions.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants import ET_TIMEZONE, GEORGIA_TIMESTAMP_FORMAT, POLYMARKET_START_TIME, POLYMARKET_END_TIME
from polymarket_predictor.time_utils import parse_timestamp


class TweetDataProcessor:
    """Process tweet data for TimesFM foundation model forecasting."""
    
    def __init__(self, data_path=None):
        """
        Initialize the data processor.
        
        Args:
            data_path (str): Path to tweet data CSV file
        """
        if data_path is None:
            data_path = "src/data/elonmusk_reformatted.csv"
        
        self.data_path = data_path
        self.raw_data = None
        self.processed_data = None
    
    def load_data(self):
        """Load tweet data from CSV file."""
        try:
            self.raw_data = pd.read_csv(self.data_path)
            print(f"Loaded {len(self.raw_data)} tweets from {self.data_path}")
            return self.raw_data
        except Exception as e:
            print(f"Error loading data: {e}")
            raise
    
    def get_timesfm_data(self):
        """
        Prepare data in TimesFM format (time series array).
        
        Returns:
            tuple: (time_series_array, timestamps) suitable for TimesFM
        """
        if self.raw_data is None:
            self.load_data()
        
        # Parse timestamps using the robust time_utils function
        self.raw_data['parsed_timestamp'] = self.raw_data['created_at'].apply(
            parse_timestamp
        )
        
        # Remove invalid timestamps
        valid_data = self.raw_data.dropna(subset=['parsed_timestamp'])
        invalid_count = len(self.raw_data) - len(valid_data)
        if invalid_count > 0:
            print(f"Removed {invalid_count} rows with invalid timestamps")
        
        # Convert to daily tweet counts
        valid_data['date'] = valid_data['parsed_timestamp'].dt.date
        daily_counts = valid_data.groupby('date').size().reset_index(name='tweet_count')
        
        # Create complete date range
        start_date = daily_counts['date'].min()
        end_date = daily_counts['date'].max()
        
        # Fill missing dates with 0 tweets
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        complete_data = pd.DataFrame({'date': date_range.date})
        complete_data = complete_data.merge(daily_counts, on='date', how='left')
        complete_data['tweet_count'] = complete_data['tweet_count'].fillna(0)
        
        # Sort by date
        complete_data = complete_data.sort_values('date').reset_index(drop=True)
        
        print(f"Processed data: {len(complete_data)} days of tweet counts")
        print(f"Date range: {complete_data['date'].min()} to {complete_data['date'].max()}")
        print(f"Tweet count range: {complete_data['tweet_count'].min()} to {complete_data['tweet_count'].max()}")
        
        # Convert to TimesFM format (time series array)
        time_series = complete_data['tweet_count'].values.astype(np.float32)
        timestamps = pd.to_datetime(complete_data['date'])
        
        self.processed_data = complete_data
        
        return time_series, timestamps
    
    def get_current_week_data(self, current_time=None):
        """
        Get information about the current prediction week.
        
        Args:
            current_time (datetime): Current time for prediction context
            
        Returns:
            dict: Information about current week and remaining time
        """
        if current_time is None:
            current_time = datetime.now(ET_TIMEZONE)
        elif current_time.tzinfo is None:
            current_time = ET_TIMEZONE.localize(current_time)
        
        # Use Polymarket event timeframe from constants instead of Friday-to-Friday calculation
        try:
            week_start = ET_TIMEZONE.localize(
                datetime.strptime(POLYMARKET_START_TIME, "%Y-%m-%d %H:%M:%S"), 
                is_dst=None
            )
        except Exception as e:
            print(f"Warning: Error parsing Polymarket start time: {e}")
            # Fallback to DST-aware localization
            week_start = ET_TIMEZONE.localize(
                datetime.strptime(POLYMARKET_START_TIME, "%Y-%m-%d %H:%M:%S"), 
                is_dst=True
            )
        
        try:
            week_end = ET_TIMEZONE.localize(
                datetime.strptime(POLYMARKET_END_TIME, "%Y-%m-%d %H:%M:%S"), 
                is_dst=None
            )
        except Exception as e:
            print(f"Warning: Error parsing Polymarket end time: {e}")
            # Fallback to DST-aware localization
            week_end = ET_TIMEZONE.localize(
                datetime.strptime(POLYMARKET_END_TIME, "%Y-%m-%d %H:%M:%S"), 
                is_dst=True
            )
        
        time_remaining = week_end - current_time
        
        # Count tweets in current week
        if self.raw_data is None:
            self.load_data()
        
        # Parse timestamps for current week analysis using robust function
        self.raw_data['parsed_timestamp'] = self.raw_data['created_at'].apply(
            parse_timestamp
        )
        valid_data = self.raw_data.dropna(subset=['parsed_timestamp'])
        
        # Filter tweets in current week
        week_tweets = valid_data[
            (valid_data['parsed_timestamp'] >= week_start) & 
            (valid_data['parsed_timestamp'] < current_time)
        ]
        
        current_week_tweets = len(week_tweets)
        
        return {
            'current_time': current_time,
            'week_start': week_start,
            'week_end': week_end,
            'time_remaining': time_remaining,
            'current_week_tweets': current_week_tweets,
            'hours_elapsed': (current_time - week_start).total_seconds() / 3600,
            'hours_remaining': time_remaining.total_seconds() / 3600
        }
    
    def get_recent_context(self, days_back=60):
        """
        Get recent time series data for context.
        
        Args:
            days_back (int): Number of recent days to include
            
        Returns:
            np.array: Recent time series values
        """
        time_series, _ = self.get_timesfm_data()
        
        # Return the last N days
        if len(time_series) > days_back:
            return time_series[-days_back:]
        else:
            return time_series
    
    def prepare_timesfm_input(self, context_len=64):
        """
        Prepare input data specifically for TimesFM model.
        
        Args:
            context_len (int): Length of context window
            
        Returns:
            dict: Prepared data for TimesFM
        """
        time_series, timestamps = self.get_timesfm_data()
        
        # Take the most recent context_len points
        if len(time_series) >= context_len:
            context_data = time_series[-context_len:]
            context_timestamps = timestamps[-context_len:]
        else:
            # Pad with zeros if not enough data
            padding_len = context_len - len(time_series)
            context_data = np.concatenate([np.zeros(padding_len), time_series])
            # Create dummy timestamps for padding
            start_ts = timestamps[0] - timedelta(days=padding_len)
            padding_timestamps = pd.date_range(start=start_ts, periods=padding_len, freq='D')
            context_timestamps = pd.concat([pd.Series(padding_timestamps), timestamps])
        
        return {
            'time_series': context_data.astype(np.float32),
            'timestamps': context_timestamps,
            'frequency': 'D',  # Daily frequency
            'series_length': len(context_data)
        } 