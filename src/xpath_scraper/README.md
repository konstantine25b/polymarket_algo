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

1. Gets CSV From xtracker
2. Downloads to local data dir
3. Runs fixDates.py on the csv
4. merge into existing reformatted csv

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

Alternatively, you can run the scripts directly:

```bash
python src/xpath_scraper/NumberGetter.py
python src/xpath_scraper/TweetCSVGetter.py
```
