import pandas as pd
import os
import re
import json
from ..utils.timestamp_handler import (
    convert_to_unix_timestamp,
    format_timestamp_edt,
    get_current_timestamp,
    EDT_TZ,
    GEORGIA_TZ,
    ET_TZ
)
from src.constants import (
    DEFAULT_TWITTER_HANDLE,
    DEFAULT_MAX_TWEETS,
    DEFAULT_TWEETS_CSV_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_FORMAT_STYLE,
    CSV_HEADER_MAP,
    GEORGIA_TIMESTAMP_FORMAT,
    EDT_TIMESTAMP_FORMAT
)
from pathlib import Path
from datetime import datetime

class TweetExtractor:
    """
    Class to extract, process, merge and reformat tweets from Apify's Twitter scraper datasets or other sources.
    
    This class provides functionality to:
    - Format timestamps in a consistent way
    - Remove duplicate tweets
    - Merge multiple datasets of tweets
    - Save to various formats (CSV, JSON)
    - Extract key pieces of information
    """
    
    def __init__(
        self,
        csv_file=DEFAULT_TWEETS_CSV_FILE,
        output_dir=DEFAULT_OUTPUT_DIR,
        twitter_handle=DEFAULT_TWITTER_HANDLE,
        format_style=DEFAULT_FORMAT_STYLE,  # Options: "georgia" or "edt"
    ):
        """
        Initialize TweetExtractor with file paths and configuration.
        
        Args:
            csv_file: Path to the CSV file for reading/writing tweets
            output_dir: Directory to save output files
            twitter_handle: Twitter handle the tweets belong to
            format_style: Timestamp format style ("georgia" for YYYY:MM:DD:HH:MM:SS, "edt" for EDT with AM/PM)
        """
        self.csv_file = Path(csv_file)
        self.output_dir = Path(output_dir)
        self.twitter_handle = twitter_handle
        self.format_style = format_style
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
    def fix_timestamp(self, timestamp_str):
        """
        Fix timestamp format according to the selected format style.
        Both formats use Eastern Time (ET) but with different display styles.
        
        Args:
            timestamp_str: Original timestamp string
            
        Returns:
            str: Formatted timestamp string
        """
        timestamp_str = str(timestamp_str).strip()
        
        try:
            # Convert to unix timestamp first
            unix_ts = convert_to_unix_timestamp(timestamp_str)
            
            if self.format_style == "georgia":
                # Format in Eastern Time with YYYY:MM:DD:HH:MM:SS format
                dt = datetime.fromtimestamp(unix_ts, ET_TZ)
                return dt.strftime(GEORGIA_TIMESTAMP_FORMAT)
            else:
                # Format in EDT with AM/PM
                return format_timestamp_edt(unix_ts)
        except Exception as e:
            print(f"Error parsing date '{timestamp_str}': {e}")
            return timestamp_str  # Return original if parsing fails
    
    def clean_text(self, text):
        """
        Clean tweet text by removing newlines, tabs, and normalizing spaces.
        
        Args:
            text: Raw tweet text
            
        Returns:
            str: Cleaned text
        """
        if text is None:
            return ""
            
        text = str(text).encode('ascii', 'replace').decode('ascii')
        return ' '.join(text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').split())
    
    def load_tweets_from_csv(self, csv_file=None):
        """
        Load tweets from a CSV file.
        
        Args:
            csv_file: Path to CSV file (defaults to self.csv_file)
            
        Returns:
            pd.DataFrame: DataFrame containing tweets
        """
        if csv_file is None:
            csv_file = self.csv_file
            
        if not os.path.exists(csv_file):
            print(f"CSV file {csv_file} not found.")
            return pd.DataFrame()
            
        try:
            # Ensure ID column is treated as string to avoid numeric conversion issues
            df = pd.read_csv(csv_file, dtype={"id": str})
            print(f"Loaded {len(df)} tweets from {csv_file}")
            return df
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            return pd.DataFrame()
    
    def merge_csv_files(self, csv_files, output_file=None, remove_duplicates=True):
        """
        Merge multiple CSV files containing tweets.
        
        Args:
            csv_files: List of CSV file paths
            output_file: Path to save merged CSV
            remove_duplicates: Whether to remove duplicate tweets
            
        Returns:
            pd.DataFrame: Merged DataFrame
        """
        if output_file is None:
            output_file = self.csv_file
            
        all_tweets = pd.DataFrame()
        
        for file in csv_files:
            print(f"Loading tweets from {file}...")
            df = self.load_tweets_from_csv(file)
            
            if df.empty:
                continue
                
            all_tweets = pd.concat([all_tweets, df], ignore_index=True)
            
        print(f"Merged {len(all_tweets)} tweets from {len(csv_files)} files")
        
        if remove_duplicates and not all_tweets.empty and "id" in all_tweets.columns:
            original_count = len(all_tweets)
            all_tweets = all_tweets.drop_duplicates(subset="id")
            duplicates_removed = original_count - len(all_tweets)
            print(f"Removed {duplicates_removed} duplicate tweets")
            
        # Convert timestamps if needed
        if not all_tweets.empty and "created_at" in all_tweets.columns:
            all_tweets["created_at"] = all_tweets["created_at"].apply(self.fix_timestamp)
            
        # Save merged DataFrame to output file
        if not all_tweets.empty and output_file:
            all_tweets.to_csv(output_file, index=False)
            print(f"Saved {len(all_tweets)} merged tweets to {output_file}")
            
        return all_tweets
    
    def reformat_tweets(self, input_df=None, output_file=None, header_map=None):
        """
        Reformat tweets by renaming columns, applying timestamp fixes, etc.
        
        Args:
            input_df: Input DataFrame (if None, loads from self.csv_file)
            output_file: Output file path for reformed CSV
            header_map: Dictionary mapping original column names to new ones
            
        Returns:
            pd.DataFrame: Reformatted DataFrame
        """
        if input_df is None:
            input_df = self.load_tweets_from_csv()
            
        if input_df.empty:
            print("No tweets to reformat.")
            return pd.DataFrame()
            
        if output_file is None:
            output_file = str(self.csv_file).replace(".csv", "_reformatted.csv")
            
        # Default header mapping if not provided
        if header_map is None:
            header_map = CSV_HEADER_MAP
            
        # Create a copy of the dataframe for reformatting
        df = input_df.copy()
        
        # Fix timestamps
        if "created_at" in df.columns:
            df["created_at"] = df["created_at"].apply(self.fix_timestamp)
            
        # Clean text
        if "text" in df.columns:
            df["text"] = df["text"].apply(self.clean_text)
            
        # Rename columns based on header map
        # Only rename columns that exist in the DataFrame
        rename_map = {k: v for k, v in header_map.items() if k in df.columns}
        if rename_map:
            df = df.rename(columns=rename_map)
            
        # Ensure we have the expected columns
        expected_columns = ["id", "text", "created_at"]
        for col in expected_columns:
            if col not in df.columns:
                print(f"Warning: Expected column '{col}' not found in DataFrame")
                
        # Save reformatted DataFrame
        if output_file:
            df.to_csv(output_file, index=False)
            print(f"Saved {len(df)} reformatted tweets to {output_file}")
            
        return df
    
    def convert_to_json(self, input_df=None, output_file=None):
        """
        Convert tweets DataFrame to JSON format.
        
        Args:
            input_df: Input DataFrame (if None, loads from self.csv_file)
            output_file: Output JSON file path
            
        Returns:
            list: List of tweet dictionaries
        """
        if input_df is None:
            input_df = self.load_tweets_from_csv()
            
        if input_df.empty:
            print("No tweets to convert to JSON.")
            return []
            
        if output_file is None:
            output_file = str(self.csv_file).replace(".csv", ".json")
            
        # Convert to list of dictionaries
        tweets_list = input_df.to_dict(orient="records")
        
        # Save to JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(tweets_list, f, indent=2)
            
        print(f"Saved {len(tweets_list)} tweets to JSON file {output_file}")
        
        return tweets_list
    
    def extract_latest_tweet_id(self, input_df=None):
        """
        Extract the ID of the latest tweet in the dataset.
        
        Args:
            input_df: Input DataFrame (if None, loads from self.csv_file)
            
        Returns:
            str: Latest tweet ID or None if not found
        """
        if input_df is None:
            input_df = self.load_tweets_from_csv()
            
        if input_df.empty or "id" not in input_df.columns:
            print("No tweets or no ID column found.")
            return None
            
        # Make sure all IDs are strings
        input_df["id"] = input_df["id"].astype(str)
        
        # If we have created_at column, we can sort by that
        if "created_at" in input_df.columns:
            # For Georgia format: "2023:04:20:01:30:21"
            if self.format_style == "georgia":
                # Extract date for sorting
                def extract_date_for_sorting(date_str):
                    try:
                        if ':' in date_str and date_str.count(':') >= 5:
                            return pd.to_datetime(date_str, format=GEORGIA_TIMESTAMP_FORMAT, errors='coerce')
                        else:
                            return pd.to_datetime(date_str, errors='coerce')
                    except Exception:
                        return pd.NaT
                        
                input_df['temp_date'] = input_df['created_at'].apply(extract_date_for_sorting)
                
                # Sort by date (newest first)
                input_df = input_df.sort_values('temp_date', ascending=False)
                
                # Get the latest tweet ID
                latest_id = input_df.iloc[0]['id'] if not input_df.empty else None
                
                # Clean up
                input_df = input_df.drop('temp_date', axis=1)
            else:  # EDT format
                # Try to sort by created_at directly
                try:
                    input_df = input_df.sort_values('created_at', ascending=False)
                    latest_id = input_df.iloc[0]['id'] if not input_df.empty else None
                except Exception:
                    # If sorting fails, just take the last row
                    latest_id = input_df['id'].iloc[-1] if not input_df.empty else None
        else:
            # If no created_at column, just take the last row
            latest_id = input_df['id'].iloc[-1] if not input_df.empty else None
            
        if latest_id:
            print(f"Latest tweet ID: {latest_id}")
            
        return latest_id
    
    def count_tweets_by_day(self, input_df=None):
        """
        Count tweets by day.
        
        Args:
            input_df: Input DataFrame (if None, loads from self.csv_file)
            
        Returns:
            pd.DataFrame: DataFrame with day and tweet count
        """
        if input_df is None:
            input_df = self.load_tweets_from_csv()
            
        if input_df.empty or "created_at" not in input_df.columns:
            print("No tweets or no created_at column found.")
            return pd.DataFrame()
            
        # For Georgia format: "2023:04:20:01:30:21"
        if self.format_style == "georgia":
            # Extract date for grouping (just get YYYY:MM:DD part)
            def extract_date(date_str):
                try:
                    if ':' in date_str and date_str.count(':') >= 3:
                        # Extract first 3 components (YYYY:MM:DD)
                        return ":".join(date_str.split(":")[:3])
                    else:
                        return date_str.split(" ")[0]  # Fallback
                except Exception:
                    return "unknown_date"
                    
            input_df['date'] = input_df['created_at'].apply(extract_date)
        else:  # EDT format
            # Extract date part (YYYY-MM-DD)
            def extract_date(date_str):
                try:
                    return date_str.split(" ")[0]  # 2023-04-20 in "2023-04-20 01:30:21 PM EDT"
                except Exception:
                    return "unknown_date"
                    
            input_df['date'] = input_df['created_at'].apply(extract_date)
            
        # Group by date and count
        counts = input_df.groupby('date').size().reset_index(name='count')
        counts = counts.sort_values('date', ascending=False)
        
        print("Tweet counts by day:")
        for _, row in counts.iterrows():
            print(f"  {row['date']}: {row['count']} tweets")
            
        return counts 