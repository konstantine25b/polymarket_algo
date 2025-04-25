import requests
import pandas as pd
import os
import time
from datetime import datetime
import csv
import re
from ..utils.timestamp_handler import (
    convert_to_unix_timestamp,
    format_timestamp_edt,
    get_current_timestamp,
    EDT_TZ,
    GEORGIA_TZ
)
from src.constants import (
    APIFY_TOKEN, 
    APIFY_TWITTER_ACTOR_TASK_ID,
    DEFAULT_TWITTER_HANDLE,
    DEFAULT_MAX_TWEETS,
    DEFAULT_TWEETS_CSV_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_FORMAT_STYLE,
    MAX_REQUEST_RETRIES,
    MAX_EXHAUSTIVE_ATTEMPTS,
    DEFAULT_TWEET_REQUEST_MULTIPLIER,
    GEORGIA_TIMESTAMP_FORMAT,
    EDT_TIMESTAMP_FORMAT
)
from pathlib import Path
from apify_client import ApifyClient  # Import the official Apify client

class TweetGetter:
    """
    Simple class to fetch tweets from a specific Twitter user.
    
    This class provides functionality to:
    - Fetch tweets from a Twitter handle (default: Elon Musk)
    - Fetch tweets from a specific tweet ID
    - Store tweets in a CSV file
    - Handle timestamp conversions and formatting
    - Remove duplicates
    """
    
    def __init__(
        self,
        twitter_handle=DEFAULT_TWITTER_HANDLE, 
        max_tweets=DEFAULT_MAX_TWEETS,
        since_id=None,
        apify_token=APIFY_TOKEN,
        actor_task_id=APIFY_TWITTER_ACTOR_TASK_ID,
        csv_file=DEFAULT_TWEETS_CSV_FILE,
        debug=False,
        format_style=DEFAULT_FORMAT_STYLE,  # Options: "georgia" for YYYY:MM:DD:HH:MM:SS, "edt" for EDT with AM/PM
        output_dir=DEFAULT_OUTPUT_DIR,
        auto_since_id=False  # New parameter to automatically use latest tweet ID
    ):
        """
        Initialize the TweetGetter.
        
        Args:
            twitter_handle: Twitter handle to fetch tweets from (default: elonmusk)
            max_tweets: Maximum number of tweets to fetch per request
            since_id: Tweet ID to start fetching from (optional)
            apify_token: Apify API token (default: value from constants.py)
            actor_task_id: Apify actor task ID (default: value from constants.py)
            csv_file: Path to save the tweets CSV file
            debug: Whether to print debug information
            format_style: Timestamp format style - "georgia" for YYYY:MM:DD:HH:MM:SS or "edt" for EDT AM/PM format
            output_dir: Directory to save the tweets CSV file
            auto_since_id: Whether to automatically use the latest tweet ID from the CSV file
        """
        self.twitter_handle = twitter_handle
        self.max_tweets = max_tweets
        self.since_id = since_id
        self.apify_token = apify_token
        self.actor_task_id = actor_task_id
        self.csv_file = csv_file
        self.debug = debug
        self.format_style = format_style
        self.output_dir = output_dir
        self.auto_since_id = auto_since_id
        
        # If auto_since_id is enabled, get the latest tweet ID from the CSV file
        if auto_since_id and not since_id:
            latest_id = self.get_latest_tweet_id()
            if latest_id:
                self.since_id = latest_id
                if self.debug:
                    print(f"Automatically using latest tweet ID from database: {self.since_id}")
                    
    def get_latest_tweet_id(self):
        """
        Get the latest tweet ID from the CSV file.
        
        Returns:
            str: Latest tweet ID or None if no tweets exist
        """
        if not os.path.exists(self.csv_file):
            if self.debug:
                print(f"CSV file {self.csv_file} does not exist yet.")
            return None
            
        try:
            # Read the CSV file
            df = pd.read_csv(self.csv_file, dtype={"id": str})
            
            if df.empty:
                if self.debug:
                    print("CSV file exists but contains no tweets.")
                return None
                
            # Make sure all IDs are strings and remove any potential NaN values
            df['id'] = df['id'].astype(str)
            df = df[df['id'].notna()]  
            
            if 'id' not in df.columns:
                if self.debug:
                    print("CSV file does not have an 'id' column.")
                return None
                
            # Extract date for sorting to ensure we get the truly latest tweet
            if 'created_at' in df.columns:
                # Extract date for sorting (using the same logic as in save_tweets)
                def extract_date_for_sorting(date_str):
                    try:
                        # For Georgia format: "2025:04:20:01:30:21"
                        if ':' in date_str and date_str.count(':') >= 3:
                            return pd.to_datetime(date_str, format=GEORGIA_TIMESTAMP_FORMAT, errors='coerce')
                        # For EDT format: "2025-04-20 01:30:21 PM EDT"
                        elif 'EDT' in date_str:
                            date_part = date_str.replace(' EDT', '')
                            return pd.to_datetime(date_part, format='%Y-%m-%d %I:%M:%S %p', errors='coerce')
                        else:
                            # Try other formats
                            return pd.to_datetime(date_str, errors='coerce')
                    except Exception:
                        return pd.NaT
                        
                df['temp_date'] = df['created_at'].apply(extract_date_for_sorting)
                
                # Sort by date (newest first)
                df = df.sort_values('temp_date', ascending=False)
                
                # Get the latest tweet ID - we'll use this as our since_id
                # IMPORTANT: Twitter API returns tweets with IDs strictly greater than the specified since_id,
                # so we don't need to adjust the ID to avoid missing tweets
                latest_id = df.iloc[0]['id'] if not df.empty else None
            else:
                # If no created_at column, just get the last row (assuming it's already sorted)
                latest_id = df['id'].iloc[-1] if not df.empty else None
                
            if self.debug and latest_id:
                print(f"Found latest tweet ID: {latest_id}")
                
            return latest_id
            
        except Exception as e:
            print(f"Error reading CSV file for latest tweet ID: {e}")
            return None
            
    def fix_timestamp(self, timestamp_str):
        """
        Fix timestamp format according to the selected format style.
        
        Args:
            timestamp_str: Timestamp string from Twitter
            
        Returns:
            str: Formatted timestamp in selected format
        """
        timestamp_str = timestamp_str.strip()
        
        try:
            # Convert to unix timestamp first
            unix_ts = convert_to_unix_timestamp(timestamp_str)
            
            if self.format_style == "georgia":
                # Format in Georgia timezone with YYYY:MM:DD:HH:MM:SS format
                dt = datetime.fromtimestamp(unix_ts, GEORGIA_TZ)
                return dt.strftime(GEORGIA_TIMESTAMP_FORMAT)
            else:
                # Format in EDT with AM/PM
                return format_timestamp_edt(unix_ts)
        except Exception as e:
            print(f"Error parsing date '{timestamp_str}': {e}")
            return timestamp_str
    
    def clean_text(self, text):
        """
        Clean tweet text by removing newlines, tabs, and normalizing spaces.
        
        Args:
            text: Raw tweet text
            
        Returns:
            str: Cleaned text without quotes (quotes will be added by CSV writer)
        """
        text = str(text).encode('ascii', 'replace').decode('ascii')
        text = ' '.join(text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').split())
        # Don't add triple quotes here, let the CSV writer handle the quoting
        return text
    
    def get_tweets(self):
        """
        Fetch tweets from the specified Twitter handle.
        Strictly limits the number of tweets returned to max_tweets.
        
        Returns:
            pd.DataFrame: DataFrame containing tweets with id, text, and created_at columns
        """
        print(f"[{datetime.now(EDT_TZ).strftime('%I:%M:%S %p EDT')}] Fetching tweets from @{self.twitter_handle}...")
        print(f"STRICT LIMIT: Will fetch EXACTLY {self.max_tweets} tweets (no more, no less if possible)")
        
        if self.since_id:
            print(f"Starting from tweet ID: {self.since_id}")
        
        # Define input with exact max_tweets values
        run_input = {
            "searchTerms": [],
            "searchMode": "live",
            "maxTweets": self.max_tweets,
            "twitterHandles": [self.twitter_handle],
            "twitterUrls": [],
            "tweetsDesired": self.max_tweets,
            "resultsLimit": self.max_tweets,
            "maxRequestRetries": MAX_REQUEST_RETRIES,            
            "skipUserTimelineScraping": False,  
            "skipRetweets": False,              
            "skipReplies": False,              
            "scrapeTweetReplies": False,
            "maxTweetsPerQuery": self.max_tweets
        }
        
        # Add since_id query if specified
        if self.since_id:
            search_query = f"from:{self.twitter_handle} since_id:{self.since_id} count:{self.max_tweets}"
            run_input["searchTerms"] = [search_query]
        else:
            search_query = f"from:{self.twitter_handle} count:{self.max_tweets}"
            run_input["searchTerms"] = [search_query]
        
        if self.debug:
            print("API Input:")
            print(run_input)
        
        # Start the Apify actor
        run_url = f"https://api.apify.com/v2/actor-tasks/{self.actor_task_id}/runs?token={self.apify_token}"
        response = requests.post(run_url, json={"useClient": True, "input": run_input})
        
        if response.status_code != 201:
            print(f"Error starting actor: {response.status_code}")
            print(f"Response: {response.text}")
            return pd.DataFrame()
        
        run_data = response.json()
        run_id = run_data.get("data", {}).get("id")
        
        if not run_id:
            print(f"Could not find run ID in response: {run_data}")
            return pd.DataFrame()
        
        print(f"Run started with ID: {run_id}")
        
        # Wait for the run to finish
        print("Waiting for run to complete...")
        status = "RUNNING"
        
        while status == "RUNNING":
            print(".", end="", flush=True)
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={self.apify_token}"
            status_response = requests.get(status_url)
            
            if status_response.status_code != 200:
                print(f"\nError checking status: {status_response.status_code}")
                time.sleep(3)
                continue
            
            status_data = status_response.json()
            status = status_data.get("data", {}).get("status", "UNKNOWN")
            
            if status in ["SUCCEEDED", "FAILED", "TIMED-OUT"]:
                print("")
                break
            
            time.sleep(3)
        
        if status != "SUCCEEDED":
            print(f"Actor run failed or timed out. Final status: {status}")
            return pd.DataFrame()
        
        # Get dataset items with strict limit
        dataset_id = status_data["data"]["defaultDatasetId"]
        dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={self.apify_token}&limit={self.max_tweets}"
        dataset_response = requests.get(dataset_url)
        
        if dataset_response.status_code != 200:
            print(f"Error fetching dataset: {dataset_response.status_code}")
            return pd.DataFrame()
        
        tweets = dataset_response.json()
        
        if not tweets:
            print("No tweets found in the dataset.")
            return pd.DataFrame()
        
        # Strictly limit to max_tweets
        if len(tweets) > self.max_tweets:
            print(f"Got {len(tweets)} tweets but limiting to {self.max_tweets}")
            tweets = tweets[:self.max_tweets]
        
        print(f"Processing {len(tweets)} tweets...")
        
        # Format tweets
        formatted_tweets = []
        for tweet in tweets:
            tweet_id = str(tweet.get("id_str", "") or tweet.get("id", ""))
            tweet_text = tweet.get("full_text", "") or tweet.get("text", "")
            
            created_time = None
            for field in ["created_at", "createdAt", "timestamp"]:
                if field in tweet and tweet[field]:
                    created_time = self.fix_timestamp(tweet[field])
                    break
            
            if not created_time:
                created_time = "TIMESTAMP_MISSING"
            
            formatted_text = self.clean_text(tweet_text)
            
            formatted_tweet = {
                "id": str(tweet_id),
                "text": formatted_text,
                "created_at": created_time
            }
            formatted_tweets.append(formatted_tweet)
            
            if self.debug:
                print(f"ID: {tweet_id}, Created: {created_time}")
                print(f"Text: {tweet_text[:100]}..." if len(tweet_text) > 100 else tweet_text)
        
        # Final DataFrame with strict limit
        df = pd.DataFrame(formatted_tweets)
        
        if len(df) > self.max_tweets:
            print(f"FINAL CHECK: Limiting {len(df)} tweets to {self.max_tweets} as requested")
            df = df.head(self.max_tweets)
        
        print(f"Final result: {len(df)} tweets (max requested: {self.max_tweets})")
        return df
    
    def get_tweets_exhaustive(self, since_id=None, max_attempts=MAX_EXHAUSTIVE_ATTEMPTS):
        """
        Fetch tweets in a paginated manner to ensure we get all tweets since a specific ID,
        but strictly limit the total to max_tweets as requested.
        
        Args:
            since_id: Tweet ID to start fetching from
            max_attempts: Maximum number of API calls to make (default from constants)
            
        Returns:
            pd.DataFrame: DataFrame containing all fetched tweets, limited to max_tweets
        """
        if since_id:
            self.since_id = since_id
            
        all_tweets = pd.DataFrame()
        attempts = 0
        last_count = -1
        total_fetched = 0
        
        # Store original max_tweets value
        original_max_tweets = self.max_tweets
        
        print(f"Starting exhaustive tweet fetching process to get exactly {original_max_tweets} tweets...")
        print(f"Will make up to {max_attempts} API calls if needed, but will STOP once we have {original_max_tweets} tweets.")
        
        # Continue fetching until we have max_tweets or run out of attempts
        while attempts < max_attempts and total_fetched < original_max_tweets:
            remaining_tweets = original_max_tweets - total_fetched
            if remaining_tweets <= 0:
                break
                
            # Set max_tweets to the remaining number we need
            self.max_tweets = remaining_tweets
            print(f"Attempt {attempts+1}/{max_attempts}: Fetching {remaining_tweets} more tweets...")
            
            # Get tweets using the current since_id
            new_batch = self.get_tweets()
            
            # If no tweets were returned, we're done
            if new_batch.empty:
                print(f"No more tweets found after {attempts+1} attempts.")
                break
                
            # Add the new batch to our collection
            all_tweets = pd.concat([all_tweets, new_batch], ignore_index=True)
            batch_size = len(new_batch)
            total_fetched += batch_size
            
            print(f"Attempt {attempts+1}: Got {batch_size} tweets (total so far: {total_fetched}/{original_max_tweets})")
            
            # If we've collected enough tweets, we can stop
            if total_fetched >= original_max_tweets:
                print(f"Successfully collected {total_fetched} tweets, which meets or exceeds the requested {original_max_tweets}")
                break
                
            # If we got fewer tweets than requested, we might be approaching the end
            if batch_size < remaining_tweets:
                print(f"Got {batch_size} tweets, which is less than the {remaining_tweets} requested in this batch.")
                print("There might not be enough tweets available. Trying again with the next batch...")
            
            # Update the since_id to the newest tweet we've seen
            if not new_batch.empty and 'id' in new_batch.columns:
                # Sort by ID (descending) to get the latest tweet
                latest_batch = new_batch.sort_values('id', ascending=False)
                new_since_id = latest_batch.iloc[0]['id']
                
                print(f"Updating since_id from {self.since_id} to {new_since_id} for next batch")
                self.since_id = new_since_id
                
                # Update the count for comparison in the next iteration
                last_count = batch_size
                
                # Increment attempts and continue
                attempts += 1
                print(f"Completed attempt {attempts}/{max_attempts}. Total tweets fetched so far: {total_fetched}/{original_max_tweets}")
            else:
                # If we couldn't get an ID from the batch, stop
                print("Could not find tweet IDs in the response. Stopping.")
                break
        
        # Restore original max_tweets
        self.max_tweets = original_max_tweets
        
        # Remove duplicate tweets that might have been collected over multiple requests
        if not all_tweets.empty and 'id' in all_tweets.columns:
            original_count = len(all_tweets)
            all_tweets = all_tweets.drop_duplicates(subset=['id'])
            duplicate_count = original_count - len(all_tweets)
            print(f"After removing duplicates: {len(all_tweets)} unique tweets (removed {duplicate_count} duplicates)")
        
        print(f"Exhaustive fetching completed. Total tweets fetched: {len(all_tweets)}")
        
        # STRICT LIMIT: Ensure we don't return more than the requested number of tweets
        if len(all_tweets) > original_max_tweets:
            print(f"Limiting result to exactly {original_max_tweets} tweets as requested.")
            return all_tweets.head(original_max_tweets)
            
        return all_tweets
    
    def get_tweets_via_client(self):
        """
        Fetch tweets using the official Apify client library.
        This method should provide better pagination and fetch more tweets than the direct API method.
        
        Returns:
            pd.DataFrame: DataFrame containing tweets with id, text, and created_at columns
        """
        print(f"[{datetime.now(EDT_TZ).strftime('%I:%M:%S %p EDT')}] Fetching tweets via Apify client from @{self.twitter_handle}...")
        
        if self.since_id:
            print(f"Starting from tweet ID: {self.since_id}")
            
        # Initialize the ApifyClient with your API token
        client = ApifyClient(self.apify_token)
        
        # Prepare the Actor input - STRICTLY limit to max_tweets
        run_input = {
            "searchTerms": [],
            "searchMode": "live",
            "maxTweets": self.max_tweets,
            "maxItems": self.max_tweets,
            "twitterHandles": [self.twitter_handle],
            "skipUserTimelineScraping": False,
            "skipRetweets": False,     
            "skipReplies": False,      
            "scrapeTweetReplies": False,
            "sort": "Latest",           
            "maxRequestRetries": MAX_REQUEST_RETRIES     
        }
        
        # Add search query for specific tweet ID if needed
        if self.since_id:
            search_query = f"from:{self.twitter_handle} since_id:{self.since_id} count:{self.max_tweets}"
            run_input["searchTerms"] = [search_query]
        else:
            search_query = f"from:{self.twitter_handle} count:{self.max_tweets}"
            run_input["searchTerms"] = [search_query]
            
        if self.debug:
            print("Apify Client Input:")
            print(run_input)
            print(f"NOTE: Strictly limiting to {self.max_tweets} tweets as requested.")
            
        # Run actor
        print(f"Running actor {self.actor_task_id}...")
        try:
            run = client.actor(self.actor_task_id).call(run_input=run_input)
        except Exception as e:
            print(f"Error calling actor: {e}")
            return pd.DataFrame()
                
        if not run or "defaultDatasetId" not in run:
            print("Run failed or did not return a dataset ID")
            return pd.DataFrame()
            
        print(f"Run succeeded, dataset ID: {run['defaultDatasetId']}")
        
        # Fetch items from the dataset WITH A STRICT LIMIT
        tweets = []
        try:
            # Get items with exact limit
            items = client.dataset(run["defaultDatasetId"]).list_items(limit=self.max_tweets).items
            tweets = items[:self.max_tweets]  # Ensure we don't exceed max_tweets
            print(f"Successfully fetched {len(tweets)} tweets (requested {self.max_tweets}).")
        except Exception as e:
            print(f"Error fetching dataset items: {e}")
            return pd.DataFrame()
        
        # Format tweets
        formatted_tweets = []
        for tweet in tweets:
            # Get tweet ID
            tweet_id = str(tweet.get("id_str", "") or tweet.get("id", ""))
            
            # Get tweet text
            tweet_text = tweet.get("full_text", "") or tweet.get("text", "")
            
            # Get created time
            created_time = None
            for field in ["created_at", "createdAt", "timestamp"]:
                if field in tweet and tweet[field]:
                    created_time = self.fix_timestamp(tweet[field])
                    break
            
            if not created_time:
                created_time = "TIMESTAMP_MISSING"
            
            # Clean and format text
            formatted_text = self.clean_text(tweet_text)
            
            formatted_tweet = {
                "id": str(tweet_id),
                "text": formatted_text,
                "created_at": created_time
            }
            formatted_tweets.append(formatted_tweet)
            
            # Print tweet details if debug is enabled
            if self.debug:
                print(f"ID: {tweet_id}, Created at: {created_time}")
                print(f"Text: {tweet_text[:100]}{'...' if len(tweet_text) > 100 else ''}")
        
        # Create DataFrame and limit to max_tweets
        df = pd.DataFrame(formatted_tweets)
        print(f"Processed {len(df)} tweets.")
        
        # Final check
        if len(df) > self.max_tweets:
            print(f"Limiting result to exactly {self.max_tweets} tweets as requested.")
            return df.head(self.max_tweets)
            
        return df
        
    def fetch_and_save_tweets_client(self, use_latest_id=False):
        """
        Fetch tweets using the Apify client and save them to CSV.
        
        Args:
            use_latest_id: Whether to automatically use the latest tweet ID from the CSV file
            
        Returns:
            pd.DataFrame: DataFrame of all tweets (including existing)
        """
        # If use_latest_id is True or auto_since_id is enabled in init, get the latest tweet ID
        if use_latest_id and not self.auto_since_id:
            latest_id = self.get_latest_tweet_id()
            if latest_id:
                original_id = self.since_id
                self.since_id = latest_id
                print(f"Using latest tweet ID from database: {self.since_id}")

        # Get tweets using the client method
        new_tweets = self.get_tweets_via_client()
        
        # Restore original since_id if it was changed and we're not in auto mode
        if use_latest_id and not self.auto_since_id and 'original_id' in locals():
            self.since_id = original_id
        
        # Check if any tweets were fetched
        if new_tweets.empty:
            print("No tweets were fetched. Please check your parameters or try again later.")
            # Return empty DataFrame if in debug mode, otherwise return existing tweets
            if self.debug:
                return new_tweets
            elif os.path.exists(self.csv_file):
                print(f"Returning existing tweets from {self.csv_file}")
                return pd.read_csv(self.csv_file, dtype={"id": str})
            else:
                return new_tweets
        else:
            print(f"Successfully fetched {len(new_tweets)} tweets.")
            
        if not self.debug:  # Only save tweets if not in debug mode
            num_saved = self.save_tweets(new_tweets)
            print(f"Saved {num_saved} new tweets to {self.csv_file}")
            
            # Load and return the full dataset
            if os.path.exists(self.csv_file):
                full_df = pd.read_csv(self.csv_file, dtype={"id": str})
                print(f"Total tweets in database: {len(full_df)}")
                return full_df
        
        return new_tweets
        
    def fetch_and_save_tweets(self, use_latest_id=False, exhaustive=False, max_attempts=5):
        """
        Fetch tweets and save them to CSV, returning the DataFrame of new tweets.
        
        Args:
            use_latest_id: Whether to automatically use the latest tweet ID from the CSV file
            exhaustive: Whether to fetch tweets exhaustively using multiple API calls
            max_attempts: Maximum number of API calls when using exhaustive mode (default: 5)
            
        Returns:
            pd.DataFrame: DataFrame of all tweets (including existing)
        """
        # If use_latest_id is True or auto_since_id is enabled in init, get the latest tweet ID
        if use_latest_id and not self.auto_since_id:
            latest_id = self.get_latest_tweet_id()
            if latest_id:
                original_id = self.since_id
                self.since_id = latest_id
                print(f"Using latest tweet ID from database: {self.since_id}")
                
                if self.max_tweets < 100 and not exhaustive:
                    print(f"WARNING: max_tweets is set to {self.max_tweets}, which may not be enough to capture all " 
                          f"new tweets since the latest stored tweet. Consider increasing this value or using --exhaustive mode.")
        
        # Get tweets - either using regular method or exhaustive method
        if exhaustive:
            print(f"Using exhaustive fetching with up to {max_attempts} API calls to obtain all tweets since ID: {self.since_id or 'None'}")
            new_tweets = self.get_tweets_exhaustive(self.since_id, max_attempts=max_attempts)
        else:
            # Regular single fetch
            print(f"Using single fetch to obtain up to {self.max_tweets} tweets since ID: {self.since_id or 'None'}")
            new_tweets = self.get_tweets()
        
        # Restore original since_id if it was changed and we're not in auto mode
        if use_latest_id and not self.auto_since_id and 'original_id' in locals():
            self.since_id = original_id
        
        # Check if any tweets were fetched
        if new_tweets.empty:
            print("No tweets were fetched. Please check your parameters or try again later.")
            # Return empty DataFrame if in debug mode, otherwise return existing tweets
            if self.debug:
                return new_tweets
            elif os.path.exists(self.csv_file):
                print(f"Returning existing tweets from {self.csv_file}")
                return pd.read_csv(self.csv_file, dtype={"id": str})
            else:
                return new_tweets
        else:
            print(f"Successfully fetched {len(new_tweets)} tweets.")
            
        if not self.debug:  # Only save tweets if not in debug mode
            num_saved = self.save_tweets(new_tweets)
            print(f"Saved {num_saved} new tweets to {self.csv_file}")
            
            # Load and return the full dataset
            if os.path.exists(self.csv_file):
                full_df = pd.read_csv(self.csv_file, dtype={"id": str})
                print(f"Total tweets in database: {len(full_df)}")
                return full_df
        
        return new_tweets
        
    def add_to_database(self, use_latest_id=False, exhaustive=False, max_attempts=5):
        """
        Fetch tweets and add only new ones to the database file.
        This is specifically for adding tweets that aren't already in the database.
        
        Args:
            use_latest_id: Whether to automatically use the latest tweet ID from the CSV file
            exhaustive: Whether to fetch tweets exhaustively using multiple API calls
            max_attempts: Maximum number of API calls when using exhaustive mode (default: 5)
            
        Returns:
            int: Number of new tweets added to the database
        """
        print(f"Fetching tweets from @{self.twitter_handle} to add to database...")
        
        # If use_latest_id is True or auto_since_id is enabled in init, get the latest tweet ID
        if use_latest_id and not self.auto_since_id:
            latest_id = self.get_latest_tweet_id()
            if latest_id:
                original_id = self.since_id
                self.since_id = latest_id
                print(f"Using latest tweet ID from database: {self.since_id}")
                
                if self.max_tweets < 100:
                    print(f"WARNING: max_tweets is set to {self.max_tweets}, which may not be enough to capture all " 
                          f"new tweets since the latest stored tweet. Consider increasing this value if needed.")
        
        # Set format to Georgia style for database storage
        old_style = self.format_style
        self.format_style = "georgia"
        
        # Get tweets - either using regular method or exhaustive method
        if exhaustive:
            print(f"Using exhaustive fetching to obtain all tweets since ID: {self.since_id}")
            new_tweets = self.get_tweets_exhaustive(self.since_id, max_attempts=max_attempts)
        else:
            # Regular single fetch
            new_tweets = self.get_tweets()
        
        # Restore original format style
        self.format_style = old_style
        
        # Restore original since_id if it was changed and we're not in auto mode
        if use_latest_id and not self.auto_since_id and 'original_id' in locals():
            self.since_id = original_id
        
        if new_tweets.empty:
            print("No tweets found to add to the database.")
            return 0
            
        # Save tweets to the database
        num_added = self.save_tweets(new_tweets)
        
        return num_added
        
    def add_to_database_client(self, use_latest_id=False):
        """
        Fetch tweets using the Apify client and add only new ones to the database file.
        
        Args:
            use_latest_id: Whether to automatically use the latest tweet ID from the CSV file
            
        Returns:
            int: Number of new tweets added to the database
        """
        print(f"Fetching tweets from @{self.twitter_handle} to add to database using Apify client...")
        
        # If use_latest_id is True or auto_since_id is enabled in init, get the latest tweet ID
        if use_latest_id and not self.auto_since_id:
            latest_id = self.get_latest_tweet_id()
            if latest_id:
                original_id = self.since_id
                self.since_id = latest_id
                print(f"Using latest tweet ID from database: {self.since_id}")
        
        # Set format to Georgia style for database storage
        old_style = self.format_style
        self.format_style = "georgia"
        
        # Get tweets using the client method
        new_tweets = self.get_tweets_via_client()
        
        # Restore original format style
        self.format_style = old_style
        
        # Restore original since_id if it was changed and we're not in auto mode
        if use_latest_id and not self.auto_since_id and 'original_id' in locals():
            self.since_id = original_id
        
        if new_tweets.empty:
            print("No tweets found to add to the database.")
            return 0
            
        # Save tweets to the database
        num_added = self.save_tweets(new_tweets)
        
        return num_added
    
    def save_tweets(self, tweets, file_name=None):
        """
        Save tweets to a CSV file, handling duplicates and proper formatting.
        
        Args:
            tweets: DataFrame containing tweets to save
            file_name: Optional custom file name to save to (if None, uses self.csv_file)
            
        Returns:
            int: Number of new tweets saved
        """
        if tweets.empty:
            print("No tweets to save.")
            return 0
        
        # Set the file path
        output_path = file_name if file_name else self.csv_file
        
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Load existing CSV if it exists
        if os.path.exists(output_path):
            try:
                existing_df = pd.read_csv(output_path, dtype={"id": str})
                print(f"Loaded existing CSV file with {len(existing_df)} tweets")
            except Exception as e:
                print(f"Error reading existing CSV: {e}")
                existing_df = pd.DataFrame(columns=["id", "text", "created_at"])
        else:
            print(f"Creating new CSV file at {output_path}")
            existing_df = pd.DataFrame(columns=["id", "text", "created_at"])
        
        # Check for duplicates
        if not existing_df.empty and "id" in existing_df.columns:
            existing_ids = set(existing_df["id"].astype(str))
            tweets = tweets[~tweets["id"].astype(str).isin(existing_ids)]
            
            if tweets.empty:
                print("No new unique tweets to save.")
                return 0
            
            print(f"Found {len(tweets)} new tweets to add")
        
        # Concatenate and sort
        updated_df = pd.concat([existing_df, tweets], ignore_index=True)
        
        # Make sure all timestamps are in correct format for sorting
        def extract_date_for_sorting(date_str):
            try:
                # For Georgia format: "2025:04:20:01:30:21"
                if ':' in date_str and date_str.count(':') >= 3:
                    return pd.to_datetime(date_str, format='%Y:%m:%d:%H:%M:%S', errors='coerce')
                # For EDT format: "2025-04-20 01:30:21 PM EDT"
                elif 'EDT' in date_str:
                    date_part = date_str.replace(' EDT', '')
                    return pd.to_datetime(date_part, format='%Y-%m-%d %I:%M:%S %p', errors='coerce')
                else:
                    # Try other formats
                    return pd.to_datetime(date_str, errors='coerce')
            except Exception:
                return pd.NaT
            
        updated_df['temp_date'] = updated_df['created_at'].apply(extract_date_for_sorting)
        
        # Sort by date (oldest first, newest last)
        updated_df = updated_df.sort_values('temp_date')
        
        # Drop the temporary column
        updated_df = updated_df.drop('temp_date', axis=1)
                     
        # Ensure all timestamps are in the correct format
        if self.format_style == "georgia":
            # Make sure all timestamps are in YYYY:MM:DD:HH:MM:SS format
            for idx, row in updated_df.iterrows():
                if ':' not in row['created_at'] or row['created_at'].count(':') < 3:
                    try:
                        # Convert to Georgia format
                        if 'EDT' in row['created_at']:
                            # Parse EDT format first
                            date_part = row['created_at'].replace(' EDT', '')
                            dt = datetime.strptime(date_part, '%Y-%m-%d %I:%M:%S %p')
                            dt = dt.replace(tzinfo=EDT_TZ)
                            # Convert to Georgia timezone
                            dt = dt.astimezone(GEORGIA_TZ)
                            updated_df.at[idx, 'created_at'] = dt.strftime("%Y:%m:%d:%H:%M:%S")
                    except Exception as e:
                        if self.debug:
                            print(f"Error converting timestamp {row['created_at']}: {e}")
        
        # Clean the tweet text (without adding triple quotes)
        updated_df['text'] = updated_df['text'].apply(self.clean_text)
        
        # Save to CSV - use the specific format requested: "id","text","created_at"
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)  # Quote all fields
            writer.writerow(['id', 'text', 'created_at'])  # Header
            for _, row in updated_df.iterrows():
                writer.writerow([row['id'], row['text'], row['created_at']])
        
        print(f"Added {len(tweets)} new tweets to {output_path}")
        print(f"Total tweets in CSV (including existing): {len(updated_df)}")
        return len(tweets)
