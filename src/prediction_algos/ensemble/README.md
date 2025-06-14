# Ensemble Tweet Prediction Model

An ensemble forecasting model that combines multiple prediction algorithms to generate robust tweet count predictions with confidence intervals and probabilities. **Features reproducible random seed control** for consistent results across runs.

## Features

- **Enhanced Models by Default**: Uses Enhanced Neural Prophet, Enhanced Facebook Prophet, and Enhanced TimesFM
- **Basic Prophet Integration**: Includes the custom Basic Prophet algorithm from polymarket_predictor
- **Configurable Model Weights**: Flexible weight system for combining predictions
- **Additional Prediction Methods**: Moving average and linear trend analysis
- **Comprehensive Analysis**: Confidence intervals, probabilities, and detailed comparisons
- **Minimal Output**: Reduced verbosity with essential information only
- **Configurable Plots**: Plot generation can be enabled or disabled
- **🎯 Reproducible Results**: Random seed control for consistent predictions across runs

## Default Configuration

```
📊 Model Weights:
   Neural Prophet: 17.0%      (Enhanced version)
   Facebook Prophet: 25.0%    (Enhanced version)
   TimesFM: 30.0%            (Enhanced version)
   Basic Prophet: 25.0%       (Custom polymarket algorithm)
   Moving Average: 1.5%       (7-day window)
   Linear Trend: 1.5%         (14-day trend)
```

## Prediction Models

### 1. Neural Prophet (17% weight)

- **Type**: Deep learning time series model
- **Strengths**: Complex pattern recognition, trend analysis
- **Version**: Enhanced Neural Prophet with multiple regressors

### 2. Facebook Prophet (25% weight)

- **Type**: Bayesian forecasting model
- **Strengths**: Seasonal decomposition, trend changes, holidays
- **Version**: Enhanced Facebook Prophet with advanced seasonality

### 3. TimesFM (30% weight)

- **Type**: Transformer-based foundation model
- **Strengths**: Attention mechanisms, large-scale pre-training
- **Version**: Enhanced TimesFM with ensemble capabilities

### 4. Basic Prophet (25% weight)

- **Type**: Custom algorithm from polymarket_predictor
- **Strengths**: Historical rate blending, lognormal distribution modeling
- **Features**: Current vs historical rate weighting, confidence intervals

### 5. Moving Average (1.5% weight)

- **Type**: Statistical baseline
- **Method**: 7-day rolling window average
- **Purpose**: Smooth trend continuation

### 6. Linear Trend (1.5% weight)

- **Type**: Statistical baseline
- **Method**: 14-day linear regression
- **Purpose**: Recent trend extrapolation

## Quick Start

### Basic Usage (All Models, No Plots)

```bash
python -m src.prediction_algos.ensemble.main
```

### Show Individual Algorithm Distributions

```bash
# Show probability distribution for each algorithm in the ensemble
python -m src.prediction_algos.ensemble.main --show-eachalgo-distribution

# Combined with other options
python -m src.prediction_algos.ensemble.main --random-seed 42 --show-eachalgo-distribution --fast
```

### 🎯 Reproducible Results with Random Seeds

```bash
# Use specific random seed for reproducible results
python -m src.prediction_algos.ensemble.main --random-seed 42

# Compare runs with same seed (should be identical)
python -m src.prediction_algos.ensemble.main --random-seed 123
python -m src.prediction_algos.ensemble.main --random-seed 123  # Same results

# Different seeds produce different but deterministic results
python -m src.prediction_algos.ensemble.main --random-seed 456
```

### With Custom Weights

```bash
python -m src.prediction_algos.ensemble.main \
    --neural-prophet-weight 0.17 \
    --facebook-prophet-weight 0.25 \
    --timesfm-weight 0.30 \
    --basic-prophet-weight 0.25 \
    --moving-average-weight 0.015 \
    --linear-trend-weight 0.015 \
    --random-seed 42
```

### Enable Plots

```bash
python -m src.prediction_algos.ensemble.main --no-plots false --random-seed 42
```

### Fast Mode (Uses Basic Models)

```bash
python -m src.prediction_algos.ensemble.main --fast --random-seed 42
```

## Command Line Options

### Basic Options

- `--data-path`: Path to tweet data CSV file
- `--current-time`: Current time in YYYY-MM-DD HH:MM:SS format
- `--fast`: Use fast mode (basic models instead of enhanced)
- `--no-plots`: Disable plot generation
- `--ensemble-method`: Combination method (weighted_average, median, best_performer)
- `--random-seed`: Random seed for reproducible results (default: 42)
- `--show-eachalgo-distribution`: Show probability distribution for each individual algorithm

### Model Weights (0.0 to exclude model)

- `--neural-prophet-weight`: Neural Prophet weight (default: 0.17)
- `--facebook-prophet-weight`: Facebook Prophet weight (default: 0.25)
- `--timesfm-weight`: TimesFM weight (default: 0.30)
- `--basic-prophet-weight`: Basic Prophet weight (default: 0.25)
- `--moving-average-weight`: Moving average weight (default: 0.015)
- `--linear-trend-weight`: Linear trend weight (default: 0.015)

## Model Architecture

### Enhanced Models (Default)

1. **Enhanced Neural Prophet**: Advanced deep learning with multiple regressors
2. **Enhanced Facebook Prophet**: Bayesian forecasting with seasonal components
3. **Enhanced TimesFM**: Transformer-based time series model with attention
4. **Basic Prophet**: Custom polymarket algorithm with rate blending

### Fallback Strategy

If enhanced models fail, the system automatically falls back to basic versions:

- Enhanced Neural Prophet → Neural Prophet → Skip
- Enhanced Facebook Prophet → Facebook Prophet → Skip
- Enhanced TimesFM → TimesFM → Skip
- Basic Prophet → Always available (stateless)

### Additional Methods

- **Moving Average**: 7-day rolling average prediction
- **Linear Trend**: 14-day linear regression trend analysis

## Weight System

Weights are automatically normalized to sum to 1.0:

```python
# Example: Default weights
raw_weights = {
    'neural_prophet': 0.17,
    'facebook_prophet': 0.25,
    'timesfm': 0.30,
    'basic_prophet': 0.25,
    'moving_average': 0.015,
    'linear_trend': 0.015
}
# Total: 1.0 (already normalized)
```

If any model fails, weights are re-normalized among remaining active models.

## Output Format

### Minimal Console Output

```
🎯 Ensemble initialized: neural_prophet: 17.0%, facebook_prophet: 25.0%, timesfm: 30.0%, basic_prophet: 25.0%, moving_average: 1.5%, linear_trend: 1.5%

🔥 Preparing models...
📊 Neural Prophet: ✅ (Enhanced)
📈 Facebook Prophet: ✅
🤖 TimesFM: ✅
🔮 Basic Prophet: ✅ (Ready)

🎯 4/4 models ready

🔮 Generating predictions...
   📊 Neural Prophet: 125.3
   📈 Facebook Prophet: 142.7
   🤖 TimesFM: 138.9
   🔮 Basic Prophet: 144.2
   📊 Moving Average: 135.2
   📈 Linear Trend: 140.1

🎯 ENSEMBLE: 139.8 tweets (118.4-160.0)

==================================================
🔥 ENSEMBLE PREDICTION SUMMARY
==================================================
Current tweets: 85
Total predicted: 139.8
80% Confidence: 118.4 - 160.0

🤖 MODEL CONTRIBUTIONS:
   neural_prophet: 125.3 tweets (weight: 0.170)
   facebook_prophet: 142.7 tweets (weight: 0.250)
   timesfm: 138.9 tweets (weight: 0.300)
   basic_prophet: 144.2 tweets (weight: 0.250)
   moving_average: 135.2 tweets (weight: 0.015)
   linear_trend: 140.1 tweets (weight: 0.015)

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
# Only Basic Prophet + TimesFM
python -m src.prediction_algos.ensemble.main \
    --neural-prophet-weight 0 \
    --facebook-prophet-weight 0 \
    --moving-average-weight 0 \
    --linear-trend-weight 0
```

### Statistical Methods Only

```bash
# Moving Average + Linear Trend only
python -m src.prediction_algos.ensemble.main \
    --neural-prophet-weight 0 \
    --facebook-prophet-weight 0 \
    --timesfm-weight 0 \
    --basic-prophet-weight 0
```

### High TimesFM Weight

```bash
# TimesFM dominant ensemble
python -m src.prediction_algos.ensemble.main \
    --neural-prophet-weight 0.1 \
    --facebook-prophet-weight 0.1 \
    --timesfm-weight 0.7 \
    --basic-prophet-weight 0.1
```

### Basic Prophet Focus

```bash
# Basic Prophet + Polymarket algorithm focus
python -m src.prediction_algos.ensemble.main \
    --neural-prophet-weight 0.1 \
    --facebook-prophet-weight 0.2 \
    --timesfm-weight 0.2 \
    --basic-prophet-weight 0.5
```

## Integration Details

### Basic Prophet Algorithm

The Basic Prophet component integrates the custom prediction algorithm from `src/polymarket_predictor` that:

1. **Calculates Current Rate**: Tweets per day since event start
2. **Analyzes Historical Patterns**: Daily tweet statistics from historical data
3. **Blends Rates**: Weighted combination of current and historical rates
4. **Monte Carlo Simulation**: Lognormal distribution modeling for confidence intervals
5. **Frame Probabilities**: Maps predictions to polymarket outcome frames

**Key Features:**

- Adapts weighting based on elapsed time (more current data = higher current rate weight)
- Uses lognormal distribution for realistic count modeling
- Provides 90% confidence intervals
- Compatible with polymarket frame structures

### Data Flow

```
Tweet Data → EnsembleTweetDataProcessor → Individual Models
                                       ↓
Enhanced Models (ML) ← → Basic Prophet (Statistical)
                                       ↓
            Weighted Combination → Final Prediction
```

## API Usage

```python
from src.prediction_algos.ensemble import EnsembleTweetPredictor

# Initialize with custom weights
predictor = EnsembleTweetPredictor(
    data_path='data/tweets.csv',
    neural_prophet_weight=0.17,
    facebook_prophet_weight=0.25,
    timesfm_weight=0.30,
    basic_prophet_weight=0.25,
    moving_average_weight=0.015,
    linear_trend_weight=0.015
)

# Generate predictions
results = predictor.generate_predictions()
print(f"Prediction: {results['total_predicted']:.1f}")
```

## Fast Ensemble

For quicker predictions, use the Fast variant:

```python
from src.prediction_algos.ensemble import FastEnsembleTweetPredictor

# Uses basic models instead of enhanced versions
fast_predictor = FastEnsembleTweetPredictor()
results = fast_predictor.generate_predictions()
```

## Dependencies

- Neural Prophet: `neuralprophet`, `pytorch`
- Facebook Prophet: `prophet`
- TimesFM: `timesfm` (requires TensorFlow)
- Basic Prophet: Custom implementation (no external dependencies)
- Visualization: `matplotlib`, `seaborn`
- Data: `pandas`, `numpy`, `scipy`

## Performance

| Model            | Preparation Time | Prediction Time | Accuracy    |
| ---------------- | ---------------- | --------------- | ----------- |
| Neural Prophet   | ~30s             | ~2s             | High        |
| Facebook Prophet | ~10s             | ~1s             | High        |
| TimesFM          | ~15s             | ~3s             | Very High   |
| Basic Prophet    | 0s               | ~1s             | Medium-High |
| Moving Average   | 0s               | <1s             | Baseline    |
| Linear Trend     | 0s               | <1s             | Baseline    |

## Troubleshooting

### Common Issues

1. **Model Import Errors**: Ensure all dependencies are installed
2. **Data Format Issues**: Check CSV structure and timestamp format
3. **Memory Issues**: Use `--fast` mode for large datasets
4. **GPU Issues**: TimesFM may require GPU for optimal performance

### Debug Mode

```bash
# Enable verbose output for debugging
PYTHONPATH=. python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.prediction_algos.ensemble.main import main
main()
" --fast
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

## Reproducible Random Seed Control

### Why Random Seeds Matter

The ensemble combines multiple models that may use randomness:

- **Neural Prophet**: PyTorch neural network training with random initialization
- **TimesFM**: Sampling-based predictions with stochastic components
- **Enhanced Models**: Random Forest components in enhanced algorithms
- **Basic Prophet**: Monte Carlo simulations (5000 samples)

Without seed control, each run produces slightly different results even with identical inputs.

### How Seed Control Works

```python
# Random seed is propagated to all models:
1. Global Python random seed
2. NumPy random seed
3. PyTorch random seed (for Neural Prophet)
4. PyTorch Lightning seed (for Neural Prophet training)
5. Individual model seeds (different but deterministic)
6. Basic Prophet simulation seed
```

### Seed Distribution

Each model gets a different but deterministic seed based on the main seed:

```python
base_seed = 42  # Your specified seed
neural_prophet_seed = base_seed + 1     # 43
facebook_prophet_seed = base_seed + 2   # 44
timesfm_seed = base_seed + 3           # 45
basic_prophet_seed = base_seed + 4     # 46
```

This ensures:

- ✅ Reproducible results with same seed
- ✅ Different models use different seeds (avoid correlation)
- ✅ Deterministic behavior across runs
- ✅ Consistent results on different machines

### Usage Examples

```bash
# Production runs with fixed seed
python -m src.prediction_algos.ensemble.main --random-seed 42

# Testing with multiple seeds
for seed in 42 123 456 789; do
    python -m src.prediction_algos.ensemble.main --random-seed $seed --output "test_seed_${seed}.csv"
done

# Compare algorithms with same seed for fair comparison
python -m src.prediction_algos.ensemble.main --random-seed 42 --output ensemble_results.csv
python -m src.prediction_algos.neural_prophet.main --random-seed 42 --output neural_results.csv
python -m src.prediction_algos.facebook_prophet.main --random-seed 42 --output facebook_results.csv
```

## Expected Reproducibility

With `--random-seed 42`, you should get **identical results** across runs:

```
🎯 ENSEMBLE: 183.1 tweets (148.4-220.3)

🤖 MODEL CONTRIBUTIONS:
   neural_prophet: 178.9 tweets (weight: 0.170)
   facebook_prophet: 183.0 tweets (weight: 0.250)
   timesfm: 188.0 tweets (weight: 0.300)
   basic_prophet: 179.5 tweets (weight: 0.250)
   moving_average: 177.2 tweets (weight: 0.015)
   linear_trend: 180.1 tweets (weight: 0.015)
```

Every run with `--random-seed 42` will produce these exact numbers.
