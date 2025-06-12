# Polymarket Algorithm Simulation Suite

This simulation suite provides comprehensive tools for testing and developing cryptocurrency trading strategies in a controlled environment using real Polymarket data without executing actual trades.

## 📁 Folder Structure

```
src/simulation/
├── README.md                    # This documentation
├── initialization/              # Simulation run creation and management
│   ├── run_initializer.py      # Core initialization logic
│   ├── __main__.py             # CLI interface
│   └── README.md               # Detailed initialization docs
├── bidding_decision/           # Trading strategy implementations
│   └── strategy_1/             # Primary simulation strategy
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

## 🚀 Quick Start Guide

### 1. Create a New Simulation Run

```bash
# Create a simulation run with initial balance
python -m src.simulation.initialization \
    --create \
    --market-name "Your Strategy Test" \
    --balance 1000 \
    --run-name "your_run_name"

# Initialize with real Polymarket data
python -m src.simulation.initialization --init-markets-from-polymarket your_run_name
```

### 2. Run Complete Simulation (Full Command Example)

```bash
# Complete simulation command with all parameters
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
    --sell-below 2.0
```

## 📋 Complete Command Reference

### Scheduler-Based Simulation (Recommended)

The main scheduler provides the most comprehensive simulation environment:

```bash
python -m src.scheduler.scheduler [SIMULATION_OPTIONS] [ALGORITHM_OPTIONS] [TRADING_OPTIONS]
```

#### Core Simulation Parameters

- `--simulate RUN_NAME`: Run in simulation mode using specified run
- `--sim-balance AMOUNT`: Set simulation balance (overrides run balance)
- `--algorithm ALGORITHM`: Prediction algorithm (`ensemble`, `enhanced_facebook_prophet`, etc.)
- `--random-seed SEED`: Random seed for reproducible results

#### Data Source Options

- `--use-csv-getter`: Use CSV data source for analysis
- `--get-tweet-count-first`: Analyze tweet counts before predictions
- `--predictions-only`: Only generate predictions without trading

#### Timing Intervals

- `--tweet-interval SECONDS`: Interval between tweet analysis (default: 300)
- `--buy-interval SECONDS`: Interval between buy decisions (default: 300)
- `--sell-interval SECONDS`: Interval between sell decisions (default: 300)

#### Trading Parameters

- `--amount DOLLARS`: Order amount per trade (default: 10.0)
- `--buy-threshold PERCENT`: Minimum opportunity for buying (default: 0.0)
- `--sell-threshold PERCENT`: Minimum opportunity for selling (default: 0.0)
- `--min-prediction PERCENT`: Minimum prediction confidence (default: 0.0)
- `--sell-below PERCENT`: Sell positions below this prediction (default: 0.0)
- `--weighted-selection`: Use probabilistic selection instead of highest opportunity

#### Execution Control

- `--dry-run`: Show decisions without executing trades
- `--run-once`: Execute one cycle instead of continuous loop
- `--quiet`: Reduce output verbosity
- `--no-tweets`: Skip tweet analysis

### Strategy-Based Simulation

For direct strategy testing without scheduler:

```bash
# Run bidding strategy
python -m src.simulation.bidding_decision.strategy_1 \
    --run RUN_NAME \
    --threshold 2.0 \
    --amount 25.0 \
    --weighted-selection

# Run selling strategy
python -m src.simulation.bidding_decision.strategy_1 \
    --sell RUN_NAME \
    --threshold 2.0 \
    --auto-sell \
    --sell-below 25.0
```

### Simulation Management

```bash
# Create new simulation run
python -m src.simulation.initialization \
    --create \
    --market-name "Market Category" \
    --balance 1000 \
    --run-name "custom_name"

# Initialize with real market data
python -m src.simulation.initialization --init-markets-from-polymarket RUN_NAME

# Update market prices
python -m src.simulation.initialization --update-markets-from-polymarket RUN_NAME

# View run information
python -m src.simulation.initialization --info RUN_NAME

# List all runs
python -m src.simulation.initialization --list
```

## 💡 Usage Examples

### Example 1: Basic Strategy Testing

```bash
# Create and initialize run
python -m src.simulation.initialization \
    --create \
    --market-name "Election Predictions" \
    --balance 500 \
    --run-name "election_test"

python -m src.simulation.initialization --init-markets-from-polymarket election_test

# Run simulation with basic parameters
python -m src.scheduler.scheduler \
    --simulate election_test \
    --sim-balance 500 \
    --algorithm enhanced_facebook_prophet \
    --buy-threshold 2.0 \
    --sell-threshold 1.5 \
    --amount 25.0 \
    --dry-run \
    --run-once
```

### Example 2: Advanced Trading Strategy

```bash
# Advanced simulation with weighted selection and minimum predictions
python -m src.scheduler.scheduler \
    --use-csv-getter \
    --get-tweet-count-first \
    --tweet-interval 120 \
    --buy-interval 60 \
    --sell-interval 30 \
    --simulate advanced_test \
    --sim-balance 1000 \
    --algorithm ensemble \
    --random-seed 42 \
    --amount 50.0 \
    --buy-threshold 3.0 \
    --min-prediction 10.0 \
    --weighted-selection \
    --sell-threshold 2.0 \
    --sell-below 15.0 \
    --predictions-only
```

### Example 3: Your Specific Command

```bash
# Your exact command for comprehensive testing
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
    --sell-below 2.0
```

### Example 4: Algorithm Comparison

```bash
# Test different algorithms on same data
ALGORITHMS=("ensemble" "enhanced_facebook_prophet" "neural_prophet" "timesfm")

for algo in "${ALGORITHMS[@]}"; do
    echo "Testing $algo..."
    python -m src.scheduler.scheduler \
        --simulate algo_test_$algo \
        --sim-balance 1000 \
        --algorithm $algo \
        --random-seed 42 \
        --buy-threshold 2.0 \
        --amount 20.0 \
        --run-once \
        --dry-run
done
```

## 📊 Simulation Features

### Real Market Integration

- **Live Data**: Fetches real market data from Polymarket
- **Price Updates**: Automatic market price synchronization
- **Market Status**: Tracks active/inactive markets
- **Historical Data**: Maintains complete price history

### Trading Simulation

- **Position Tracking**: Complete portfolio management
- **Transaction History**: Detailed audit trail
- **Profit/Loss Calculation**: Real-time P&L tracking
- **Balance Management**: Prevents overdrafts and tracks cash flow

### Algorithm Support

- **Multiple Algorithms**: Support for various prediction models
- **Ensemble Methods**: Weighted combination of multiple models
- **Reproducible Results**: Random seed control for consistent testing
- **Performance Metrics**: Detailed algorithm performance tracking

### Strategy Testing

- **Threshold Testing**: Test different opportunity thresholds
- **Risk Management**: Configurable risk parameters
- **Selection Methods**: Weighted vs highest opportunity selection
- **Market Filtering**: Filter by prediction confidence and market activity

## 🔧 Configuration Options

### Prediction Algorithms

- `ensemble`: Weighted combination of multiple models
- `enhanced_facebook_prophet`: Advanced Prophet with multiple timeframes
- `neural_prophet`: Neural network-based Prophet
- `timesfm`: Time Series Foundation Model
- `basic_prophet`: Standard Facebook Prophet
- `moving_average`: Moving average predictor
- `linear_trend`: Linear trend analysis

### Trading Strategies

- **Opportunity-based**: Trade based on prediction vs market price difference
- **Threshold-based**: Only trade when opportunity exceeds threshold
- **Weighted Selection**: Probabilistic selection from multiple opportunities
- **Risk-managed**: Stop-loss and minimum prediction filtering

### Data Sources

- **Real-time Polymarket**: Live market data
- **CSV Data**: Historical data analysis
- **Tweet Integration**: Social sentiment analysis
- **Combined Sources**: Multi-source data fusion

## 📈 Monitoring and Analysis

### Run Information

```bash
# Get detailed run statistics
python -m src.simulation.initialization --info RUN_NAME
```

### Performance Tracking

- **Portfolio Value**: Real-time portfolio valuation
- **Win Rate**: Success rate of predictions
- **Profit/Loss**: Financial performance tracking
- **Transaction Costs**: Trading fee simulation
- **Risk Metrics**: Drawdown and volatility analysis

### Strategy Comparison

```bash
# Compare multiple strategies
python -m src.simulation.bidding_decision.strategy_1 --analyze-opportunities \
    --threshold 2.0 --weighted-selection --min-prediction 5.0
```

## 🛠️ Development and Testing

### Debug Mode

```bash
# Enable detailed debugging
python -m src.scheduler.scheduler \
    --simulate debug_test \
    --algorithm ensemble \
    --dry-run \
    --run-once \
    --debug \
    --verbose
```

### Performance Testing

```bash
# Test performance with different parameters
python -m src.scheduler.scheduler \
    --simulate performance_test \
    --sim-balance 10000 \
    --amount 100.0 \
    --buy-threshold 1.0 \
    --run-once \
    --predictions-only
```

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
