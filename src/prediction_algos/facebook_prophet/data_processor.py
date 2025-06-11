"""
Data processor for preparing Elon Musk tweet data for Facebook Prophet.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from pathlib import Path
import sys
import os

# Add the src directory to the path to import constants
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from constants import (
    DEFAULT_DATA_PATH, ET_TIMEZONE, POLYMARKET_START_TIME, 
    POLYMARKET_END_TIME, GEORGIA_TIMESTAMP_FORMAT
)


class TweetDataProcessor:
    """Processes tweet data for Prophet forecasting."""
    
    def __init__(self, data_path=None):
        """
        Initialize the data processor.
        
        Args:
            data_path (str): Path to the CSV file containing tweet data.
                           If None, uses the default path from constants.
        """
        self.data_path = data_path or DEFAULT_DATA_PATH
        self.timezone = ET_TIMEZONE
        self.raw_data = None
        self.processed_data = None
        
    def load_data(self):
        """Load tweet data from CSV file."""
        try:
            self.raw_data = pd.read_csv(self.data_path)
            print(f"Loaded {len(self.raw_data)} tweets from {self.data_path}")
            return self.raw_data
        except Exception as e:
            raise ValueError(f"Error loading data from {self.data_path}: {e}")
    
    def parse_timestamp(self, timestamp_str):
        """
        Parse timestamp from the Georgia format used in the data.
        
        Args:
            timestamp_str (str): Timestamp in format "YYYY:MM:DD:HH:MM:SS"
            
        Returns:
            datetime: Parsed datetime object in ET timezone
        """
        try:
            # Parse the timestamp using the Georgia format
            dt = datetime.strptime(timestamp_str, GEORGIA_TIMESTAMP_FORMAT)
            # Localize to ET timezone
            dt_et = self.timezone.localize(dt)
            return dt_et
        except Exception as e:
            print(f"Error parsing timestamp '{timestamp_str}': {e}")
            return None
    
    def process_data(self):
        """
        Process raw tweet data into Prophet-compatible format.
        
        Returns:
            pd.DataFrame: DataFrame with 'ds' (datetime) and 'y' (tweet count) columns
        """
        if self.raw_data is None:
            self.load_data()
        
        # Parse timestamps
        self.raw_data['parsed_timestamp'] = self.raw_data['created_at'].apply(self.parse_timestamp)
        
        # Remove rows with invalid timestamps
        valid_data = self.raw_data.dropna(subset=['parsed_timestamp'])
        print(f"Removed {len(self.raw_data) - len(valid_data)} rows with invalid timestamps")
        
        # Convert to daily tweet counts
        valid_data['date'] = valid_data['parsed_timestamp'].dt.date
        daily_counts = valid_data.groupby('date').size().reset_index(name='tweet_count')
        
        # Convert date back to datetime for Prophet
        daily_counts['ds'] = pd.to_datetime(daily_counts['date'])
        daily_counts['y'] = daily_counts['tweet_count']
        
        # Sort by date
        daily_counts = daily_counts.sort_values('ds').reset_index(drop=True)
        
        # Keep only ds and y columns for Prophet
        self.processed_data = daily_counts[['ds', 'y']].copy()
        
        print(f"Processed data: {len(self.processed_data)} days of tweet counts")
        print(f"Date range: {self.processed_data['ds'].min()} to {self.processed_data['ds'].max()}")
        print(f"Tweet count range: {self.processed_data['y'].min()} to {self.processed_data['y'].max()}")
        
        return self.processed_data
    
    def get_current_week_data(self, current_time=None):
        """
        Get tweet data for the current Polymarket prediction week.
        
        Args:
            current_time (datetime): Current time. If None, uses current system time.
            
        Returns:
            dict: Contains 'historical_data', 'current_week_tweets', 'time_remaining'
        """
        if current_time is None:
            current_time = datetime.now(self.timezone)
        elif current_time.tzinfo is None:
            current_time = self.timezone.localize(current_time)
        
        # Parse Polymarket timeframe
        start_time = datetime.strptime(POLYMARKET_START_TIME, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(POLYMARKET_END_TIME, "%Y-%m-%d %H:%M:%S")
        
        # Localize to ET timezone
        start_time = self.timezone.localize(start_time)
        end_time = self.timezone.localize(end_time)
        
        # Get tweets in the current prediction week
        if self.raw_data is None:
            self.load_data()
        
        # Parse all timestamps
        self.raw_data['parsed_timestamp'] = self.raw_data['created_at'].apply(self.parse_timestamp)
        valid_data = self.raw_data.dropna(subset=['parsed_timestamp'])
        
        # Filter tweets in the prediction week
        week_tweets = valid_data[
            (valid_data['parsed_timestamp'] >= start_time) & 
            (valid_data['parsed_timestamp'] <= end_time)
        ]
        
        # Count tweets posted so far in the week
        current_week_tweets = len(week_tweets[week_tweets['parsed_timestamp'] <= current_time])
        
        # Calculate time remaining
        if current_time >= end_time:
            time_remaining = timedelta(0)
        else:
            time_remaining = end_time - current_time
        
        # Get historical data (before the prediction week)
        historical_tweets = valid_data[valid_data['parsed_timestamp'] < start_time]
        
        return {
            'historical_data': historical_tweets,
            'current_week_tweets': current_week_tweets,
            'time_remaining': time_remaining,
            'total_week_duration': end_time - start_time,
            'week_start': start_time,
            'week_end': end_time,
            'current_time': current_time
        }
    
    def get_prophet_data(self):
        """Get processed data in Prophet format."""
        if self.processed_data is None:
            self.process_data()
        return self.processed_data 