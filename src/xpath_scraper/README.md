# Tweet Count Getter And Tweet CSV Getter

A tool that gets how many tweets has elon tweeted on the latest market on polymarket AND get's the tweets in a csv and formats them

## Count Getter Overview

1. Gets current date
2. gets url from constants.
3. Reads the count from polymarkets own website using a generalized xpath

## CSV Getter Overview

1. Gets CSV From xtracker
2. Downloads to local data dir
3. Runs fixDates.py on the csv
4. merge into existing reformatted csv

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