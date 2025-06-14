# Polymarket Algorithm Simulation Suite

A comprehensive simulation framework for testing and analyzing Polymarket trading strategies with advanced prediction algorithms.

## 🎯 Quick Start

1. **Activate Environment**: `source venv/bin/activate`
2. **Create Simulation Run**: `python -m src.simulation.initialization.run_creator`
3. **Run Strategy**: `python -m src.simulation.bidding_decision.strategy_1 --run <run_name> --algorithm ensemble`
4. **Monitor Results**: Check `src/simulation/runs/<run_name>/`

## 📁 Folder Structure

```
src/simulation/
├── README.md                    # This documentation
├── initialization/              # Simulation run creation and management
│   ├── run_creator.py          # Interactive run creation
│   ├── run_initializer.py      # Core initialization logic
│   ├── __main__.py             # CLI interface
│   └── README.md               # Detailed initialization docs
├── bidding_decision/           # Trading strategy implementations
│   ├── strategy_1/             # Primary simulation strategy
│   │   ├── simulation_bidder.py # Bidding logic
│   │   ├── simulation_seller.py # Position selling logic
│   │   ├── __main__.py         # CLI interface
│   │   └── README.md           # Strategy documentation
│   └── strategy_2/             # Secondary simulation strategy
│       ├── simulation_bidder.py # Bidding logic
│       ├── simulation_seller.py # Position selling logic
│       ├── __main__.py         # CLI interface
│       └── README.md           # Strategy documentation
├── runs/                       # All simulation run data
│   ├── pirvelad/              # Example run directories
│   ├── test_merge/            # Contains JSON simulation data
│   └── ...                    # More simulation runs
└── tests/                     # Test suites
```

## 🤖 Algorithm Support

The simulation system supports all advanced prediction algorithms available in the main trading system:

### Available Algorithms

- **ensemble** - Multi-model ensemble with weighted predictions (Recommended)
- **enhanced_facebook_prophet** - Multiple Prophet models (daily, hourly, conservative, aggressive, weekly)
- **neural_prophet** - Neural network-based Prophet variant
- **facebook_prophet** - Standard Facebook Prophet
- **timesfm** - Time Series Foundation Model
- **basic_prophet** - Simplified Prophet implementation
- **moving_average** - Simple moving average predictor
- **linear_trend** - Linear trend analysis

### Algorithm Parameters

- `--algorithm <name>` - Choose prediction algorithm
- `--random-seed <number>` - Set random seed for reproducible results (recommended: 42)

### Algorithm Usage Examples

```bash
# Complete Scheduler-Based Simulation with Strategy 1
python -m src.scheduler.scheduler --strategy strategy_1 --algorithm ensemble --random-seed 42 --use-csv-getter --get-tweet-count-first --tweet-interval 110 --buy-interval 60 --sell-interval 5 --simulate pirvelad092231 --sim-balance 144 --amount 1.0 --buy-threshold 1.0 --min-prediction 5.0 --weighted-selection --sell-threshold 0.5 --sell-below 2.0 --show-eachalgo-distribution

# Complete Scheduler-Based Simulation with Strategy 2
python -m src.scheduler.scheduler --strategy strategy_2 --algorithm ensemble --random-seed 42 --use-csv-getter --get-tweet-count-first --tweet-interval 110 --buy-interval 60 --sell-interval 5 --simulate kkikik --sim-balance 144 --amount 1.0 --buy-threshold 1.0 --min-prediction 5.0 --weighted-selection --sell-threshold 0.5 --sell-below 2.0 --show-eachalgo-distribution

# Ensemble algorithm (multi-model approach) - Direct Strategy Usage
python -m src.simulation.bidding_decision.strategy_1 \
    --analyze-opportunities \
    --algorithm ensemble \
    --random-seed 42 \
    --threshold 2.0
```

## 🚀 Usage Guide

### Method 1: Scheduler-Based Simulation (Recommended)

Run complete trading simulation with real market integration:

```bash
python -m src.scheduler.scheduler \
    --use-csv-getter \
    --get-tweet-count-first \
    --tweet-interval 110 \
    --buy-interval 60 \
    --sell-interval 5 \
    --simulate <run_name> \
    --sim-balance 144 \
    --amount 1.0 \
    --buy-threshold 1.0 \
    --min-prediction 5.0 \
    --weighted-selection \
    --sell-threshold 0.5 \
    --sell-below 2.0 \
    --algorithm ensemble \
    --random-seed 42
```

### Method 2: Strategy-Based Simulation

Run individual strategy components with algorithm support:

#### Bidding Analysis

```bash
python -m src.simulation.bidding_decision.strategy_1 \
    --analyze-opportunities \
    --algorithm ensemble \
    --random-seed 42 \
    --threshold 1.5 \
    --amount 25.0 \
    --dry-run
```

#### Position Management

```bash
python -m src.simulation.bidding_decision.strategy_1 \
    --run <simulation_name> \
    --algorithm enhanced_facebook_prophet \
    --random-seed 42 \
    --threshold 3.0 \
    --amount 25.0 \
    --debug
```

#### Selling Strategy

```bash
python -m src.simulation.bidding_decision.strategy_1 \
    --sell <simulation_name> \
    --algorithm neural_prophet \
    --random-seed 42 \
    --threshold 2.0 \
    --auto-sell
```

#### Portfolio Analysis

```bash
python -m src.simulation.bidding_decision.strategy_1 \
    --analyze <simulation_name> \
    --algorithm ensemble \
    --random-seed 42 \
    --debug
```

## 📊 Complete Usage Examples

### Example 1: Quick Algorithm Test

```bash
# Test ensemble algorithm with dry run
python -m src.simulation.bidding_decision.strategy_1 \
    --analyze-opportunities \
    --algorithm ensemble \
    --random-seed 42 \
    --threshold 1.0 \
    --dry-run \
    --debug
```

### Example 2: Full Trading Simulation with Algorithms

```bash
# Complete trading simulation with enhanced prophet
python -m src.scheduler.scheduler \
    --use-csv-getter \
    --get-tweet-count-first \
    --tweet-interval 110 \
    --buy-interval 60 \
    --sell-interval 5 \
    --simulate my_trading_run \
    --sim-balance 100 \
    --amount 2.0 \
    --buy-threshold 2.0 \
    --min-prediction 6.0 \
    --weighted-selection \
    --sell-threshold 1.0 \
    --sell-below 3.0 \
    --algorithm enhanced_facebook_prophet \
    --random-seed 42
```

### Example 3: Advanced Multi-Strategy Simulation

```bash
# Advanced simulation with ensemble algorithm (Featured Command)
python -m src.scheduler.scheduler \
    --use-csv-getter \
    --get-tweet-count-first \
    --tweet-interval 110 \
    --buy-interval 60 \
    --sell-interval 5 \
    --simulate pirvelad \
    --sim-balance 144 \
    --amount 1.0 \
    --buy-threshold 1.0 \
    --min-prediction 5.0 \
    --weighted-selection \
    --sell-threshold 0.5 \
    --sell-below 2.0 \
    --algorithm ensemble \
    --random-seed 42
```

**Parameters explained:**

- `--algorithm ensemble`: Uses multi-model ensemble predictions
- `--random-seed 42`: Ensures reproducible results
- `--simulate pirvelad`: Uses the "pirvelad" simulation run
- `--sim-balance 144`: Starting with $144 simulated balance
- `--amount 1.0`: Bet $1.0 per opportunity
- `--buy-threshold 1.0`: Buy when prediction exceeds 1.0%
- `--min-prediction 5.0`: Minimum prediction confidence of 5.0%
- `--weighted-selection`: Use weighted market selection
- `--sell-threshold 0.5`: Sell when profit exceeds 0.5%
- `--sell-below 2.0`: Sell if loss exceeds 2.0%

### Example 4: Neural Prophet Analysis

```bash
# Deep learning approach with neural prophet
python -m src.simulation.bidding_decision.strategy_1 \
    --run advanced_simulation \
    --algorithm neural_prophet \
    --random-seed 42 \
    --threshold 2.5 \
    --amount 5.0 \
    --debug
```

## 🔧 Command Reference

### Core Commands

- `--analyze-opportunities`: Analyze current market opportunities with algorithms
- `--run <name>`: Execute bidding strategy for simulation run with algorithms
- `--sell <name>`: Execute selling strategy for simulation run with algorithms
- `--analyze <name>`: Analyze simulation run performance with algorithms

### Algorithm Parameters

- `--algorithm <name>`: Prediction algorithm to use
- `--random-seed <number>`: Random seed for reproducible results

### Trading Parameters

- `--threshold <float>`: Prediction confidence threshold
- `--amount <float>`: Bet amount per opportunity
- `--auto-sell`: Enable automatic selling
- `--dry-run`: Test mode without actual trades
- `--debug`: Enable detailed logging

### Simulation Parameters (Scheduler)

- `--simulate <run>`: Enable simulation mode
- `--sim-balance <float>`: Starting simulation balance
- `--buy-threshold <float>`: Minimum prediction for buying
- `--min-prediction <float>`: Minimum prediction confidence
- `--sell-threshold <float>`: Profit threshold for selling
- `--sell-below <float>`: Loss threshold for selling
- `--weighted-selection`: Use weighted market selection

## 📈 Performance Monitoring

### Real-time Monitoring

- **Position Tracking**: Monitor active positions in simulation runs
- **Performance Metrics**: Track ROI, win rate, and profit/loss
- **Algorithm Performance**: Compare algorithm effectiveness
- **Risk Management**: Monitor exposure and position sizes

### Files Generated

- `positions.json`: Current position data with algorithm metadata
- `trading_history.json`: Complete trading history with algorithm details
- `performance_summary.json`: Performance metrics by algorithm
- `market_analysis.csv`: Market analysis with algorithm predictions

## 🎛️ Algorithm Configuration

### Ensemble Configuration

The ensemble algorithm combines multiple models:

- Neural Prophet (weight: 0.3)
- Enhanced Facebook Prophet (weight: 0.25)
- TimesFM (weight: 0.2)
- Basic Prophet (weight: 0.15)
- Moving Average (weight: 0.1)

### Enhanced Facebook Prophet Models

- **Daily Model**: Long-term trend analysis
- **Hourly Model**: Short-term fluctuation prediction
- **Conservative Model**: Low-risk predictions
- **Aggressive Model**: High-confidence opportunities
- **Weekly Model**: Week-over-week pattern analysis

## 🔍 Troubleshooting

### Algorithm Issues

```bash
# Test algorithm availability
python -m src.simulation.bidding_decision.strategy_1 --help

# Verify algorithm functionality
python -m src.simulation.bidding_decision.strategy_1 \
    --analyze-opportunities \
    --algorithm ensemble \
    --random-seed 42 \
    --dry-run \
    --debug
```

### Common Algorithm Problems

- **Import Errors**: Ensure all dependencies are installed
- **Memory Issues**: Use smaller datasets for testing
- **Timeout Issues**: Increase timeout for complex algorithms
- **Reproducibility**: Always use `--random-seed` for consistent results

## 🛠️ Development

### Testing Algorithm Integration

```bash
# Test all algorithms
for algo in ensemble enhanced_facebook_prophet neural_prophet facebook_prophet timesfm basic_prophet moving_average linear_trend; do
    echo "Testing $algo..."
    python -m src.simulation.bidding_decision.strategy_1 \
        --analyze-opportunities \
        --algorithm $algo \
        --random-seed 42 \
        --dry-run
done
```

### Best Practices

- Use `--random-seed 42` for reproducible results
- Start with `--dry-run` for testing
- Monitor algorithm performance with `--debug`
- Use ensemble algorithm for production simulations
- Test different algorithms on historical data

### Custom Algorithm Development

1. Add algorithm to `src/bidding_decision/stats/comparison.py`
2. Update algorithm choices in `__main__.py`
3. Test with simulation framework
4. Document in this README

## 📝 Best Practices

1. **Start Small**: Begin with small balances and conservative thresholds
2. **Use Dry-Run**: Always test with `--dry-run` before live simulation
3. **Monitor Closely**: Use `--run-once` for step-by-step testing
4. **Compare Algorithms**: Test multiple algorithms with same parameters
5. **Track Performance**: Regularly check run information and statistics
6. **Update Markets**: Keep market data fresh with regular updates
7. **Document Results**: Save successful configurations for future reference

## 🔍 Troubleshooting

### Common Issues

**Market Data Not Loading**

```bash
# Update markets manually
python -m src.simulation.initialization --update-markets-from-polymarket RUN_NAME
```

**Balance Issues**

```bash
# Check current balance
python -m src.simulation.initialization --info RUN_NAME

# Add balance if needed
python -m src.simulation.initialization --add-balance RUN_NAME 500.0
```

**Algorithm Errors**

```bash
# Test with basic algorithm first
python -m src.scheduler.scheduler \
    --simulate test_run \
    --algorithm basic_prophet \
    --dry-run \
    --run-once
```

### Debug Information

- Use `--debug` flag for detailed error information
- Check log files in simulation run directories
- Verify network connectivity for market data updates
- Ensure all required dependencies are installed

## 📚 Additional Resources

- **Initialization Documentation**: `src/simulation/initialization/README.md`
- **Strategy Documentation**: `src/simulation/bidding_decision/strategy_1/README.md`
- **Main Scheduler Documentation**: `src/scheduler/README.md`
- **Algorithm Documentation**: Algorithm-specific documentation in respective modules

---

_This simulation suite provides a comprehensive testing environment for developing and validating cryptocurrency trading strategies. Use it to test your approaches before deploying to real markets._
