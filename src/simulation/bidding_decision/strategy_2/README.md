# Simulation Strategy 2 - Bidding Decision System with Stop Loss

This package provides a simulation-based bidding decision system that replicates the real-world auto bidding functionality but operates on simulated JSON data instead of making actual trades. **Strategy 2 includes advanced stop loss functionality** for automated risk management.

## Overview

The simulation strategy uses the same statistical analysis as the real `src/bidding_decision/auto_bid` system but:

- Updates market prices from real Polymarket data before making decisions
- Executes "trades" in simulation JSON files instead of real markets
- Tracks all positions, transactions, and balance changes in the simulation
- **Matches real auto_bid behavior exactly** with identical CLI options and table display
- **🛑 Includes comprehensive stop loss functionality** for automated risk management

## Features

- **Real Market Analysis**: Uses the same comparison table generation as the real system
- **Complete Table Display**: Shows full comparison table with Token IDs and expected values
- **Simulation Trading**: Executes buy/sell decisions in JSON simulation files
- **Market Price Updates**: Automatically updates market prices before trading decisions
- **Position Management**: Tracks all positions and their performance
- **Risk Management**: Applies the same thresholds and filters as the real system
- **Auto-Sell Functionality**: Automatically execute sell orders with `--auto-sell`
- **Weighted Selection**: Probabilistic selection from multiple opportunities
- **🛑 Stop Loss System**: Automated position management with configurable thresholds
- **🛑 Profit Taking**: Automatic profit realization at specified gain levels
- **🛑 Loss Protection**: Automatic position reduction/liquidation at loss thresholds
- **🛑 History Tracking**: Complete audit trail of all stop loss actions

## 🛑 Stop Loss Functionality

### Stop Loss Overview

Strategy 2 includes a comprehensive **automated stop loss system** that manages risk by automatically selling positions when they reach predefined profit or loss thresholds. This feature helps protect against large losses and lock in profits.

### Default Stop Loss Configuration

```
Loss Thresholds (Stop Loss Protection):
- Sell 50% of position at -40% loss (partial protection)
- Sell 100% of position at -60% loss (full liquidation)

Gain Thresholds (Profit Taking):
- Sell 40% of position at +40% gain (initial profit taking)
- Sell 40% of position at +80% gain (additional profit taking)
```

### Stop Loss Features

- **🔒 Loss Protection**: Automatically reduce or liquidate losing positions
- **💰 Profit Taking**: Lock in gains at specified profit levels
- **⚙️ Fully Configurable**: All thresholds and sell percentages are customizable
- **📚 History Tracking**: Complete audit trail with timestamps and reasoning
- **🧪 Dry Run Mode**: Test stop loss logic without executing trades
- **🔄 Duplicate Prevention**: Prevents re-execution of previously triggered stops
- **📊 Detailed Analysis**: Shows current P&L and trigger analysis
- **🔗 Integrated**: Seamlessly works with regular selling strategy

### Stop Loss Usage Examples

#### Basic Stop Loss Commands

```bash
# Execute stop loss with default thresholds
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name>

# Test stop loss logic first (RECOMMENDED)
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> --dry-run

# Detailed stop loss analysis and execution
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> --debug

# View stop loss history only
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> --dry-run
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

# Profit-focused strategy (minimal loss protection, aggressive profit taking)
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> \
    --loss-threshold-1 -80.0 --loss-sell-1 100.0 \
    --loss-threshold-2 -95.0 --loss-sell-2 100.0 \
    --gain-threshold-1 10.0 --gain-sell-1 30.0 \
    --gain-threshold-2 25.0 --gain-sell-2 40.0
```

### Stop Loss CLI Parameters

```bash
# Loss threshold parameters
--loss-threshold-1 PERCENT    # First loss threshold (default: -40.0%)
--loss-sell-1 PERCENT         # Percentage to sell at first loss (default: 50.0%)
--loss-threshold-2 PERCENT    # Second loss threshold (default: -60.0%)
--loss-sell-2 PERCENT         # Percentage to sell at second loss (default: 100.0%)

# Gain threshold parameters
--gain-threshold-1 PERCENT    # First gain threshold (default: 40.0%)
--gain-sell-1 PERCENT         # Percentage to sell at first gain (default: 40.0%)
--gain-threshold-2 PERCENT    # Second gain threshold (default: 80.0%)
--gain-sell-2 PERCENT         # Percentage to sell at second gain (default: 40.0%)

# Execution and testing options
--dry-run                     # Test mode - shows what would happen
--debug                       # Detailed analysis and execution information
```

### Stop Loss Integration with Selling Strategy

The stop loss system is **automatically integrated** with the regular selling strategy:

```bash
# Selling strategy checks stop loss first, then regular opportunities
python -m src.simulation.bidding_decision.strategy_2 --sell <run_name> --auto-sell

# The workflow is:
# 1. Update market prices
# 2. Check and execute stop loss triggers
# 3. Analyze regular selling opportunities
# 4. Execute regular sells if requested

# Disable stop loss integration if needed (not recommended)
python -m src.simulation.bidding_decision.strategy_2 --sell <run_name> --auto-sell \
    --loss-threshold-1 -999 --loss-threshold-2 -999 \
    --gain-threshold-1 999 --gain-threshold-2 999
```

### Complete Stop Loss Workflow

```bash
# 1. Create simulation with stop loss management
python -m src.simulation.initialization --create --market-name "Risk Managed Strategy" \
    --balance 1000 --run-name "risk_managed"

# 2. Initialize with real market data
python -m src.simulation.initialization --init-markets-from-polymarket risk_managed

# 3. Execute bidding strategy
python -m src.simulation.bidding_decision.strategy_2 --run risk_managed \
    --threshold 2.0 --amount 50.0 --weighted-selection

# 4. Test stop loss configuration first
python -m src.simulation.bidding_decision.strategy_2 --stop-loss risk_managed --dry-run --debug

# 5. Execute stop loss with custom thresholds
python -m src.simulation.bidding_decision.strategy_2 --stop-loss risk_managed \
    --loss-threshold-1 -30.0 --gain-threshold-1 30.0

# 6. Regular selling with integrated stop loss
python -m src.simulation.bidding_decision.strategy_2 --sell risk_managed \
    --threshold 1.0 --auto-sell

# 7. Check results and stop loss history
python -m src.simulation.initialization --info risk_managed
python -m src.simulation.bidding_decision.strategy_2 --stop-loss risk_managed --dry-run
```

### Advanced Stop Loss Scenarios

#### Multiple Stop Loss Executions

```bash
# Execute stop loss, wait for market changes, execute again
python -m src.simulation.bidding_decision.strategy_2 --stop-loss risk_managed

# ... market moves, prices change ...

python -m src.simulation.bidding_decision.strategy_2 --stop-loss risk_managed
# Only NEW triggers are executed, previous ones are tracked in history
```

#### Stop Loss Monitoring and Analysis

```bash
# Detailed analysis of current positions vs stop loss thresholds
python -m src.simulation.bidding_decision.strategy_2 --stop-loss <run_name> \
    --dry-run --debug

# Shows:
# - Current win/loss percentage for each position
# - Which positions would trigger stop loss
# - Exact number of shares that would be sold
# - Reasoning for each stop loss decision
# - Complete stop loss history
```

## File Structure

```
src/simulation/bidding_decision/strategy_2/
├── README.md                    # This documentation
├── simulation_bidder.py         # Main simulation bidder class
├── simulation_seller.py         # Position selling logic (with stop loss integration)
├── stop_loss_manager.py         # 🛑 Complete stop loss functionality
└── __main__.py                  # CLI interface (with stop loss commands)
```

## Quick Start

### Method 1: Complete Scheduler-Based Simulation (Recommended)

Run the full trading simulation with scheduler integration:

```bash
# Complete trading simulation with strategy_2
python -m src.scheduler.scheduler --strategy strategy_2 --algorithm ensemble --random-seed 42 --use-csv-getter --get-tweet-count-first --tweet-interval 110 --buy-interval 60 --sell-interval 5 --simulate pirvelad09231 --sim-balance 144 --amount 1.0 --buy-threshold 1.0 --min-prediction 5.0 --weighted-selection --sell-threshold 0.5 --sell-below 2.0

# With dry-run for testing
python -m src.scheduler.scheduler --strategy strategy_2 --algorithm ensemble --random-seed 42 --use-csv-getter --get-tweet-count-first --tweet-interval 110 --buy-interval 60 --sell-interval 5 --simulate pirvelad09231 --sim-balance 144 --amount 1.0 --buy-threshold 1.0 --min-prediction 5.0 --weighted-selection --sell-threshold 0.5 --sell-below 2.0 --dry-run --run-once
```

### Method 2: Direct Strategy Usage

### 1. Create a Simulation Run

First, create a simulation run and initialize it with real market data:

```bash
# Create a new simulation run
python -m src.simulation.initialization --create --market-name "Strategy 2 Test" --balance 1000 --run-name "strategy2_test"

# Initialize markets from real Polymarket data
python -m src.simulation.initialization --init-markets-from-polymarket strategy2_test
```

### 2. Run the Bidding Strategy

Execute the simulation bidding strategy:

```bash
# Run with default settings (0% threshold, $10 order size)
python -m src.simulation.bidding_decision.strategy_2 --run strategy2_test

# Run with custom threshold and order amount
python -m src.simulation.bidding_decision.strategy_2 --run strategy2_test --threshold 5.0 --amount 25.0

# Run seller to analyze and show selling opportunities
python -m src.simulation.bidding_decision.strategy_2 --sell strategy2_test --threshold 2.0

# Run seller with automatic execution
python -m src.simulation.bidding_decision.strategy_2 --sell strategy2_test --threshold 2.0 --auto-sell
```

### 3. Monitor Results

Check your simulation run status:

```bash
# View run information and current positions
python -m src.simulation.initialization --info strategy2_test
```

## Complete CLI Reference

### Primary Action Commands (mutually exclusive)

```bash
python -m src.simulation.bidding_decision.strategy_2 [ACTION] [OPTIONS]
```

**Primary Actions:**

- `--run RUN_NAME`: Execute bidding strategy on simulation run
- `--sell RUN_NAME`: Analyze and show selling opportunities for simulation run
- `--analyze RUN_NAME`: Analyze opportunities and positions without executing trades
- `--analyze-opportunities`: Analyze current market opportunities without any simulation run
- `--stop-loss RUN_NAME`: Execute stop loss orders for positions that have triggered thresholds

### Bidding/Opportunity Parameters

- `--threshold PERCENT`: Minimum opportunity percentage required (default: 0.0%)
- `--amount DOLLARS`: Order amount in USD (default: $10.00)
- `--weighted-selection`: Use weighted selection instead of highest opportunity
- `--min-prediction PERCENT`: Minimum prediction percentage required (default: 0.0%)

### Selling Parameters

- `--sell-below PERCENT`: Sell positions with prediction below this percentage (default: 0.0%)
- `--auto-sell`: Automatically execute sell orders for recommended positions
- `--active-market-only`: Only sell positions for the active market (current time frame)

### Stop Loss Parameters

- `--loss-threshold-1 PERCENT`: First loss threshold percentage (default: -40.0%)
- `--loss-sell-1 PERCENT`: Percentage to sell at first loss threshold (default: 50.0%)
- `--loss-threshold-2 PERCENT`: Second loss threshold percentage (default: -60.0%)
- `--loss-sell-2 PERCENT`: Percentage to sell at second loss threshold (default: 100.0%)
- `--gain-threshold-1 PERCENT`: First gain threshold percentage (default: 40.0%)
- `--gain-sell-1 PERCENT`: Percentage to sell at first gain threshold (default: 40.0%)
- `--gain-threshold-2 PERCENT`: Second gain threshold percentage (default: 80.0%)
- `--gain-sell-2 PERCENT`: Percentage to sell at second gain threshold (default: 40.0%)

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
python -m src.simulation.bidding_decision.strategy_2 --run election_strategy --threshold 3.0 --amount 50.0

# Check results
python -m src.simulation.initialization --info election_strategy
```

### Advanced Bidding with Weighted Selection

```bash
# Run bidding strategy with weighted selection and minimum prediction filter
python -m src.simulation.bidding_decision.strategy_2 --run election_strategy \
    --threshold 2.0 --amount 25.0 --weighted-selection --min-prediction 5.0

# Analyze what the strategy would do without executing
python -m src.simulation.bidding_decision.strategy_2 --run election_strategy \
    --threshold 3.0 --amount 50.0 --weighted-selection --dry-run --debug
```

### Selling Strategy Examples

```bash
# Analyze selling opportunities (show table and recommendations)
python -m src.simulation.bidding_decision.strategy_2 --sell election_strategy --threshold 2.0

# Sell positions with low predictions
python -m src.simulation.bidding_decision.strategy_2 --sell election_strategy \
    --sell-below 25.0 --auto-sell --dry-run

# Execute selling with opportunity threshold
python -m src.simulation.bidding_decision.strategy_2 --sell election_strategy \
    --threshold 3.0 --auto-sell --debug

# Filter for active market only
python -m src.simulation.bidding_decision.strategy_2 --sell election_strategy \
    --threshold 2.0 --active-market-only --auto-sell
```

### 🛑 Stop Loss Strategy Examples

```bash
# Basic stop loss execution with default thresholds
python -m src.simulation.bidding_decision.strategy_2 --stop-loss election_strategy

# Test stop loss logic before execution (RECOMMENDED)
python -m src.simulation.bidding_decision.strategy_2 --stop-loss election_strategy --dry-run

# Conservative stop loss (tighter risk management)
python -m src.simulation.bidding_decision.strategy_2 --stop-loss election_strategy \
    --loss-threshold-1 -25.0 --loss-sell-1 40.0 \
    --gain-threshold-1 25.0 --gain-sell-1 30.0 --debug

# Aggressive stop loss (wider risk tolerance)
python -m src.simulation.bidding_decision.strategy_2 --stop-loss election_strategy \
    --loss-threshold-1 -70.0 --loss-sell-1 80.0 \
    --gain-threshold-1 70.0 --gain-sell-1 60.0

# Profit-focused strategy (tight profit taking, wide loss tolerance)
python -m src.simulation.bidding_decision.strategy_2 --stop-loss election_strategy \
    --loss-threshold-1 -90.0 --loss-sell-1 100.0 \
    --gain-threshold-1 15.0 --gain-sell-1 50.0 \
    --gain-threshold-2 30.0 --gain-sell-2 50.0

# View stop loss history and current analysis
python -m src.simulation.bidding_decision.strategy_2 --stop-loss election_strategy --dry-run --debug
```

### Analysis and Monitoring

```bash
# Analyze current market opportunities without any simulation
python -m src.simulation.bidding_decision.strategy_2 --analyze-opportunities \
    --threshold 3.0 --weighted-selection --min-prediction 5.0

# Comprehensive analysis of a simulation run
python -m src.simulation.bidding_decision.strategy_2 --analyze election_strategy \
    --threshold 2.0 --sell-below 30.0 --debug

# Quick market update only
python -m src.simulation.bidding_decision.strategy_2 --sell election_strategy --update-only
```

### Testing and Development

```bash
# Test what the strategy would do without executing
python -m src.simulation.bidding_decision.strategy_2 --run election_strategy \
    --threshold 5.0 --amount 100.0 --dry-run --verbose

# Test selling strategy with detailed output
python -m src.simulation.bidding_decision.strategy_2 --sell election_strategy \
    --threshold 2.0 --sell-below 25.0 --auto-sell --dry-run --debug

# Test stop loss with very sensitive thresholds
python -m src.simulation.bidding_decision.strategy_2 --stop-loss election_strategy \
    --loss-threshold-1 -1.0 --gain-threshold-1 1.0 --dry-run --debug

# Silent mode for scripting
python -m src.simulation.bidding_decision.strategy_2 --run election_strategy \
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

### 4. Enhanced Position Management with Stop Loss

The selling strategy:

- **Always updates market prices first** (like real auto_bid)
- **Automatically checks stop loss triggers** before regular selling analysis
- **Displays full comparison table** before analysis
- Analyzes current positions against opportunities
- Supports both opportunity-based and prediction-based selling
- **Shows recommendations table** with detailed position information
- Executes simulated sell orders with profit/loss calculation
- **Tracks stop loss history** to prevent duplicate executions

## Workflow Examples

### Complete Trading Session with Stop Loss

```bash
# 1. Initialize simulation with stop loss management
python -m src.simulation.initialization --create --market-name "Risk Managed Session" --balance 2000 --run-name "session1"
python -m src.simulation.initialization --init-markets-from-polymarket session1

# 2. Execute buying strategy
python -m src.simulation.bidding_decision.strategy_2 --run session1 \
    --threshold 3.0 --amount 50.0 --weighted-selection --min-prediction 10.0

# 3. Monitor positions and test stop loss
python -m src.simulation.bidding_decision.strategy_2 --stop-loss session1 --dry-run --debug

# 4. Execute stop loss with custom thresholds
python -m src.simulation.bidding_decision.strategy_2 --stop-loss session1 \
    --loss-threshold-1 -30.0 --gain-threshold-1 30.0

# 5. Execute selling strategy (includes automatic stop loss check)
python -m src.simulation.bidding_decision.strategy_2 --sell session1 \
    --threshold 2.0 --sell-below 20.0 --auto-sell

# 6. Check final results and stop loss history
python -m src.simulation.initialization --info session1
python -m src.simulation.bidding_decision.strategy_2 --stop-loss session1 --dry-run
```

### Market Opportunity Analysis

```bash
# Real-time market analysis without simulation
python -m src.simulation.bidding_decision.strategy_2 --analyze-opportunities \
    --threshold 2.0 --min-prediction 5.0 --debug

# Compare with simulation analysis
python -m src.simulation.bidding_decision.strategy_2 --analyze existing_run \
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
- **🛑 Stop Loss Thresholds**: Configurable loss and gain thresholds for automatic position management
- **🛑 Stop Loss Integration**: Seamless integration with regular selling strategy

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
- **🛑 Stop Loss Protection**: Automated risk management with configurable thresholds
- **🛑 History Tracking**: Prevents duplicate stop loss executions

## Troubleshooting

### Common Issues

1. **"No opportunities found"**: Lower the threshold or check if markets are active
2. **"Insufficient funds"**: Check simulation balance or reduce order amounts
3. **"Market not found"**: Ensure markets are properly initialized
4. **"Connection errors"**: Real price updates require internet connection
5. **"No positions to sell"**: Check if you have positions or adjust sell criteria
6. **🛑 "No stop loss triggers found"**: Check position P&L values and adjust thresholds if needed

### Stop Loss Issues

#### Stop Loss Not Triggering

```bash
# Check current position P&L and thresholds
python -m src.simulation.bidding_decision.strategy_2 --stop-loss RUN_NAME --dry-run --debug

# Update market prices to get current P&L values
python -m src.simulation.initialization --update-markets-from-polymarket RUN_NAME
python -m src.simulation.bidding_decision.strategy_2 --stop-loss RUN_NAME --dry-run
```

#### Stop Loss Already Executed

```bash
# View stop loss history to see previous actions
python -m src.simulation.bidding_decision.strategy_2 --stop-loss RUN_NAME --dry-run

# System prevents duplicate executions - check history section
```

#### Testing Stop Loss Logic

```bash
# Test with very sensitive thresholds to verify functionality
python -m src.simulation.bidding_decision.strategy_2 --stop-loss RUN_NAME \
    --loss-threshold-1 -1.0 --gain-threshold-1 1.0 --dry-run --debug

# This should show which positions would trigger if they had 1% gain/loss
```

### Debug Mode

Enable detailed logging with `--debug` to see:

- Market price update process with detailed changes
- Complete comparison table with Token IDs
- Opportunity calculation details and filtering
- Position matching logic and sell criteria
- Trade execution steps with order details
- Balance and position changes
- **🛑 Stop loss analysis with current P&L values**
- **🛑 Stop loss trigger logic and reasoning**
- **🛑 Stop loss history and duplicate prevention**

## Comparison with Real Auto-Bid

| Feature           | Real Auto-Bid            | Simulation System         |
| ----------------- | ------------------------ | ------------------------- |
| CLI Options       | ✅ Complete              | ✅ **Identical**          |
| Table Display     | ✅ Full comparison table | ✅ **Identical**          |
| Market Updates    | ✅ Live prices           | ✅ **Same API calls**     |
| Order Execution   | ✅ Real trades           | ✅ **Simulated trades**   |
| Position Analysis | ✅ Real positions        | ✅ **Same logic**         |
| Debug Output      | ✅ Detailed logs         | ✅ **Same format**        |
| Safety Features   | ✅ Real money risk       | ✅ **No risk**            |
| 🛑 Stop Loss      | ❌ Not available         | ✅ **Full functionality** |

The simulation system now provides a **perfect testing environment** for the real auto-bid system with identical behavior, zero financial risk, **and advanced stop loss functionality**.
