# Simulation Strategy 1 - Bidding Decision System

This package provides a simulation-based bidding decision system that replicates the real-world auto bidding functionality but operates on simulated JSON data instead of making actual trades.

## Overview

The simulation strategy uses the same statistical analysis as the real `src/bidding_decision/auto_bid` system but:

- Updates market prices from real Polymarket data before making decisions
- Executes "trades" in simulation JSON files instead of real markets
- Tracks all positions, transactions, and balance changes in the simulation
- **Matches real auto_bid behavior exactly** with identical CLI options and table display

## Features

- **Real Market Analysis**: Uses the same comparison table generation as the real system
- **Complete Table Display**: Shows full comparison table with Token IDs and expected values
- **Simulation Trading**: Executes buy/sell decisions in JSON simulation files
- **Market Price Updates**: Automatically updates market prices before trading decisions
- **Position Management**: Tracks all positions and their performance
- **Risk Management**: Applies the same thresholds and filters as the real system
- **Auto-Sell Functionality**: Automatically execute sell orders with `--auto-sell`
- **Weighted Selection**: Probabilistic selection from multiple opportunities

## File Structure

```
src/simulation/bidding_decision/strategy_1/
├── README.md                    # This documentation
├── simulation_bidder.py         # Main simulation bidder class
├── simulation_seller.py         # Position selling logic
└── __main__.py                  # CLI interface
```

## Quick Start

### Method 1: Complete Scheduler-Based Simulation (Recommended)

Run the full trading simulation with scheduler integration:

```bash
# Complete trading simulation with strategy_1
python -m src.scheduler.scheduler --strategy strategy_1 --algorithm ensemble --random-seed 42 --use-csv-getter --get-tweet-count-first --tweet-interval 110 --buy-interval 60 --sell-interval 5 --simulate pirvelad09231 --sim-balance 144 --amount 1.0 --buy-threshold 1.0 --min-prediction 5.0 --weighted-selection --sell-threshold 0.5 --sell-below 2.0

# With dry-run for testing
python -m src.scheduler.scheduler --strategy strategy_1 --algorithm ensemble --random-seed 42 --use-csv-getter --get-tweet-count-first --tweet-interval 110 --buy-interval 60 --sell-interval 5 --simulate pirvelad09231 --sim-balance 144 --amount 1.0 --buy-threshold 1.0 --min-prediction 5.0 --weighted-selection --sell-threshold 0.5 --sell-below 2.0 --dry-run --run-once
```

### Method 2: Direct Strategy Usage

### 1. Create a Simulation Run

First, create a simulation run and initialize it with real market data:

```bash
# Create a new simulation run
python -m src.simulation.initialization --create --market-name "Strategy 1 Test" --balance 1000 --run-name "strategy1_test"

# Initialize markets from real Polymarket data
python -m src.simulation.initialization --init-markets-from-polymarket strategy1_test
```

### 2. Run the Bidding Strategy

Execute the simulation bidding strategy:

```bash
# Run with default settings (0% threshold, $10 order size)
python -m src.simulation.bidding_decision.strategy_1 --run strategy1_test

# Run with custom threshold and order amount
python -m src.simulation.bidding_decision.strategy_1 --run strategy1_test --threshold 5.0 --amount 25.0

# Run seller to analyze and show selling opportunities
python -m src.simulation.bidding_decision.strategy_1 --sell strategy1_test --threshold 2.0

# Run seller with automatic execution
python -m src.simulation.bidding_decision.strategy_1 --sell strategy1_test --threshold 2.0 --auto-sell
```

### 3. Monitor Results

Check your simulation run status:

```bash
# View run information and current positions
python -m src.simulation.initialization --info strategy1_test
```

## Complete CLI Reference

### Primary Action Commands (mutually exclusive)

```bash
python -m src.simulation.bidding_decision.strategy_1 [ACTION] [OPTIONS]
```

**Primary Actions:**

- `--run RUN_NAME`: Execute bidding strategy on simulation run
- `--sell RUN_NAME`: Analyze and show selling opportunities for simulation run
- `--analyze RUN_NAME`: Analyze opportunities and positions without executing trades
- `--analyze-opportunities`: Analyze current market opportunities without any simulation run

### Bidding/Opportunity Parameters

- `--threshold PERCENT`: Minimum opportunity percentage required (default: 0.0%)
- `--amount DOLLARS`: Order amount in USD (default: $10.00)
- `--weighted-selection`: Use weighted selection instead of highest opportunity
- `--min-prediction PERCENT`: Minimum prediction percentage required (default: 0.0%)

### Selling Parameters

- `--sell-below PERCENT`: Sell positions with prediction below this percentage (default: 0.0%)
- `--auto-sell`: Automatically execute sell orders for recommended positions
- `--active-market-only`: Only sell positions for the active market (current time frame)

### Market Update Options

- `--no-update`: Skip updating market prices from Polymarket
- `--update-only`: Only update market prices, do not place any orders

### Execution Options

- `--dry-run`: Show what would happen without executing any trades
- `--no-stats`: Skip displaying the full comparison table

### Debug and Display Options

- `--debug`: Enable detailed debugging output
- `--verbose`, `-v`: Enable verbose logging
- `--quiet`: Reduce output to essential information only

## Usage Examples

### Basic Bidding Strategy

```bash
# Create and initialize a run
python -m src.simulation.initialization --create --market-name "Election Markets" --balance 1000 --run-name "election_strategy"
python -m src.simulation.initialization --init-markets-from-polymarket election_strategy

# Run bidding with 3% minimum opportunity threshold
python -m src.simulation.bidding_decision.strategy_1 --run election_strategy --threshold 3.0 --amount 50.0

# Check results
python -m src.simulation.initialization --info election_strategy
```

### Advanced Bidding with Weighted Selection

```bash
# Run bidding strategy with weighted selection and minimum prediction filter
python -m src.simulation.bidding_decision.strategy_1 --run election_strategy \
    --threshold 2.0 --amount 25.0 --weighted-selection --min-prediction 5.0

# Analyze what the strategy would do without executing
python -m src.simulation.bidding_decision.strategy_1 --run election_strategy \
    --threshold 3.0 --amount 50.0 --weighted-selection --dry-run --debug
```

### Selling Strategy Examples

```bash
# Analyze selling opportunities (show table and recommendations)
python -m src.simulation.bidding_decision.strategy_1 --sell election_strategy --threshold 2.0

# Sell positions with low predictions
python -m src.simulation.bidding_decision.strategy_1 --sell election_strategy \
    --sell-below 25.0 --auto-sell --dry-run

# Execute selling with opportunity threshold
python -m src.simulation.bidding_decision.strategy_1 --sell election_strategy \
    --threshold 3.0 --auto-sell --debug

# Filter for active market only
python -m src.simulation.bidding_decision.strategy_1 --sell election_strategy \
    --threshold 2.0 --active-market-only --auto-sell
```

### Analysis and Monitoring

```bash
# Analyze current market opportunities without any simulation
python -m src.simulation.bidding_decision.strategy_1 --analyze-opportunities \
    --threshold 3.0 --weighted-selection --min-prediction 5.0

# Comprehensive analysis of a simulation run
python -m src.simulation.bidding_decision.strategy_1 --analyze election_strategy \
    --threshold 2.0 --sell-below 30.0 --debug

# Quick market update only
python -m src.simulation.bidding_decision.strategy_1 --sell election_strategy --update-only
```

### Testing and Development

```bash
# Test what the strategy would do without executing
python -m src.simulation.bidding_decision.strategy_1 --run election_strategy \
    --threshold 5.0 --amount 100.0 --dry-run --verbose

# Test selling strategy with detailed output
python -m src.simulation.bidding_decision.strategy_1 --sell election_strategy \
    --threshold 2.0 --sell-below 25.0 --auto-sell --dry-run --debug

# Silent mode for scripting
python -m src.simulation.bidding_decision.strategy_1 --run election_strategy \
    --threshold 3.0 --no-stats --quiet
```

## How It Works

### 1. Market Price Updates

Before making any trading decisions, the system:

- Fetches current market prices from Polymarket
- Updates the simulation run's market data
- Marks inactive markets with 0 prices
- **Displays update progress with detailed price changes**

### 2. Statistical Analysis with Full Table Display

The system uses the same comparison table generation as the real auto bidder:

- **Generates and displays complete comparison table** with all columns
- Shows Token IDs for each market range
- Displays expected values and prediction differences
- **Shows threshold being used** and opportunity calculations
- Applies thresholds and filters identical to real system

### 3. Simulated Trading

Instead of placing real orders:

- Updates the simulation JSON file with new positions
- Records all transactions with timestamps
- Updates balance and position values
- Tracks profit/loss for each trade
- **Shows detailed order information** in dry-run mode

### 4. Enhanced Position Management

The selling strategy:

- **Always updates market prices first** (like real auto_bid)
- **Displays full comparison table** before analysis
- Analyzes current positions against opportunities
- Supports both opportunity-based and prediction-based selling
- **Shows recommendations table** with detailed position information
- Executes simulated sell orders with profit/loss calculation

## Workflow Examples

### Complete Trading Session

```bash
# 1. Initialize simulation
python -m src.simulation.initialization --create --market-name "Trading Session" --balance 2000 --run-name "session1"
python -m src.simulation.initialization --init-markets-from-polymarket session1

# 2. Execute buying strategy
python -m src.simulation.bidding_decision.strategy_1 --run session1 \
    --threshold 3.0 --amount 50.0 --weighted-selection --min-prediction 10.0

# 3. Monitor and analyze
python -m src.simulation.bidding_decision.strategy_1 --analyze session1 --debug

# 4. Execute selling strategy
python -m src.simulation.bidding_decision.strategy_1 --sell session1 \
    --threshold 2.0 --sell-below 20.0 --auto-sell

# 5. Check final results
python -m src.simulation.initialization --info session1
```

### Market Opportunity Analysis

```bash
# Real-time market analysis without simulation
python -m src.simulation.bidding_decision.strategy_1 --analyze-opportunities \
    --threshold 2.0 --min-prediction 5.0 --debug

# Compare with simulation analysis
python -m src.simulation.bidding_decision.strategy_1 --analyze existing_run \
    --threshold 2.0 --debug
```

## Configuration

The system now **perfectly matches** all configuration options from the real bidding system:

- **Threshold**: Minimum opportunity percentage to trigger trades
- **Order Amount**: Fixed USD amount per trade
- **Weighted Selection**: Probabilistic choice from multiple opportunities
- **Minimum Prediction**: Filter opportunities below prediction threshold
- **Sell Below**: Exit positions with predictions below threshold
- **Auto-sell**: Automatic execution vs. recommendation display
- **Active Market Only**: Filter for current time frame markets

## Integration with Real System

This simulation system is designed to:

- **Use identical logic** to the real auto bidder
- **Match CLI options exactly** for easy transition
- **Display same tables and information** as real system
- Allow strategy testing without financial risk
- Validate trading algorithms before live deployment
- Analyze historical performance scenarios

## Safety Features

- **No Real Trading**: All operations are simulation-only
- **Balance Protection**: Prevents orders exceeding available funds
- **Market Validation**: Ensures markets exist before trading
- **Transaction Logging**: Complete audit trail of all operations
- **Dry Run Mode**: Test strategies without any changes
- **Table Display**: Always shows what the system is analyzing

## Troubleshooting

### Common Issues

1. **"No opportunities found"**: Lower the threshold or check if markets are active
2. **"Insufficient funds"**: Check simulation balance or reduce order amounts
3. **"Market not found"**: Ensure markets are properly initialized
4. **"Connection errors"**: Real price updates require internet connection
5. **"No positions to sell"**: Check if you have positions or adjust sell criteria

### Debug Mode

Enable detailed logging with `--debug` to see:

- Market price update process with detailed changes
- Complete comparison table with Token IDs
- Opportunity calculation details and filtering
- Position matching logic and sell criteria
- Trade execution steps with order details
- Balance and position changes

### Verbose Output

Use `--verbose` or `-v` for enhanced logging:

- Shows all HTTP requests to Polymarket
- Displays detailed market update progress
- Shows statistical calculation steps
- Provides complete position analysis

## Comparison with Real Auto-Bid

| Feature           | Real Auto-Bid            | Simulation System       |
| ----------------- | ------------------------ | ----------------------- |
| CLI Options       | ✅ Complete              | ✅ **Identical**        |
| Table Display     | ✅ Full comparison table | ✅ **Identical**        |
| Market Updates    | ✅ Live prices           | ✅ **Same API calls**   |
| Order Execution   | ✅ Real trades           | ✅ **Simulated trades** |
| Position Analysis | ✅ Real positions        | ✅ **Same logic**       |
| Debug Output      | ✅ Detailed logs         | ✅ **Same format**      |
| Safety Features   | ✅ Real money risk       | ✅ **No risk**          |

The simulation system now provides a **perfect testing environment** for the real auto-bid system with identical behavior and zero financial risk.
