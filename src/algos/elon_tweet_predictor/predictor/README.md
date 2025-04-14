# Tweet Predictor Module

This module contains the code for predicting tweet activity based on historical patterns. The original monolithic `predictor.py` has been refactored into a more modular structure.

## Module Structure

- `__init__.py` - Exports the main TweetPredictor class
- `base_predictor.py` - Contains the TweetPredictor class with core functionality
- `daily_predictor.py` - Implements daily prediction logic
- `hourly_predictor.py` - Implements hourly prediction logic
- `utils.py` - Common utility functions shared across prediction modules
- `logging_utils.py` - Logging configuration and verbosity control

## Main Classes and Functions

### TweetPredictor

The main class that orchestrates the prediction process:

```python
predictor = TweetPredictor(analyzer)
predictor.predict_count(target_date_str="2023-12-31")
predictor.predict_next_hours(hours_ahead=4)
```

### Prediction Methods

- `predict_count()`: Predicts tweet count until a specific date or for N days

  - Parameters:
    - `target_date_str`: Target date in format YYYY-MM-DD
    - `days`: Number of days to predict for (alternative to target_date)
    - `use_trend`: Whether to apply recent trend adjustment
    - `hours`: List of specific hours to focus on

- `predict_next_hours()`: Predicts tweet count for the next N hours

  - Parameters:
    - `hours_ahead`: Number of hours to predict for
    - `use_trend`: Whether to apply recent trend adjustment

- `predict_remaining_hours()`: Helper method for predicting hours remaining in a day
  - Parameters:
    - `current_datetime`: Current datetime
    - `target_datetime`: Target datetime
    - `trend_factor`: Trend adjustment factor
    - `specific_hours`: List of specific hours to include

### Utility Functions

- `calculate_trend_factor()`: Calculate trend adjustment based on recent activity
- `validate_hours()`: Validate and filter hour inputs
- `get_weekday_name()`: Convert weekday index to name
- `format_hour_ampm()`: Format hour in 12-hour AM/PM format

### Logging Utilities

The `logging_utils.py` module provides tools to control the verbosity of output:

- `setup_logger()`: Configure logging with specified verbosity level

  - Parameters:
    - `name`: Logger name (default: 'elon_tweet_predictor')
    - `level`: Verbosity level (SILENT, ERROR, WARNING, INFO, DEBUG, VERBOSE)
    - `log_file`: Optional path to log file
    - `clean_format`: Whether to use a clean format (True) or detailed format with timestamps (False)

- `get_verbosity()`: Get current verbosity level
- `set_verbosity()`: Set global verbosity level
- `verbose_print()`: Print message only if current verbosity allows it

Example usage:

```python
from src.algos.elon_tweet_predictor.predictor.logging_utils import setup_logger

# Create logger with INFO level
logger = setup_logger(level='INFO')
logger.info("Standard information")
logger.debug("Detailed debug information - not shown at INFO level")

# Create logger with DEBUG level and file output
logger = setup_logger(level='DEBUG', log_file='logs/prediction.log')
logger.debug("Detailed debug information - now visible and saved to file")
```

Available log levels (from less to more verbose):

- SILENT: No output
- ERROR: Only errors
- WARNING: Warnings and errors
- INFO: Standard information, warnings, and errors
- DEBUG: Detailed debugging information
- VERBOSE: Maximum verbosity
