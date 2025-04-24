import requests
import pandas as pd
import time
import os
from datetime import datetime, timedelta
import schedule
import csv
import pytz
import re
import argparse  # Add argparse for command-line arguments

# Parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='Fetch tweets from Elon Musk\'s Twitter account')
    parser.add_argument('--interval', '-i', type=int, default=5,
                      help='Refresh interval in minutes (default: 5)')
    parser.add_argument('--max-tweets', '-m', type=int, default=5,
                      help='Maximum number of tweets to fetch per request (default: 5)')
    parser.add_argument('--one-time', '-o', action='store_true',
                      help='Run once and exit (don\'t keep running on schedule)')
    return parser.parse_args()

# Get command-line arguments
args = parse_args()

# CONFIGURATION
APIFY_TOKEN = "apify_api_e6Vimb3keKr5cNn5Ac6WolYLDJdSYb0DKdym"
ACTOR_TASK_ID = "sosoxuc~twitter-x-com-scraper-unlimited-test"  # ✅ Must be defined before it's used
CSV_FILE = "src/data/elonmusk_reformatted.csv"  # Updated path to the correct location
MAX_TWEETS = args.max_tweets
REFRESH_INTERVAL = args.interval  # Minutes between refreshes - now configurable via command line

# Georgia timezone (UTC+4)
GEORGIA_TZ = pytz.timezone('Asia/Tbilisi')

def fix_timestamp(timestamp_str):
    """
    Fix timestamp format by converting to Georgia time and removing unwanted patterns
    """
    # Remove trailing spaces if any
    timestamp_str = timestamp_str.strip()
    
    try:
        # Check various timestamp formats
        if '+0000' in timestamp_str:
            # Handle Twitter's format: Thu Apr 24 15:02:52 +0000 2025
            match = re.match(r'(\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2})', timestamp_str)
            if match:
                date_part = match.group(1)
                try:
                    # Try parsing with full Twitter format first
                    dt = datetime.strptime(timestamp_str, '%a %b %d %H:%M:%S +0000 %Y')
                except:
                    # Fallback to just the date part and assume current year
                    current_year = datetime.now().year
                    dt = datetime.strptime(f"{date_part} {current_year}", '%a %b %d %H:%M:%S %Y')
                
                dt = pytz.utc.localize(dt)
            else:
                # If regex fails, try direct conversion
                dt = datetime.strptime(timestamp_str, '%a %b %d %H:%M:%S +0000 %Y')
                dt = pytz.utc.localize(dt)
        elif re.match(r'\d{4}:\d{2}:\d{2}:\d{2}:\d{2}:\d{2}', timestamp_str):
            # Already in our target format, just parse it
            dt = datetime.strptime(timestamp_str, '%Y:%m:%d:%H:%M:%S')
            # Assume it's already in Georgia time if it's in our format
            return timestamp_str
        else:
            # Try to handle other formats
            # Remove any timezone indicator at the end
            clean_timestamp = re.sub(r'\s*\+\d{4}.*$', '', timestamp_str)
            clean_timestamp = clean_timestamp.strip()
            
            if re.match(r'\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2}', clean_timestamp):
                # Thu Apr 24 15:02:52 format without timezone
                current_year = datetime.now().year
                dt = datetime.strptime(f"{clean_timestamp} {current_year}", '%a %b %d %H:%M:%S %Y')
                dt = pytz.utc.localize(dt)
            else:
                # Last resort - try ISO format or raise error
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
        # Convert to Georgia time
        dt = dt.astimezone(GEORGIA_TZ)
        return dt.strftime("%Y:%m:%d:%H:%M:%S")
    except Exception as e:
        print(f"Error parsing date '{timestamp_str}': {e}")
        # Return original timestamp as fallback rather than current time
        return timestamp_str

def clean_existing_csv():
    """
    Clean up timestamps and text formatting in the existing CSV file
    """
    if not os.path.exists(CSV_FILE):
        print(f"CSV file {CSV_FILE} does not exist yet.")
        return
        
    try:
        df = pd.read_csv(CSV_FILE)
        if 'created_at' not in df.columns:
            print("No 'created_at' column found in CSV.")
            return
            
        print(f"Cleaning timestamps and text formatting in {CSV_FILE}...")
        # Fix all timestamps
        df['created_at'] = df['created_at'].apply(fix_timestamp)
        
        # Clean text formatting - remove extra whitespace, newlines, tabs
        if 'text' in df.columns:
            def clean_text(text):
                # Ensure it's a string
                text = str(text)
                # Remove triple quotes if they exist
                if text.startswith('"""') and text.endswith('"""'):
                    text = text[3:-3]
                # Replace all newlines, tabs and normalize spaces
                text = ' '.join(text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').split())
                # Add back triple quotes
                return f'"""{text}"""'
            
            df['text'] = df['text'].apply(clean_text)
            print(f"Cleaned text formatting for {len(df)} tweets")
        
        # Convert to datetime for sorting
        df['temp_date'] = pd.to_datetime(df['created_at'], format='%Y:%m:%d:%H:%M:%S', errors='coerce')
        
        # Sort by date (oldest first, newest last)
        df = df.sort_values('temp_date')
        
        # Drop the temporary column
        df = df.drop('temp_date', axis=1)
        
        # Save the cleaned file
        df.to_csv(CSV_FILE, index=False, encoding='utf-8', quoting=csv.QUOTE_NONNUMERIC)
        print(f"Successfully cleaned and sorted {len(df)} timestamps in {CSV_FILE}")
    except Exception as e:
        print(f"Error cleaning CSV: {e}")

def fetch_new_tweets():
    print(f"[{datetime.now(GEORGIA_TZ)}] Fetching tweets...")

    # Run input for Twitter scraper lite
    run_input = {
        "searchTerms": [],
        "searchMode": "live",
        "maxTweets": MAX_TWEETS,
        "twitterHandles": [],
        "twitterUrls": ["https://x.com/elonmusk"]
    }
    
    # Start the actor directly
    run_url = f"https://api.apify.com/v2/actor-tasks/{ACTOR_TASK_ID}/runs?token={APIFY_TOKEN}"
    response = requests.post(run_url, json={"useClient": True, "input": run_input})
    
    if response.status_code != 201:
        print(f"Error starting actor: {response.status_code}")
        print(f"Response: {response.text}")
        return
        
    run_data = response.json()
    run_id = run_data.get("data", {}).get("id")
    
    if not run_id:
        print(f"Could not find run ID in response: {run_data}")
        return
    
    print(f"Run started with ID: {run_id}")

    # Wait for the run to finish
    print("Waiting for run to complete...")
    status = "RUNNING"
    
    while status == "RUNNING":
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        status_response = requests.get(status_url)
        
        if status_response.status_code != 200:
            print(f"Error checking status: {status_response.status_code}")
            time.sleep(3)
            continue
            
        status_data = status_response.json()
        status = status_data.get("data", {}).get("status", "UNKNOWN")
            
        if status in ["SUCCEEDED", "FAILED", "TIMED-OUT"]:
            break
            
        print(f"Current status: {status}")
        time.sleep(3)

    if status != "SUCCEEDED":
        print(f"Actor run failed or timed out. Final status: {status}")
        return

    # Get dataset items
    dataset_id = status_data["data"]["defaultDatasetId"]
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}"
    dataset_response = requests.get(dataset_url)
    
    if dataset_response.status_code != 200:
        print(f"Error fetching dataset: {dataset_response.status_code}")
        return
        
    tweets = dataset_response.json()

    if not tweets:
        print("No tweets found in the dataset.")
        return
        
    print(f"Fetched {len(tweets)} tweets.")
    
    # Debug first tweet structure
    if tweets:
        print("Tweet structure example:")
        print(tweets[0])

    # Format tweets
    formatted_tweets = []
    for tweet in tweets:
        # Get tweet ID
        tweet_id = str(tweet.get("id_str", "") or tweet.get("id", ""))
        
        # Get tweet text
        tweet_text = tweet.get("full_text", "") or tweet.get("text", "")
        
        # Get created time - prioritize original creation timestamp
        created_time = None
        
        # Debug timestamp fields
        if tweets and len(formatted_tweets) == 0:
            print("Available timestamp fields:")
            for field in ["created_at", "createdAt", "timestamp"]:
                if field in tweet:
                    print(f"- {field}: {tweet[field]}")
        
        # Check multiple possible date fields
        for field in ["created_at", "createdAt", "timestamp"]:
            if field in tweet and tweet[field]:
                # Store the original timestamp for debugging
                original_timestamp = tweet[field]
                created_time = fix_timestamp(original_timestamp)
                print(f"Original tweet timestamp: {original_timestamp}")
                print(f"Converted timestamp: {created_time}")
                break
        
        # If no time found, use a placeholder to indicate missing data
        if not created_time:
            created_time = "TIMESTAMP_MISSING"
            print("Warning: No creation timestamp found for tweet")
        
        # Clean text and format with triple quotes to match elonmusk_reformatted.csv format
        # Replace all whitespace (newlines, tabs, multiple spaces) with a single space
        tweet_text = str(tweet_text).encode('ascii', 'replace').decode('ascii')
        # Remove all newlines, tabs and normalize spaces
        tweet_text = ' '.join(tweet_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').split())
        formatted_text = f'"""{tweet_text}"""'
        
        formatted_tweet = {
            "id": str(tweet_id),
            "text": formatted_text,
            "created_at": created_time
        }
        formatted_tweets.append(formatted_tweet)
    
    # Save to CSV
    new_data = pd.DataFrame(formatted_tweets)
    
    if new_data.empty:
        print("No tweets to save after formatting.")
        return
    
    # Load existing CSV if it exists
    if os.path.exists(CSV_FILE):
        try:
            existing_df = pd.read_csv(CSV_FILE, dtype={"id": str})
            print(f"Loaded existing CSV file with {len(existing_df)} tweets")
        except Exception as e:
            print(f"Error reading existing CSV: {e}")
            existing_df = pd.DataFrame(columns=["id", "text", "created_at"])
    else:
        print(f"Creating new CSV file at {CSV_FILE}")
        existing_df = pd.DataFrame(columns=["id", "text", "created_at"])
    
    # Check for duplicates
    if not existing_df.empty and "id" in existing_df.columns:
        # Get existing IDs
        existing_ids = set(existing_df["id"].astype(str))
        
        # Filter out tweets that already exist in the CSV
        new_tweets = [tweet for tweet in formatted_tweets if str(tweet["id"]) not in existing_ids]
        
        if not new_tweets:
            print("No new unique tweets to save.")
            return
            
        print(f"Found {len(new_tweets)} new tweets to add")
        new_data = pd.DataFrame(new_tweets)
    
    # Concatenate and sort
    updated_df = pd.concat([existing_df, new_data], ignore_index=True)
    
    # Make sure all timestamps are in correct format
    updated_df['created_at'] = updated_df['created_at'].apply(fix_timestamp)
    
    # Convert created_at to datetime for sorting
    updated_df['temp_date'] = pd.to_datetime(updated_df['created_at'], format='%Y:%m:%d:%H:%M:%S', errors='coerce')
    
    # Sort by date (oldest first, newest last)
    updated_df = updated_df.sort_values('temp_date')
    
    # Drop the temporary column
    updated_df = updated_df.drop('temp_date', axis=1)
    
    # Save to CSV with proper quoting to maintain triple quotes
    # Use the Python CSV writer for more control over line endings and to ensure we're appending not replacing
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        # Write header
        writer.writerow(['id', 'text', 'created_at'])
        # Write data rows - this includes BOTH existing and new tweets
        for _, row in updated_df.iterrows():
            writer.writerow([row['id'], row['text'], row['created_at']])
    
    print(f"Added {len(new_data)} new tweets to {CSV_FILE}")
    print(f"Total tweets in CSV (including existing): {len(updated_df)}")
    if len(new_data) > 0:
        print(f"Sample of newly added tweet: {new_data.iloc[0]['text']}")

print(f"Tweet fetcher started with refresh interval of {REFRESH_INTERVAL} minutes.")
if args.one_time:
    print("Running in one-time mode. Will exit after fetching tweets once.")
else:
    print("Running in continuous mode. Press Ctrl+C to stop.")

# Clean existing CSV file first
clean_existing_csv()

# Run once immediately
fetch_new_tweets()

# If not in one-time mode, continue with schedule
if not args.one_time:
    # Schedule to run every X minutes (from command-line argument)
    schedule.every(REFRESH_INTERVAL).minutes.do(fetch_new_tweets)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Script stopped by user")
else:
    print("One-time fetch completed. Exiting.")
