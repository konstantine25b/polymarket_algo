# Polymarket Auto-Bidder and Position Seller

A suite of tools for automating trading on Polymarket, including:

1. **Auto-Bidder** - Analyzes statistical market opportunities and places buy orders
2. **Position Seller** - Identifies which existing positions should be sold based on statistical analysis

## Features

### Auto-Bidder

- Automatically identifies the best buy opportunities using statistical analysis
- Places market buy orders for a specified amount (default: 1 USDC)
- Configurable minimum threshold for opportunities (default: 0.0%)
- Supports weighted selection from multiple opportunities (instead of always choosing the best one)
- Displays full statistical comparison table
- Safely skips bidding when no valid opportunities exist
- Supports dry run mode to test without placing actual orders

### Position Seller

- Displays all your current positions with complete statistical information
- Highlights positions that are recommended for selling
- Identifies positions where Buy-Only value is 0, indicating they should be sold
- **Automatically executes sell orders for recommended positions**
- Sells positions with model predictions below a specified threshold
- Shows current market prices (bid/ask), spread, and your model's predictions for each position
- Provides token IDs needed for programmatic selling
- Shows Buy-Only and Sell-Only opportunity values for every position
- Includes a summary of which positions should be sold and why
- Supports dry run mode to test without placing actual sell orders

## Usage

### Auto-Bidder

#### Command Line

```bash
# Basic usage (uses values from .env file)
python -m src.bidding_decision.auto_bid.run

# Specify minimum opportunity threshold
python -m src.bidding_decision.auto_bid.run --threshold 3.0

# Change the bid amount
python -m src.bidding_decision.auto_bid.run --amount 2.5

# Use weighted selection instead of always choosing the best opportunity
python -m src.bidding_decision.auto_bid.run --weighted-selection

# Run in dry run mode (no real orders placed)
python -m src.bidding_decision.auto_bid.run --dry-run

# Skip displaying the full stats table
python -m src.bidding_decision.auto_bid.run --no-stats

# Provide private key directly (not recommended for security reasons)
python -m src.bidding_decision.auto_bid.run --key YOUR_PRIVATE_KEY
```

#### Python API

```python
from src.bidding_decision.auto_bid.bidder import AutoBidder

# Initialize with custom parameters
bidder = AutoBidder(
    threshold=3.0,  # Minimum 3% edge required
    order_amount=1.0,  # 1 USDC per order
    use_weighted_selection=True  # Use weighted probability selection instead of highest edge
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

### Position Seller

#### Command Line

```bash
# Basic usage - shows all positions with recommendations
python -m src.bidding_decision.auto_bid.run_seller

# Display only positions recommended for selling (not all positions)
python -m src.bidding_decision.auto_bid.run_seller --sell-only

# Automatically sell all recommended positions
python -m src.bidding_decision.auto_bid.run_seller --auto-sell

# Do a dry run of auto-sell (shows what would be sold without executing orders)
python -m src.bidding_decision.auto_bid.run_seller --auto-sell --dry-run

# Specify minimum opportunity threshold
python -m src.bidding_decision.auto_bid.run_seller --threshold 3.0

# Automatically sell positions with prediction below 5%
python -m src.bidding_decision.auto_bid.run_seller --auto-sell --sell-below 5.0

# Skip displaying the full stats table
python -m src.bidding_decision.auto_bid.run_seller --no-stats

# Enable verbose logging
python -m src.bidding_decision.auto_bid.run_seller --verbose
```

#### Python API

```python
from src.bidding_decision.auto_bid.position_seller import PositionSeller

# Initialize with custom parameters
seller = PositionSeller(threshold=3.0, sell_below=5.0)  # 3% edge required, sell below 5% prediction

# Get all positions with statistical information
all_positions, comparison_df = seller.get_all_positions_with_stats()

# Display all positions with recommendations
seller.print_all_positions(all_positions)

# Or just get positions that should be sold
positions_to_sell = seller.get_positions_to_sell()
seller.print_sell_recommendations(positions_to_sell)

# Execute sell orders for recommended positions
results = seller.execute_sell_orders(positions_to_sell)

# Or do a dry run without executing actual orders
dry_run_results = seller.execute_sell_orders(positions_to_sell, dry_run=True)
```

### Sample Output

#### Auto-Bidder Output

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

#### Weighted Selection Output

With the `--weighted-selection` flag, you might see output like this:

```
Comparison Table:
         Range  Pred (%)  Mkt (%)  Bid (%)  Ask (%)  Spread (%)  Diff (%)  Opp (%)  Adj-Sp (%)  Adj-Full (0.0%)  Buy-Only (0.0%)
       175–199      5.83     2.30     1.90     2.70        0.80      3.13     3.13        2.33             2.33             2.33
       200–224     17.30     7.05     6.60     7.50        0.90      9.80     9.80        8.90             8.90             8.90
       225–249     22.28    17.00    16.00    18.00        2.00      4.28     4.28        2.28             2.28             2.28
// ... more ranges ...

Selected Buy Opportunity:
Range: 225–249
Prediction: 22.28%
Market Ask Price: 18.00%
Edge: 2.28% (after applying 0.0% threshold)
Token ID: 58491148303239718595459688678505994852918801795590099599410816935825697202048
Selection method: weighted selection from 3 positive opportunities

DRY RUN - No order placed.
```

Even though the "200-224" range had the highest edge (8.9%), the weighted selection algorithm chose the "225-249" range, which still has a positive edge (2.28%). This helps diversify your bidding strategy over time.

#### Position Seller Output (All Positions)

When running the position seller, you'll see all your positions with recommendations for which ones to sell:

```
ALL YOUR CURRENT POSITIONS:
============================

Will Elon tweet 225–249 times May 2–9? (225–249) (RECOMMENDED TO SELL):
  Outcome: Yes
  Quantity: 0.071903 shares
  Token ID: 99677738681569692969530319808900493429917602001237659764921467975358516664236
  Current Price: Bid 55.00% / Ask 56.00% (Spread: 1.00%)
  Your Model's Prediction: 49.67%
  Difference: -6.33%
  Buy-Only Opportunity: 0.00%
  Sell-Only Opportunity: 5.33%

Will Elon tweet 200–224 times May 2–9? (200–224):
  Outcome: Yes
  Quantity: 62.500000 shares
  Token ID: 58491148303239718595459688678505994852918801795590099599410816935825697202168
  Current Price: Bid 0.80% / Ask 1.70% (Spread: 0.90%)
  Your Model's Prediction: 14.64%
  Difference: 12.94%
  Buy-Only Opportunity: 12.04%
  Sell-Only Opportunity: 0.00%

Will Elon tweet 300–324 times May 2–9? (300–324):
  Outcome: Yes
  Quantity: 0.554505 shares
  Token ID: 65797596156986552520681751081841163827397285360337892026989663816422180341953
  Current Price: Bid 0.60% / Ask 1.00% (Spread: 0.40%)
  Your Model's Prediction: 3.05%
  Difference: 2.05%
  Buy-Only Opportunity: 1.65%
  Sell-Only Opportunity: 0.00%

SUMMARY: You have 1 positions recommended for selling.

Found 1 positions to sell out of 3 total positions.
```

#### Position Seller Output (Sell-Only Mode)

Using the `--sell-only` flag will show only the positions you should sell:

```
POSITIONS RECOMMENDED FOR SELLING:
==================================

Will Elon tweet 225–249 times May 2–9? (225–249):
  Outcome: Yes
  Quantity: 0.071903 shares
  Token ID: 99677738681569692969530319808900493429917602001237659764921467975358516664236
  Current Bid Price: 55.00%
  Your Model's Prediction: 49.67%
  Difference: -6.33%

Note: These positions are recommended for selling because they
have zero buy opportunity in the comparison table, which suggests
they are overvalued compared to your model's predictions.

Found 1 positions to sell based on current market conditions.
```

#### Auto-Sell Output

Using the `--auto-sell --sell-below 5.0 --dry-run` flags will show which positions would be sold based on low prediction:

```
POSITIONS RECOMMENDED FOR SELLING:
Threshold for sell opportunity: 0.0%
Threshold for low prediction: 5.0%
==================================

Will Elon tweet 300–324 times May 2–9? (300–324):
  Outcome: Yes
  Quantity: 0.554505 shares
  Token ID: 65797596156986552520681751081841163827397285360337892026989663816422180341953
  Current Bid Price: 0.70%
  Your Model's Prediction: 1.5X%
  Difference: 0.8X%
  Reason: Model prediction (1.5X%) is below the 5.0% threshold

Will Elon tweet 325–349 times May 2–9? (325–349):
  Outcome: Yes
  Quantity: 128.615000 shares
  Token ID: 63763014879028996551101083827875019681826101444515365120772529536860324618159
  Current Bid Price: 0.20%
  Your Model's Prediction: 0.5X%
  Difference: 0.3X%
  Reason: Low prediction below threshold

SELL RECOMMENDATION SUMMARY:
  - 0 positions with positive sell opportunity (overvalued)
  - 2 positions with prediction below the 5.0% threshold

Skipping 2 positions with quantity less than 0.01 (Polymarket minimum):
  - 250–274: 0.002536 shares (below minimum)
  - 275–299: 0.000345 shares (below minimum)

Executing sell orders for 2 positions...

Selling 0.554505 shares of 300–324 (Token ID: 65797596156986552520681751081841163827397285360337892026989663816422180341953)
Expected sale price: 0.70%
Reason: Low prediction below threshold
Model prediction (1.5X%) is below the 5.0% threshold
DRY RUN - No actual sell order executed

Selling 128.615000 shares of 325–349 (Token ID: 63763014879028996551101083827875019681826101444515365120772529536860324618159)
Expected sale price: 0.20%
Reason: Low prediction below threshold
Model prediction (0.5X%) is below the 5.0% threshold
DRY RUN - No actual sell order executed

DRY RUN SUMMARY: Would have sold 2 positions
```

If you run without the `--dry-run` flag, real orders will be executed and you'll see confirmation messages:

```
Sell order executed successfully!
Response: {'orderId': '123456789', 'status': 'filled', 'price': '0.007', 'fillAmount': '0.554505'}
```

## How It Works

### Auto-Bidder Process

1. The auto-bidder connects to Polymarket using the configured wallet
2. It generates a statistical comparison between predictions and current market prices
3. It displays the full statistics table showing all opportunities
4. It checks if any buy-only opportunities are greater than 0
   - If all buy-only opportunities are 0 or negative, it exits without placing orders
5. It selects an opportunity to trade:
   - **Default mode**: It identifies the opportunity with the highest "buy-only" edge above your threshold
   - **Weighted selection mode**: It selects from all positive opportunities using a weighted probability system where higher edges have a higher chance of being selected
6. It places a market buy order for the configured amount (default: 1 USDC)

The "buy-only" edge is calculated as:

- `(Prediction - Ask Price) - Spread - Threshold`
- Only positive values are considered for buying

### Position Seller Process

1. The position seller retrieves all your current positions
2. It generates a statistical comparison table between predictions and market prices
3. It displays information about every position you own including:
   - Market name and range
   - Outcome and quantity
   - Current bid/ask prices and spread
   - Your model's prediction and the difference from market price
   - Buy-Only and Sell-Only opportunity values
4. It identifies positions that should be sold based on two criteria:
   - Positions with a positive sell-only opportunity exceeding your threshold
   - Positions where the model's prediction is below your specified sell-below threshold
5. If auto-sell is enabled:
   - It filters out positions with less than 0.01 shares (Polymarket's minimum order size)
   - It automatically executes market sell orders for the remaining valid positions
6. For positions recommended for selling, it provides:
   - The quantity you currently own
   - The token ID needed for selling
   - The current bid price (what you'd get if you sold)
   - The model's prediction vs. the market
   - The difference between your prediction and the market
   - The reason for the sell recommendation (opportunity or low prediction)

## Configuration

- **Threshold**: Minimum percentage edge required (default: 0.0%)
- **Amount**: USDC amount to bid for Auto-Bidder (default: 1.0 USDC)
- **Weighted Selection**: Whether to use weighted probability selection from multiple opportunities instead of always choosing the best one (default: false)
- **Auto-Sell**: Whether to automatically execute sell orders for recommended positions (default: false)
- **Sell-Below**: Sell positions with model prediction below this percentage (default: 0.0%)
- **Dry Run**: Show what would be done but don't execute actual orders (default: false)
- **Wallet**: Uses the `WALLET_PRIVATE_KEY` from your `.env` file by default
- **Stats Display**: Displays full statistics by default, can be disabled with `--no-stats`
- **Position Display**: Shows all positions by default, can be limited to sell recommendations with `--sell-only`
- **Minimum Order Size**: Positions with less than 0.01 shares will be skipped when selling (Polymarket requirement)

## Requirements

- Configured `.env` file with `WALLET_PRIVATE_KEY`
- Properly set up Polymarket bidding module
- Prophet predictions properly configured

## Common Issues

### Auto-Sell

- **Minimum Order Size**: Polymarket requires a minimum order size of 0.01 shares. Positions with smaller quantities will be automatically skipped.
- **Invalid Amounts**: This error occurs when trying to execute an order that's too small, typically below 0.01 shares.
- **Insufficient Funds**: Make sure your wallet has enough USDC to cover transaction fees.
- **Price Slippage**: Sometimes market prices change between the time of analysis and order execution, causing slippage errors. Try again or adjust your threshold.
