from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import logging
from src.algos.elon_tweet_predictor.predictor.utils import (
    calculate_trend_factor, 
    validate_hours,
    get_weekday_name,
    format_hour_ampm
)

class TweetPredictor:
    def __init__(self, analyzer=None, logger=None):
        self.analyzer = analyzer
        self.logger = logger or logging.getLogger(__name__)
    
    def predict_count(self, target_date_str=None, days=None, use_trend=True, hours=None):
        """
        Predict how many tweets Elon will post until a specific date and time.
        
        Parameters:
        target_date_str (str): Target date in format YYYY-MM-DD
        days (int): Number of days to predict for (alternative to target_date)
        use_trend (bool): Whether to apply recent trend adjustment to predictions
        hours (list): List of specific hours (0-23) to include in the prediction
        
        Returns:
        dict: Prediction results
        """
        # Import here to avoid circular imports
        from src.algos.elon_tweet_predictor.predictor.daily_predictor import predict_daily
        return predict_daily(self, target_date_str, days, use_trend, hours)
    
    def predict_next_hours(self, hours_ahead=4, use_trend=True):
        """
        Predict how many tweets Elon will post in the next N hours.
        
        Parameters:
        hours_ahead (int): Number of hours to predict for
        use_trend (bool): Whether to apply recent trend adjustment to predictions
        
        Returns:
        dict: Prediction results
        """
        # Import here to avoid circular imports
        from src.algos.elon_tweet_predictor.predictor.hourly_predictor import predict_next_hours
        return predict_next_hours(self, hours_ahead, use_trend)
    
    def predict_remaining_hours(self, current_datetime, target_datetime, trend_factor=1.0, specific_hours=None):
        """
        Predict tweets for remaining hours of a day
        
        Parameters:
        current_datetime: Current datetime
        target_datetime: Target datetime
        trend_factor: Trend adjustment factor
        specific_hours: List of specific hours (0-23) to include in the prediction
        
        Returns:
        dict: Prediction results containing expected tweets
        """
        # Calculate remaining hours
        remaining_seconds = (target_datetime - current_datetime).total_seconds()
        remaining_hours = remaining_seconds / 3600
        
        if remaining_hours <= 0:
            return {
                'date': current_datetime.date(),
                'expected_tweets': 0,
                'remaining_hours': 0
            }
        
        current_hour = current_datetime.hour
        current_weekday = current_datetime.weekday()
        
        # For the exact hours, calculate expected tweets based on hourly rates
        expected_tweets = 0
        
        # Remaining portion of current hour
        current_minute = current_datetime.minute
        current_second = current_datetime.second
        remaining_portion = (60 - current_minute) / 60 - current_second / 3600
        
        # Check if we should include the current hour
        include_current_hour = specific_hours is None or current_hour in specific_hours
        
        if include_current_hour:
            # Get rate for current hour and weekday
            try:
                current_hour_rate = self.analyzer.hour_of_day_averages.get((current_weekday, current_hour), 0)
                expected_tweets += current_hour_rate * remaining_portion * trend_factor
            except:
                # Fallback to overall hourly rate
                current_hour_rate = self.analyzer.hourly_rates.get(current_hour, 0)
                expected_tweets += current_hour_rate * remaining_portion / 24 * trend_factor
        
        # Full hours after current hour
        for hour in range(current_hour + 1, 24):
            # Skip hours not in specific_hours if provided
            if specific_hours is not None and hour not in specific_hours:
                continue
                
            try:
                hour_rate = self.analyzer.hour_of_day_averages.get((current_weekday, hour), 0)
                expected_tweets += hour_rate * trend_factor
            except:
                # Fallback to overall hourly rate
                hour_rate = self.analyzer.hourly_rates.get(hour, 0)
                expected_tweets += hour_rate / 24 * trend_factor
        
        return {
            'date': current_datetime.date(),
            'expected_tweets': expected_tweets,
            'remaining_hours': remaining_hours,
            'hours_included': specific_hours
        } 