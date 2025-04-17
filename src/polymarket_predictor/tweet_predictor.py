import os
import sys
import logging
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta, timezone
import pytz
from typing import Dict, List, Tuple, Optional
import json
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import re

# Import Polymarket API client to get the count frames
from src.polymarket.api_client import PolymarketAPIClient

# Import the tweet predictor components
from src.algos.elon_tweet_predictor.data_loader import TweetDataLoader
from src.algos.elon_tweet_predictor.pattern_analyzer import TweetPatternAnalyzer
from src.algos.elon_tweet_predictor.predictor import TweetPredictor
from src.utils.file_utils import get_data_path

# Constants
ET_TIMEZONE = pytz.timezone('US/Eastern')
API_ENDPOINT = "https://clob.polymarket.com/"
MARKET_ID = "0x3e69ba4320546e712a7b094341f52b69c45c6352"
MARKET_HASH = "will-elon-musk-tweet-over-100-times-april-11-18"
EVENT_HASH = "elon-musk-of-tweets-april-1118"
FULL_EVENT_HASH = "elon-musk-of-tweets-april-1118"
DEFAULT_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "elonmusk_reformatted.csv")
POLYMARKET_START_TIME = "2025-04-11 12:00:00"
POLYMARKET_END_TIME = "2025-04-18 12:00:00"
POLYMARKET_TIMEZONE = ET_TIMEZONE  # Eastern Time

def get_current_et_time():
    """
    Get the current time in Eastern Time (ET) timezone.
    
    Returns:
        datetime: Current datetime in ET timezone
    """
    return datetime.now(ET_TIMEZONE)

def convert_to_et(dt):
    """
    Convert a naive datetime to Eastern Time (ET) timezone.
    If the datetime is already timezone-aware, convert it to ET.
    
    Args:
        dt: A datetime object
        
    Returns:
        datetime: The datetime in ET timezone
    """
    if dt.tzinfo is None:
        # Assume it's already in ET if no timezone is specified
        return ET_TIMEZONE.localize(dt)
    else:
        # Convert to ET if it has another timezone
        return dt.astimezone(ET_TIMEZONE)

def verify_tweet_count(start_date_str, end_date_str, data_file=None, logger=None):
    """
    Utility function to verify the exact tweet count within a date range
    by manually counting and displaying detailed information.
    
    Args:
        start_date_str: Start date/time in 'YYYY-MM-DD HH:MM:SS' format (ET timezone)
        end_date_str: End date/time in 'YYYY-MM-DD HH:MM:SS' format (ET timezone)
        data_file: Path to the tweet data file
        logger: Logger instance
    
    Returns:
        int: The count of tweets within the specified range
    """
    # Set up logging
    if logger is None:
        logger = logging.getLogger("tweet_count_verifier")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(handler)
    
    # Parse dates with ET timezone
    try:
        start_datetime = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
        start_datetime = ET_TIMEZONE.localize(start_datetime, is_dst=None)
        
        end_datetime = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
        end_datetime = ET_TIMEZONE.localize(end_datetime, is_dst=None)
        
        logger.info(f"Using Eastern Time (ET) for start: {start_datetime} and end: {end_datetime}")
    except ValueError as e:
        logger.error(f"Invalid date format: {e}. Please use 'YYYY-MM-DD HH:MM:SS'")
        return 0
    except pytz.exceptions.AmbiguousTimeError as e:
        logger.error(f"Ambiguous time during DST transition: {e}")
        logger.info("Please specify a time that is not during the DST 'fall back' transition")
        return 0
    except pytz.exceptions.NonExistentTimeError as e:
        logger.error(f"Non-existent time during DST transition: {e}")
        logger.info("Please specify a time that is not during the DST 'spring forward' transition")
        return 0
    
    # Load data
    if data_file is None:
        data_path = get_data_path('elonmusk_reformatted.csv')
    else:
        data_path = data_file
        
    logger.info(f"Loading tweet data from: {data_path}")
    
    # Read the CSV file
    try:
        df = pd.read_csv(data_path)
        logger.info(f"Loaded {len(df)} total tweets")
        
        # Parse created_at timestamps and properly handle timezone
        logger.info("Parsing timestamps with custom function to handle timezone properly...")
        
        # First, convert timestamps with our robust parser
        df['created_at_dt'] = df['created_at'].apply(parse_timestamp)
        
        # Drop entries with invalid timestamps
        invalid_count = df['created_at_dt'].isna().sum()
        if invalid_count > 0:
            logger.warning(f"Found {invalid_count} tweets with invalid timestamps")
            df = df.dropna(subset=['created_at_dt'])
        
        # IMPORTANT: Compare timezone-aware datetime objects directly
        # This is safer than converting to naive datetime objects
        filtered_df = df[(df['created_at_dt'] >= start_datetime) & (df['created_at_dt'] <= end_datetime)]
        total_count = len(filtered_df)
        
        logger.info(f"\n=== Tweet Count Verification ===")
        logger.info(f"Time range (ET): {start_datetime} to {end_datetime}")
        logger.info(f"Total tweets in range: {total_count}")
        
        # Show counts by day
        if not filtered_df.empty:
            filtered_df['date'] = filtered_df['created_at_dt'].dt.date
            daily_counts = filtered_df.groupby('date').size()
            
            logger.info(f"\nDaily tweet counts (ET):")
            for date, count in daily_counts.items():
                logger.info(f"  {date}: {count} tweets")
            
            # Show a few sample tweets from the range
            logger.info(f"\nSample tweets from this range:")
            sample = filtered_df.sample(min(5, len(filtered_df)))
            for idx, row in sample.iterrows():
                date_str = row['created_at_dt'].strftime('%Y-%m-%d %H:%M:%S %Z')
                text = row['text']
                if len(text) > 50:
                    text = text[:50] + "..."
                logger.info(f"  [{date_str}] {text}")
        
        return total_count
    
    except Exception as e:
        logger.error(f"Error verifying tweet count: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def parse_timestamp(timestamp_str: str) -> datetime:
    """
    Parse a timestamp string in YYYY:MM:DD:HH:MM:SS format and convert to timezone-aware 
    Eastern Time datetime, carefully handling DST transitions.
    
    Args:
        timestamp_str: Timestamp string in YYYY:MM:DD:HH:MM:SS format
        
    Returns:
        datetime: Timezone-aware datetime object in Eastern Time, or None if parsing fails
    """
    try:
        parts = timestamp_str.split(':')
        if len(parts) != 6:
            print(f"Warning: Invalid timestamp format '{timestamp_str}' - expected YYYY:MM:DD:HH:MM:SS")
            return None
            
        year, month, day, hour, minute, second = map(int, parts)
        
        # Create naive datetime
        naive_dt = datetime(year, month, day, hour, minute, second)
        
        # Try to localize to Eastern Time, safely handling DST transitions
        try:
            # First attempt with is_dst=None (let pytz figure it out)
            dt = ET_TIMEZONE.localize(naive_dt, is_dst=None)
        except pytz.exceptions.AmbiguousTimeError:
            # During DST "fall back", the hour repeats - default to the first (DST) instance
            print(f"Note: Ambiguous time during DST transition: {naive_dt}. Using DST=True.")
            dt = ET_TIMEZONE.localize(naive_dt, is_dst=True)
        except pytz.exceptions.NonExistentTimeError:
            # During DST "spring forward", there's a missing hour - adjust forward
            print(f"Note: Non-existent time during DST transition: {naive_dt}. Adding 1 hour.")
            dt = ET_TIMEZONE.localize(naive_dt + timedelta(hours=1))
            
        return dt
        
    except Exception as e:
        print(f"Error parsing timestamp {timestamp_str}: {e}")
        return None

def get_market_details():
    """Get details about the Polymarket prediction market"""
    try:
        response = requests.get(f"{API_ENDPOINT}markets/{MARKET_ID}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch from Polymarket API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching market details: {e}")
        return None

def parse_count_frames(market_details):
    """Parse tweet count frames from market details"""
    if not market_details:
        return []
    
    count_frames = []
    markets = market_details.get("markets", [])
    for market in markets:
        outcomes = market.get("outcomes", [])
        for outcome in outcomes:
            title = outcome.get("title", "")
            token_id = outcome.get("tokenId", "")
            print(f"  [Debug] Pairing outcome: {title} with token_id: {token_id}")
    
    print(f"[Debug] Finished processing markets. market_details count: {len(markets)}")
    
    # Process by finding the event details
    events = market_details.get("events", [])
    if events:
        print(f"Retrieved {len(events)} count frames from Polymarket")
        # Assuming the first event is the one we want
        return events
    
    return []

def preprocess_tweets(df):
    """Preprocess tweets data for analysis"""
    # Filter out tweets with invalid timestamps
    df = df.dropna(subset=['created_at'])
    
    # Convert timestamp strings to datetime objects
    df['created_at_dt'] = df['created_at'].apply(parse_timestamp)
    
    # Filter out rows with invalid timestamps
    df = df.dropna(subset=['created_at_dt'])
    
    return df

def analyze_tweet_patterns(df):
    """Analyze tweeting patterns to identify trends"""
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

def predict_tweet_frame_probabilities(data_path=DEFAULT_DATA_PATH):
    """Predict probabilities for tweet count frames with robust timezone handling"""
    # Load and preprocess tweet data
    print(f"Loading data from: {data_path}")
    try:
        df = pd.read_csv(data_path)
        print(f"Loaded {len(df)} tweets")
        
        # Add data validation step to filter out rows with improperly formatted timestamps
        # We expect the timestamp format to be YYYY:MM:DD:HH:MM:SS
        print("Validating timestamp format...")
        valid_format = df['created_at'].str.match(r'^\d{4}:\d{2}:\d{2}:\d{2}:\d{2}:\d{2}$', na=False)
        invalid_count = (~valid_format).sum()
        if invalid_count > 0:
            print(f"Warning: Found {invalid_count} tweets with invalid timestamp format, removing them from analysis")
            
            # Print a few examples of invalid timestamps for debugging
            invalid_examples = df[~valid_format]['created_at'].head(5)
            print("Examples of invalid timestamps:")
            for i, example in enumerate(invalid_examples):
                print(f"  {i+1}. '{example}'")
                
            # Filter out invalid timestamps
            df = df[valid_format]
            print(f"Continuing with {len(df)} valid tweets")
        
        # Proceed with datetime processing
        print("\nAnalyzing tweeting patterns...")
        
        # Parse timestamps using our robust handler
        print("Parsing timestamps with robust timezone handling...")
        df['created_at_dt'] = df['created_at'].apply(parse_timestamp)
        
        # Filter out rows with invalid timestamps
        invalid_dt_count = df['created_at_dt'].isna().sum()
        if invalid_dt_count > 0:
            print(f"Warning: Found {invalid_dt_count} tweets with parsing errors, removing from analysis")
            df = df.dropna(subset=['created_at_dt'])
            print(f"Continuing with {len(df)} valid tweets")
            
        # Auto-count tweets in the Polymarket timeframe
        try:
            polymarket_start = ET_TIMEZONE.localize(datetime.strptime(POLYMARKET_START_TIME, "%Y-%m-%d %H:%M:%S"), is_dst=None)
        except pytz.exceptions.AmbiguousTimeError:
            print(f"Warning: Start time {POLYMARKET_START_TIME} is ambiguous (during DST transition). Using DST=True.")
            polymarket_start = ET_TIMEZONE.localize(datetime.strptime(POLYMARKET_START_TIME, "%Y-%m-%d %H:%M:%S"), is_dst=True)
        except pytz.exceptions.NonExistentTimeError:
            print(f"Warning: Start time {POLYMARKET_START_TIME} is non-existent (during DST transition). Adjusting forward 1 hour.")
            nonexistent_dt = datetime.strptime(POLYMARKET_START_TIME, "%Y-%m-%d %H:%M:%S")
            polymarket_start = ET_TIMEZONE.localize(nonexistent_dt + timedelta(hours=1))
            
        try:
            polymarket_end = ET_TIMEZONE.localize(datetime.strptime(POLYMARKET_END_TIME, "%Y-%m-%d %H:%M:%S"), is_dst=None)
        except pytz.exceptions.AmbiguousTimeError:
            print(f"Warning: End time {POLYMARKET_END_TIME} is ambiguous (during DST transition). Using DST=True.")
            polymarket_end = ET_TIMEZONE.localize(datetime.strptime(POLYMARKET_END_TIME, "%Y-%m-%d %H:%M:%S"), is_dst=True)
        except pytz.exceptions.NonExistentTimeError:
            print(f"Warning: End time {POLYMARKET_END_TIME} is non-existent (during DST transition). Adjusting forward 1 hour.")
            nonexistent_dt = datetime.strptime(POLYMARKET_END_TIME, "%Y-%m-%d %H:%M:%S")
            polymarket_end = ET_TIMEZONE.localize(nonexistent_dt + timedelta(hours=1))
            
        now = datetime.now(ET_TIMEZONE)
        
        print(f"Current time (ET): {now}")
        print(f"Analysis time range (ET): {polymarket_start} to {polymarket_end}")
        
        # Continue with existing analysis logic
        if now < polymarket_end:
            elapsed_days = (now - polymarket_start).total_seconds() / (24 * 3600)
            remaining_days = (polymarket_end - now).total_seconds() / (24 * 3600)
            
            # Count tweets so far (comparing timezone-aware datetimes)
            tweets_so_far = df[(df['created_at_dt'] >= polymarket_start) & (df['created_at_dt'] <= now)]
            tweet_count = len(tweets_so_far)
            
            print(f"Using current tweet count of {tweet_count} tweets")
            
            # Add historical context by preparing the data for time series analysis
            # Convert created_at_dt to date for daily aggregation
            df['date'] = df['created_at_dt'].dt.date
            
            # Calculate daily counts
            daily_counts = df.groupby('date').size().reset_index(name='count')
            daily_counts['date'] = pd.to_datetime(daily_counts['date'])
            daily_counts = daily_counts.sort_values('date')
            
            # Calculate moving averages of different windows
            daily_counts['MA_7'] = daily_counts['count'].rolling(window=7).mean()
            daily_counts['MA_14'] = daily_counts['count'].rolling(window=14).mean()
            daily_counts['MA_30'] = daily_counts['count'].rolling(window=30).mean()
            
            # Calculate current daily rate from elapsed period
            if elapsed_days > 0:
                current_rate = tweet_count / elapsed_days
                print(f"Current daily rate: {current_rate:.2f} tweets per day")
                
                # Calculate tweeting rate for different time periods
                last_7_days = now - timedelta(days=7)
                last_14_days = now - timedelta(days=14)
                last_30_days = now - timedelta(days=30)
                
                recent_7d_tweets = df[(df['created_at_dt'] >= last_7_days) & (df['created_at_dt'] <= now)]
                recent_14d_tweets = df[(df['created_at_dt'] >= last_14_days) & (df['created_at_dt'] <= now)]
                recent_30d_tweets = df[(df['created_at_dt'] >= last_30_days) & (df['created_at_dt'] <= now)]
                
                rate_7d = len(recent_7d_tweets) / 7 if now > last_7_days else current_rate
                rate_14d = len(recent_14d_tweets) / 14 if now > last_14_days else current_rate
                rate_30d = len(recent_30d_tweets) / 30 if now > last_30_days else current_rate
                
                # Get the average daily tweet count from full history
                historical_avg = daily_counts['count'].mean()
                
                # Calculate trend indicators
                trend_7d = rate_7d / historical_avg if historical_avg > 0 else 1.0
                trend_14d = rate_14d / historical_avg if historical_avg > 0 else 1.0
                trend_30d = rate_30d / historical_avg if historical_avg > 0 else 1.0
                
                # Use an ensemble of trend indicators with more weight on recent trends
                weighted_trend = (trend_7d * 0.6) + (trend_14d * 0.3) + (trend_30d * 0.1)
                
                print("\n--- Advanced Prediction Analysis ---")
                print(f"Prediction window (ET): {polymarket_start} to {polymarket_end} ({(polymarket_end - polymarket_start).total_seconds() / (24 * 3600):.1f} days)")
                print(f"Current tweet count: {tweet_count} tweets ({elapsed_days:.2f} days elapsed, {remaining_days:.2f} days remaining)")
                print(f"Historical daily average: {historical_avg:.1f} tweets per day")
                print(f"Recent rates: 7-day: {rate_7d:.1f}, 14-day: {rate_14d:.1f}, 30-day: {rate_30d:.1f} tweets/day")
                print(f"Trend factors: 7-day: {trend_7d:.2f}, 14-day: {trend_14d:.2f}, 30-day: {trend_30d:.2f}")
                print(f"Weighted trend factor: {weighted_trend:.2f}")
                
                # Analyze hourly and day-of-week patterns
                df['hour'] = df['created_at_dt'].dt.hour
                df['weekday'] = df['created_at_dt'].dt.weekday
                
                # Check if there's a day-of-week or hourly pattern to consider
                weekday_counts = df.groupby('weekday').size()
                weekday_unique_dates = df.groupby('weekday')['date'].nunique()
                weekday_avg = weekday_counts / weekday_unique_dates
                
                # Calculate which weekdays are in the remaining period
                remaining_start = now
                remaining_end = polymarket_end
                remaining_weekdays = []
                
                current_day = remaining_start
                while current_day <= remaining_end:
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
                
                # Now calculate multiple prediction models
                
                # 1. Simple linear extrapolation (base prediction)
                base_prediction = tweet_count + (current_rate * remaining_days)
                
                # 2. Trend-adjusted prediction
                trend_adjusted_prediction = tweet_count + (current_rate * remaining_days * weighted_trend)
                
                # 3. Weekday-adjusted prediction
                weekday_adjusted_prediction = tweet_count + (current_rate * remaining_days * weekday_adjustment)
                
                # 4. Combined model (ensemble)
                ensemble_prediction = tweet_count + (current_rate * remaining_days * weighted_trend * weekday_adjustment)
                
                # Safety check: predictions can never be less than current count
                base_prediction = max(tweet_count, base_prediction)
                trend_adjusted_prediction = max(tweet_count, trend_adjusted_prediction)
                weekday_adjusted_prediction = max(tweet_count, weekday_adjusted_prediction)
                ensemble_prediction = max(tweet_count, ensemble_prediction)
                
                print("\n--- Prediction Models ---")
                print(f"Current count (lower bound): {tweet_count:.1f} tweets")
                print(f"Simple linear prediction: {base_prediction:.1f} tweets")
                print(f"Trend-adjusted prediction: {trend_adjusted_prediction:.1f} tweets")
                print(f"Weekday-adjusted prediction: {weekday_adjusted_prediction:.1f} tweets")
                print(f"Ensemble prediction: {ensemble_prediction:.1f} tweets")
                
                # The final prediction we'll use
                final_prediction = ensemble_prediction
                
                # Calculate volatility for Monte Carlo simulation
                std_dev = daily_counts['count'].std() if len(daily_counts) > 1 else current_rate * 0.2
                
                # 95% confidence interval (±2 standard deviations)
                confidence_interval = (
                    max(tweet_count, final_prediction - 2 * std_dev),  # Cannot be less than current count
                    final_prediction + 2 * std_dev
                )
                print(f"95% confidence interval: {confidence_interval[0]:.1f} to {confidence_interval[1]:.1f} tweets")
                
                # Prepare for Monte Carlo simulation
                print(f"Using ensemble prediction: {final_prediction:.1f} tweets as base for Monte Carlo simulation")
                print(f"Time period: {polymarket_start} to {polymarket_end} (ET timezone)")
                
                # Use the standard deviation for simulation
                remaining_vol = std_dev * (remaining_days**0.5)
                print(f"Using standard deviation of {remaining_vol:.1f} for remaining period simulation")
                
                # Run Monte Carlo simulation (5000 samples for better accuracy)
                np.random.seed(42)  # For reproducibility
                simulations = np.random.normal(final_prediction, remaining_vol, 5000)
                
                # Enforce the constraint that predictions cannot be less than current count
                simulations = np.maximum(simulations, tweet_count)
                
                # Define the count frames from Polymarket
                count_frames = [
                    {"name": "less than 100", "min": 0, "max": 99},
                    {"name": "100–124", "min": 100, "max": 124},
                    {"name": "125–149", "min": 125, "max": 149},
                    {"name": "150–174", "min": 150, "max": 174},
                    {"name": "175–199", "min": 175, "max": 199},
                    {"name": "200–224", "min": 200, "max": 224},
                    {"name": "225–249", "min": 225, "max": 249},
                    {"name": "250–274", "min": 250, "max": 274},
                    {"name": "275–299", "min": 275, "max": 299},
                    {"name": "300–324", "min": 300, "max": 324},
                    {"name": "325–349", "min": 325, "max": 349},
                    {"name": "350–374", "min": 350, "max": 374},
                    {"name": "375–399", "min": 375, "max": 399},
                    {"name": "400 or more", "min": 400, "max": float('inf')}
                ]
                
                # Calculate probabilities for each frame
                frame_probabilities = {}
                for frame in count_frames:
                    count = np.sum((simulations >= frame["min"]) & (simulations <= frame["max"]))
                    probability = count / len(simulations) * 100
                    frame_probabilities[frame["name"]] = probability
                
                print(f"\nPredicted probabilities for tweet count frames ({polymarket_start} to {polymarket_end}, ET timezone):")
                
                # Sort the frames by the predefined order (ascending count frames) instead of by probability
                ordered_frames = []
                for frame in count_frames:
                    ordered_frames.append((frame["name"], frame_probabilities[frame["name"]]))
                
                for frame_name, probability in ordered_frames:
                    print(f"{frame_name}: {probability:.1f}%")
                
                # Also present top 3 most likely outcomes for quick reference
                print("\nTop 3 most likely outcomes:")
                sorted_by_prob = sorted(frame_probabilities.items(), key=lambda x: x[1], reverse=True)
                for i, (frame_name, probability) in enumerate(sorted_by_prob[:3]):
                    if probability > 0:
                        print(f"{i+1}. {frame_name}: {probability:.1f}%")
                
                # Generate and save a visualization of the Monte Carlo simulations
                try:
                    plt.figure(figsize=(12, 8))
                    
                    # Create histogram of simulations
                    n, bins, patches = plt.hist(simulations, bins=30, alpha=0.6, color='skyblue', density=True)
                    
                    # Add KDE for smooth distribution
                    sns.kdeplot(simulations, color='darkblue', lw=2)
                    
                    # Add vertical lines for key values
                    plt.axvline(x=tweet_count, color='red', linestyle='-', label=f'Current count: {tweet_count}', linewidth=2)
                    plt.axvline(x=final_prediction, color='green', linestyle='--', label=f'Prediction: {final_prediction:.1f}', linewidth=2)
                    
                    # Add CI
                    plt.axvline(x=confidence_interval[0], color='orange', linestyle=':', label=f'95% CI: {confidence_interval[0]:.1f} - {confidence_interval[1]:.1f}', linewidth=1.5)
                    plt.axvline(x=confidence_interval[1], color='orange', linestyle=':', linewidth=1.5)
                    
                    # Add frame boundaries
                    for frame in count_frames:
                        if frame["min"] >= tweet_count and frame["min"] <= confidence_interval[1] + 50:
                            plt.axvline(x=frame["min"], color='gray', linestyle='-', alpha=0.3, linewidth=1)
                    
                    plt.title('Monte Carlo Simulation of Final Tweet Count', fontsize=16)
                    plt.xlabel('Total Tweets', fontsize=14)
                    plt.ylabel('Probability Density', fontsize=14)
                    plt.legend(fontsize=12)
                    plt.grid(True, alpha=0.3)
                    
                    # Add text annotation for most likely frames
                    y_pos = 0.85
                    plt.text(0.02, y_pos, "Most likely outcomes:", transform=plt.gca().transAxes, fontsize=12, 
                            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
                    
                    for i, (frame_name, probability) in enumerate(sorted_by_prob[:3]):
                        y_pos -= 0.05
                        plt.text(0.02, y_pos, f"{i+1}. {frame_name}: {probability:.1f}%", 
                                transform=plt.gca().transAxes, fontsize=12, 
                                bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.3'))
                    
                    # Save the plot
                    plt.tight_layout()
                    plot_path = os.path.join(os.path.dirname(data_path), 'tweet_prediction.png')
                    plt.savefig(plot_path)
                    plt.close()
                    print(f"\nVisualization saved to: {plot_path}")
                except Exception as e:
                    print(f"Warning: Could not generate visualization: {e}")
                
                return frame_probabilities
            else:
                print("Not enough data to make a prediction yet.")
                return None
        else:
            # Event is over, just count the actual tweets
            tweets_in_window = df[(df['created_at_dt'] >= polymarket_start) & (df['created_at_dt'] <= polymarket_end)]
            final_count = len(tweets_in_window)
            print(f"Event has ended. Final tweet count: {final_count}")
            
            # Map the final count to a frame
            count_frames = [
                {"name": "less than 100", "min": 0, "max": 99},
                {"name": "100–124", "min": 100, "max": 124},
                {"name": "125–149", "min": 125, "max": 149},
                {"name": "150–174", "min": 150, "max": 174},
                {"name": "175–199", "min": 175, "max": 199},
                {"name": "200–224", "min": 200, "max": 224},
                {"name": "225–249", "min": 225, "max": 249},
                {"name": "250–274", "min": 250, "max": 274},
                {"name": "275–299", "min": 275, "max": 299},
                {"name": "300–324", "min": 300, "max": 324},
                {"name": "325–349", "min": 325, "max": 349},
                {"name": "350–374", "min": 350, "max": 374},
                {"name": "375–399", "min": 375, "max": 399},
                {"name": "400 or more", "min": 400, "max": float('inf')}
            ]
            
            winning_frame = None
            for frame in count_frames:
                if frame["min"] <= final_count <= frame["max"]:
                    winning_frame = frame["name"]
                    break
            
            print(f"Final count falls in the '{winning_frame}' frame")
            
            # Return 100% probability for the winning frame
            frame_probabilities = {frame["name"]: 0.0 for frame in count_frames}
            frame_probabilities[winning_frame] = 100.0
            
            return frame_probabilities
            
    except Exception as e:
        print(f"Error auto-counting tweets: {e}")
        import traceback
        traceback.print_exc()
        
        # Return a default of 0 for all frames on error
        count_frames = [
            "less than 100", "100–124", "125–149", "150–174", "175–199",
            "200–224", "225–249", "250–274", "275–299", "300–324",
            "325–349", "350–374", "375–399", "400 or more"
        ]
        
        print("Using 0 as the current tweet count due to error")
        return {frame: 0.0 for frame in count_frames}

def main():
    parser = argparse.ArgumentParser(description='Predict Elon Musk tweet counts')
    parser.add_argument('--verify-count', action='store_true', help='Verify tweet count in a specific timeframe')
    parser.add_argument('--data-path', type=str, default=DEFAULT_DATA_PATH, help='Path to tweet data CSV')
    args = parser.parse_args()
    
    if args.verify_count:
        verify_tweet_count(POLYMARKET_START_TIME, POLYMARKET_END_TIME, args.data_path)
    else:
        # Get market details
        market_details = get_market_details()
        if market_details:
            count_frames = parse_count_frames(market_details)
        
        # Specify the start and end times (Eastern Time)
        start_time = POLYMARKET_START_TIME
        end_time = POLYMARKET_END_TIME
        
        start_time_dt = ET_TIMEZONE.localize(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S"))
        end_time_dt = ET_TIMEZONE.localize(datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S"))
        
        print(f"Using provided start time (ET): {start_time_dt}")
        print(f"Using provided end time (ET): {end_time_dt}")
        
        # Calculate elapsed and remaining time
        now = datetime.now(ET_TIMEZONE)
        print(f"Current time (ET): {now}")
        
        total_days = (end_time_dt - start_time_dt).total_seconds() / (24 * 3600)
        elapsed_days = (now - start_time_dt).total_seconds() / (24 * 3600)
        remaining_days = (end_time_dt - now).total_seconds() / (24 * 3600)
        
        if remaining_days < 0:
            print(f"Prediction window has ended. Total duration was {total_days:.2f} days.")
        else:
            print(f"Currently {elapsed_days:.2f} days into the prediction window, with {remaining_days:.2f} days remaining")
        
        # Predict probabilities
        print(f"Loading data from: {args.data_path}")
        predict_tweet_frame_probabilities(args.data_path)

if __name__ == "__main__":
    main() 