# Elon Musk Tweet Fetcher

A robust tool for automatically fetching and archiving tweets from Elon Musk's Twitter account.

## Overview

This module continuously collects tweets from Elon Musk's Twitter account and stores them in a standardized format. It features:

- Automatic Twitter API integration through Apify
- Scheduled fetching at configurable intervals
- Timestamp standardization to Georgia timezone (UTC+4)
- Duplicate tweet detection and filtering
- Chronological sorting of tweets
- CSV-based storage with proper text encoding

## Features

- **Automatic scheduling**: Runs at configurable intervals (default: every 5 minutes) to fetch new tweets
- **Timezone handling**: Standardizes all timestamps to Georgia time (UTC+4)
- **Robust error handling**: Gracefully handles API failures and network issues
- **CSV cleaning**: Automatically fixes and standardizes existing CSV data
- **Duplicate prevention**: Ensures each tweet is only stored once
- **Date normalization**: Handles various timestamp formats from Twitter's API
- **Sorting**: Keeps tweets in chronological order (oldest first, newest last)
- **Debug logging**: Detailed output for monitoring and troubleshooting
- **Command-line options**: Configure refresh interval, number of tweets, and one-time runs

## Command-Line Usage

```bash
# Run with default settings (5-minute refresh interval, fetch 5 tweets per request)
python src/apify/tweetfetcher.py

# Run with a custom refresh interval (e.g. every 15 minutes)
python src/apify/tweetfetcher.py --interval 15

# Run with a custom number of tweets to fetch per request
python src/apify/tweetfetcher.py --max-tweets 10

# Run once and exit (don't keep running on schedule)
python src/apify/tweetfetcher.py --one-time

# Combine options (fetch 20 tweets every 30 minutes)
python src/apify/tweetfetcher.py --interval 30 --max-tweets 20

# Run with Python 3.13 specifically
C:/Users/99557/AppData/Local/Programs/Python/Python313/python.exe src/apify/tweetfetcher.py --interval 10
```

## Command-Line Options

- `--interval`, `-i`: Refresh interval in minutes (default: 5)
- `--max-tweets`, `-m`: Maximum number of tweets to fetch per request (default: 5)
- `--one-time`, `-o`: Run once and exit (don't keep running on schedule)

## Configuration Options

At the top of the script, you can customize these variables:

- `APIFY_TOKEN`: Your Apify API token
- `ACTOR_TASK_ID`: The Apify actor task ID for Twitter scraping
- `CSV_FILE`: Path to the CSV file where tweets will be stored

## Timezone Handling

All timestamps are converted to Georgia timezone (UTC+4) to ensure consistency. The script:

1. Parses various timestamp formats from Twitter's API
2. Normalizes and converts them to Georgia time
3. Stores timestamps in a standardized format: "YYYY:MM:DD:HH:MM:SS"

## Programmatic Usage

You can also import and use the functions in your Python code:

```python
from src.apify.tweetfetcher import fetch_new_tweets, clean_existing_csv

# Clean and normalize an existing CSV file
clean_existing_csv()

# Fetch new tweets one time
fetch_new_tweets()

# To run continuously with scheduling, use the main loop:
import schedule
import time

# Set up the schedule
schedule.every(5).minutes.do(fetch_new_tweets)

# Run the scheduling loop
while True:
    schedule.run_pending()
    time.sleep(1)
```

## Output

The script produces:

1. **Console output** with detailed information about:
   - Fetch operations and timing
   - Number of tweets fetched and saved
   - Tweet structure samples for debugging
   - Timestamp conversion details
   - Error messages and warnings

2. **CSV file** with the following columns:
   - `id`: Twitter's unique tweet ID
   - `text`: The full text content of the tweet
   - `created_at`: Standardized timestamp in "YYYY:MM:DD:HH:MM:SS" format

## CSV File Structure

The tweets are stored in a CSV file with this format:

```
id,text,created_at
1913827557314617480,"""RT @ElonClipsX: Kevin O'Leary: The government drips with fat. Let Elon do his thing – there's nobody like him.  "I'm okay with [Elon going…""",2025:04:20:01:30:21
1913829481040560546,"""RT @Tesla: ❤️""",2025:04:20:01:38:00
```

Note that tweet text is wrapped in triple quotes to handle embedded quote characters.

## Key Functions

- `fix_timestamp()`: Normalizes various Twitter timestamp formats
- `clean_existing_csv()`: Cleans and sorts an existing CSV file
- `fetch_new_tweets()`: Fetches new tweets from Elon's account

## Requirements

This module requires:

- Python 3.6+
- pandas
- pytz
- requests
- schedule
- re (standard library)
- csv (standard library)
- os (standard library)
- time (standard library)
- datetime (standard library) 