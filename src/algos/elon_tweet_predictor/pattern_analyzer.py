import pandas as pd
import numpy as np
from collections import defaultdict
import logging

class TweetPatternAnalyzer:
    def __init__(self, df=None, logger=None):
        self.df = df
        self.hourly_rates = None
        self.daily_counts = None
        self.weekday_averages = None
        self.hour_of_day_averages = None
        self.logger = logger or logging.getLogger(__name__)
    
    def analyze_patterns(self, df=None):
        """Analyze tweeting patterns to extract features for prediction"""
        if df is not None:
            self.df = df
            
        if self.df is None:
            self.logger.error("Please load data first")
            return
            
        self.logger.info("\nAnalyzing tweeting patterns...")
        
        # Calculate daily counts
        self.daily_counts = self.df.groupby('date').size().reset_index(name='count')
        self.daily_counts['date'] = pd.to_datetime(self.daily_counts['date'])
        
        # Extract date components
        self.daily_counts['weekday'] = self.daily_counts['date'].dt.weekday
        
        # Calculate average tweets by weekday
        self.weekday_averages = self.daily_counts.groupby('weekday')['count'].mean()
        self.logger.info("\nAverage tweets by weekday:")
        for day, avg in self.weekday_averages.items():
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
            self.logger.info(f"{day_name}: {avg:.2f} tweets per day")
        
        # Calculate hourly distribution
        hour_counts = self.df.groupby('hour').size()
        total_days = (self.df['date'].max() - self.df['date'].min()).days + 1
        self.hourly_rates = hour_counts / total_days
        
        self.logger.info("\nAverage hourly tweets (top 5):")
        for hour, rate in self.hourly_rates.nlargest(5).items():
            hour_ampm = f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"
            self.logger.info(f"{hour_ampm}: {rate:.3f} tweets per day")
        
        # Display all hourly rates
        self.logger.debug("\nFull hourly tweet distribution:")
        for hour in range(24):
            rate = self.hourly_rates.get(hour, 0)
            hour_ampm = f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"
            self.logger.debug(f"{hour_ampm}: {rate:.3f} tweets per day")
        
        # Calculate average tweets per day
        avg_daily = self.daily_counts['count'].mean()
        self.logger.info(f"\nOverall average: {avg_daily:.2f} tweets per day")
        
        # Calculate recent average (last 7 days)
        recent_avg = self.daily_counts.iloc[-7:]['count'].mean() if len(self.daily_counts) >= 7 else avg_daily
        self.logger.info(f"Recent average (last 7 days): {recent_avg:.2f} tweets per day")
        
        # Calculate hour of day + weekday averages
        self.df['hour_weekday'] = self.df['weekday'] * 24 + self.df['hour']
        hour_weekday_counts = self.df.groupby(['weekday', 'hour']).size().reset_index(name='count')
        
        # Calculate averages by dividing by the number of that weekday in the dataset
        weekday_counts = self.daily_counts.groupby('weekday').size()
        hour_weekday_counts['rate'] = hour_weekday_counts.apply(
            lambda x: x['count'] / weekday_counts[x['weekday']], axis=1
        )
        
        self.hour_of_day_averages = hour_weekday_counts.set_index(['weekday', 'hour'])['rate']
    
    def display_hourly_averages(self):
        """Display average tweet counts for all 24 hours"""
        if self.hourly_rates is None:
            self.logger.error("Please analyze patterns first")
            return
            
        self.logger.info("\nAverage tweet counts for all 24 hours:")
        hours = []
        for hour in range(24):
            rate = self.hourly_rates.get(hour, 0)
            hour_ampm = f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"
            hours.append((hour, hour_ampm, rate))
        
        # Sort by rate in descending order
        hours.sort(key=lambda x: x[2], reverse=True)
        
        for _, hour_ampm, rate in hours:
            self.logger.info(f"{hour_ampm}: {rate:.3f} tweets per day")
        
        return self.hourly_rates 