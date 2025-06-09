# Neural Prophet Tweet Count Predictor

A **fast Neural Prophet implementation** for predicting Elon Musk's weekly tweet counts using deep learning time series forecasting.

## 🚀 Quick Start (Speed-Optimized Commands)

### Ultra-Fast Mode (5 seconds training)

```bash
# Fastest possible prediction - 15 epochs, no plots
python -m src.prediction_algos.neural_prophet.fast_main --ultra-fast --no-plots

# Ultra-fast with plots
python -m src.prediction_algos.neural_prophet.fast_main --ultra-fast
```

### Fast Mode (30 seconds training)

```bash
# Fast single Neural Prophet model - 30 epochs
python -m src.prediction_algos.neural_prophet.main --fast

# Or using fast_main interface
python -m src.prediction_algos.neural_prophet.fast_main --fast
```

### Normal Mode (60 seconds training) - **RECOMMENDED**

```bash
# Standard Neural Prophet model - 50 epochs (best balance)
python -m src.prediction_algos.neural_prophet.main

# Or using fast_main interface
python -m src.prediction_algos.neural_prophet.fast_main --normal
```

### Enhanced Ensemble Mode (3-4 minutes training)

```bash
# Multiple neural networks ensemble (slower but most comprehensive)
python -m src.prediction_algos.neural_prophet.enhanced_main
```

## ⚡ Speed Comparison

| Command                  | Training Time    | Epochs | Models               | Accuracy  | Use Case        |
| ------------------------ | ---------------- | ------ | -------------------- | --------- | --------------- |
| `fast_main --ultra-fast` | **~5 seconds**   | 15     | 1 neural (minimal)   | Good      | Quick testing   |
| `main --fast`            | **~30 seconds**  | 30     | 1 neural (optimized) | Very Good | Fast production |
| `main` (normal)          | **~60 seconds**  | 50     | 1 neural (enhanced)  | Excellent | **Recommended** |
| `enhanced_main`          | **~3-4 minutes** | 30-50  | 4 neural + 2 support | Maximum   | Comprehensive   |

## 📋 Command Options

### Basic Commands

```bash
# Ultra-fast Neural Prophet (15 epochs, ~5 seconds)
python -m src.prediction_algos.neural_prophet.fast_main --ultra-fast

# Fast Neural Prophet (30 epochs, ~30 seconds)
python -m src.prediction_algos.neural_prophet.main --fast

# Normal Neural Prophet (50 epochs, ~60 seconds) - RECOMMENDED
python -m src.prediction_algos.neural_prophet.main

# Enhanced ensemble (multiple models, ~3-4 minutes)
python -m src.prediction_algos.neural_prophet.enhanced_main
```

### Advanced Options

```bash
# Specify custom data path
python -m src.prediction_algos.neural_prophet.main --data-path path/to/tweets.csv

# Use specific prediction time
python -m src.prediction_algos.neural_prophet.main --current-time "2025-06-09 14:49:37"

# Fast mode with custom time
python -m src.prediction_algos.neural_prophet.main --fast --current-time "2025-06-09 16:00:00"

# Disable plot generation for faster execution
python -m src.prediction_algos.neural_prophet.fast_main --ultra-fast --no-plots

# Ultra-fast mode with custom options
python -m src.prediction_algos.neural_prophet.fast_main --ultra-fast --current-time "2025-06-09 16:00:00"
```

## 🎯 Neural Prophet Advantages Over Facebook Prophet

| Feature                   | Neural Prophet           | Facebook Prophet      | Advantage                                |
| ------------------------- | ------------------------ | --------------------- | ---------------------------------------- |
| **Model Type**            | Neural Networks          | Linear Components     | Better non-linear patterns               |
| **Auto-regression**       | ✅ n_lags features       | ❌ No auto-regression | Uses historical values as NN input       |
| **Changepoint Detection** | Neural network-based     | Rule-based            | AI-powered trend detection               |
| **Seasonality**           | Deep learning patterns   | Fourier series        | Complex non-linear seasonality           |
| **Training Speed**        | 5-30 seconds (optimized) | 3-8 seconds           | Acceptable trade-off for neural benefits |

## 🔧 Technical Configuration

### Ultra-Fast Mode (5 seconds)

```python
NeuralProphet(
    epochs=15,              # VERY LOW
    learning_rate=0.4,      # HIGH for fast convergence
    yearly_seasonality=False, # DISABLED for max speed
    weekly_seasonality=True,  # Keep only weekly patterns
    daily_seasonality=False,
    n_lags=5,              # Minimal autoregressive features
    n_changepoints=6       # Minimal changepoint detection
)
```

### Fast Mode (30 seconds)

```python
NeuralProphet(
    epochs=30,              # REDUCED from 50
    learning_rate=0.2,      # INCREASED from 0.15
    n_lags=5,              # REDUCED from 7
    n_changepoints=6,       # REDUCED from 10
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False, # DISABLED for speed
    quantiles=[0.1, 0.9],
    trend_reg=1.5,
    seasonality_reg=1.5
)
```

### Normal Mode (60 seconds) - **RECOMMENDED**

```python
NeuralProphet(
    epochs=50,              # Standard training
    learning_rate=0.15,     # Balanced learning rate
    n_lags=7,              # Full autoregressive features
    n_changepoints=10,      # Full changepoint detection
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False, # Still disabled for reasonable speed
    quantiles=[0.1, 0.9],
    trend_reg=1.0,          # Standard regularization
    seasonality_reg=1.0
)
```

## 📊 Output Example

```
🚀 ULTRA-FAST MODE: 15 epochs, LR=0.4, minimal features
Training FAST Neural Prophet with 417 days of data...
FAST Neural Prophet model training completed!

=== NEURAL PROPHET PREDICTION SUMMARY ===
Current tweets: 82
Total predicted: 197.3
80% Confidence interval: 167.7 - 226.8

PROBABILITIES BY TIME FRAME:
175–199             :    0.449 ( 44.9%)
200–224             :    0.374 ( 37.4%)
150–174             :    0.102 ( 10.2%)
```

## 🏗️ Project Structure

```
src/prediction_algos/neural_prophet/
├── __init__.py              # Module initialization
├── data_processor.py        # Data loading and preprocessing
├── predictor.py            # Fast single Neural Prophet model
├── enhanced_predictor.py   # Multi-model ensemble (slower)
├── main.py                 # Basic CLI (fast mode)
├── fast_main.py           # Ultra-fast CLI with speed options
├── enhanced_main.py       # Enhanced ensemble CLI
└── README.md              # This file
```

## ⚙️ Installation

```bash
# Install Neural Prophet and dependencies
pip install neuralprophet torch pytorch-lightning

# For GPU acceleration (optional)
pip install torch[cuda]  # If you have CUDA-compatible GPU
```

## 🎨 Features

### Neural Network Capabilities

- **Auto-regressive features**: Uses past 5-7 days as neural network inputs
- **Neural changepoint detection**: AI-powered trend change identification
- **Deep learning seasonality**: Complex non-linear seasonal patterns
- **Uncertainty quantiles**: Neural network-based confidence intervals

### Speed Optimizations Applied

- ✅ **Reduced epochs**: 15-30 vs 100+ epochs
- ✅ **Higher learning rates**: 0.2-0.4 vs 0.1 for faster convergence
- ✅ **Disabled daily seasonality**: Focus on yearly + weekly patterns
- ✅ **Fewer autoregressive lags**: 5 vs 7 historical inputs
- ✅ **Reduced changepoints**: 6 vs 10 trend detection points
- ✅ **Single model focus**: Avoid ensemble overhead when speed is priority

### Activity Detection & Adaptation

- Analyzes recent tweet rates (6h, 24h, 3d windows)
- Detects activity modes: `high_activity`, `low_activity`, `increasing_activity`, `normal_activity`
- Applies adaptive multipliers for enhanced predictions

## 🔄 Comparison with Facebook Prophet

Both implementations provide:

- Same sophisticated probability calculations
- Same activity detection and bias correction
- Same output format and visualization
- Same data preprocessing pipeline

**Choose Neural Prophet when:**

- You want better pattern recognition for complex non-linear trends
- Auto-regressive features are important for your use case
- You can accept 5-30 seconds training time vs 3-8 seconds

**Choose Facebook Prophet when:**

- You need the absolute fastest training (3-8 seconds)
- Interpretability of linear components is important
- You're working with very simple seasonal patterns

## 📈 Performance Metrics

### Recent Test Results

```
Fast Mode (30 epochs, 30 seconds):
- Prediction: 191.5 tweets
- Top probability: 175–199 (62.1%)
- MAE: 13.4, RMSE: 18.2

Ultra-Fast Mode (15 epochs, 5 seconds):
- Prediction: 197.3 tweets
- Top probability: 175–199 (44.9%)
- MAE: 14.3, RMSE: 19.8
```

## 🐛 Troubleshooting

### Common Issues

1. **Import errors**: Ensure Neural Prophet is installed

   ```bash
   pip install neuralprophet
   ```

2. **Slow training**: Use ultra-fast mode

   ```bash
   python -m src.prediction_algos.neural_prophet.fast_main --ultra-fast
   ```

3. **CUDA warnings**: Install PyTorch with CUDA support or ignore (CPU training is fast enough)

4. **Plot generation errors**: Disable plots for faster execution
   ```bash
   python -m src.prediction_algos.neural_prophet.fast_main --no-plots
   ```

## 🎯 Best Practices

1. **For quick testing**: Use `--ultra-fast` mode (5 seconds)
2. **For production**: Use standard fast mode (30 seconds) - good balance of speed/accuracy
3. **For maximum accuracy**: Use enhanced ensemble mode (3-4 minutes)
4. **For automation**: Use `--no-plots` flag to disable visualization
5. **For debugging**: Enable plots to visualize forecast trends

---

## 📝 License

This implementation is part of the Polymarket Algorithm project and follows the same licensing terms.
