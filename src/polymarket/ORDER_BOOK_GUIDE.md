# Understanding and Working with Polymarket Order Book Data

This guide explains the structure of Polymarket's order book data and how to work with it in the Polymarket Data Analyzer.

## Order Book Data Structure

The order book data in Polymarket represents the buy (bid) and sell (ask) orders for a particular market. In our implementation, the order book data is structured as follows:

```json
{
  "Market Question 1": {
    "buy_orders": [
      {"price": 95.5, "size": 100.0, "total": 9550.0},
      {"price": 95.0, "size": 50.0, "total": 4750.0},
      ...
    ],
    "sell_orders": [
      {"price": 97.8, "size": 200.0, "total": 19560.0},
      {"price": 98.3, "size": 150.0, "total": 14745.0},
      ...
    ],
    "market_id": "token_id_here"
  },
  "Market Question 2": {
    ...
  }
}
```

Where:

- **Market Question**: The specific question for this prediction market
- **buy_orders**: A list of orders to buy YES tokens, sorted by price (descending)
- **sell_orders**: A list of orders to sell YES tokens, sorted by price (ascending)
- **market_id**: The token ID for the YES outcome of this market

Each order contains:

- **price**: The price in percentage points (0-100)
- **size**: The number of tokens being bought or sold
- **total**: The total value of the order in dollars (price \* size / 100)

## How Orders Work in Polymarket

In Polymarket:

- Buying a YES token means you're betting that the outcome will happen
- Selling a YES token means you're betting against the outcome
- Buy orders represent the highest prices people are willing to pay for YES tokens
- Sell orders represent the lowest prices people are willing to accept for YES tokens
- The spread between the highest buy and lowest sell is the market spread

## How Our Application Uses Order Book Data

In the Polymarket Data Analyzer:

1. **Synthetic Order Generation**: Due to API limitations, we generate synthetic order data based on the real midpoint prices from the CLOB API.

2. **Spread Calculation**: We calculate the difference between the lowest sell price and highest buy price to determine the market spread.

3. **Market Analysis**: The order book data helps understand market liquidity and can indicate strong market sentiment when there are large orders at certain price points.

## Working with the Order Book Data Programmatically

```python
# Example of working with order book data
from src.polymarket.api_client import PolymarketAPIClient

# Fetch order frames for an event
event_slug = "example-event-slug"
order_frames = PolymarketAPIClient.get_order_frames(event_slug)

# Analyze a specific market's order book
for question, data in order_frames.items():
    print(f"Market: {question}")

    # Get the best bid (highest buy price)
    if data["buy_orders"]:
        best_bid = data["buy_orders"][0]["price"]
        print(f"Best bid: {best_bid}%")

    # Get the best ask (lowest sell price)
    if data["sell_orders"]:
        best_ask = data["sell_orders"][0]["price"]
        print(f"Best ask: {best_ask}%")

    # Calculate the spread
    if data["buy_orders"] and data["sell_orders"]:
        spread = best_ask - best_bid
        print(f"Spread: {spread}%")

    # Calculate total liquidity (sum of all orders)
    buy_liquidity = sum(order["total"] for order in data["buy_orders"])
    sell_liquidity = sum(order["total"] for order in data["sell_orders"])
    print(f"Buy liquidity: ${buy_liquidity:.2f}")
    print(f"Sell liquidity: ${sell_liquidity:.2f}")
```

## Understanding the CLOB API and ClobClient

The CLOB (Central Limit Order Book) API is Polymarket's backend for order handling. In our implementation, we interact with it through the `py_clob_client` library.

The main components are:

1. **ClobClient**: The main client for interacting with the CLOB API

   ```python
   client = ClobClient(host=CLOB_API_HOST, chain_id=137)  # 137 is for Polygon network
   ```

2. **BookParams**: Used to specify parameters for querying the order book

   ```python
   book_params = BookParams(token_id="your_token_id_here")
   ```

3. **OrderBookSummary**: The response structure containing bids and asks for a specific token

4. **OrderArgs/MarketOrderArgs**: Used when creating and placing orders (not used in our read-only application)

## Retrieving Real Order Book Data (Advanced)

If you want to retrieve the actual order book data instead of using synthetic data, you can use the ClobClient's get_order_book method:

```python
def get_real_order_book(token_id):
    client = ClobClient(host=CLOB_API_HOST, chain_id=137)
    try:
        order_book = client.get_order_book(token_id)
        return order_book
    except Exception as e:
        print(f"Error fetching order book: {e}")
        return None
```

However, note that this requires proper authentication for some operations and might be rate-limited for excessive requests.

## Best Practices

1. **Cache Order Book Data**: Order book data can change frequently but caching it for short periods (e.g., 5-10 seconds) can prevent excessive API calls.

2. **Handle Missing Data**: Always check if buy_orders or sell_orders lists are empty before attempting to access their elements.

3. **Respect API Limits**: Polymarket may have rate limits on their API. Be mindful of how frequently you request order book data.

4. **Analyze Order Size**: Large orders may indicate strong market conviction and can be more meaningful than many small orders.
