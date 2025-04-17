# Polymarket Tweet Predictor

A powerful tool for predicting Elon Musk's tweet counts within specific time frames for Polymarket events.

## Overview

This module calculates probabilities for tweet count brackets used in Polymarket markets. It combines:

- Historical tweet pattern analysis
- Current tweet count data
- Monte Carlo simulation
- Dynamic probability adjustment based on real-time data
- **Eastern Time (ET) timezone handling** for accurate Polymarket resolution

## Features

- **Auto-counting**: Automatically counts tweets within the prediction window
- **Manual counting override**: Support for specifying exact tweet counts
- **Monte Carlo simulation**: Accounts for variability in tweeting patterns
- **Eastern Time (ET) compatibility**: All timestamps are handled in ET timezone to match Polymarket resolution criteria
- **Verification tools**: Verify actual tweet counts in the specified time window
- **Detailed analytics**: Daily tweet counts, rates, and pattern analysis
- **Polymarket integration**: Uses actual Polymarket count frames for predictions

## Command-Line Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run with default settings (April 11-18, 2025 timeframe, 12:00 PM ET to 12:00 PM ET)
python -m src.polymarket_predictor

# Specify exact tweet count
python -m src.polymarket_predictor --exact-count 147

# Run with custom date range (in Eastern Time)
python -m src.polymarket_predictor --start "2025-04-11 12:00:00" --end "2025-04-18 12:00:00"

# Verify the tweet count in a date range without running predictions
python -m src.polymarket_predictor --verify-count

# Disable trend adjustment
python -m src.polymarket_predictor --no-trend

# Increase Monte Carlo simulation accuracy
python -m src.polymarket_predictor --sims 5000

# Use a custom tweet data file
python -m src.polymarket_predictor --file /path/to/tweets.csv
```

## Command-Line Options

- `--start`: Start date/time for prediction period (YYYY-MM-DD HH:MM:SS) in Eastern Time (ET)
- `--end`: End date/time for prediction period (YYYY-MM-DD HH:MM:SS) in Eastern Time (ET)
- `--file`: Path to tweet data CSV file
- `--no-trend`: Disable trend adjustment based on recent activity
- `--sims`: Number of Monte Carlo simulations to run (default: 1000)
- `--current-count`: Current tweet count (overrides auto-counting)
- `--force-count`: Force using the provided count instead of auto-counting
- `--exact-count`: Specify exact number of tweets (simplifies overriding auto-count)
- `--verify-count`: Only verify tweet count within date range without prediction

## Timezone Handling

All dates and times in this tool are processed in Eastern Time (ET) to match Polymarket's resolution criteria. This is critical because:

1. Polymarket explicitly resolves markets based on Eastern Time (ET)
2. Tweet timestamps need to be properly aligned with the market resolution window
3. Current progress in the prediction window must be accurately calculated in ET

When specifying dates, always use Eastern Time (ET). The default time window is April 11, 2025, 12:00 PM ET to April 18, 2025, 12:00 PM ET.

## Programmatic Usage

You can use this module programmatically in your Python code:

```python
from src.polymarket_predictor import predict_tweet_frame_probabilities, verify_tweet_count

# Get predictions with automatic tweet counting
# Note: Dates are interpreted as Eastern Time (ET)
probabilities = predict_tweet_frame_probabilities(
    start_date_str="2025-04-11 12:00:00",  # 12:00 PM ET
    end_date_str="2025-04-18 12:00:00"     # 12:00 PM ET
)

# Print the predicted probabilities
for frame, probability in probabilities.items():
    print(f"{frame}: {probability:.1f}%")

# Verify the actual tweet count in a date range (in ET)
count = verify_tweet_count(
    start_date_str="2025-04-11 12:00:00",  # 12:00 PM ET
    end_date_str="2025-04-18 12:00:00"     # 12:00 PM ET
)
print(f"Verified tweet count: {count}")

# Override with exact count
probabilities = predict_tweet_frame_probabilities(
    start_date_str="2025-04-11 12:00:00",  # 12:00 PM ET
    end_date_str="2025-04-18 12:00:00",    # 12:00 PM ET
    current_tweet_count=147,
    override_auto_count=True
)
```

## Output

The tool provides detailed output including:

1. **Current tweet count**: Either auto-counted or manually specified
2. **Daily tweet rate**: Current and historical averages
3. **Detailed prediction analysis**:
   - Raw prediction
   - Trend-adjusted prediction
   - Volatility-boosted prediction
   - Standard deviation
   - 95% confidence interval
4. **Probabilities for each count frame**: Percentage chance of each outcome
5. **Daily breakdown**: Tweet counts by day within the window
6. **Timezone information**: Clearly indicates that all dates/times are in ET

## Verification Tool

The verification feature counts tweets within a specified date range (in Eastern Time) and provides daily breakdowns. This is useful for:

- Validating the auto-counting algorithm
- Getting exact tweet counts for a time period
- Debugging and auditing prediction accuracy

## Data Format

The tool expects tweet data in a CSV format with the following columns:

- `created_at`: Timestamp in the format 'YYYY:MM:DD:HH:MM:SS' (assumed to be in ET timezone)
- `text`: Tweet content

## Requirements

This module requires:

- Python 3.6+
- pandas
- numpy
- pytz
- datetime
