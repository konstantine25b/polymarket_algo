#!/usr/bin/env python3
"""
Simple script to fetch tweets from Elon Musk.
"""

import argparse
import pandas as pd
import os
import sys

# When running as a module (python -m src.apify.get_elon_tweets), use the correct import paths
try:
    from src.apify.models.tweet_getter import TweetGetter
    from src.constants import APIFY_TOKEN, APIFY_TWITTER_ACTOR_TASK_ID
except ModuleNotFoundError:
    # Fallback for direct execution
    try:
        # Add the project root to the path for imports
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
        from src.apify.models.tweet_getter import TweetGetter
        from src.constants import APIFY_TOKEN, APIFY_TWITTER_ACTOR_TASK_ID
    except ModuleNotFoundError:
        # Last resort fallback
        from models.tweet_getter import TweetGetter
        # Constants will be loaded from the TweetGetter defaults

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Fetch tweets from Elon Musk\'s Twitter account')
    parser.add_argument('--max-tweets', '-m', type=int, default=20,
                      help='Maximum number of tweets to fetch (default: 20)')
    parser.add_argument('--since-id', '-s', type=str,
                      help='Tweet ID to start fetching from (e.g., "1915647254519795869")')
    parser.add_argument('--output', '-o', type=str, default=None,
                      help='Output CSV file path (default: src/data/elonmusk_reformatted.csv)')
    parser.add_argument('--debug', '-d', action='store_true',
                      help='Print debug information and do not store tweets')
    parser.add_argument('--add-to-db', '-a', action='store_true',
                      help='Add new tweets to the database in the Georgia timestamp format')
    parser.add_argument('--format', '-f', type=str, choices=['georgia', 'edt'], default='georgia',
                      help='Timestamp format (both use Eastern Time - georgia: YYYY:MM:DD:HH:MM:SS, edt: YYYY-MM-DD HH:MM:SS AM/PM EDT)')
    parser.add_argument('--latest', '-l', action='store_true',
                      help='Automatically use the latest tweet ID from the database')
    parser.add_argument('--auto-since-id', action='store_true',
                      help='Always automatically use the latest tweet ID (works across runs)')
    parser.add_argument('--exhaustive', '-e', action='store_true',
                      help='Use exhaustive fetching to ensure all tweets are captured')
    parser.add_argument('--max-attempts', type=int, default=3,
                      help='Maximum number of API calls when using exhaustive mode (default: 3)')
    parser.add_argument('--use-max-id', '-u', action='store_true',
                      help='Use max_id approach for pagination (fetches older tweets)')
    parser.add_argument('--use-client', '-c', action='store_true',
                      help='Use the Apify client library instead of direct API calls')
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    # Initialize TweetGetter with specified parameters
    csv_file = args.output if args.output else "src/data/elonmusk_reformatted.csv"
    
    print("=" * 80)
    print("STRICT LIMIT: Will fetch EXACTLY {} tweets from Elon Musk (no more, no less if possible)".format(args.max_tweets))
    print("=" * 80)
    
    if args.since_id:
        print("Starting from tweet ID: {}".format(args.since_id))
    if args.auto_since_id:
        print("Auto-since-id mode enabled - will use latest tweet ID from database")
    if args.latest:
        print("Latest mode enabled - will use latest tweet ID from database for this run")
    if args.exhaustive:
        print("Exhaustive mode enabled - will make up to {} API calls to fetch tweets".format(args.max_attempts))
        print("Still strictly limiting to {} tweets total".format(args.max_tweets))
    if args.use_max_id:
        print("Using max_id approach to fetch older tweets")
    if args.use_client:
        print("Using Apify client library for better results")
    if args.debug:
        print("Debug mode enabled - tweets will not be saved")
    if args.add_to_db:
        print("Add-to-DB mode enabled - tweets will be added to the database in Georgia format")
    
    # Create TweetGetter instance with explicit max_tweets enforcement
    getter = TweetGetter(
        twitter_handle="elonmusk",
        max_tweets=args.max_tweets,  # Ensure this is passed correctly
        since_id=args.since_id,
        csv_file=csv_file,
        debug=args.debug,
        format_style=args.format,
        auto_since_id=args.auto_since_id
    )
    
    # If using client approach, handle it specially
    if args.use_client:
        if args.add_to_db:
            # Add to database using client approach
            num_added = getter.add_to_database_client(use_latest_id=args.latest)
            if num_added > 0:
                print("Successfully added {} new tweets to the database using Apify client.".format(num_added))
            else:
                print("No new tweets were added to the database.")
                
            # Load the database to get the total number of tweets
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file, dtype={"id": str})
                print("Total tweets in database: {}".format(len(df)))
        else:
            # Regular fetch and save using client approach
            df = getter.fetch_and_save_tweets_client(use_latest_id=args.latest)
            
            # Print summary
            if not df.empty:
                print("\nSummary:")
                print("Total tweets fetched: {}".format(len(df)))
                
                # Extra check: only show at most max_tweets
                if len(df) > args.max_tweets:
                    print("NOTE: Got {} tweets total, but limiting to displaying only {} as requested.".format(
                        len(df), args.max_tweets))
                    df = df.head(args.max_tweets)
                
                if len(df) < args.max_tweets:
                    print("Note: Got {} tweets, which is less than the {} requested.".format(len(df), args.max_tweets))
                    print("      This is likely due to Twitter API limitations or there aren't that many tweets available.")
                
                print("Date range: {} to {}".format(df['created_at'].min(), df['created_at'].max()))
                
                if not args.debug:
                    # Print sample of latest tweets (at most 3)
                    print("\nLatest {} tweets:".format(min(3, len(df))))
                    latest = df.iloc[-min(3, len(df)):] if len(df) > 0 else df
                    for i, row in latest.iterrows():
                        text = row['text']
                        if len(text) > 100:
                            text = text[:97] + "..."
                        print("[{}] {}".format(row['created_at'], text))
        return
    
    # If using max_id approach, handle it specially
    if args.use_max_id:
        df = getter.get_tweets_by_max_id(max_attempts=args.max_attempts)
        
        if not args.debug and not df.empty:
            # Save tweets
            num_saved = getter.save_tweets(df)
            print("Saved {} tweets to {}".format(num_saved, csv_file))
            
            # Extra check: only show at most max_tweets
            if len(df) > args.max_tweets:
                print("NOTE: Got {} tweets total, but limiting to displaying only {} as requested.".format(
                    len(df), args.max_tweets))
                df = df.head(args.max_tweets)
            
            # Print summary
            print("\nSummary:")
            print("Total tweets fetched: {}".format(len(df)))
            
            if len(df) < args.max_tweets:
                print("Note: Got {} tweets, which is less than the {} requested.".format(len(df), args.max_tweets))
                print("      This is likely due to Twitter API limitations or there aren't that many tweets available.")
            
            print("Date range: {} to {}".format(df['created_at'].min(), df['created_at'].max()))
            
            # Print sample of latest tweets (at most 3)
            print("\nLatest {} tweets:".format(min(3, len(df))))
            latest = df.iloc[-min(3, len(df)):] if len(df) > 0 else df
            for i, row in latest.iterrows():
                text = row['text']
                if len(text) > 100:
                    text = text[:97] + "..."
                print("[{}] {}".format(row['created_at'], text))
        
        return
    
    # Fetch and either save tweets or add to database
    if args.add_to_db:
        # This will always save in Georgia format (YYYY:MM:DD:HH:MM:SS)
        num_added = getter.add_to_database(
            use_latest_id=args.latest, 
            exhaustive=args.exhaustive, 
            max_attempts=args.max_attempts if args.exhaustive else 5
        )
        if num_added > 0:
            print("Successfully added {} new tweets to the database.".format(num_added))
        else:
            print("No new tweets were added to the database.")
            
        # Load the database to get the total number of tweets
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file, dtype={"id": str})
            print("Total tweets in database: {}".format(len(df)))
    else:
        # Regular fetch and save
        df = getter.fetch_and_save_tweets(
            use_latest_id=args.latest, 
            exhaustive=args.exhaustive,
            max_attempts=args.max_attempts if args.exhaustive else 5
        )
        
        # Print summary
        if not df.empty:
            # Extra check: only show at most max_tweets
            if len(df) > args.max_tweets:
                print("NOTE: Got {} tweets total, but limiting to displaying only {} as requested.".format(
                    len(df), args.max_tweets))
                df = df.head(args.max_tweets)
                
            print("\nSummary:")
            print("Total tweets fetched: {}".format(len(df)))
            
            if len(df) < args.max_tweets and not args.exhaustive:
                print("Note: Got {} tweets, which is less than the {} requested.".format(len(df), args.max_tweets))
                print("      Try using --exhaustive mode to get more tweets.")
            
            print("Date range: {} to {}".format(df['created_at'].min(), df['created_at'].max()))
            
            if not args.debug:
                # Print sample of latest tweets (at most 3)
                print("\nLatest {} tweets:".format(min(3, len(df))))
                latest = df.iloc[-min(3, len(df)):] if len(df) > 0 else df
                for i, row in latest.iterrows():
                    # Remove triple quotes for display
                    text = row['text'].replace('"""', '')
                    if len(text) > 100:
                        text = text[:97] + "..."
                    print("[{}] {}".format(row['created_at'], text))

if __name__ == "__main__":
    main() 