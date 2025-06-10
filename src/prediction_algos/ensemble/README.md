# Ensemble Tweet Prediction Model

An ensemble forecasting model that combines multiple prediction algorithms to generate robust tweet count predictions with confidence intervals and probabilities.

## Features

- **Enhanced Models by Default**: Uses Enhanced Neural Prophet, Enhanced Facebook Prophet, and Enhanced TimesFM
- **Configurable Model Weights**: Flexible weight system for combining predictions
- **Additional Prediction Methods**: Moving average and linear trend analysis
- **Comprehensive Analysis**: Confidence intervals, probabilities, and detailed comparisons
- **Minimal Output**: Reduced verbosity with essential information only
- **No Plots by Default**: Lightweight execution without automatic plot generation

## Default Configuration

```
📊 Model Weights:
   Neural Prophet: 15.0%      (Enhanced version)
   Facebook Prophet: 40.0%    (Enhanced version)
   TimesFM: 40.0%            (Enhanced version)
   Moving Average: 2.5%       (7-day window)
   Linear Trend: 2.5%         (14-day trend)
```

## Quick Start

### Basic Usage (Enhanced Models, No Plots)

```bash
python -m src.prediction_algos.ensemble.main
```

### With Custom Weights

```bash
python -m src.prediction_algos.ensemble.main \
    --neural-prophet-weight 0.2 \
    --facebook-prophet-weight 0.5 \
    --timesfm-weight 0.3 \
    --moving-average-weight 0 \
    --linear-trend-weight 0
```

### Enable Plots

```bash
python -m src.prediction_algos.ensemble.main --plots
```

### Fast Mode (Uses Basic Models)

```bash
python -m src.prediction_algos.ensemble.main --fast
```

## Command Line Options

### Basic Options

- `--data-path`: Path to tweet data CSV file
- `--current-time`: Current time in YYYY-MM-DD HH:MM:SS format
- `--fast`: Use fast mode (basic models instead of enhanced)
- `--plots`: Enable plot generation (disabled by default)

### Model Weights (0.0 to exclude model)

- `--neural-prophet-weight`: Neural Prophet weight (default: 0.15)
- `--facebook-prophet-weight`: Facebook Prophet weight (default: 0.40)
- `--timesfm-weight`: TimesFM weight (default: 0.40)
- `--moving-average-weight`: Moving average weight (default: 0.025)
- `--linear-trend-weight`: Linear trend weight (default: 0.025)

### Legacy Options (for backward compatibility)

- `--no-moving-average`: Sets moving average weight to 0
- `--no-linear-trend`: Sets linear trend weight to 0

## Model Architecture

### Enhanced Models (Default)

1. **Enhanced Neural Prophet**: Advanced deep learning with multiple regressors
2. **Enhanced Facebook Prophet**: Bayesian forecasting with seasonal components
3. **Enhanced TimesFM**: Transformer-based time series model with attention

### Fallback Strategy

If enhanced models fail, the system automatically falls back to basic versions:

- Enhanced Neural Prophet → Neural Prophet → Skip
- Enhanced Facebook Prophet → Facebook Prophet → Skip
- Enhanced TimesFM → TimesFM → Skip

### Additional Methods

- **Moving Average**: 7-day rolling average prediction
- **Linear Trend**: 14-day linear regression trend analysis

## Weight System

Weights are automatically normalized to sum to 1.0:

```python
# Example: Custom weights
raw_weights = {
    'neural_prophet': 0.15,
    'facebook_prophet': 0.40,
    'timesfm': 0.40,
    'moving_average': 0.025,
    'linear_trend': 0.025
}
# Total: 1.0 (already normalized)
```

If any model fails, weights are re-normalized among remaining active models.

## Output Format

### Minimal Console Output

```
🔥 Ensemble Tweet Count Predictor
==================================================
📊 Model Weights:
   Neural Prophet: 15.0%
   Facebook Prophet: 40.0%
   TimesFM: 40.0%
   Moving Average: 2.5%
   Linear Trend: 2.5%

🔥 Preparing forecasting models...
📊 [1/3] Neural Prophet...
   ✅ Ready
📈 [2/3] Facebook Prophet...
   ✅ Ready
🤖 [3/3] TimesFM...
   ✅ Ready

🎯 Ensemble ready with 3/3 models active

🔮 Generating predictions...
   📊 Neural Prophet: 125.3 tweets
   📈 Facebook Prophet: 142.7 tweets
   🤖 TimesFM: 138.9 tweets
   📊 Moving Average: 135.2 tweets
   📈 Linear Trend: 140.1 tweets

🎯 ENSEMBLE RESULT: 139.2 tweets
   Confidence: 118.4 - 160.0

==================================================
🔥 ENSEMBLE PREDICTION SUMMARY
==================================================
Current tweets: 85
Total predicted: 139.2
80% Confidence: 118.4 - 160.0

🤖 MODEL CONTRIBUTIONS:
   neural_prophet: 125.3 tweets (weight: 0.150)
   facebook_prophet: 142.7 tweets (weight: 0.400)
   timesfm: 138.9 tweets (weight: 0.400)
   moving_average: 135.2 tweets (weight: 0.025)
   linear_trend: 140.1 tweets (weight: 0.025)

📊 TOP PROBABILITIES:
100-149              : 45.2%
150-199              : 28.7%
50-99                : 15.8%
200-249              : 6.9%
250-299              : 2.4%
300-399              : 0.8%
25-49                : 0.2%
0-24                 : 0.0%
==================================================
```

## Example Use Cases

### Disable Specific Models

```bash
# Only Facebook Prophet + TimesFM
python -m src.prediction_algos.ensemble.main \
    --neural-prophet-weight 0 \
    --moving-average-weight 0 \
    --linear-trend-weight 0
```

### Statistical Methods Only

```bash
# Moving Average + Linear Trend only
python -m src.prediction_algos.ensemble.main \
    --neural-prophet-weight 0 \
    --facebook-prophet-weight 0 \
    --timesfm-weight 0
```

### High TimesFM Weight

```bash
# Favor TimesFM heavily
python -m src.prediction_algos.ensemble.main \
    --neural-prophet-weight 0.1 \
    --facebook-prophet-weight 0.1 \
    --timesfm-weight 0.8
```

### Legacy Mode (Backward Compatibility)

```bash
# Old style flags still work
python -m src.prediction_algos.ensemble.main \
    --neural-prophet-weight 0 \
    --facebook-prophet-weight 0 \
    --timesfm-weight 0 \
    --no-moving-average \
    --no-linear-trend
```

## Technical Details

### Model Integration

- Each model provides predictions in different formats
- Automatic format detection and normalization
- Graceful error handling with fallbacks
- Confidence interval estimation and aggregation

### Performance Optimizations

- Enhanced models disabled in fast mode for speed
- Parallel model preparation where possible
- Efficient weight normalization
- Minimal logging and output

### Dependencies

- Uses existing individual model packages
- Shared data processor for consistency
- Compatible with all existing data formats
- Follows workspace virtual environment rules

## Files Structure

```
src/prediction_algos/ensemble/
├── __init__.py              # Module exports
├── data_processor.py        # Ensemble data processing
├── predictor.py            # Main ensemble predictor
├── main.py                 # CLI interface
└── README.md               # This file
```

The ensemble system provides a robust, configurable, and efficient way to combine multiple forecasting approaches while maintaining simplicity and reliability.

## 🎯 Model Comparison

| Model                | Strengths                        | Default Weight | Exclude With                  |
| -------------------- | -------------------------------- | -------------- | ----------------------------- |
| **Neural Prophet**   | Auto-regression, neural networks | 0.33           | `--neural-prophet-weight 0`   |
| **Facebook Prophet** | Stability, interpretability      | 0.34           | `--facebook-prophet-weight 0` |
| **TimesFM**          | Foundation model, complexity     | 0.33           | `--timesfm-weight 0`          |
| **Moving Average**   | Simple, reliable baseline        | N/A            | `--no-moving-average`         |
| **Linear Trend**     | Recent trend projection          | N/A            | `--no-linear-trend`           |

## 🔄 Use Cases

### Production Use (Balanced)

```bash
python -m src.prediction_algos.ensemble.main --fast
```

### Research/Analysis (All Methods)

```bash
python -m src.prediction_algos.ensemble.main
```

### Quick Testing (Moving Average Only)

```bash
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --facebook-prophet-weight 0 --timesfm-weight 0 --no-linear-trend --no-plots
```

### Model Comparison (Single Models)

```bash
# Test Neural Prophet only
python -m src.prediction_algos.ensemble.main --facebook-prophet-weight 0 --timesfm-weight 0 --no-moving-average --no-linear-trend

# Test Facebook Prophet only
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --timesfm-weight 0 --no-moving-average --no-linear-trend
```

### Custom Ensemble (Your Preferences)

```bash
# Heavy Facebook Prophet with moving average backup
python -m src.prediction_algos.ensemble.main --facebook-prophet-weight 0.8 --neural-prophet-weight 0.2 --timesfm-weight 0 --no-linear-trend
```

## 🐛 Troubleshooting

### Weight Validation Errors

```bash
# ❌ This will fail (all weights are 0)
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --facebook-prophet-weight 0 --timesfm-weight 0 --no-moving-average --no-linear-trend

# ✅ This works (at least one method available)
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --facebook-prophet-weight 0 --timesfm-weight 0
```

### Model Failures

- Individual model failures are handled gracefully
- Remaining models get renormalized weights
- Additional methods provide fallback predictions

### Performance Issues

- Use `--fast` for quicker model training
- Use `--no-plots` to skip visualization
- Exclude heavy models with weight 0

---

## 📝 License

This implementation is part of the Polymarket Algorithm project.
