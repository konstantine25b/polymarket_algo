# Ensemble Tweet Count Predictor

A **flexible ensemble implementation** that combines Neural Prophet, Facebook Prophet, and TimesFM models with **custom weight controls** and **additional prediction methods** (moving averages, linear trends) for predicting Elon Musk's weekly tweet counts.

## 🚀 Quick Start Commands

### Basic Ensemble (Default Weights)

```bash
# Standard ensemble with all models (recommended)
python -m src.prediction_algos.ensemble.main

# Fast ensemble mode (using fast individual models)
python -m src.prediction_algos.ensemble.main --fast
```

### Custom Model Weights

```bash
# Only Facebook Prophet (disable others with weight 0)
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --timesfm-weight 0 --facebook-prophet-weight 1

# Heavy Facebook Prophet, light others
python -m src.prediction_algos.ensemble.main --facebook-prophet-weight 0.7 --neural-prophet-weight 0.2 --timesfm-weight 0.1

# Only Neural Prophet and TimesFM (no Facebook Prophet)
python -m src.prediction_algos.ensemble.main --facebook-prophet-weight 0 --neural-prophet-weight 0.6 --timesfm-weight 0.4
```

### Additional Prediction Methods Control

```bash
# Disable additional methods (only use main models)
python -m src.prediction_algos.ensemble.main --no-moving-average --no-linear-trend

# Only moving average predictions (disable all main models)
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --facebook-prophet-weight 0 --timesfm-weight 0

# Only linear trend predictions
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --facebook-prophet-weight 0 --timesfm-weight 0 --no-moving-average
```

## 🎛️ Weight Control System

### Model Weight Arguments

| Argument                    | Default | Description                               |
| --------------------------- | ------- | ----------------------------------------- |
| `--neural-prophet-weight`   | 0.33    | Weight for Neural Prophet (0 = exclude)   |
| `--facebook-prophet-weight` | 0.34    | Weight for Facebook Prophet (0 = exclude) |
| `--timesfm-weight`          | 0.33    | Weight for TimesFM (0 = exclude)          |

**Important Notes:**

- Weights are automatically normalized (don't need to sum to 1)
- Setting weight to `0` completely excludes that model
- At least one model weight must be > 0

### Examples of Weight Control

```bash
# Equal weights (default behavior)
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 1 --facebook-prophet-weight 1 --timesfm-weight 1

# Facebook Prophet only
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --timesfm-weight 0

# Neural Prophet dominant
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0.8 --facebook-prophet-weight 0.1 --timesfm-weight 0.1
```

## 📊 Additional Prediction Methods

### Moving Average Prediction

- Uses historical weekly tweet counts
- 7-day window by default
- Provides baseline statistical prediction
- Enabled by default (use `--no-moving-average` to disable)

### Linear Trend Prediction

- Calculates recent trend from last 14 days
- Projects trend forward for remaining week days
- Shows daily trend slope in output
- Enabled by default (use `--no-linear-trend` to disable)

### Fallback Behavior

- If all main models fail, additional methods provide backup predictions
- If main models succeed, additional methods complement the ensemble
- Always ensures at least one prediction method is available

## 📋 Complete Command Reference

### Basic Options

```bash
# Standard ensemble
python -m src.prediction_algos.ensemble.main

# Fast mode (quicker training)
python -m src.prediction_algos.ensemble.main --fast

# No plots (faster execution)
python -m src.prediction_algos.ensemble.main --no-plots

# Custom data path
python -m src.prediction_algos.ensemble.main --data-path path/to/tweets.csv

# Custom prediction time
python -m src.prediction_algos.ensemble.main --current-time "2025-06-09 14:30:00"
```

### Weight Control Examples

```bash
# Facebook Prophet only
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --timesfm-weight 0

# Neural Prophet + TimesFM (no Facebook Prophet)
python -m src.prediction_algos.ensemble.main --facebook-prophet-weight 0

# Custom weights with additional methods disabled
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0.5 --facebook-prophet-weight 0.3 --timesfm-weight 0.2 --no-moving-average --no-linear-trend
```

### Method Control Examples

```bash
# Only moving average (no models)
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --facebook-prophet-weight 0 --timesfm-weight 0 --no-linear-trend

# Only linear trend (no models, no moving average)
python -m src.prediction_algos.ensemble.main --neural-prophet-weight 0 --facebook-prophet-weight 0 --timesfm-weight 0 --no-moving-average

# Models + moving average only (no linear trend)
python -m src.prediction_algos.ensemble.main --no-linear-trend
```

## 🔧 Technical Features

### Weight Normalization

- Input weights are automatically normalized to sum to 1.0
- Example: `--neural-prophet-weight 2 --facebook-prophet-weight 1` becomes 0.667 and 0.333

### Model Exclusion

- Setting any weight to `0` completely excludes that model from:
  - Training/preparation phase
  - Prediction generation
  - Ensemble combination
  - Resource usage

### Graceful Fallbacks

- If a model fails during training → excluded automatically
- If all main models fail → additional methods provide predictions
- If some models fail → remaining models get renormalized weights

### Additional Method Integration

- Moving average and linear trend are calculated independently
- Used as fallback when main models unavailable
- Can be primary prediction source if all models disabled

## 📊 Output Example

```
🔥 Ensemble Tweet Count Predictor
==================================================
📊 Model Weights:
   Neural Prophet: 0.500
   Facebook Prophet: 0.500
   TimesFM: DISABLED
📈 Additional Methods: Moving Average, Linear Trend

🎯 Ensemble initialized with weights: {'neural_prophet': 0.5, 'facebook_prophet': 0.5, 'timesfm': 0.0}
📊 Including moving average predictions
📈 Including linear trend predictions

🔮 Generating ensemble predictions...
📊 Neural Prophet predicting...
   Neural Prophet: 194.8 tweets (weight: 0.500)
📈 Facebook Prophet predicting...
   Facebook Prophet: 193.7 tweets (weight: 0.500)
📊 Moving Average predicting...
   Moving Average: 185.2 tweets
📈 Linear Trend predicting...
   Linear Trend: 189.3 tweets (slope: 2.15)

🎯 ENSEMBLE RESULT: 194.3 tweets
   Confidence: 140.1 - 238.5

============================================================
🔥 ENSEMBLE PREDICTION SUMMARY
============================================================
Current tweets: 84
Total predicted: 194.3
80% Confidence interval: 140.1 - 238.5

🤖 MODEL CONTRIBUTIONS:
   neural_prophet: 194.8 tweets (weight: 0.500)
   facebook_prophet: 193.7 tweets (weight: 0.500)
```

## 🏗️ Project Structure

```
src/prediction_algos/ensemble/
├── __init__.py              # Module initialization
├── data_processor.py        # Data loading and preprocessing
├── predictor.py            # Main ensemble predictor with weight control
├── main.py                 # CLI interface with all options
└── README.md              # This file
```

## ⚙️ Installation

All dependencies are included with the individual model packages:

```bash
# Neural Prophet dependencies
pip install neuralprophet torch pytorch-lightning

# Facebook Prophet dependencies
pip install prophet

# TimesFM dependencies
pip install timesfm  # Optional - will use mock if unavailable

# Additional dependencies
pip install pandas numpy matplotlib seaborn scipy scikit-learn
```

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
