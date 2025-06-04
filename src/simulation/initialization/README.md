# Polymarket Simulation Initialization

This module provides tools for initializing and managing Polymarket trading simulations. It creates structured simulation runs with comprehensive tracking of balances, positions, transactions, and market data with proper bid/ask pricing.

## Features

- ✅ **Create simulation runs** with initial market and balance setup
- ✅ **Market management** - create markets with bid/ask pricing and price history
- ✅ **Position management** - buy at ask price, sell at bid price
- ✅ **Balance management** - add/remove funds with transaction tracking
- ✅ **Price updates** - update market prices (price/bid/ask) with historical tracking
- ✅ **Portfolio tracking** - real-time balance and position monitoring with proper P&L
- ✅ **Transaction history** - complete audit trail of all activities
- ✅ **Command-line interface** - easy-to-use CLI for all operations

## Important Workflow

**⚠️ Markets must be created BEFORE positions can be added!**

1. Create a simulation run
2. Create markets with initial pricing
3. Add positions (buy shares at ask price)
4. Update market prices as needed
5. Sell positions (sell shares at bid price)

## Installation & Setup

```bash
# Navigate to project root
cd /path/to/polymarket_algo

# Activate virtual environment
source venv/bin/activate

# The module is ready to use via CLI
python -m src.simulation.initialization --help
```

## Quick Start

### 1. Create a New Simulation Run

```bash
# Create with default name (timestamp-based)
python -m src.simulation.initialization --create --market "2024 Election" --balance 10000

# Create with custom name
python -m src.simulation.initialization --create --market "Crypto Predictions" --balance 5000 --name "crypto_v1"
```

### 2. Create Markets (Required Before Trading)

```bash
# Create a prediction market
python -m src.simulation.initialization --create-market \
  --run "crypto_v1" \
  --market-id "0x123abc" \
  --market-name "Trump Wins 2024" \
  --category "prediction" \
  --initial-price 0.65 \
  --bid-price 0.64 \
  --ask-price 0.66

# Create another market
python -m src.simulation.initialization --create-market \
  --run "crypto_v1" \
  --market-id "0x456def" \
  --market-name "Bitcoin $100k" \
  --category "crypto" \
  --initial-price 0.45 \
  --bid-price 0.44 \
  --ask-price 0.46
```

### 3. Add Positions (Buy Shares)

```bash
# Buy shares at current ask price
python -m src.simulation.initialization --add-position \
  --run "crypto_v1" \
  --market-id "0x123abc" \
  --shares 100

# Buy fractional shares
python -m src.simulation.initialization --add-position \
  --run "crypto_v1" \
  --market-id "0x456def" \
  --shares 50.5
```

### 4. Update Market Prices

```bash
# Update prices with new bid/ask spreads
python -m src.simulation.initialization --update-prices \
  --run "crypto_v1" \
  --price-data '{
    "0x123abc": {"price": 0.70, "bid": 0.69, "ask": 0.71},
    "0x456def": {"price": 0.48, "bid": 0.47, "ask": 0.49}
  }'
```

### 5. Sell Positions

```bash
# Sell shares at current bid price
python -m src.simulation.initialization --sell-position \
  --run "crypto_v1" \
  --market-id "0x123abc" \
  --shares 50
```

## Core Operations

### Market Management

#### Create Markets

```bash
# Create a new market (required before trading)
python -m src.simulation.initialization --create-market \
  --run "my_run" \
  --market-id "0x789ghi" \
  --market-name "Ethereum $5000" \
  --category "crypto" \
  --description "ETH reaches $5000 by end of year" \
  --initial-price 0.30 \
  --bid-price 0.29 \
  --ask-price 0.31
```

#### Update Market Prices

```bash
# Update from JSON file
echo '{
  "0x123abc": {"price": 0.75, "bid": 0.74, "ask": 0.76},
  "0x456def": {"price": 0.40, "bid": 0.39, "ask": 0.41}
}' > prices.json

python -m src.simulation.initialization --update-prices \
  --run "my_run" \
  --price-file "prices.json"

# Update from command line
python -m src.simulation.initialization --update-prices \
  --run "my_run" \
  --price-data '{"0x123abc": {"price": 0.75, "bid": 0.74, "ask": 0.76}}'
```

### Position Management

#### Buy Shares (at Ask Price)

```bash
# Add new position - purchases at current ask price
python -m src.simulation.initialization --add-position \
  --run "my_run" \
  --market-id "0x123abc" \
  --shares 100

# Allow negative balance (overdraft)
python -m src.simulation.initialization --add-position \
  --run "my_run" \
  --market-id "0x456def" \
  --shares 200 \
  --allow-negative
```

#### Sell Shares (at Bid Price)

```bash
# Partial sale - sells at current bid price
python -m src.simulation.initialization --sell-position \
  --run "my_run" \
  --market-id "0x123abc" \
  --shares 50

# Sell entire position
python -m src.simulation.initialization --sell-position \
  --run "my_run" \
  --market-id "0x123abc" \
  --shares 100
```

### Balance Management

#### Add Balance

```bash
# Add funds with description
python -m src.simulation.initialization --add-balance \
  --run "my_run" \
  --amount 1000 \
  --description "Additional funding"

# Add without custom description
python -m src.simulation.initialization --add-balance \
  --run "my_run" \
  --amount 500
```

#### Remove Balance

```bash
# Remove funds (respects available balance)
python -m src.simulation.initialization --remove-balance \
  --run "my_run" \
  --amount 500 \
  --description "Withdrawal"

# Force removal (allow negative balance)
python -m src.simulation.initialization --remove-balance \
  --run "my_run" \
  --amount 2000 \
  --allow-negative \
  --description "Emergency withdrawal"
```

## JSON Data Structure

Each simulation run creates a `simulation_data.json` file with the following structure:

```json
{
  "whole_market_name": "2024 Election",
  "run_id": "uuid-string",
  "run_name": "run_20241215_143022",
  "start_time": "2024-12-15T14:30:22.123456",
  "current_balance": 8500.0,
  "initial_balance": 10000.0,
  "total_balance": 9750.0,
  "balance_of_shares": 1250.0,
  "balance_invested": 1200.0,
  "shares": [
    {
      "market_id": "0x123abc",
      "market_name": "Trump Wins 2024",
      "num_shares": 150.0
    }
  ],
  "transactions": [
    {
      "timestamp": "2024-12-15T14:30:22.123456",
      "type": "BUY",
      "market_id": "0x123abc",
      "market_name": "Trump Wins 2024",
      "num_shares": 100.0,
      "price_per_share": 0.66,
      "total_amount": 66.0
    },
    {
      "timestamp": "2024-12-15T14:35:10.654321",
      "type": "SELL",
      "market_id": "0x123abc",
      "market_name": "Trump Wins 2024",
      "num_shares": 50.0,
      "price_per_share": 0.69,
      "total_amount": 34.5,
      "cost_basis": 33.0,
      "profit_loss": 1.5
    },
    {
      "timestamp": "2024-12-15T14:40:00.789012",
      "type": "BALANCE_ADD",
      "description": "Additional funding",
      "amount": 1000.0,
      "balance_after": 9535.0
    }
  ],
  "total_balances": [
    {
      "timestamp": "2024-12-15T14:30:22.123456",
      "total_balance": 10000.0,
      "current_balance": 10000.0,
      "balance_of_shares": 0.0,
      "balance_invested": 0.0,
      "total_market_value": 0.0
    }
  ],
  "positions": [
    {
      "market_id": "0x123abc",
      "market_name": "Trump Wins 2024",
      "current_price_per_share": 0.7,
      "num_shares": 150.0,
      "current_total_price": 105.0,
      "current_value_if_sold": 103.5,
      "initial_price_per_share": 0.66,
      "initial_total_price": 99.0,
      "total_invested": 99.0,
      "win_loss_percentage": 6.06
    }
  ],
  "markets": [
    {
      "market_id": "0x123abc",
      "market_name": "Trump Wins 2024",
      "description": "Market for Trump Wins 2024",
      "category": "prediction",
      "initial_price": 0.65,
      "current_price": 0.7,
      "current_bid": 0.69,
      "current_ask": 0.71,
      "price_history": [
        {
          "timestamp": "2024-12-15T14:30:22.123456",
          "price": 0.65,
          "bid": 0.64,
          "ask": 0.66
        },
        {
          "timestamp": "2024-12-15T14:35:00.789012",
          "price": 0.7,
          "bid": 0.69,
          "ask": 0.71
        }
      ]
    }
  ]
}
```

## Key Features Explained

### Market-First Architecture

- **Markets must exist** before positions can be created
- **Bid/Ask spreads** - realistic trading with proper pricing
- **Price history** - complete tracking of all price movements

### Trading Logic

- **Buy orders** execute at current **ask price**
- **Sell orders** execute at current **bid price**
- **Realistic spreads** simulate real market conditions

### Position Calculations

- **Initial price** never changes (preserves cost basis)
- **Current price** always matches market price
- **Total invested** tracks actual money spent
- **Current value if sold** uses current bid price
- **Win/Loss %** = (current_market_value - total_invested) / total_invested × 100

### Balance Tracking

- **Current Balance**: Available cash for trading
- **Balance of Shares**: Current market value of all positions (changes with market prices)
- **Balance Invested**: Total amount actually spent on positions (remains constant)
- **Total Balance**: Current cash + current market value of positions
- **Profit/Loss**: Balance of Shares - Balance Invested

### Balance Protection

- **Default**: Prevents transactions that would result in negative balance
- **Override**: Use `--allow-negative` flag to permit overdrafts
- **Tracking**: All balance changes are logged with timestamps

### Position Merging

- **Smart Merging**: Adding shares to existing positions maintains separate cost basis tracking
- **Proportional Sales**: Selling shares uses proportional cost basis calculation

## Directory Structure

```
src/simulation/
├── initialization/
│   ├── __init__.py              # Package initialization
│   ├── __main__.py              # CLI interface
│   ├── run_initializer.py       # Core RunInitializer class
│   └── README.md                # This documentation
└── runs/                        # Created automatically
    ├── run_20241215_143022/
    │   └── simulation_data.json
    ├── crypto_v1/
    │   └── simulation_data.json
    └── ...
```

## Python API Usage

```python
from src.simulation.initialization import RunInitializer

# Initialize
initializer = RunInitializer()

# Create new run
run_info = initializer.create_new_run(
    market_name="2024 Election",
    initial_balance=10000.0,
    run_name="my_simulation"
)

# Create market
success = initializer.create_market(
    run_name="my_simulation",
    market_id="0x123abc",
    market_name="Trump Wins 2024",
    description="Presidential election prediction",
    category="prediction",
    initial_price=0.65,
    bid_price=0.64,
    ask_price=0.66
)

# Add position (buys at ask price)
success = initializer.add_position(
    run_name="my_simulation",
    market_id="0x123abc",
    num_shares=100.0,
    allow_negative_balance=False
)

# Update prices
price_updates = {
    "0x123abc": {
        "price": 0.70,
        "bid": 0.69,
        "ask": 0.71
    }
}
initializer.update_market_prices("my_simulation", price_updates)

# Sell position (sells at bid price)
initializer.sell_position(
    run_name="my_simulation",
    market_id="0x123abc",
    num_shares=50.0
)

# Add balance
initializer.add_balance(
    run_name="my_simulation",
    amount=1000.0,
    description="Additional funding"
)

# List runs
runs = initializer.list_runs()
print(f"Available runs: {runs}")

# Get run info
run_data = initializer.get_run_info("my_simulation")
print(f"Current balance: ${run_data['current_balance']}")
```

## Error Handling

The module includes comprehensive error handling:

- **Market Validation**: Ensures markets exist before allowing position creation
- **File Validation**: Checks for run existence before operations
- **Balance Validation**: Prevents insufficient fund transactions (unless overridden)
- **Input Validation**: Validates amounts, shares, and other inputs
- **JSON Safety**: Graceful handling of malformed JSON files

## Complete Example Workflow

```bash
# 1. Create a new simulation run
python -m src.simulation.initialization --create --market "Crypto Markets" --balance 10000 --name "crypto_sim"

# 2. Create markets
python -m src.simulation.initialization --create-market \
  --run "crypto_sim" \
  --market-id "0x001" \
  --market-name "Bitcoin $100k" \
  --category "crypto" \
  --initial-price 0.30 \
  --bid-price 0.29 \
  --ask-price 0.31

python -m src.simulation.initialization --create-market \
  --run "crypto_sim" \
  --market-id "0x002" \
  --market-name "Ethereum $5k" \
  --category "crypto" \
  --initial-price 0.45 \
  --bid-price 0.44 \
  --ask-price 0.46

# 3. Buy positions (at ask prices)
python -m src.simulation.initialization --add-position \
  --run "crypto_sim" \
  --market-id "0x001" \
  --shares 100

python -m src.simulation.initialization --add-position \
  --run "crypto_sim" \
  --market-id "0x002" \
  --shares 75.5

# 4. Update market prices
python -m src.simulation.initialization --update-prices \
  --run "crypto_sim" \
  --price-data '{
    "0x001": {"price": 0.35, "bid": 0.34, "ask": 0.36},
    "0x002": {"price": 0.50, "bid": 0.49, "ask": 0.51}
  }'

# 5. Check status
python -m src.simulation.initialization --info "crypto_sim"

# 6. Sell some positions (at bid prices)
python -m src.simulation.initialization --sell-position \
  --run "crypto_sim" \
  --market-id "0x001" \
  --shares 50

# 7. Add more funding
python -m src.simulation.initialization --add-balance \
  --run "crypto_sim" \
  --amount 2000 \
  --description "Quarterly allocation"
```

## Troubleshooting

### Common Issues

1. **Market not found**: Create the market first using `--create-market`
2. **Run not found**: Ensure run name is correct, check with `--list`
3. **Insufficient funds**: Use `--allow-negative` if overdraft needed
4. **Permission errors**: Check file permissions in runs directory
5. **JSON errors**: Validate JSON syntax in price data

### Debug Commands

```bash
# Check run status
python -m src.simulation.initialization --info "run_name"

# List all runs
python -m src.simulation.initialization --list

# Verify JSON structure
cat src/simulation/runs/my_run/simulation_data.json | python -m json.tool
```

## Support

For issues or feature requests, check the module code in:

- `src/simulation/initialization/run_initializer.py` - Core functionality
- `src/simulation/initialization/__main__.py` - CLI interface
