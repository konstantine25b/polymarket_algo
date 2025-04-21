import os
from datetime import datetime
import pandas as pd

class TweetAppender:
    def __init__(self):
        # Get the correct path to the data directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(current_dir)
        self.csv_file = os.path.join(src_dir, 'data', 'elonmusk_reformatted.csv')
        print(f"Tweet Appender initialized - will add tweets to: {self.csv_file}")
        
        # Ensure the file exists and has headers
        if not os.path.exists(self.csv_file):
            print(f"Creating new file: {self.csv_file}")
            with open(self.csv_file, 'w', encoding='utf-8') as f:
                f.write("id,text,created_at\n")
        else:
            # If file exists, ensure all existing entries have quotes
            self.fix_existing_quotes()

    def fix_existing_quotes(self):
        """Ensure all existing entries have quotes around text"""
        try:
            # Read the existing CSV
            df = pd.read_csv(self.csv_file)
            
            # Add quotes to text if they don't exist
            df['text'] = df['text'].apply(lambda x: f'"{x}"' if not x.startswith('"') else x)
            
            # Save back to CSV
            df.to_csv(self.csv_file, index=False)
            print("✅ Fixed quotes in existing entries")
        except Exception as e:
            print(f"Error fixing existing quotes: {str(e)}")

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
                    # Clean the text for CSV format and add quotes
                    safe_text = tweet['text'].replace('\n', ' ')
                    if not safe_text.startswith('"'):
                        safe_text = f'"{safe_text}"'
                    
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
