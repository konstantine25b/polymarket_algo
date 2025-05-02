# Polymarket Tweet Predictor

A modular Python package for predicting tweet counts for Polymarket prediction markets.

## Structure

The package has been refactored into a modular design for better maintainability:

- `time_utils.py`: Time handling and timezone utilities
- `data_processing.py`: Tweet data loading and preprocessing
- `market_api.py`: Polymarket API interactions
- `analysis.py`: Statistical analysis and pattern detection
- `simulation.py`: Monte Carlo simulation and probability calculation
- `visualization.py`: Plotting and visualization
- `enhanced_prediction.py`: Advanced prediction algorithm with improved statistical modeling
- `prophet_prediction.py`: Time series forecasting using Facebook Prophet
- `main.py`: Command-line interface and orchestration

## Enhanced Prediction Algorithm

The enhanced prediction algorithm significantly improves accuracy through several advanced techniques:

- **Negative Binomial Distribution**: Uses a more appropriate probability distribution for count data, replacing the normal distribution which was causing the "less than 100" bucket to have unrealistically high probability
- **Anomaly Detection**: Identifies and accounts for outliers, trend changes, and unusual patterns in the data
- **Weighted Time Periods**: Gives more weight to recent activity while still considering historical patterns
- **Acceleration Factor**: Models the rate of change in tweet frequency for more accurate projections
- **Day-of-Week Patterns**: Incorporates historical tweeting patterns by day of week
- **Hourly Patterns**: Considers time-of-day patterns in tweet frequency
- **Robust Statistics**: Filters out extreme outliers for more stable variance estimation

## Prophet-Based Prediction Algorithm

The Prophet-based prediction algorithm leverages Facebook's Prophet library for time series forecasting with these benefits:

- **Advanced Time Series Modeling**: Automatically decomposes time series into trend, seasonality, and holiday components
- **Robust Handling of Seasonality**: Captures daily, weekly, and other periodic patterns in tweeting behavior
- **Automatic Changepoint Detection**: Identifies trend shifts and adjusts forecasts accordingly
- **Uncertainty Quantification**: Provides robust confidence intervals for predictions
- **Non-Linear Growth Modeling**: Adapts to changing growth rates and saturation effects in tweeting patterns
- **Handles Missing Data**: Robust to gaps and irregular data points in the tweet history
- **Specialized for Social Media Data**: Well-suited for the bursty, non-stationary nature of social media activity

## Usage

### From Command Line

```bash
# Basic usage with enhanced algorithm (default)
python -m src.polymarket_predictor

# Use classic algorithm instead of enhanced
python -m src.polymarket_predictor --classic

# Use Prophet-based algorithm for time series forecasting
python -m src.polymarket_predictor --prophet

# Override current tweet count
python -m src.polymarket_predictor --count 75

# Verify tweet count in a specific timeframe
python -m src.polymarket_predictor --verify-count

# Custom data path and time range
python -m src.polymarket_predictor --data-path path/to/tweets.csv --start-time "2023-12-01 00:00:00" --end-time "2023-12-31 23:59:59"

# Advanced options
python -m src.polymarket_predictor --no-trend --simulations 20000

# Get output in JSON format
python -m src.polymarket_predictor --prophet --json

# Save JSON output to a file
python -m src.polymarket_predictor --prophet --json --output prediction_data.json

# Get only JSON output without any logging or additional text
python -m src.polymarket_predictor --prophet --json --brief
```

### JSON Output Format

When using the `--json` flag, the output will be structured as follows:

```json
{
  "timestamp": "2025-05-02T09:24:35.530828-04:00",
  "prediction_type": "prophet",
  "frame_probabilities": {
    "less than 100": 0.0,
    "100–124": 0.0,
    "125–149": 0.0,
    "150–174": 95.56,
    "175–199": 3.66,
    "200–224": 0.49,
    "225–249": 0.14,
    "250–274": 0.09,
    "275–299": 0.02,
    "300–324": 0.01,
    "325–349": 0.0,
    "350–374": 0.01,
    "375–399": 0.0,
    "400 or more": 0.02
  },
  "summary": {
    "most_likely": {
      "frame": "150–174",
      "probability": 95.56
    },
    "expected_value": 163.48
  }
}
```

The `--brief` flag can be used with `--json` to output only the JSON data without any additional text or logging information, making it ideal for automated scripts and programmatic access.

> **Note:** The JSON output uses proper Unicode characters for range separators (en dashes) rather than ASCII hyphens. When parsing this JSON in your applications, make sure to use a JSON parser that properly handles Unicode characters.

### As a Library

```python
from src.polymarket_predictor import predict_tweet_frame_probabilities

# Basic usage with enhanced algorithm
probabilities = predict_tweet_frame_probabilities()

# With custom parameters
probabilities = predict_tweet_frame_probabilities(
    data_path="path/to/tweets.csv",
    start_date_str="2023-12-01 00:00:00",
    end_date_str="2023-12-31 23:59:59",
    use_trend=True,
    num_simulations=10000,
    current_tweet_count=75,  # Override auto-count
    override_auto_count=True,
    use_enhanced_algorithm=True,  # Use enhanced algorithm
    use_prophet_algorithm=False   # Don't use Prophet algorithm
)

# Using Prophet-based prediction
prophet_probabilities = predict_tweet_frame_probabilities(
    data_path="path/to/tweets.csv",
    use_prophet_algorithm=True
)

# Process results
for frame, probability in probabilities.items():
    print(f"{frame}: {probability:.1f}%")
```

## Command-line Options

```
--verify-count       Verify tweet count in a specific timeframe
--data-path PATH     Path to tweet data CSV (default: src/data/elonmusk_reformatted.csv)
--start-time TIME    Start time in format YYYY-MM-DD HH:MM:SS
--end-time TIME      End time in format YYYY-MM-DD HH:MM:SS
--no-trend           Disable trend adjustment
--simulations N      Number of Monte Carlo simulations (default: 10000)
--count N            Override current tweet count
--classic            Use classic algorithm instead of enhanced
--prophet            Use Prophet-based algorithm for prediction
--json               Output prediction results in JSON format
--output FILE        Save JSON output to the specified file
--brief              Output JSON data only without additional text or logging
```

## Features

- **Enhanced Statistical Model**: Negative Binomial distribution better fits tweet count data
- **Time Series Forecasting**: Prophet-based algorithm for handling complex patterns and seasonality
- **Automatic Anomaly Detection**: Identifies patterns that could affect predictions
- **Advanced Trend Analysis**: Captures acceleration in tweeting rates
- **Robust Timezone Handling**: All dates and times use Eastern Time (ET) for Polymarket compatibility
- **Multiple Prediction Models**: Ensemble approach combines different prediction techniques
- **Visualization Tools**: Generate plots to understand prediction distributions and historical trends
- **Command-Line Interface**: Easy to use from terminal or scripts
- **JSON Output**: Export prediction results in structured JSON format for integration with other tools
- **Brief Mode**: Clean JSON output suitable for automated scripts and API integrations

## Requirements

- Python 3.6+
- pandas
- numpy
- scipy
- matplotlib
- seaborn
- pytz
- requests
- prophet
