# Tweet Collector Module

A robust system for continuously collecting and storing Elon Musk's tweets using the Apify API.

## Overview

The Tweet Collector is a Python-based system that:
- Fetches tweets from Elon Musk's Twitter account every 2 minutes
- Processes and formats the tweets
- Appends new tweets to a CSV file without duplicates
- Provides detailed logging of all activities

## Components

### 1. Tweet Fetcher (`tweet_fetcher.py`)
- Connects to Apify API
- Fetches latest tweets
- Processes and formats tweet data
- Prevents duplicate tweets

### 2. Tweet Appender (`tweet_appender.py`)
- Manages the CSV file
- Appends new tweets in the correct format
- Ensures data integrity
- Handles file creation if needed

### 3. Tweet Scheduler (`tweet_scheduler.py`)
- Coordinates the fetching and appending process
- Runs on a 2-minute interval
- Provides comprehensive logging
- Handles errors gracefully

## Installation

1. Ensure you have Python 3.7+ installed
2. Install required dependencies:
```bash
pip install requests pandas
```

3. Configure your Apify credentials in `tweet_fetcher.py`:
```python
API_TOKEN = "your_apify_api_token"
TASK_ID = "your_apify_task_id"
```

## Usage

Run the tweet collector:
```bash
python -m src.tweet_collector.tweet_scheduler
```

## Output

### 1. CSV File (`src/data/elonmusk_reformatted.csv`)
Format:
```
id,text,created_at
123456789,This is a tweet text,2024:04:18:15:30:00
```

### 2. Log File (`tweet_collector.log`)
- Records all system activities
- Tracks errors and retries
- Shows tweet collection statistics

## Features

- **Continuous Collection**: Runs every 2 minutes
- **Duplicate Prevention**: Uses tweet IDs to prevent duplicates
- **Error Handling**: Graceful recovery from errors
- **Data Integrity**: Proper CSV formatting and file handling
- **Comprehensive Logging**: Detailed activity tracking

## File Structure

```
tweet_collector/
├── __init__.py         # Package initialization
├── tweet_fetcher.py    # Tweet fetching logic
├── tweet_appender.py   # CSV file management
└── tweet_scheduler.py  # Main coordination
```

## Error Handling

The system includes robust error handling:
- API connection failures
- File access issues
- Data formatting errors
- Network problems

All errors are logged and the system attempts to recover automatically.

## Monitoring

You can monitor the system in several ways:

1. **Console Output**: Real-time status updates
2. **Log File**: Detailed activity log
3. **CSV File**: Verify new tweets are being added

## Requirements

- Python 3.7+
- requests
- pandas
- Valid Apify API credentials

## Troubleshooting

Common issues and solutions:

1. **API Connection Issues**
   - Verify your Apify credentials
   - Check network connection
   - Review API rate limits

2. **File Access Problems**
   - Ensure proper file permissions
   - Verify file paths
   - Check disk space

3. **Data Formatting Errors**
   - Verify CSV file structure
   - Check tweet formatting
   - Review error logs

## Support

For issues or questions:
1. Check the error logs
2. Review the console output
3. Verify your configuration

## License

This module is part of the Polymarket Algorithmic Analysis project. 