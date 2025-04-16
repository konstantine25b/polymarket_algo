# Polymarket Algorithmic Analysis

A collection of algorithms and tools for analyzing Elon Musk's tweeting patterns and related markets.

## Setup

```bash
# Set up virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Available Modules

### 1. Data Formatting

Prepares tweet data for analysis:

```bash
# Format raw tweet data
python3 src/formating_tweet_data/fixDates.py

# Aggregate tweets by day
python3 src/formating_tweet_data/formatByDay.py
```

### 2. Prediction Algorithms

Various algorithms for predicting Elon Musk's tweeting patterns:

See `src/algos/README.md` for details on available prediction algorithms.

### 3. Polymarket Analysis

Tools for analyzing Polymarket data related to Elon Musk's tweeting:

```bash
# Get current timeframes and odds from Polymarket
python3 src/polymarket/get_timeframes.py

# CLI interface with more options
python3 src/polymarket/cli.py --verbose
```

#### CLI Options

```
--url URL       Polymarket event URL
--tid TID       Thread ID from the Polymarket URL
--output PATH   Output directory path
--format FORMAT Output format: csv, json, or both
--verbose       Enable verbose output
```

Example with custom URL and thread ID:

```bash
python3 src/polymarket/cli.py --url "https://polymarket.com/event/your-event-slug" --tid "your-thread-id" --verbose
```

## Output

Results from the Polymarket analysis are saved in `src/polymarket/data/` with CSV and JSON formats available.
