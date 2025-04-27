import os
import logging
import pandas as pd
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

# Import local modules
from src.polymarket_predictor.time_utils import parse_timestamp, convert_to_et
from src.constants import ET_TIMEZONE

def preprocess_tweets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess tweets data for analysis
    
    Args:
        df: DataFrame containing raw tweet data
    
    Returns:
        DataFrame: Processed tweet data
    """
    # Filter out tweets with invalid timestamps
    df = df.dropna(subset=['created_at'])
    
    # Convert timestamp strings to datetime objects
    df['created_at_dt'] = df['created_at'].apply(parse_timestamp)
    
    # Filter out rows with invalid timestamps
    df = df.dropna(subset=['created_at_dt'])
    
    return df

def verify_tweet_count(start_date_str: str, end_date_str: str, data_file: Optional[str] = None, logger: Optional[logging.Logger] = None) -> int:
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
    except Exception as e:
        logger.error(f"Error parsing dates: {e}")
        logger.info("Please use 'YYYY-MM-DD HH:MM:SS' format")
        return 0
    
    # Load data
    if data_file is None:
        from src.utils.file_utils import get_data_path
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

def load_and_validate_tweet_data(data_path: str) -> pd.DataFrame:
    """
    Load tweet data from CSV and validate its format
    
    Args:
        data_path: Path to the tweet data file
        
    Returns:
        DataFrame: Validated tweet data
    """
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
        
        # Parse timestamps using our robust handler
        print("Parsing timestamps with robust timezone handling...")
        df['created_at_dt'] = df['created_at'].apply(parse_timestamp)
        
        # Filter out rows with invalid timestamps
        invalid_dt_count = df['created_at_dt'].isna().sum()
        if invalid_dt_count > 0:
            print(f"Warning: Found {invalid_dt_count} tweets with parsing errors, removing from analysis")
            df = df.dropna(subset=['created_at_dt'])
            print(f"Continuing with {len(df)} valid tweets")
            
        return df
        
    except Exception as e:
        print(f"Error loading tweet data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()  # Return empty DataFrame on error

def count_tweets_in_timeframe(df: pd.DataFrame, start_time: datetime, end_time: datetime) -> int:
    """
    Count tweets within a specific timeframe
    
    Args:
        df: DataFrame containing tweet data with 'created_at_dt' column
        start_time: Start datetime (timezone-aware)
        end_time: End datetime (timezone-aware)
        
    Returns:
        int: Number of tweets in the timeframe
    """
    if df.empty:
        return 0
        
    # Ensure both datetimes are timezone-aware
    if start_time.tzinfo is None:
        start_time = ET_TIMEZONE.localize(start_time)
    if end_time.tzinfo is None:
        end_time = ET_TIMEZONE.localize(end_time)
    
    # Count tweets in the date range
    tweets_in_timeframe = df[(df['created_at_dt'] >= start_time) & (df['created_at_dt'] <= end_time)]
    return len(tweets_in_timeframe) 