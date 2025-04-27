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
```

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

## Features

- **Enhanced Statistical Model**: Negative Binomial distribution better fits tweet count data
- **Time Series Forecasting**: Prophet-based algorithm for handling complex patterns and seasonality
- **Automatic Anomaly Detection**: Identifies patterns that could affect predictions
- **Advanced Trend Analysis**: Captures acceleration in tweeting rates
- **Robust Timezone Handling**: All dates and times use Eastern Time (ET) for Polymarket compatibility
- **Multiple Prediction Models**: Ensemble approach combines different prediction techniques
- **Visualization Tools**: Generate plots to understand prediction distributions and historical trends
- **Command-Line Interface**: Easy to use from terminal or scripts

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
