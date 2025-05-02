# Polymarket Orders Module

This module provides functionality to retrieve and manage your orders from the Polymarket CLOB API.

## Prerequisites

1. You must have a Polymarket account with:

   - Wallet private key exported from Polymarket UI
   - Wallet address (funder address) from Polymarket UI

2. Your `.env` file should contain the following variables:
   ```
   WALLET_ADDRESS=0xYourWalletAddress
   WALLET_PRIVATE_KEY=0xYourPrivateKey
   ```

## Usage Examples

### Get All Orders

```python
from src.polymarket.my_orders import get_all_orders

# Retrieve all orders
orders = get_all_orders()
print(f"Found {len(orders)} orders")
for order in orders:
    print(f"Order ID: {order.get('orderId')}, Market: {order.get('marketId')}, Side: {order.get('side')}")

# Get orders with additional API details
orders, details = get_all_orders(return_details=True)
print(f"Connected to {details['api_host']} with wallet {details['wallet_address']}")
```

### Filter Orders by Status

```python
from src.polymarket.my_orders import get_orders_by_status

# Get only open orders
open_orders = get_orders_by_status("open")
print(f"Found {len(open_orders)} open orders")

# Get filled orders with details
filled_orders, details = get_orders_by_status("filled", return_details=True)
print(f"Found {len(filled_orders)} filled orders")
```

### Filter Orders by Market

```python
from src.polymarket.my_orders import get_orders_by_market

# Get orders for a specific market
market_id = "0x3b34b5dbc1f7baf76b9984d9661f70e1c4ef39d60f911205741450086ecceb00"
market_orders = get_orders_by_market(market_id)
print(f"Found {len(market_orders)} orders for market {market_id}")
```

### Filter Orders by Side (Buy/Sell)

```python
from src.polymarket.my_orders import get_orders_by_side

# Get buy orders
buy_orders = get_orders_by_side("buy")
print(f"Found {len(buy_orders)} buy orders")

# Get sell orders
sell_orders = get_orders_by_side("sell")
print(f"Found {len(sell_orders)} sell orders")
```

## Command Line Usage

The simplest way to view your orders is to run the module directly:

```bash
# Run this command from your project root directory
python -m src.polymarket.my_orders
```

### Additional Command Line Options

You can get more detailed API information using these flags:

```bash
# Show detailed connection info and API metadata
python -m src.polymarket.my_orders --verbose

# Show full debug information, including raw API responses
python -m src.polymarket.my_orders --debug
```

This will display:

- API connection status
- Your wallet address
- Detailed information about orders
- Raw API response data (with --debug flag)

## Troubleshooting

### If You See "No Orders Found"

This is normal if:

1. You haven't placed any orders on Polymarket yet
2. All your orders have been filled or canceled
3. The wallet address in your .env file is different from the one you use on Polymarket

### Common Issues

1. **Missing Environment Variables**

   - Make sure your `.env` file contains both `WALLET_ADDRESS` and `WALLET_PRIVATE_KEY`
   - The format should be: `WALLET_ADDRESS=0x...` (with or without the `0x` prefix)

2. **Invalid Private Key**

   - Ensure you've exported the correct private key from Polymarket
   - The private key should be from the same account where you've placed orders

3. **Account Setup Issues**

   - Your Polymarket account must have completed at least one trade
   - If using a wallet-connected account, make sure you've set up the required allowances

4. **Connection Problems**
   - Check your internet connection
   - Polymarket API may be temporarily unavailable (try again later)

### Example Debug Workflow

If you're having trouble:

1. Verify your credentials in the `.env` file
2. Run with the `--debug` flag to see detailed API responses
3. Confirm you've placed orders on Polymarket with the same account
4. Try accessing the Polymarket website to confirm your orders are visible there
