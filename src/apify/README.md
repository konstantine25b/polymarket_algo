# Elon Musk Tweet Fetcher

A simple tool for fetching tweets from Elon Musk's Twitter account.

## Overview

This module provides a simple and efficient way to fetch tweets from Elon Musk's Twitter account and save them in a standardized format. It uses the Apify API to scrape Twitter data.

## Components

### TweetGetter Class

The `TweetGetter` class provides a simple interface to fetch tweets:

- **File location:** `src/apify/models/tweet_getter.py`
- **Purpose:** Fetch tweets from a Twitter user (default: Elon Musk)
- **Features:**
  - Fetch tweets from any Twitter handle (default: elonmusk)
  - Fetch tweets starting from a specific tweet ID
  - Store tweets in a CSV file
  - Handle timestamp conversions and formatting
  - Remove duplicates
  - Debug mode for development
  - Add to database functionality

### Utility Functions

The `timestamp_handler` module contains utility functions for handling timestamps:

- **File location:** `src/apify/utils/timestamp_handler.py`
- **Purpose:** Convert and format timestamps from various formats
- **Features:**
  - Convert various timestamp formats to unix timestamps
  - Format timestamps in human-readable format with AM/PM in Eastern Time
  - Get current timestamp
  - Check if a timestamp is within a range

## Usage

### Command Line

You can use the included script to fetch tweets from Elon Musk. The recommended way to run the script is using Python's module notation:

```bash
# Fetch 100 tweets (default)
python -m src.apify.get_elon_tweets

# Fetch 20 tweets
python -m src.apify.get_elon_tweets --max-tweets 20

# Fetch tweets starting from a specific tweet ID
python -m src.apify.get_elon_tweets --since-id 1915647254519795869

# Enable debug mode (prints detailed info and doesn't save to CSV)
python -m src.apify.get_elon_tweets --debug

# Specify a custom output file
python -m src.apify.get_elon_tweets --output path/to/output.csv

# Add tweets to the database (in Georgia timestamp format)
python -m src.apify.get_elon_tweets --add-to-db

# Use EDT timestamp format (YYYY-MM-DD HH:MM:SS AM/PM EDT)
python -m src.apify.get_elon_tweets --format edt

# Automatically use the latest tweet ID from the database for this run
python -m src.apify.get_elon_tweets --latest

# Always automatically use the latest tweet ID (persistent setting)
python -m src.apify.get_elon_tweets --auto-since-id

# Combine multiple options
python -m src.apify.get_elon_tweets --max-tweets 50 --add-to-db --latest

# best here
python -m src.apify.get_elon_tweets --max-tweets 40 --use-client --debug --add-to-db

```

### Command Line Options

- `--max-tweets`, `-m`: Maximum number of tweets to fetch (default: 100)
- `--since-id`, `-s`: Tweet ID to start fetching from (e.g., "1915647254519795869")
- `--output`, `-o`: Output CSV file path (default: src/data/elonmusk_reformatted.csv)
- `--debug`, `-d`: Print debug information and do not store tweets
- `--add-to-db`, `-a`: Add tweets to the database in Georgia timestamp format
- `--format`, `-f`: Timestamp format to use (choices: 'georgia', 'edt', default: 'georgia')
- `--latest`, `-l`: Automatically use the latest tweet ID from the database for this run only
- `--auto-since-id`: Always automatically use the latest tweet ID from the database (works across runs)
- `--exhaustive`, `-e`: Use exhaustive fetching to ensure all available tweets are captured
- `--max-attempts`: Maximum number of API calls when using exhaustive mode (default: 3)
- `--use-max-id`, `-u`: Use max_id approach for pagination (fetches older tweets)
- `--use-client`, `-c`: Use the Apify client library instead of direct API calls
- `--incremental`, `-i`: Use incremental batch size to ensure no gaps between database and new tweets
- `--initial-batch`: Initial batch size for incremental fetching (default: 40)
- `--max-batch`: Maximum batch size for incremental fetching (default: 200)
- `--batch-increment`: How much to increase batch size in each incremental attempt (default: 20)
- `--incremental-attempts`: Maximum number of attempts for incremental fetching (default: 5)

### Advanced Fetching Strategies

The tool implements several sophisticated fetching strategies to ensure reliable and complete tweet collection:

#### 1. Client-based Fetching

Uses the official Apify client library instead of direct API calls for better reliability and performance:

```bash
python -m src.apify.get_elon_tweets --use-client --max-tweets 40
```

This method often provides more reliable results and better handles API pagination.

#### 2. Incremental Fetching

A sophisticated strategy designed to avoid gaps between your existing database and newly fetched tweets:

```bash
python -m src.apify.get_elon_tweets --use-client --add-to-db --incremental
```

Here's how it works:

- Starts with a small batch size (default: 40 tweets)
- Checks if this batch overlaps with your existing database (finding the latest tweet from your DB)
- If not found, gradually increases the batch size and tries again
- Continues until either:
  - The latest database tweet is found (ensuring continuity)
  - Maximum batch size is reached (default: 200 tweets)
  - Maximum attempts are exhausted (default: 5 attempts)

This approach is especially useful for:

- Ensuring no gaps in your tweet timeline
- Minimizing API calls when there are few new tweets
- Handling situations where many tweets were posted between runs

You can customize the parameters:

```bash
python -m src.apify.get_elon_tweets --use-client --add-to-db --incremental \
  --initial-batch 60 --max-batch 300 --batch-increment 30 --incremental-attempts 7
```

#### 3. Exhaustive Fetching

Makes multiple API calls to ensure all available tweets within your constraints are captured:

```bash
python -m src.apify.get_elon_tweets --exhaustive --max-attempts 5
```

This is useful when you need to be certain you're not missing tweets due to API limitations.

#### 4. Max ID Approach

Uses Twitter's max_id pagination approach to fetch older tweets:

```bash
python -m src.apify.get_elon_tweets --use-max-id
```

This is helpful when you specifically want to collect historical tweets rather than the most recent ones.

#### Recommended Strategy for Most Use Cases

For general-purpose tweet collection with maximum reliability, we recommend:

```bash
python -m src.apify.get_elon_tweets --max-tweets 40 --use-client --add-to-db --incremental
```

This combination:

- Uses the reliable client library
- Automatically adds tweets to your database
- Uses incremental fetching to avoid gaps
- Limits to 40 tweets per request to control costs

### Automatically Fetching New Tweets

The tool offers two convenient ways to automatically fetch only new tweets:

1. **For a single run** - Use the `--latest` flag to automatically detect and use the latest tweet ID from your existing database just for this run.

   ```bash
   python -m src.apify.get_elon_tweets --latest
   ```

2. **For persistent configuration** - Use the `--auto-since-id` flag to always use the latest tweet ID from the database for all runs (unless overridden with `--since-id`).

   ```bash
   python -m src.apify.get_elon_tweets --auto-since-id
   ```

> **Note:** When using the automatic latest tweet ID functionality, make sure to set an appropriate `--max-tweets` value. If the value is too low (e.g., less than 100), you might miss some tweets because the tool can only fetch a limited number of tweets in a single run. The default is 100, which should be sufficient for most cases, but you can increase it if the user tweets frequently.

This makes it easy to keep your tweet database up-to-date by only fetching new tweets that have appeared since your last update.

### Timestamp Formats

The script supports two timestamp formats, both using Eastern Time (ET):

- **Georgia Format (default)**: `YYYY:MM:DD:HH:MM:SS` in Eastern Time (e.g., "2025:04:25:02:49:05")
- **EDT Format**: `YYYY-MM-DD HH:MM:SS AM/PM EDT` (e.g., "2025-04-25 02:49:05 AM EDT")

The name "Georgia" format is kept for backward compatibility, but both formats now use the Eastern Time (ET) timezone.

### Programmatic Usage

You can also use the `TweetGetter` class in your code:

```python
from src.apify.models.tweet_getter import TweetGetter

# Create a TweetGetter instance
getter = TweetGetter(
    twitter_handle="elonmusk",     # Default: elonmusk
    max_tweets=100,                # Default: 100
    since_id="1915647254519795869", # Optional: start from a specific tweet ID
    csv_file="path/to/output.csv", # Default: src/data/elonmusk_reformatted.csv
    debug=True,                    # Optional: enable debug mode
    format_style="georgia"         # Optional: timestamp format ('georgia' or 'edt')
)

# Fetch and save tweets
df = getter.fetch_and_save_tweets()

# Or add tweets to the database
num_added = getter.add_to_database()

# Use incremental fetching
num_added = getter.add_to_database_client_incremental(
    initial_batch_size=40,
    max_batch_size=200,
    increment=20,
    max_attempts=5
)
```

## Output Format

The tweets are saved in a CSV file with the following columns:

- `id`: Twitter's unique tweet ID
- `text`: The full text content of the tweet (wrapped in triple quotes)
- `created_at`: Timestamp in the specified format

Georgia Format Example:

```
"id","text","created_at"
"1915659312464339287",""""RT @naval: Peace is not when nothing bothersome happens, peace is when nothing bothers you."""","2025:04:25:02:49:05"
```

EDT Format Example:

```
"id","text","created_at"
"1915659312464339287",""""RT @naval: Peace is not when nothing bothersome happens, peace is when nothing bothers you."""","2025-04-25 02:49:05 AM EDT"
```
