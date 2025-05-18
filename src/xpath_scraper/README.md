# Tweet Count Getter And Tweet CSV Getter

A tool that gets how many tweets Elon Musk has tweeted according to the latest market on Polymarket AND gets the tweets in a CSV format.

## Count Getter Overview

The `TweetCountGetter` class scrapes the current tweet count from Polymarket's Elon Musk tweets market:

1. Uses Playwright to visit the Polymarket page defined in constants
2. Extracts the tweet count using XPath selectors targeting the UI element
3. Returns the current integer tweet count, or -1 if retrieval fails
4. Includes comprehensive logging for monitoring and debugging

### Features:

- Headless browser automation (no visible browser window)
- Error handling with informative logging
- Simple API through the `getTweetCount()` method

## CSV Getter Overview

The `TweetCSVGetter` class manages downloading and processing Elon Musk's tweet data:

1. Downloads the CSV file from XTracker using Playwright
2. Saves the file to the local temp directory (`src/xpath_scraper/temp/`)
3. Reformats tweet dates using `secondFixDates.py`
4. Merges new tweets with existing data in `src/data/elonmusk_reformatted.csv`

### Features:

- Preserves CSV headers during processing
- Prevents duplicate tweets when merging
- Sorts tweets by timestamp
- Comprehensive logging for debugging and monitoring
- Error handling for subprocess calls

## Dependencies

The scraper requires the Playwright library:

```bash
pip install playwright
playwright install chromium
```

## Command-Line Usage

Run the scripts directly from the command line using Python module syntax:

```bash
python -m src.xpath_scraper.NumberGetter
```

Example output:

```
2023-06-01 14:30:22 - TweetCountGetter - INFO - Starting tweet count retrieval process
...
Tweet count: 30
```

To get the tweets in CSV format:

```bash
python -m src.xpath_scraper.TweetCSVGetter
```

Example output:

```
2023-06-01 14:35:10 - TweetCSVGetter - INFO - Starting CSV download process
2023-06-01 14:35:12 - TweetCSVGetter - INFO - Downloaded and saved to: src/xpath_scraper/temp/elonmusk.csv
...
2023-06-01 14:35:45 - TweetCSVCombiner - INFO - CSV merge complete
```

Alternatively, you can run the scripts directly:

```bash
python src/xpath_scraper/NumberGetter.py
python src/xpath_scraper/TweetCSVGetter.py
```
