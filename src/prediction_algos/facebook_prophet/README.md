# Elon Musk Tweet Count Predictor using Facebook Prophet

This module implements Facebook Prophet time series forecasting to predict Elon Musk's tweet counts for Polymarket prediction time frames.

## Overview

The predictor analyzes historical tweet data and generates predictions for specific time ranges defined in your constants (e.g., "less than 150", "150-174", etc.). It takes into account:

- Current tweets already posted in the prediction week
- Time remaining in the prediction period
- Historical tweet patterns and seasonality
- Uncertainty intervals for robust probability estimates

## Features

- **Enhanced Predictions**: Multiple forecasting models (Daily Prophet, Hourly Prophet, Random Forest, Pattern-based)
- **Real-time Predictions**: Accounts for tweets already posted and time remaining
- **Multiple Time Frames**: Generates probabilities for all Polymarket betting categories
- **Visualization**: Creates comprehensive plots showing forecasts and probabilities
- **Flexible Parameters**: Customizable Prophet model parameters
- **Historical Analysis**: Uses all available historical tweet data for training

## Files Structure

```
src/prediction_algos/facebook_prophet/
├── __init__.py              # Module initialization
├── data_processor.py        # Data loading and preprocessing
├── predictor.py            # Original Prophet prediction logic
├── enhanced_predictor.py    # Enhanced multi-model predictor
├── main.py                 # Original command-line interface
├── enhanced_main.py        # Enhanced command-line interface
├── README.md               # This file
└── plots/                  # Generated prediction plots (created automatically)
```

## Installation Requirements

The following packages are required (should already be installed in your environment):

```bash
prophet>=1.1.6
pandas
numpy
matplotlib
seaborn
pytz
scikit-learn
scipy
```

## Usage

**Important**: All commands should be run from the main project directory (where `venv/` is located) using Python module syntax.

### Basic Usage

Run predictions with default settings:

```bash
# Activate virtual environment
source venv/bin/activate

# Run original predictor
python -m src.prediction_algos.facebook_prophet.main

# Run enhanced predictor (recommended)
python -m src.prediction_algos.facebook_prophet.enhanced_main
```

### Advanced Usage

#### Original Predictor

```bash
# Custom data path
python -m src.prediction_algos.facebook_prophet.main --data-path /path/to/your/tweets.csv

# Custom current time (useful for testing)
python -m src.prediction_algos.facebook_prophet.main --current-time "2025-06-08 15:30:00"

# Disable plots
python -m src.prediction_algos.facebook_prophet.main --no-plots

# Custom Prophet parameters
python -m src.prediction_algos.facebook_prophet.main --changepoint-prior 0.1 --seasonality-prior 20.0

# Combined options
python -m src.prediction_algos.facebook_prophet.main --current-time "2025-06-08 12:00:00" --changepoint-prior 0.08
```

#### Enhanced Predictor (Recommended)

```bash
# Basic enhanced prediction
python -m src.prediction_algos.facebook_prophet.enhanced_main

# Custom current time
python -m src.prediction_algos.facebook_prophet.enhanced_main --current-time "2025-06-09 14:49:37"

# Custom data path
python -m src.prediction_algos.facebook_prophet.enhanced_main --data-path /path/to/your/tweets.csv

# Example with specific time for testing
python -m src.prediction_algos.facebook_prophet.enhanced_main --current-time "2025-06-10 10:00:00"
```

### Programmatic Usage

#### Original Predictor

```python
from src.prediction_algos.facebook_prophet import TweetPredictor
from datetime import datetime

# Initialize predictor
predictor = TweetPredictor()

# Generate predictions
predictions = predictor.generate_predictions()

# Print formatted summary
predictor.print_prediction_summary(predictions)

# Create visualization plots
predictor.plot_predictions(predictions)

# Access raw prediction data
for frame_name, data in predictions['predictions_by_frame'].items():
    print(f"{frame_name}: {data['probability']:.3f}")
```

#### Enhanced Predictor (Recommended)

```python
from src.prediction_algos.facebook_prophet import EnhancedTweetPredictor
from datetime import datetime

# Initialize enhanced predictor
predictor = EnhancedTweetPredictor()

# Generate enhanced predictions
predictions = predictor.generate_enhanced_predictions()

# Print enhanced summary
predictor.print_enhanced_summary(predictions)

# Access model breakdown
breakdown = predictions['predictions_breakdown']
print(f"Daily Prophet: {breakdown['prophet_daily']:.1f}")
print(f"Hourly Prophet: {breakdown['prophet_hourly']:.1f}")
print(f"Pattern-based: {breakdown['pattern_based']:.1f}")
print(f"Random Forest: {breakdown['random_forest']:.1f}")
print(f"Ensemble: {breakdown['ensemble']:.1f}")
```

## How It Works

### Enhanced Predictor Features

The enhanced predictor uses **multiple forecasting models** for better accuracy:

1. **Daily Prophet Model**: Traditional daily aggregation approach
2. **Hourly Prophet Model**: Captures intra-day tweet patterns (10,005+ hours of data)
3. **Pattern-based Model**: Analyzes recent 14-day trends
4. **Random Forest Model**: Uses engineered features (day of week, rolling averages, lag features)
5. **Ensemble Method**: Weighted combination (40% hourly, 30% daily, 20% pattern, 10% RF)

### 1. Data Processing

- Loads tweet data from CSV file with columns: `id`, `text`, `created_at`
- Parses timestamps in Georgia format (`YYYY:MM:DD:HH:MM:SS`)
- Converts to both daily and hourly tweet counts for training
- Handles timezone conversion and DST ambiguity

### 2. Model Training

- **Daily Model**: Historical daily tweet counts with seasonality
- **Hourly Model**: Hour-by-hour patterns with custom hourly seasonality
- **Random Forest**: Feature engineering with date/time, moving averages, lag features
- **Pattern Analysis**: Recent trend detection and averaging

### 3. Current Week Analysis

- Identifies tweets already posted in the current prediction week
- Calculates remaining time in the prediction period
- Accounts for the exact timing of the prediction request

### 4. Enhanced Prediction Generation

- Generates predictions from all 4 models
- Combines using weighted ensemble approach
- Calculates confidence intervals using prediction variance
- Uses gamma distribution for better count data modeling

### 5. Probability Calculation

- Fits gamma distribution to ensemble predictions (better for count data)
- Fallback to normal distribution if gamma fitting fails
- Calculates probability for each Polymarket time frame
- Normalizes probabilities to sum to 100%

## Output Explanation

### Enhanced Console Output

```
=== Enhanced Prediction Analysis ===
Current time: 2025-06-09 14:49:37-04:00
Week period: 2025-06-06 12:00:00-04:00 to 2025-06-13 12:00:00-04:00
Tweets posted so far: 81
Time remaining: 3 days, 21:10:23

=== Model Predictions (Remaining Tweets) ===
prophet_daily  :  111.7
prophet_hourly :   57.4
pattern_based  :  125.0
random_forest  :  109.2
ensemble       :   92.4

=== Final Predictions ===
Ensemble remaining: 92.4
Total predicted: 173.4
95% CI: 127.8 - 219.1

ENHANCED ELON MUSK TWEET COUNT PREDICTIONS
======================================================================
Model Predictions (Remaining Tweets):
  Daily Prophet    :  111.7
  Hourly Prophet   :   57.4
  Pattern-based    :  125.0
  Random Forest    :  109.2
  Ensemble Average :   92.4

Total predicted tweets: 173.4
95% Confidence interval: 127.8 - 219.1

PROBABILITIES BY TIME FRAME:
--------------------------------------------------
175–199             :   0.340 ( 34.0%)
150–174             :   0.300 ( 30.0%)
200–224             :   0.183 ( 18.3%)
less than 150       :   0.112 ( 11.2%)
225–249             :   0.054 (  5.4%)
...
```

### Model Comparison

**Enhanced vs Original Predictor:**

| Metric              | Original                | Enhanced               | Improvement    |
| ------------------- | ----------------------- | ---------------------- | -------------- |
| Total Prediction    | 191.6                   | 173.4                  | More realistic |
| Confidence Interval | 309.4 range             | 91.3 range             | 70% tighter    |
| Top Prediction      | "less than 150" (28.9%) | "175–199" (34.0%)      | Better focus   |
| Models Used         | 1 (Daily Prophet)       | 4 (Ensemble)           | Multi-model    |
| Data Granularity    | Daily (417 points)      | Hourly (10,005 points) | 24x more data  |

## Configuration

### Enhanced Model Weights

```python
weights = {
    'prophet_daily': 0.3,    # Traditional daily model
    'prophet_hourly': 0.4,   # Hourly patterns (highest weight)
    'pattern_based': 0.2,    # Recent trends
    'random_forest': 0.1     # Feature-based model
}
```

### Prophet Parameters

- `changepoint_prior_scale`: 0.1 (daily), 0.15 (hourly)
- `seasonality_prior_scale`: 20.0 (daily), 10.0 (hourly)
- `interval_width`: 0.8 for both models

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the main project directory with `python -m src.prediction_algos.facebook_prophet.enhanced_main`
2. **Data Path Issues**: Check that the CSV file exists and has the correct columns
3. **Timezone Issues**: The enhanced predictor handles DST ambiguity automatically
4. **Memory Usage**: Hourly model uses more memory (~10K data points vs 417)

### Performance Notes

- Enhanced model training: 3-8 seconds (vs 1-3 seconds for original)
- Hourly model processes 10,005+ data points
- Random Forest training: ~1 second
- Memory usage: ~50MB for full dataset

## Command Examples

```bash
# Quick prediction
python -m src.prediction_algos.facebook_prophet.enhanced_main

# Test with specific time
python -m src.prediction_algos.facebook_prophet.enhanced_main --current-time "2025-06-10 12:00:00"

# Use custom data
python -m src.prediction_algos.facebook_prophet.enhanced_main --data-path src/data/custom_tweets.csv

# Compare with original
python -m src.prediction_algos.facebook_prophet.main --current-time "2025-06-09 14:49:37"
python -m src.prediction_algos.facebook_prophet.enhanced_main --current-time "2025-06-09 14:49:37"
```

## Future Improvements

- Add LSTM/neural network models to ensemble
- Implement real-time Twitter API integration
- Add cross-validation for model performance assessment
- Include external factors (news events, market movements)
- Add automated betting recommendation system
- Implement model performance tracking and alerts

## References

- [Facebook Prophet Documentation](https://facebook.github.io/prophet/docs/quick_start.html#python-api)
- [Prophet Paper](https://peerj.com/preprints/3190/)
- [Time Series Forecasting Best Practices](https://facebook.github.io/prophet/docs/diagnostics.html)
- [Ensemble Methods](https://scikit-learn.org/stable/modules/ensemble.html)
