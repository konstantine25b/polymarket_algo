# Tweet Count Getter And Tweet CSV Getter

A tool that gets how many tweets has elon tweeted on the latest market on polymarket AND get's the tweets in a csv and formats them

## Count Getter Overview

1. Gets current date
2. Iterates over 7 days to see which markets are real.
3. Reads the count from polymarkets own website using a generalized xpath

## CSV Getter Overview

1. Gets CSV From xtracker
2. Downloads to local data dir
3. Runs fixDates.py on the csv

## Dependencies
playwright is needed
```bash
pip install playwright
```
## Command-Line Usage
How to run
```bash
python src/xpath_scraper/NumberGetter.py
```
```bash
python src/xpath_scraper/TweetCSVGetter.py
```