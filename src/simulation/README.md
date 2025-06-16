# Polymarket Algorithm Simulation Suite

A comprehensive simulation framework for testing and analyzing Polymarket trading strategies with advanced prediction algorithms and automated risk management.

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
│   └── strategy_2/             # Secondary simulation strategy (with stop loss)
│       ├── simulation_bidder.py # Bidding logic
│       ├── simulation_seller.py # Position selling logic
│       ├── stop_loss_manager.py # 🛑 Stop loss functionality
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
python -m src.scheduler.scheduler --strategy strategy_2 --algorithm ensemble --random-seed 42 --use-csv-getter --get-tweet-count-first --tweet-interval 110 --buy-interval 60 --sell-interval 5 --simulate kkikik --sim-balance 144 --amount 1.0 --buy-threshold 1.0 --min-prediction 5.0 --weighted-selection --sell-threshold 0.5 --sell-below 2.0 --show-eachalgo-distribution --loss-threshold-1 -5.0 --loss-sell-1 30.0 --loss-threshold-2 -10.0 --loss-sell-2 100.0 --gain-threshold-1 0.5 --gain-sell-1 20.0 --gain-threshold-2 3.0 --gain-sell-2 50.0 

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

## 🛑 Stop Loss Functionality (Strategy 2)

### Overview

The simulation system includes comprehensive **automated stop loss functionality** that helps manage risk by automatically selling positions when they reach predefined profit or loss thresholds. This feature is available in **Strategy 2** and provides configurable risk management for both losses and gains.

### Stop Loss Features

- **Loss Protection**: Automatically sell portions of losing positions
- **Profit Taking**: Lock in gains at specified profit levels
- **Configurable Thresholds**: All percentages and sell amounts are customizable
- **History Tracking**: Complete audit trail of all stop loss actions
- **Dry Run Mode**: Test stop loss logic without executing trades
- **Integration**: Seamlessly works with existing selling strategies

### Default Stop Loss Configuration

```
Loss Thresholds:
- Sell 50% of position at -40% loss (stop loss protection)
- Sell 100% of position at -60% loss (full liquidation)

Gain Thresholds:
- Sell 40% of position at +40% gain (initial profit taking)
- Sell 40% of position at +80% gain (additional profit taking)
```

### Stop Loss Usage Examples

#### Basic Stop Loss Execution

```bash
# Execute stop loss with default thresholds
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name>

# Test stop loss logic without executing (recommended first)
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> --dry-run

# Execute with detailed debugging information
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> --debug
```

#### Custom Stop Loss Thresholds

```bash
# Conservative stop loss (tighter risk management)
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> \
    --loss-threshold-1 -20.0 --loss-sell-1 30.0 \
    --loss-threshold-2 -40.0 --loss-sell-2 100.0 \
    --gain-threshold-1 20.0 --gain-sell-1 25.0 \
    --gain-threshold-2 50.0 --gain-sell-2 25.0

# Aggressive stop loss (wider risk tolerance)
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> \
    --loss-threshold-1 -60.0 --loss-sell-1 75.0 \
    --loss-threshold-2 -80.0 --loss-sell-2 100.0 \
    --gain-threshold-1 60.0 --gain-sell-1 50.0 \
    --gain-threshold-2 120.0 --gain-sell-2 50.0
```

#### Stop Loss CLI Parameters

```bash
# Loss thresholds
--loss-threshold-1 PERCENT    # First loss threshold (default: -40.0%)
--loss-sell-1 PERCENT         # Percentage to sell at first loss (default: 50.0%)
--loss-threshold-2 PERCENT    # Second loss threshold (default: -60.0%)
--loss-sell-2 PERCENT         # Percentage to sell at second loss (default: 100.0%)

# Gain thresholds
--gain-threshold-1 PERCENT    # First gain threshold (default: 40.0%)
--gain-sell-1 PERCENT         # Percentage to sell at first gain (default: 40.0%)
--gain-threshold-2 PERCENT    # Second gain threshold (default: 80.0%)
--gain-sell-2 PERCENT         # Percentage to sell at second gain (default: 40.0%)

# Execution options
--dry-run                     # Test mode without actual execution
--debug                       # Detailed stop loss analysis output
```

### Stop Loss Integration with Selling Strategy

Stop loss functionality is **automatically integrated** with the selling strategy in Strategy 2:

```bash
# Selling strategy automatically checks stop loss first
python -m src.simulation.bidding_decision.strategy_2 --sell <run_name> --auto-sell

# Disable stop loss integration if needed
python -m src.simulation.bidding_decision.strategy_2 --sell <run_name> --auto-sell \
    --loss-threshold-1 -999 --loss-threshold-2 -999 \
    --gain-threshold-1 999 --gain-threshold-2 999
```

### Stop Loss History and Monitoring

```bash
# View stop loss history for a run
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> --dry-run

# The system automatically shows:
# - All previous stop loss actions with timestamps
# - Positions that triggered stop loss with reasons
# - Shares sold and prices at execution
# - Current win/loss percentages for all positions
```

### Stop Loss Complete Workflow Example

```bash
# 1. Create simulation run
python -m src.simulation.initialization --create --market-name "Risk Managed Trading" \
    --balance 1000 --run-name "risk_test"

# 2. Initialize with real market data
python -m src.simulation.initialization --init-markets-from-polymarket risk_test

# 3. Execute bidding strategy
python -m src.simulation.bidding_decision.strategy_2 --run risk_test \
    --threshold 2.0 --amount 50.0 --weighted-selection

# 4. Monitor positions and execute stop loss
python -m src.simulation.bidding_decision.strategy_2 --stop-loss risk_test

# 5. Execute regular selling strategy (with integrated stop loss)
python -m src.simulation.bidding_decision.strategy_2 --sell risk_test \
    --threshold 1.0 --auto-sell

# 6. Check final results and stop loss history
python -m src.simulation.initialization --info risk_test
```

### Advanced Stop Loss Scenarios

#### Multiple Stop Loss Executions

```bash
# Execute stop loss multiple times as markets change
python -m src.simulation.bidding_decision.strategy_2 --stop-loss risk_test
# ... wait for market changes ...
python -m src.simulation.bidding_decision.strategy_2 --stop-loss risk_test
# System only executes NEW triggers, not previously executed ones
```

#### Profit Taking Strategy

```bash
# Focus on profit taking with wider loss tolerance
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> \
    --loss-threshold-1 -70.0 --loss-sell-1 30.0 \
    --loss-threshold-2 -90.0 --loss-sell-2 100.0 \
    --gain-threshold-1 15.0 --gain-sell-1 20.0 \
    --gain-threshold-2 30.0 --gain-sell-2 30.0 \
    --debug
```

#### Risk Management Analysis

```bash
# Analyze stop loss triggers without execution
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> \
    --dry-run --debug

# Output shows:
# - Current P&L for all positions
# - Which positions would trigger stop loss
# - Exact shares that would be sold
# - Estimated proceeds from stop loss sales
# - Complete reasoning for each decision
```

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

### Stop Loss Issues

**Stop Loss Not Triggering**

```bash
# Check current position values and thresholds
python -m src.simulation.bidding_decision.strategy_2 --stop-loss RUN_NAME --dry-run --debug

# Update market prices to get current P&L
python -m src.simulation.initialization --update-markets-from-polymarket RUN_NAME
python -m src.simulation.bidding_decision.strategy_2 --stop-loss RUN_NAME --dry-run
```

**Stop Loss History Verification**

```bash
# View complete stop loss history
python -m src.simulation.bidding_decision.strategy_2 --stop-loss RUN_NAME --dry-run

# Check if stop loss was already executed (prevents duplicate executions)
```

**Custom Stop Loss Testing**

```bash
# Test with very sensitive thresholds to verify functionality
python -m src.simulation.bidding_decision.strategy_2 --stop-loss RUN_NAME \
    --loss-threshold-1 -1.0 --gain-threshold-1 1.0 --dry-run --debug
```

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

**Stop Loss Execution Errors**

```bash
# Verify run exists and has positions
python -m src.simulation.initialization --info RUN_NAME

# Test stop loss logic without execution
python -m src.simulation.bidding_decision.strategy_2 --stop-loss RUN_NAME --dry-run --debug

# Check if positions meet minimum share requirements (>0.01)
```

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
8. **🛑 Stop Loss Management**: Use Strategy 2 with appropriate stop loss thresholds for risk management
9. **Test Stop Loss**: Always test stop loss configuration with `--dry-run` before live use
10. **Monitor P&L**: Regularly check position performance to adjust stop loss thresholds

### Stop Loss Best Practices

1. **Conservative Approach**: Start with tighter thresholds (-20%/-40% loss, +20%/+40% gain)
2. **Test First**: Always use `--dry-run` to verify stop loss logic before execution
3. **Regular Monitoring**: Check stop loss triggers after market updates
4. **History Tracking**: Review stop loss history to optimize thresholds
5. **Integration**: Use stop loss with selling strategy for comprehensive risk management

```bash
# Recommended stop loss testing workflow
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> --dry-run --debug
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> --dry-run
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name>
```

## 📚 Additional Resources

- **Initialization Documentation**: `src/simulation/initialization/README.md`
- **Strategy Documentation**: `src/simulation/bidding_decision/strategy_1/README.md`
- **Main Scheduler Documentation**: `src/scheduler/README.md`
- **Algorithm Documentation**: Algorithm-specific documentation in respective modules

## 🔧 Command Reference

### Core Commands

- `--analyze-opportunities`: Analyze current market opportunities with algorithms
- `--run <name>`: Execute bidding strategy for simulation run with algorithms
- `--sell <name>`: Execute selling strategy for simulation run with algorithms
- `--analyze <name>`: Analyze simulation run performance with algorithms
- `--stop-loss <name>`: Execute stop loss orders for simulation run (Strategy 2 only)

### Algorithm Parameters

- `--algorithm <name>`: Prediction algorithm to use
- `--random-seed <number>`: Random seed for reproducible results

### Trading Parameters

- `--threshold <float>`: Prediction confidence threshold
- `--amount <float>`: Bet amount per opportunity
- `--auto-sell`: Enable automatic selling
- `--dry-run`: Test mode without actual trades
- `--debug`: Enable detailed logging

### Stop Loss Parameters (Strategy 2 only)

- `--loss-threshold-1 <float>`: First loss threshold percentage (default: -40.0%)
- `--loss-sell-1 <float>`: Percentage to sell at first loss threshold (default: 50.0%)
- `--loss-threshold-2 <float>`: Second loss threshold percentage (default: -60.0%)
- `--loss-sell-2 <float>`: Percentage to sell at second loss threshold (default: 100.0%)
- `--gain-threshold-1 <float>`: First gain threshold percentage (default: 40.0%)
- `--gain-sell-1 <float>`: Percentage to sell at first gain threshold (default: 40.0%)
- `--gain-threshold-2 <float>`: Second gain threshold percentage (default: 80.0%)
- `--gain-sell-2 <float>`: Percentage to sell at second gain threshold (default: 40.0%)

### Simulation Parameters (Scheduler)

- `--simulate <run>`: Enable simulation mode
- `--sim-balance <float>`: Starting simulation balance
- `--buy-threshold <float>`: Minimum prediction for buying
- `--min-prediction <float>`: Minimum prediction confidence
- `--sell-threshold <float>`: Profit threshold for selling
- `--sell-below <float>`: Loss threshold for selling
- `--weighted-selection`: Use weighted market selection

### 🛑 **Enhanced Strategy 2 with Automatic Stop Loss**

Strategy 2 now includes **automatic stop loss checking** after every bidding and selling operation. You can control the stop loss behavior using these parameters:

```bash
# Basic Strategy 2 bidding with automatic stop loss (default thresholds)
python -m src.simulation.bidding_decision.strategy_2 --run my_simulation --threshold 1.0 --amount 50.0

# Custom stop loss thresholds for bidding
python -m src.simulation.bidding_decision.strategy_2 --run my_simulation --threshold 1.0 --amount 50.0 --loss-threshold-1 -30.0 --loss-sell-1 25.0 --gain-threshold-1 50.0 --gain-sell-1 30.0
```

**Automatic Stop Loss Features:**

- ✅ **After Bidding**: Automatically checks and executes stop loss orders after placing any bid
- ✅ **After Selling**: Automatically checks and executes stop loss orders during selling strategy
- ✅ **Configurable Thresholds**: All stop loss parameters can be customized
- ✅ **Dry Run Support**: Test stop loss behavior with `--dry-run` flag
- ✅ **Debug Information**: Use `--debug` to see detailed stop loss analysis

**Default Stop Loss Thresholds:**

- **Loss Protection**: -40% → sell 50%, -60% → sell 100%
- **Profit Taking**: +40% → sell 40%, +80% → sell 40%

---

_This simulation suite provides a comprehensive testing environment for developing and validating cryptocurrency trading strategies. Use it to test your approaches before deploying to real markets._
