import requests
import pandas as pd
import time
from datetime import datetime
import os
from tweet_appender import TweetAppender

# Update for Elon's account
API_TOKEN = "apify_api_6d8pA83aCt4qBagSR1xmONKZDFafYf0OFdXk"
TASK_ID = "aI9hN4c6Edw8VdUc3"  # Elon's task ID

class TestTweetScraper:
    def __init__(self):
        self.headers = {
            'Authorization': f'Bearer {API_TOKEN}'
        }
        self.appender = TweetAppender()  # Create the appender
        self.seen_tweets = set()
        print("Tweet Scraper initialized for @elonmusk")

    def fetch_tweets(self):
        """Start task and get tweets"""
        try:
            start_url = f'https://api.apify.com/v2/actor-tasks/{TASK_ID}/runs'
            print(f"\nStarting new task run to fetch @elonmusk tweets...")
            
            start_response = requests.post(start_url, headers=self.headers)
            if start_response.status_code != 201:
                print(f"Failed to start task: {start_response.text}")
                return []
            
            run_id = start_response.json()['data']['id']
            print(f"Started run: {run_id}")

            # Wait for task to finish
            status = 'RUNNING'
            while status in ['RUNNING', 'READY']:
                time.sleep(5)
                status_url = f'https://api.apify.com/v2/actor-runs/{run_id}'
                status_response = requests.get(status_url, headers=self.headers)
                if status_response.status_code == 200:
                    status = status_response.json()['data']['status']
                    print(f"Status: {status}")
                else:
                    print(f"Error checking status: {status_response.text}")
                    return []

            dataset_id = status_response.json()['data']['defaultDatasetId']
            dataset_url = f'https://api.apify.com/v2/datasets/{dataset_id}/items'
            tweets_response = requests.get(dataset_url, headers=self.headers)
            
            if tweets_response.status_code != 200:
                print(f"Failed to get tweets: {tweets_response.text}")
                return []

            tweets = tweets_response.json()
            print(f"Retrieved {len(tweets)} tweets from API")
            return tweets

        except Exception as e:
            print(f"Error fetching tweets: {str(e)}")
            return []

    def process_tweets(self, tweets):
        """Process and format tweets"""
        new_tweets = []
        print(f"\nChecking {len(tweets)} tweets/retweets from @elonmusk")
        
        for tweet in tweets:
            tweet_id = str(tweet.get('id', ''))
            
            # Skip if we've seen this tweet before
            if tweet_id in self.seen_tweets:
                continue
                
            created_at = tweet.get('createdAt', '')
            text = tweet.get('text', '')
            is_retweet = tweet.get('retweetedTweet') is not None
            
            try:
                dt = datetime.strptime(created_at, '%a %b %d %H:%M:%S +0000 %Y')
                formatted_time = dt.strftime('%Y:%m:%d:%H:%M:%S')
            except Exception as e:
                print(f"Error formatting time {created_at}: {str(e)}")
                formatted_time = created_at
            
            new_tweets.append({
                'id': tweet_id,
                'text': text,
                'created_at': formatted_time
            })
            self.seen_tweets.add(tweet_id)
            print(f"\nFound new {'retweet' if is_retweet else 'tweet'} from @elonmusk:")
            print(f"ID: {tweet_id}")
            print(f"Time: {formatted_time}")
            print(f"Text: {text[:100]}...")
        
        return new_tweets

    def save_tweets(self, new_tweets):
        """Pass tweets to the appender"""
        if new_tweets:
            self.appender.append_tweets(new_tweets)
        else:
            print("No new tweets to append")

def main():
    scraper = TestTweetScraper()
    print("🚀 Elon Musk Tweet Scraper Started!")
    
    while True:
        try:
            check_start_time = datetime.now()
            print(f"\n{'='*50}")
            print(f"⏳ Checking for @elonmusk tweets at {check_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Fetch and process tweets
            tweets = scraper.fetch_tweets()
            new_tweets = scraper.process_tweets(tweets)
            scraper.save_tweets(new_tweets)  # This will pass tweets to the appender
            
            # Calculate wait time for next check
            check_duration = (datetime.now() - check_start_time).total_seconds()
            wait_time = max(0, 120 - check_duration)  # 120 seconds = 2 minutes
            
            next_check_time = datetime.now() + pd.Timedelta(seconds=wait_time)
            print(f"\n⏰ Next check at: {next_check_time.strftime('%H:%M:%S')}")
            print(f"{'='*50}\n")
            
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"Error in main loop: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()