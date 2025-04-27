import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Import from local modules
from src.constants import ET_TIMEZONE

def analyze_tweet_patterns(df: pd.DataFrame) -> Tuple[float, float]:
    """
    Analyze tweeting patterns to identify trends
    
    Args:
        df: DataFrame containing preprocessed tweet data
        
    Returns:
        tuple: (overall_avg, recent_avg) containing overall and recent 7-day average
    """
    # Extract date and time components
    df['date'] = df['created_at_dt'].dt.date
    df['weekday'] = df['created_at_dt'].dt.weekday
    df['hour'] = df['created_at_dt'].dt.hour
    
    # Analyze tweets by weekday
    weekday_counts = df.groupby('weekday').size()
    weekday_unique_dates = df.groupby('weekday')['date'].nunique()
    weekday_avg = weekday_counts / weekday_unique_dates
    
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    print("\nAverage tweets by weekday:")
    for i in range(7):
        if i in weekday_avg.index:
            print(f"{weekday_names[i]}: {weekday_avg[i]:.2f} tweets per day")
    
    # Analyze tweets by hour
    hour_counts = df.groupby('hour').size()
    hour_unique_dates = df.groupby('hour')['date'].nunique()
    hour_avg = hour_counts / hour_unique_dates
    
    print("\nAverage hourly tweets (top 5):")
    top_hours = hour_avg.sort_values(ascending=False).head(5)
    for hour, avg in top_hours.items():
        am_pm = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        print(f"{display_hour} {am_pm}: {avg:.3f} tweets per day")
    
    # Overall average
    total_days = (df['date'].max() - df['date'].min()).days + 1
    total_tweets = len(df)
    overall_avg = total_tweets / total_days
    
    print(f"\nOverall average: {overall_avg:.2f} tweets per day")
    
    # Recent average (last 7 days)
    last_date = df['date'].max()
    week_ago = last_date - timedelta(days=7)
    recent_tweets = df[(df['date'] > week_ago) & (df['date'] <= last_date)]
    recent_avg = len(recent_tweets) / 7
    
    print(f"Recent average (last 7 days): {recent_avg:.2f} tweets per day")
    
    return overall_avg, recent_avg

def calculate_time_periods(df: pd.DataFrame, 
                         polymarket_start: datetime, 
                         polymarket_end: datetime) -> Dict[str, float]:
    """
    Calculate various time periods and tweet rates
    
    Args:
        df: DataFrame containing preprocessed tweet data
        polymarket_start: Start datetime for the analysis period
        polymarket_end: End datetime for the analysis period
        
    Returns:
        dict: Dictionary containing time period analysis results
    """
    now = datetime.now(ET_TIMEZONE)
    
    # Calculate time periods
    elapsed_days = (now - polymarket_start).total_seconds() / (24 * 3600)
    remaining_days = (polymarket_end - now).total_seconds() / (24 * 3600)
    
    # Count tweets so far
    tweets_so_far = df[(df['created_at_dt'] >= polymarket_start) & (df['created_at_dt'] <= now)]
    tweet_count = len(tweets_so_far)
    
    # Calculate current daily rate
    current_rate = tweet_count / elapsed_days if elapsed_days > 0 else 0
    
    # Calculate tweeting rates for different time periods
    last_7_days = now - timedelta(days=7)
    last_14_days = now - timedelta(days=14)
    last_30_days = now - timedelta(days=30)
    
    recent_7d_tweets = df[(df['created_at_dt'] >= last_7_days) & (df['created_at_dt'] <= now)]
    recent_14d_tweets = df[(df['created_at_dt'] >= last_14_days) & (df['created_at_dt'] <= now)]
    recent_30d_tweets = df[(df['created_at_dt'] >= last_30_days) & (df['created_at_dt'] <= now)]
    
    rate_7d = len(recent_7d_tweets) / 7 if now > last_7_days else current_rate
    rate_14d = len(recent_14d_tweets) / 14 if now > last_14_days else current_rate
    rate_30d = len(recent_30d_tweets) / 30 if now > last_30_days else current_rate
    
    # Add daily aggregation for historical context
    df['date'] = df['created_at_dt'].dt.date
    daily_counts = df.groupby('date').size()
    historical_avg = daily_counts.mean()
    daily_std = daily_counts.std()
    
    # Calculate trend indicators
    trend_7d = rate_7d / historical_avg if historical_avg > 0 else 1.0
    trend_14d = rate_14d / historical_avg if historical_avg > 0 else 1.0
    trend_30d = rate_30d / historical_avg if historical_avg > 0 else 1.0
    
    # Calculate weekday patterns
    df['weekday'] = df['created_at_dt'].dt.weekday
    weekday_counts = df.groupby('weekday').size()
    weekday_unique_dates = df.groupby('weekday')['date'].nunique()
    weekday_avg = weekday_counts / weekday_unique_dates
    
    # Calculate which weekdays are in the remaining period
    remaining_weekdays = []
    current_day = now
    while current_day <= polymarket_end:
        remaining_weekdays.append(current_day.weekday())
        current_day += timedelta(days=1)
    
    remaining_weekdays = list(set(remaining_weekdays))  # Unique weekdays
    
    # Calculate expected daily rate for remaining period based on weekday patterns
    expected_weekday_rate = 0
    if len(remaining_weekdays) > 0:
        for weekday in remaining_weekdays:
            if weekday in weekday_avg.index:
                expected_weekday_rate += weekday_avg[weekday]
        expected_weekday_rate /= len(remaining_weekdays)
    else:
        expected_weekday_rate = current_rate
    
    # Adjust based on weekday patterns
    weekday_adjustment = expected_weekday_rate / historical_avg if historical_avg > 0 else 1.0
    
    # Return analysis results as dictionary
    return {
        'tweet_count': tweet_count,
        'elapsed_days': elapsed_days,
        'remaining_days': remaining_days,
        'current_rate': current_rate,
        'historical_avg': historical_avg,
        'daily_std': daily_std,
        'rate_7d': rate_7d,
        'rate_14d': rate_14d,
        'rate_30d': rate_30d,
        'trend_7d': trend_7d,
        'trend_14d': trend_14d,
        'trend_30d': trend_30d,
        'weekday_adjustment': weekday_adjustment
    }

def calculate_predictions(time_analysis: Dict[str, float], use_trend: bool = True) -> Dict[str, float]:
    """
    Calculate various prediction models based on time period analysis
    
    Args:
        time_analysis: Dictionary containing time period analysis results
        use_trend: Whether to use trend adjustment in predictions
        
    Returns:
        dict: Dictionary containing different prediction models
    """
    # Extract values from time_analysis
    tweet_count = time_analysis['tweet_count']
    current_rate = time_analysis['current_rate']
    remaining_days = time_analysis['remaining_days']
    trend_7d = time_analysis['trend_7d']
    trend_14d = time_analysis['trend_14d']
    trend_30d = time_analysis['trend_30d']
    weekday_adjustment = time_analysis['weekday_adjustment']
    
    # Calculate weighted trend
    weighted_trend = (trend_7d * 0.6) + (trend_14d * 0.3) + (trend_30d * 0.1)
    
    # 1. Simple linear extrapolation (base prediction)
    base_prediction = tweet_count + (current_rate * remaining_days)
    
    # 2. Trend-adjusted prediction
    trend_adjusted_prediction = tweet_count + (current_rate * remaining_days * weighted_trend)
    
    # 3. Weekday-adjusted prediction
    weekday_adjusted_prediction = tweet_count + (current_rate * remaining_days * weekday_adjustment)
    
    # 4. Combined model (ensemble)
    if use_trend:
        ensemble_prediction = tweet_count + (current_rate * remaining_days * weighted_trend * weekday_adjustment)
    else:
        # Skip trend factor if trend adjustment is disabled
        ensemble_prediction = tweet_count + (current_rate * remaining_days * weekday_adjustment)
    
    # Safety check: predictions can never be less than current count
    base_prediction = max(tweet_count, base_prediction)
    trend_adjusted_prediction = max(tweet_count, trend_adjusted_prediction)
    weekday_adjusted_prediction = max(tweet_count, weekday_adjusted_prediction)
    ensemble_prediction = max(tweet_count, ensemble_prediction)
    
    return {
        'current_count': tweet_count,
        'base_prediction': base_prediction,
        'trend_adjusted_prediction': trend_adjusted_prediction,
        'weekday_adjusted_prediction': weekday_adjusted_prediction,
        'ensemble_prediction': ensemble_prediction,
        'weighted_trend': weighted_trend
    } 