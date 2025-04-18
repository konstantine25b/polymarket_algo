import time
import os
from datetime import datetime, timedelta
import logging
from tweet_fetcher import TestTweetScraper
from tweet_appender import TweetAppender

# Set up logging
log_file = os.path.join(os.path.dirname(__file__), 'tweet_collector.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

class TweetScheduler:
    def __init__(self):
        self.scraper = TestTweetScraper()
        self.appender = TweetAppender()
        self.check_interval = 120  # 2 minutes in seconds
        logging.info("Tweet Scheduler initialized")

    def run(self):
        """Run the scheduler indefinitely"""
        logging.info("🚀 Starting Tweet Collection Service")
        
        while True:
            try:
                check_start_time = datetime.now()
                logging.info(f"⏳ Checking for new tweets at {check_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Fetch and process tweets
                tweets = self.scraper.fetch_tweets()
                new_tweets = self.scraper.process_tweets(tweets)
                
                # Append new tweets
                if new_tweets:
                    self.appender.append_tweets(new_tweets)
                else:
                    logging.info("No new tweets found")
                
                # Calculate wait time for next check
                check_duration = (datetime.now() - check_start_time).total_seconds()
                wait_time = max(0, self.check_interval - check_duration)
                
                next_check_time = datetime.now() + timedelta(seconds=wait_time)
                logging.info(f"⏰ Next check scheduled for: {next_check_time.strftime('%H:%M:%S')}")
                
                time.sleep(wait_time)
                
            except Exception as e:
                logging.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying if there's an error

def main():
    scheduler = TweetScheduler()
    scheduler.run()

if __name__ == "__main__":
    main() 