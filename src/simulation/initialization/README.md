# Polymarket Simulation Initialization

This package provides comprehensive tools for initializing and managing Polymarket trading simulation runs. It creates structured JSON files containing all necessary simulation data including balances, positions, transactions, and market information.

## Features

- **Run Creation**: Create new simulation runs with unique IDs and timestamps
- **Real Market Integration**: Initialize markets using live Polymarket data
- **Position Management**: Add, update, and sell positions with automatic duplicate handling
- **Balance Management**: Add/remove balance with transaction logging and negative balance protection
- **Price Updates**: Update market prices and calculate profit/loss percentages
- **Transaction History**: Complete audit trail of all operations
- **Command-Line Interface**: Full CLI for all operations

## Quick Start

### 1. Create a New Run

```bash
python -m src.simulation.initialization --create --run "run name" --market-name "Elon Tweet Prediction" --balance 1000
```

### 2. Initialize Markets from Real Polymarket Data

```bash
python -m src.simulation.initialization --init-markets-from-polymarket my_run
```

This will fetch all currently active markets from Polymarket and add them to your simulation with real prices.

### 3. Add Positions

```bash
python -m src.simulation.initialization --add-position my_run market_id 100
```

### 4. Sell Positions

```bash
python -m src.simulation.initialization --sell-position my_run market_id 50
```

## Installation Requirements

For real Polymarket data integration, ensure you have:

- The `py_clob_client` library installed
- The `src.polymarket.order_book.get_prices` module available
- Network access to fetch market data

## Command Reference

### Core Commands

#### Create New Run

```bash
python -m src.simulation.initialization --create --market-name "Market Name" --balance 1000 [--run-name custom_name]
```

#### Initialize Markets from Polymarket

```bash
python -m src.simulation.initialization --init-markets-from-polymarket RUN_NAME [--category prediction]
```

- Fetches all active markets from Polymarket
- Creates markets with current bid/ask prices
- Calculates mid-price for market value
- Skips markets with invalid or missing price data
- Provides detailed progress feedback

#### List All Runs

```bash
python -m src.simulation.initialization --list
```

#### Get Run Information

```bash
python -m src.simulation.initialization --info RUN_NAME
```

### Position Management

#### Add Position

```bash
python -m src.simulation.initialization --add-position RUN_NAME MARKET_ID NUM_SHARES [--allow-negative]
```

- Purchases at current ask price
- Automatically merges with existing positions for same market
- Prevents transactions exceeding available balance (unless `--allow-negative`)

#### Sell Position

```bash
python -m src.simulation.initialization --sell-position RUN_NAME MARKET_ID NUM_SHARES
```

- Sells at current bid price
- Calculates profit/loss based on cost basis
- Supports partial sales
- Maintains transaction history

### Price Management

#### Update Market Prices

```bash
python -m src.simulation.initialization --update-prices RUN_NAME MARKET_ID PRICE BID ASK
```

- Updates market prices and recalculates position values
- Adds price history entries
- Updates profit/loss percentages for all positions

### Balance Management

#### Add Balance

```bash
python -m src.simulation.initialization --add-balance RUN_NAME AMOUNT [--description "reason"]
```

#### Remove Balance

```bash
python -m src.simulation.initialization --remove-balance RUN_NAME AMOUNT [--description "reason"] [--allow-negative]
```

## Data Structure

Each simulation run creates a `simulation_data.json` file with the following structure:

```json
{
  "whole_market_name": "Market category name",
  "run_id": "unique-uuid",
  "run_name": "run_name",
  "start_time": "2024-01-01T12:00:00.000000",
  "current_balance": 1000.0,
  "initial_balance": 1000.0,
  "total_balance": 1000.0,
  "balance_of_shares": 0.0,
  "balance_invested": 0.0,
  "shares": [],
  "transactions": [],
  "total_balances": [],
  "positions": [],
  "markets": []
}
```

### Markets Structure

When using `--init-markets-from-polymarket`, markets are created with:

```json
{
  "market_id": "polymarket_token_id",
  "market_name": "Market question from Polymarket",
  "description": "Polymarket prediction: [question]",
  "category": "prediction",
  "initial_price": 0.5,
  "current_price": 0.5,
  "current_bid": 0.49,
  "current_ask": 0.51,
  "price_history": [...]
}
```

### Position Tracking

Positions include comprehensive tracking:

- **Transaction History**: All buy/sell transactions with timestamps
- **Profit/Loss Calculation**: Real-time P&L based on current market prices
- **Cost Basis Tracking**: Accurate cost basis for tax/accounting purposes
- **Status Management**: ACTIVE/CLOSED position status

### Balance Protection

- **Negative Balance Prevention**: Configurable protection against overdrafts
- **Transaction Validation**: All transactions validated before execution
- **Audit Trail**: Complete history of all balance changes

## Error Handling

The system includes robust error handling:

- **Price Validation**: Prevents negative prices
- **Market Validation**: Ensures markets exist before position creation
- **Balance Validation**: Prevents overdrafts unless explicitly allowed
- **Data Integrity**: Validates all inputs and maintains consistent state

## Advanced Features

### Real-time Market Integration

- Automatic fetching of current Polymarket data
- Live price updates from order book
- Seamless integration with existing simulation framework

### Duplicate Position Handling

- Automatic merging of positions for same market
- Weighted average cost basis calculation
- Consolidated transaction history

### Comprehensive Reporting

- Detailed transaction logs
- Time-series balance tracking
- Position-level profit/loss analysis
- Market performance metrics

## Examples

### Complete Workflow

```bash
# 1. Create run
python -m src.simulation.initialization --create --market-name "Crypto Predictions" --balance 5000

# 2. Initialize with real markets
python -m src.simulation.initialization --init-markets-from-polymarket crypto_predictions

# 3. Add positions
python -m src.simulation.initialization --add-position crypto_predictions market123 100

# 4. Check status
python -m src.simulation.initialization --info crypto_predictions

# 5. Update prices (if needed)
python -m src.simulation.initialization --update-prices crypto_predictions market123 0.75 0.74 0.76

# 6. Sell position
python -m src.simulation.initialization --sell-position crypto_predictions market123 50
```

### Working with Real Data

The `--init-markets-from-polymarket` command automatically:

1. Fetches all active markets from Polymarket
2. Validates price data quality
3. Creates markets with current bid/ask spreads
4. Provides detailed feedback on success/failures
5. Skips invalid markets with clear error messages

This integration allows you to start trading simulations immediately with real market conditions and current pricing data.

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
