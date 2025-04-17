import os
from datetime import datetime

class TweetAppender:
    def __init__(self):
        self.csv_file = 'elonmusk_reformatted.csv'  # The target file
        print(f"Tweet Appender initialized - will add tweets to: {self.csv_file}")

    def append_tweets(self, tweets):
        """ONLY append new tweets to elonmusk_reformatted.csv"""
        if not tweets:
            print("No new tweets to add")
            return

        try:
            # Sort tweets by time (oldest first, newest last)
            sorted_tweets = sorted(tweets, key=lambda x: x['created_at'])
            
            # Open file in append mode ONLY
            with open(self.csv_file, 'a', encoding='utf-8') as f:
                tweets_added = 0
                for tweet in sorted_tweets:
                    # Clean the text for CSV format
                    safe_text = tweet['text'].replace(',', ' ').replace('\n', ' ')
                    
                    # Create the CSV line
                    line = f"{tweet['id']},{safe_text},{tweet['created_at']}\n"
                    f.write(line)
                    tweets_added += 1
                    
                    # Print info about added tweet
                    print(f"\nAdded to {self.csv_file}:")
                    print(f"ID: {tweet['id']}")
                    print(f"Time: {tweet['created_at']}")
                    print(f"Text: {safe_text[:100]}...")

                print(f"\n✅ Successfully added {tweets_added} new tweets to {self.csv_file}")

        except Exception as e:
            print(f"Error while adding tweets: {str(e)}")

