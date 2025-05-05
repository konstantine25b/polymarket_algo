# Polymarket Auto-Bidder

A simple automated bidding system that analyzes statistical market opportunities and places orders on Polymarket.

## Features

- Automatically identifies the best buy opportunities using statistical analysis
- Places market buy orders for a specified amount (default: 1 USDC)
- Configurable minimum threshold for opportunities (default: 0.0%)
- Displays full statistical comparison table
- Safely skips bidding when no valid opportunities exist
- Supports dry run mode to test without placing actual orders

## Usage

### Command Line

```bash
# Basic usage (uses values from .env file)
python -m src.bidding_decision.auto_bid.run

# Specify minimum opportunity threshold
python -m src.bidding_decision.auto_bid.run --threshold 3.0

# Change the bid amount
python -m src.bidding_decision.auto_bid.run --amount 2.5

# Run in dry run mode (no real orders placed)
python -m src.bidding_decision.auto_bid.run --dry-run

# Skip displaying the full stats table
python -m src.bidding_decision.auto_bid.run --no-stats

# Provide private key directly (not recommended for security reasons)
python -m src.bidding_decision.auto_bid.run --key YOUR_PRIVATE_KEY
```

### Python API

```python
from src.bidding_decision.auto_bid import AutoBidder

# Initialize with custom parameters
bidder = AutoBidder(
    threshold=3.0,  # Minimum 3% edge required
    order_amount=1.0  # 1 USDC per order
)

# Complete automated process
success = bidder.auto_bid()

# Or step by step:

# 1. Connect
bidder.connect()

# 2. Find opportunities
opportunity = bidder.find_best_opportunity()
if opportunity:
    print(f"Found opportunity: {opportunity['range']} with {opportunity['opportunity']}% edge")

    # 3. Place order
    bidder.place_order(opportunity)
```

### Sample Output

Running with the `--dry-run` flag will show you the full stats table and the best opportunity without placing an actual order:

```
Comparison Table:
         Range  Pred (%)  Mkt (%)  Bid (%)  Ask (%)  Spread (%)  Diff (%)  Opp (%)  Adj-Sp (%)  Adj-Full (0.0%)  Buy-Only (0.0%)
       150–174      0.43     0.50     0.30     0.70        0.40     -0.27     0.27        0.00             0.00             0.00
       175–199      5.83     2.30     1.90     2.70        0.80      3.13     3.13        2.33             2.33             2.33
       200–224     17.30     7.05     6.60     7.50        0.90      9.80     9.80        8.90             8.90             8.90
       225–249     22.28    17.00    16.00    18.00        2.00      4.28     4.28        2.28             2.28             2.28
       250–274     19.98    20.50    20.00    21.00        1.00     -1.02     1.02        0.02             0.02             0.00
       275–299     14.02    22.30    22.00    22.60        0.60     -8.58     8.58        7.98             7.98             0.00
       300–324      8.78    12.50    12.00    13.00        1.00     -4.22     4.22        3.22             3.22             0.00
       325–349      4.98     8.65     8.50     8.80        0.30     -3.82     3.82        3.52             3.52             0.00
   350 or more      6.40    10.70    10.40    11.00        0.60     -4.60     4.60        4.00             4.00             0.00
EXPECTED VALUE    263.57   289.01      NaN      NaN         NaN    -25.44    25.44       25.44            25.44             0.00

Token IDs:
150–174: 58491148303239718595459688678505994852918801795590099599410816935825697203376
175–199: 58491148303239718595459688678505994852918801795590099599410816935825697203296
200–224: 58491148303239718595459688678505994852918801795590099599410816935825697202168
225–249: 58491148303239718595459688678505994852918801795590099599410816935825697202048
250–274: 58491148303239718595459688678505994852918801795590099599410816935825697202128
275–299: 5849114830323971859545968867850599485291880179559009959941081693582569720720
300–324: 27595460940597974936971179444892437928112930418924683122217724579143647231008
325–349: 27595460940597974936971179444892437928112930418924683122217724579143647231088
350 or more: 27595460940597974936971179444892437928112930418924683122217724579143647230864

Expected Values:
Prediction: 263.57%
Market: 289.01%
Difference: -25.44%

Best Buy Opportunity:
Range: 200–224
Prediction: 17.3%
Market Ask Price: 7.5%
Edge: 8.9%
Token ID: 58491148303239718595459688678505994852918801795590099599410816935825697202168

DRY RUN - No order placed.
```

If all buy-only opportunities are 0 or negative, the program will exit without placing any orders:

```
Comparison Table:
[...table shows all opportunities...]

Token IDs:
[...token IDs listed...]

Expected Values:
[...expected values shown...]

2025-05-05 23:01:25,012 - src.bidding_decision.auto_bid.bidder - INFO - All buy-only opportunities are 0 or negative. No suitable trades available.
2025-05-05 23:01:25,012 - src.bidding_decision.auto_bid.run - INFO - No suitable opportunities found. Exiting.
```

## How It Works

1. The auto-bidder connects to Polymarket using the configured wallet
2. It generates a statistical comparison between predictions and current market prices
3. It displays the full statistics table showing all opportunities
4. It checks if any buy-only opportunities are greater than 0
   - If all buy-only opportunities are 0 or negative, it exits without placing orders
5. It identifies the opportunity with the highest "buy-only" edge above your threshold
6. It places a market buy order for the configured amount (default: 1 USDC)

The "buy-only" edge is calculated as:

- `(Prediction - Ask Price) - Spread - Threshold`
- Only positive values are considered for buying

## Configuration

- **Threshold**: Minimum percentage edge required to place an order (default: 0.0%)
- **Amount**: USDC amount to bid (default: 1.0 USDC)
- **Wallet**: Uses the `WALLET_PRIVATE_KEY` from your `.env` file by default
- **Stats Display**: Displays full statistics by default, can be disabled with `--no-stats`

## Requirements

- Configured `.env` file with `WALLET_PRIVATE_KEY`
- Properly set up Polymarket bidding module
- Prophet predictions properly configured
