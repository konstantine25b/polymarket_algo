# Elon Musk Tweet Predictor

## Overview

This is a data-driven tool that analyzes Elon Musk's Twitter/X posting patterns and predicts future tweet volumes based on historical data. The tool uses time-series analysis to identify patterns in Elon's tweeting habits across different days of the week and hours of the day, then applies these patterns to predict future activity.

## Features

- **Historical Pattern Analysis**: Analyzes tweet frequency by day of week, hour of day, and recent trends
- **Multiple Prediction Modes**:
  - Predict for specific target dates
  - Predict for N days in the future
  - Predict for the next N hours
  - Predict for specific hours of the day only
- **Trend Adjustment**: Adjusts predictions based on recent tweet frequency changes
- **Precision Evaluation**: Evaluates prediction accuracy against historical data
- **Data Visualization**: Creates plots of tweeting patterns and prediction accuracy

## Data

The predictor uses a CSV file containing Elon Musk's historical tweets with the following format:

```
id,created_at,text
1234567890,2023:01:15:14:30:00,This is a tweet
```

Key fields:

- `id`: Unique tweet identifier
- `created_at`: Timestamp in the format YYYY:MM:DD:HH:MM:SS
- `text`: Content of the tweet

The data file should be named `elonmusk_reformatted.csv` and placed in either the project's root `data/` directory or in `src/data/`.

## Components

### 1. Data Loader (`data_loader.py`)

Loads and preprocesses the tweet data, extracting key time-based features:

- Parses timestamps
- Extracts date, hour, and weekday components
- Provides information about the loaded dataset

### 2. Pattern Analyzer (`pattern_analyzer.py`)

Analyzes historical tweet patterns to extract:

- Daily tweet counts
- Average tweets by day of week
- Average tweets by hour of day
- Combined weekday-hour averages
- Recent tweet volume trends

### 3. Predictor Module (`predictor/`)

Uses analyzed patterns to make predictions. The predictor has been refactored into a modular structure:

- `base_predictor.py`: Core TweetPredictor class
- `daily_predictor.py`: Daily prediction logic
- `hourly_predictor.py`: Hourly prediction logic
- `utils.py`: Shared utility functions

Main prediction methods:

- `predict_count()`: Predicts tweets until a specific date or for N days
- `predict_next_hours()`: Predicts tweets for the next N hours

See the [Predictor README](predictor/README.md) for detailed information.

### 4. Evaluator (`evaluator.py`)

Evaluates prediction accuracy:

- Backtests predictions against historical data
- Calculates Mean Absolute Error (MAE), Root Mean Squared Error (RMSE)
- Produces day-by-day comparisons of predicted vs. actual tweets

### 5. Visualizer (`visualizer.py`)

Creates visualizations of:

- Daily tweet activity and 7-day moving average
- Tweet distribution by day of week
- Tweet distribution by hour of day
- Prediction accuracy evaluation

### 6. Main Module (`main.py`)

Provides command-line interface that integrates all components

## Usage Examples

### Basic Usage

```bash
# Predict for the next 7 days (default)
python -m src.algos.elon_tweet_predictor.main

# Predict for a specific date
python -m src.algos.elon_tweet_predictor.main --date 2023-12-31

# Predict for the next N days
python -m src.algos.elon_tweet_predictor.main --days 14

# Predict for specific hours only
python -m src.algos.elon_tweet_predictor.main --hours 9,12,18,21

# Predict for the next N hours
python -m src.algos.elon_tweet_predictor.main --next-hours 12
```

### Advanced Options

```bash
# Generate activity plots
python -m src.algos.elon_tweet_predictor.main --plot

# Evaluate prediction precision
python -m src.algos.elon_tweet_predictor.main --precision

# Show all 24-hour averages
python -m src.algos.elon_tweet_predictor.main --all-hours

# Disable trend adjustment (use historical averages only)
python -m src.algos.elon_tweet_predictor.main --no-trend

# Combine multiple options
python -m src.algos.elon_tweet_predictor.main --date 2023-12-31 --hours 9,12,18,21 --plot --precision
```

## Command-Line Arguments

| Argument       | Type | Description                                                  |
| -------------- | ---- | ------------------------------------------------------------ |
| `--file`       | str  | Path to custom data file (default: elonmusk_reformatted.csv) |
| `--date`       | str  | Target date to predict (YYYY-MM-DD format)                   |
| `--days`       | int  | Number of days to predict (default: 7)                       |
| `--hours`      | str  | Comma-separated list of specific hours (0-23) to include     |
| `--next-hours` | int  | Predict for the next N hours instead of full days            |
| `--plot`       | flag | Generate activity plots                                      |
| `--precision`  | flag | Evaluate prediction precision                                |
| `--days-back`  | int  | Number of days back for precision evaluation (default: 14)   |
| `--all-hours`  | flag | Display tweet counts for all 24 hours                        |
| `--no-trend`   | flag | Disable trend adjustment (use historical averages only)      |

## Installation

1. Clone the repository
2. Install required dependencies:
   ```bash
   pip install pandas matplotlib
   ```
3. Place the `elonmusk_reformatted.csv` file in the `data/` directory
4. Run the predictor using one of the command examples above

## Output Examples

### Prediction Output

```
Prediction results:
From 2023-01-15 to 2023-01-22
Expected tweets: 127.5

Day-by-day breakdown:
- 2023-01-15 (remaining hours): 8.3 tweets
- 2023-01-16 (Monday): 19.2 tweets
- 2023-01-17 (Tuesday): 17.5 tweets
- 2023-01-18 (Wednesday): 15.9 tweets
- 2023-01-19 (Thursday): 20.4 tweets
- 2023-01-20 (Friday): 18.7 tweets
- 2023-01-21 (Saturday): 13.8 tweets
- 2023-01-22 (Sunday): 13.7 tweets
```

### Hourly Prediction Output

```
Prediction results:
Expected tweets in the next 4 hours: 2.64

Hour-by-hour breakdown:
- 2023-01-15 14:30:00 (2 PM, 30 min): 0.47 tweets
- 2023-01-15 15:00 (3 PM): 0.62 tweets
- 2023-01-15 16:00 (4 PM): 0.85 tweets
- 2023-01-15 17:00 (5 PM): 0.70 tweets
```

### Visualizations

The `--plot` option generates two visualization files:

- `elon_tweet_activity.png`: Shows historical patterns
- `elon_tweet_prediction_accuracy.png`: Shows prediction accuracy (when used with `--precision`)

## License

This project is for educational and research purposes only.
