# Tweet Scheduler

A tool for automating the tweet fetching, prediction processes, and automated trading for Polymarket.

## Overview

This module provides an automated scheduler that periodically:

1. Fetches Elon Musk's tweets and stores them in the database
2. Runs the Polymarket predictor to update predictions
3. Runs the Auto-Bidder to place orders based on identified trading opportunities
4. Runs the Position Seller to automatically sell positions that should be sold

## Features

- **Configurable interval**: Set how often to run the process (default: 20 minutes)
- **Selective execution**: Run only tweet fetching or only predictions
- **Smart incremental fetching**: Uses advanced incremental fetching strategy by default to ensure continuous tweet collection
- **Logging**: Comprehensive logging to file and console
- **One-time execution**: Option to run once and exit
- **Quiet mode**: Reduce output verbosity
- **Automated trading**: Automatically places buy orders and sells positions on Polymarket based on prediction data
- **Trading opportunities**: Identifies potential trading opportunities with customizable thresholds
- **Weighted selection**: Option to use weighted probability selection for buy opportunities instead of always choosing the best one
- **Separate thresholds**: Configure different thresholds for buying and selling positions
- **Dry run mode**: Test the auto-bidder and auto-seller without placing actual orders
- **Configurable bid amount**: Set the amount of USDC to use for each bid
- **Statistical analysis**: View detailed stats on each market opportunity
- **Balance checking**: Automatically checks wallet balance before placing buy orders, skipping if insufficient funds
- **Conditional bidding**: Only runs auto-bidder if there's enough USDC balance (configurable minimum threshold)
- **Tweet verification**: Shows the total and daily tweet counts after fetching to track activity

## Command-Line Usage

```bash
# Activate virtual environment
source venv/bin/activate

# I use it commonly
python -m src.scheduler.scheduler --buy-threshold 1.0 --sell-threshold 0.5 --weighted-selection --interval 30

# Run with default settings (every 20 minutes)
python -m src.scheduler.scheduler

# Run with custom interval (every 5 minutes)
python -m src.scheduler.scheduler --interval 5

# Only fetch tweets, don't run predictions or trading
python -m src.scheduler.scheduler --tweets-only

# Only run predictions and trading, don't fetch tweets
python -m src.scheduler.scheduler --predictions-only

# Run jobs once and exit (don't keep running)
python -m src.scheduler.scheduler --run-once

# Change the maximum number of tweets to fetch
python -m src.scheduler.scheduler --max-tweets 100

# Disable debug mode for tweet fetching
python -m src.scheduler.scheduler --no-debug

# Run in quiet mode with less output
python -m src.scheduler.scheduler --quiet

# Customize incremental fetching parameters
python -m src.scheduler.scheduler --initial-batch 60 --max-batch 300

# Disable incremental fetching (not recommended)
python -m src.scheduler.scheduler --no-incremental

# Don't run the auto-bidder after predictions
python -m src.scheduler.scheduler --no-bidding

# Don't run the auto-seller after predictions
python -m src.scheduler.scheduler --no-selling

# Set minimum thresholds for buying and selling (e.g., 3% for buying, 2% for selling)
python -m src.scheduler.scheduler --buy-threshold 3.0 --sell-threshold 2.0

# Set the bid amount to 2.5 USDC
python -m src.scheduler.scheduler --amount 2.5

# Use weighted selection for buy opportunities
python -m src.scheduler.scheduler --weighted-selection

# Run in dry run mode (don't place real orders)
python -m src.scheduler.scheduler --dry-run

# Don't display the full statistics table
python -m src.scheduler.scheduler --no-stats

# Set the minimum USDC balance required for bidding
python -m src.scheduler.scheduler --min-usdc 2.0

# Skip balance checking (always attempt to place buy orders)
python -m src.scheduler.scheduler --skip-balance-check

# Skip tweet count verification after fetching
python -m src.scheduler.scheduler --no-tweet-verify

# Combine multiple options
python -m src.scheduler.scheduler --interval 15 --max-tweets 50 --quiet --buy-threshold 3.0 --sell-threshold 2.0 --amount 2.0 --weighted-selection --dry-run --min-usdc 1.5
```

## Command-Line Options

- `--interval`: Set the interval between runs in minutes (default: 20)
- `--tweets-only`: Only run the tweet fetching job
- `--predictions-only`: Only run the prediction and trading jobs
- `--max-tweets`: Maximum number of tweets to fetch (default: 40)
- `--no-debug`: Disable debug mode for tweet fetching
- `--run-once`: Run jobs once and exit
- `--quiet`: Reduce output verbosity
- `--no-incremental`: Disable incremental fetching (not recommended)
- `--initial-batch`: Initial batch size for incremental fetching (default: 40)
- `--max-batch`: Maximum batch size for incremental fetching (default: 200)
- `--no-prophet`: Disable Prophet algorithm for predictions (use standard algorithm instead)
- `--no-bidding`: Don't run the auto-bidder after predictions
- `--no-selling`: Don't run the auto-seller after predictions
- `--buy-threshold`: Minimum opportunity percentage for placing buy orders (default: 0.0)
- `--sell-threshold`: Minimum opportunity percentage for selling positions (default: 0.0)
- `--amount`: Amount to bid in USDC (default: 1.0)
- `--dry-run`: Run auto-bidder and auto-seller in dry run mode (don't place real orders)
- `--no-stats`: Don't display the full statistics table with market opportunities
- `--weighted-selection`: Use weighted probability selection for buy opportunities instead of always choosing the best opportunity
- `--skip-balance-check`: Skip checking wallet balance before running auto-bidder
- `--min-usdc`: Minimum USDC balance required to run auto-bidder (default: 1.0)
- `--no-tweet-verify`: Skip verifying and displaying tweet counts after fetching

## Smart Incremental Fetching

The scheduler uses an intelligent incremental fetching strategy by default, which:

1. Starts with a small batch size (default: 40 tweets)
2. Checks if this batch overlaps with your existing database
3. If not found, gradually increases the batch size and tries again
4. Ensures no gaps in your tweet timeline

This approach provides several benefits:

- Ensures continuous, gap-free tweet collection
- Minimizes API costs by adapting to the actual number of new tweets
- Handles cases where many tweets are posted between scheduled runs
- Automatically adjusts batch sizes to maintain data continuity

You can customize the incremental fetching parameters using the `--initial-batch` and
`--max-batch` options, or disable it entirely with `--no-incremental` (though this is not recommended).

## Tweet Count Verification

After successfully fetching tweets, the scheduler automatically verifies and displays the tweet count for the current market week. This feature:

1. Shows the total number of tweets for the current market week
2. Displays a daily breakdown of tweets for each day of the week
3. Helps you monitor Elon's tweeting activity and ensure data is being collected correctly

The tweet verification feature provides valuable information for monitoring:
- Whether the expected number of tweets are being collected
- The daily pattern of tweet activity during the week
- Progress toward the various tweet count ranges on Polymarket

Example output:

```
==================================================
TWEET COUNT VERIFICATION
==================================================
Total tweets this week: 235

Daily tweet counts:
  2025-05-02: 25 tweets
  2025-05-03: 44 tweets
  2025-05-04: 50 tweets
  2025-05-05: 18 tweets
  2025-05-06: 28 tweets
  2025-05-07: 40 tweets
  2025-05-08: 30 tweets
==================================================
```

You can disable this feature with the `--no-tweet-verify` flag if you don't need the information.

## Automated Trading with Auto-Bidder

After running predictions, the scheduler automatically executes the Auto-Bidder, which:

1. Checks the wallet balance to ensure sufficient USDC is available
2. Compares Prophet model predictions with actual Polymarket order book data
3. Calculates differences between predicted and actual market prices
4. Measures the bid-ask spread on each market to determine real trading costs
5. Identifies the best buying opportunities where the "buy-only" edge is highest
6. Places a market buy order for the configured amount (default: 1 USDC)
7. Provides detailed output about the selected opportunity and order status

The auto-bidder is configured to place buy orders, focusing on opportunities with the highest edge after accounting for:

- The bid-ask spread that must be crossed to execute a trade
- The configured minimum threshold for meaningful opportunities

When weighted selection is enabled, the auto-bidder will select from multiple positive opportunities using a weighted probability system where higher edges have a higher chance of being selected, instead of always choosing the single best opportunity.

To customize the auto-bidder behavior:

- `--buy-threshold`: Set the minimum opportunity percentage for buying (default: 0.0%)
- `--amount`: Set the USDC amount for each bid (default: 1.0 USDC)
- `--weighted-selection`: Use weighted selection instead of always choosing the best opportunity
- `--dry-run`: Test the auto-bidder without placing actual orders
- `--no-stats`: Skip displaying the full statistical comparison table
- `--no-bidding`: Skip running the auto-bidder entirely
- `--skip-balance-check`: Skip checking wallet balance before running auto-bidder
- `--min-usdc`: Set the minimum USDC balance required to run auto-bidder (default: 1.0)

Example output in dry run mode:

```
==================================================
WALLET BALANCE: 0x08E9Fa6d9De086eed6a83A8bE9A54ccC9478b776
==================================================
MATIC Balance: 2.9880 MATIC
USDC Balance:  7.93 USDC
==================================================

Comparison Table:
[Full statistics table showing all market opportunities]

Token IDs:
[Token IDs for each range]

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

## Wallet Balance Checking

The scheduler now includes automatic wallet balance checking before running the auto-bidder. This feature:

1. Retrieves your MATIC and USDC balances from the Polygon network
2. Displays the balances in a clear, formatted output
3. Verifies that you have sufficient USDC to place buy orders
4. Skips the auto-bidder if your USDC balance is below the configured minimum

The balance checker:

- Uses the wallet address from your `.env` file
- Falls back to RPC queries if the Polymarket API fails
- Will not affect the auto-seller, which runs regardless of balance
- Can be disabled with the `--skip-balance-check` flag

If your USDC balance is insufficient:

- The auto-bidder will be skipped with a clear warning message
- The auto-seller will still run as normal (selling does not require USDC)
- In dry run mode, the auto-bidder will run regardless of balance

To customize the balance checking behavior:

- `--min-usdc`: Set the minimum required USDC balance (default: 1.0 USDC)
- `--skip-balance-check`: Disable balance checking entirely
- `--dry-run`: Run the auto-bidder regardless of balance (for testing)

## Automated Trading with Position Seller

After running predictions, the scheduler also executes the Position Seller, which:

1. Retrieves all your current positions from your Polymarket account
2. Generates a statistical comparison between predictions and market prices
3. Identifies positions where the model predicts a lower probability than the market price
4. Calculates the "sell-only" opportunity for each position, accounting for spread and threshold
5. Executes market sell orders for positions with positive sell opportunities
6. Provides detailed output about positions sold and execution status

The position seller:

- Filters out positions with less than 0.01 shares (Polymarket's minimum order size)
- Only sells positions with sell opportunities above the configured threshold
- Executes market sell orders at the current bid price
- Provides comprehensive error handling and notifications
- Runs regardless of your USDC balance (selling doesn't require USDC)

To customize the position seller behavior:

- `--sell-threshold`: Set the minimum opportunity percentage for selling (default: 0.0%)
- `--dry-run`: Test the position seller without placing actual sell orders
- `--no-stats`: Skip displaying the full statistical comparison table
- `--no-selling`: Skip running the position seller entirely

Example output in production mode:

```
POSITIONS RECOMMENDED FOR SELLING (THRESHOLD: 2.0%):
==================================

Will Elon tweet 275–299 times May 2–9? (275–299):
  Outcome: Yes
  Quantity: 1.492536 shares
  Token ID: 5849114830323971859545968867850599485291880179559009959941081693582569720720
  Current Bid Price: 22.00%
  Your Model's Prediction: 14.02%
  Difference: -7.98%
  Sell Opportunity: 5.98% (after applying 2.0% threshold)

Executing sell orders for 1 positions...

Selling 1.492536 shares of 275–299 (Token ID: 5849114830323971859545968867850599485291880179559009959941081693582569720720)
Expected sale price: 22.00%
Sell opportunity: 5.98% (after applying 2.0% threshold)
Connected with wallet: 0x08E9Fa...
Sell order executed successfully!
Response: {'orderId': '987654321', 'status': 'filled', 'price': '0.22', 'fillAmount': '1.492536'}

SELL ORDER SUMMARY: Successfully sold 1 out of 1 positions
```

## Logs

The scheduler writes logs to both the console and a log file:

- **Log file location**: `src/logs/scheduler.log`
- **Log format**: `timestamp - name - level - message`

## Running as a Background Service

To run the scheduler as a background service (e.g., on a server), you can use:

```bash
nohup python -m src.scheduler.scheduler > /dev/null 2>&1 &
```

Or with custom options:

```bash
nohup python -m src.scheduler.scheduler --interval 10 --quiet --buy-threshold 3.0 --sell-threshold 2.0 --amount 2.0 --dry-run --min-usdc 1.5 > /dev/null 2>&1 &
```

To stop the scheduler running in the background:

```bash
# Find the process ID
ps aux | grep src.scheduler

# Kill the process
kill <process_id>
```

## Implementation Details

The scheduler uses Python's `subprocess` module to run the tweet fetching, prediction, auto-bidder, and position seller scripts as separate processes. This ensures that any failures in one process don't affect the others.

Each process is monitored, and failures are logged. If the tweet fetching process fails, the prediction process is still attempted (unless configured otherwise). If the prediction process succeeds, the auto-bidder and position seller are then executed to place buy orders and sell positions based on the updated predictions.

## Related Modules

- **src.apify.get_elon_tweets**: Module for fetching tweets
- **src.polymarket_predictor**: Module for running predictions
- **src.bidding_decision.auto_bid.run**: Module for automated bidding based on predictions
- **src.bidding_decision.auto_bid.run_seller**: Module for automated selling of positions
- **src.polymarket.balance**: Module for checking wallet balances
- **src.polymarket_predictor.tweet_predictor**: Module for tweet analysis and verification
