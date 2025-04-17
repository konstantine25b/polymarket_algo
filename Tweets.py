import requests
import time
import json
from datetime import datetime, timedelta
import pandas as pd
import os
import logging

# Configure logging
logging.basicConfig(
    filename='tweet_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
MAIN_CSV_FILE = 'all_tweets_database.csv'
BACKUP_DIR = 'backups'
MAX_RETRIES = 3

# Store previously seen tweet IDs to avoid duplicates
seen_tweets = set()

# Load existing tweets from main CSV file if it exists
def load_existing_tweets():
    if os.path.exists(MAIN_CSV_FILE):
        df = pd.read_csv(MAIN_CSV_FILE)
        return set(df['id'].astype(str))  # Convert IDs to strings for consistency
    return set()

def track_error(error_msg):
    logging.error(error_msg)
    # Could add notification system here

def fetch_and_format_tweets():
    API_TOKEN = "your_paid_api_token"  # Replace with your paid token
    TASK_ID = "gDjT6EMCYCi0Ry8BZ"
    
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Content-Type': 'application/json'
    }

    try:
        # 1. Start the task
        print(f"\nStarting new fetch at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        start_url = f'https://api.apify.com/v2/actor-tasks/{TASK_ID}/runs'
        start_response = requests.post(start_url, headers=headers)
        start_response.raise_for_status()
        run_id = start_response.json()['data']['id']
        print(f"✅ Started run with ID: {run_id}")

        # 2. Wait for the run to finish
        status = 'RUNNING'
        while status in ['RUNNING', 'READY']:
            time.sleep(5)
            status_url = f'https://api.apify.com/v2/actor-runs/{run_id}'
            status_response = requests.get(status_url, headers=headers)
            status_response.raise_for_status()
            status = status_response.json()['data']['status']
            print(f"⏳ Current status: {status}")

        # 3. Get the dataset with tweets
        dataset_id = status_response.json()['data']['defaultDatasetId']
        dataset_url = f'https://api.apify.com/v2/datasets/{dataset_id}/items?format=json'
        tweets_response = requests.get(dataset_url, headers=headers)
        tweets_response.raise_for_status()
        tweets = tweets_response.json()

        # 4. Process tweets
        new_tweets = []
        for tweet in tweets[:5]:  # Get only 5 most recent
            tweet_id = str(tweet.get('id', ''))  # Convert ID to string
            if tweet_id and tweet_id not in seen_tweets:
                text = tweet.get('text', tweet.get('fullText', ''))
                created_at = tweet.get('createdAt', '')
                
                if text and created_at:
                    try:
                        # Parse Twitter's timestamp and format it
                        dt = datetime.strptime(created_at, '%a %b %d %H:%M:%S +0000 %Y')
                        formatted_time = dt.strftime('%Y:%m:%d:%H:%M:%S')
                        
                        new_tweets.append({
                            'id': tweet_id,
                            'text': text,
                            'created_at': formatted_time
                        })
                        seen_tweets.add(tweet_id)
                    except Exception as e:
                        print(f"Error processing tweet {tweet_id}: {str(e)}")
                        continue

        # 5. Save new tweets to both temporary and main CSV files
        if new_tweets:
            # Create DataFrame with new tweets
            new_df = pd.DataFrame(new_tweets)
            
            # Save to timestamped file (temporary file for this batch)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_filename = f'tweets_{timestamp}.csv'
            new_df.to_csv(temp_filename, index=False)
            print(f"✅ Saved {len(new_tweets)} new tweets to {temp_filename}")
            
            # Update main CSV file
            if os.path.exists(MAIN_CSV_FILE):
                # Read existing file
                main_df = pd.read_csv(MAIN_CSV_FILE)
                # Append new tweets
                main_df = pd.concat([main_df, new_df], ignore_index=True)
                # Remove any duplicates based on tweet ID
                main_df = main_df.drop_duplicates(subset=['id'])
                # Sort by created_at
                main_df['created_at'] = pd.to_datetime(main_df['created_at'])
                main_df = main_df.sort_values('created_at', ascending=False)
            else:
                # If main file doesn't exist, use new tweets as initial data
                main_df = new_df
            
            # Save updated main file
            main_df.to_csv(MAIN_CSV_FILE, index=False)
            print(f"✅ Updated main database in {MAIN_CSV_FILE}")
            
            # Print the new tweets we just added
            print("\nNew tweets added to database:")
            for tweet in new_tweets:
                print(f"ID: {tweet['id']}")
                print(f"Time: {tweet['created_at']}")
                print(f"Text: {tweet['text'][:100]}...")  # Show first 100 chars
                print("-" * 50)
        else:
            print("No new tweets found")

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error: {str(e)}")
        return False
    except pd.errors.EmptyDataError:
        logging.error("No data received from API")
        return False
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return False
    return True

def validate_tweet(tweet_data):
    required_fields = ['id', 'text', 'created_at']
    return all(field in tweet_data for field in required_fields)

def cleanup_old_files():
    # Keep only last 7 days of individual files
    current_time = datetime.now()
    for file in os.listdir('.'):
        if file.startswith('tweets_') and file.endswith('.csv'):
            file_time = datetime.strptime(file[7:-4], '%Y%m%d_%H%M%S')
            if (current_time - file_time).days > 7:
                os.remove(file)

def create_backup():
    if os.path.exists(MAIN_CSV_FILE):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{BACKUP_DIR}/backup_{timestamp}.csv"
        os.makedirs(BACKUP_DIR, exist_ok=True)
        pd.read_csv(MAIN_CSV_FILE).to_csv(backup_file, index=False)
        logging.info(f"Created backup: {backup_file}")

def main():
    print("Starting tweet monitoring...")
    logging.info("Application started")
    
    # Create backup directory
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Load existing tweets
    global seen_tweets
    seen_tweets = load_existing_tweets()
    logging.info(f"Loaded {len(seen_tweets)} existing tweet IDs")
    
    backup_counter = 0
    while True:
        try:
            # Run the fetch and format
            fetch_and_format_tweets()
            
            # Create backup every 24 hours
            backup_counter += 1
            if backup_counter >= 720:  # 720 * 2 minutes = 24 hours
                create_backup()
                backup_counter = 0
            
            # Cleanup old files
            cleanup_old_files()
            
            # Wait for next run
            next_run = (datetime.now() + timedelta(minutes=2)).strftime('%H:%M:%S')
            print(f"\nWaiting 2 minutes... Next run at {next_run}")
            time.sleep(120)
            
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()