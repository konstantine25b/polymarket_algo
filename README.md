# Tweet Collector Module

A Python-based system for collecting and storing Elon Musk's tweets using the Apify API.

## Overview

This module consists of three main components that work together to:
1. Fetch tweets from Elon Musk's Twitter account
2. Process and format the tweets
3. Store them in a CSV file
4. Run on a scheduled basis (every 2 minutes)

## Core Files

### 1. `init__.py`
This file makes the tweet_collector directory a Python package and defines what can be imported from it. It:
- Imports and exposes the main classes from each component
- Defines what's available when you import the package
- Contains:
  ```python
  from .tweet_fetcher import TestTweetScraper
  from .tweet_appender import TweetAppender
  from .tweet_scheduler import TweetScheduler

  __all__ = ['TestTweetScraper', 'TweetAppender', 'TweetScheduler']
  ```

### 2. `run_tweet_collector.py`
This is the main entry point script that:
- Sets up the correct Python path
- Imports and runs the TweetScheduler
- Makes it easy to run the entire system with one command
- Contains:
  ```python
  import os
  import sys
  project_root = os.path.dirname(os.path.abspath(__file__))
  sys.path.append(project_root)
  from src.tweet_collector.tweet_scheduler import TweetScheduler
  ```

## Components

### 1. Tweet Fetcher (`tweet_fetcher.py`)

The `TestTweetScraper` class handles fetching tweets from the Apify API.

#### Key Functions:
- `__init__()`: Initializes the scraper with API credentials
- `fetch_tweets()`: 
  - Starts a new Apify task run
  - Waits for completion
  - Retrieves the tweets
- `process_tweets(tweets)`: 
  - Formats tweet data
  - Removes duplicates
  - Converts timestamps
- `save_tweets(new_tweets)`: Passes tweets to the appender

### 2. Tweet Appender (`tweet_appender.py`)

The `TweetAppender` class manages the CSV file storage.

#### Key Functions:
- `__init__()`: 
  - Sets up the CSV file path
  - Creates file if it doesn't exist
  - Ensures proper formatting
- `fix_existing_quotes()`: Ensures all text entries have proper quotes
- `append_tweets(tweets)`: 
  - Sorts tweets by time
  - Appends new tweets to CSV
  - Handles text formatting

### 3. Tweet Scheduler (`tweet_scheduler.py`)

The `TweetScheduler` class coordinates the entire process.

#### Key Functions:
- `__init__()`: Initializes scraper and appender
- `run()`: 
  - Runs the collection process every 2 minutes
  - Handles errors and retries
  - Provides logging

## How to Run

### Option 1: Using the Run Script (Recommended)

1. Navigate to the project root directory:
   ```
   C:\Users\99557\OneDrive\Desktop\polymarket_algo
   ```

2. Run the script:
   ```
   python run_tweet_collector.py
   ```

### Option 2: Running Individual Components

1. To run just the fetcher:
   ```python
   from tweet_collector.tweet_fetcher import TestTweetScraper
   scraper = TestTweetScraper()
   tweets = scraper.fetch_tweets()
   ```

2. To run just the appender:
   ```python
   from tweet_collector.tweet_appender import TweetAppender
   appender = TweetAppender()
   appender.append_tweets(tweets)
   ```

3. To run the scheduler:
   ```python
   from tweet_collector.tweet_scheduler import TweetScheduler
   scheduler = TweetScheduler()
   scheduler.run()
   ```

## Output

### 1. CSV File
- Location: `src/data/elonmusk_reformatted.csv`
- Format: `id,text,created_at`
- Updates: New tweets are appended every 2 minutes

### 2. Log File
- Location: `src/tweet_collector/tweet_collector.log`
- Contains: Timestamps, status updates, and error messages

## Requirements

- Python 3.7+
- Required packages:
  - requests
  - pandas
  - Valid Apify API credentials

## Error Handling

The system includes comprehensive error handling:
- API connection failures
- File access issues
- Data formatting errors
- Network problems

All errors are logged and the system attempts to recover automatically.

## Monitoring

You can monitor the system through:
1. Console output (real-time updates)
2. Log file (`tweet_collector.log`)
3. CSV file (verify new tweets are being added)

## Stopping the Service

To stop the tweet collector:
1. If running in IDE: Click the "Stop" button
2. If running in terminal: Press Ctrl+C 