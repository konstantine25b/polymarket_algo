import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
import time


class PolymarketDataFetcher:
    """
    Improved implementation for fetching and analyzing Polymarket data.
    With better error handling and updated API endpoints.
    """

    def __init__(self, wallet_address=None, api_key=None):
        """
        Initialize the Polymarket data fetcher.

        Args:
            wallet_address (str): The Ethereum wallet address to analyze (optional)
            api_key (str): API key for authenticated requests (required for trade data)
        """
        self.wallet_address = wallet_address
        self.api_key = api_key
        self.session = requests.Session()

        # Updated Base URLs - May 2025
        self.clob_api = "https://clob.polymarket.com"
        self.portfolio_api = "https://app.polymarket.com/api"  # Updated endpoint
        self.subgraph_api = "https://subgraph.polygon.polymarket.com/subgraphs/name/polymarket/matic-markets"

        # Configure session headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; PolymarketDataFetcher/1.0)"
        })

        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

        print(f"PolymarketDataFetcher initialized" +
              (f" for wallet: {wallet_address[:6]}...{wallet_address[-4:]}" if wallet_address else ""))

        # Validate API connectivity
        self._validate_connectivity()

    def _validate_connectivity(self):
        """Check if the API endpoints are responding"""
        try:
            # Try to fetch public market data - should work without authentication
            test_url = f"{self.portfolio_api}/markets"
            params = {"limit": 1}
            response = self.session.get(test_url, params=params, timeout=10)

            if response.status_code == 200:
                print("✓ Successfully connected to Polymarket API")
            else:
                print(f"⚠️ API connectivity test returned status code: {response.status_code}")

            # Check if we have proper authentication for private data
            if self.api_key:
                try:
                    orders_url = f"{self.clob_api}/orders"
                    params = {"limit": 1}
                    response = self.session.get(orders_url, params=params, timeout=10)
                    if response.status_code == 200:
                        print("✓ API authentication successful")
                    else:
                        print(f"⚠️ API authentication failed: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ Could not validate API authentication: {e}")
        except Exception as e:
            print(f"⚠️ API connectivity test failed: {e}")
            print("Continuing with decreased functionality...")

    def _make_request(self, method, url, params=None, data=None, retries=3, retry_delay=2):
        """
        Make an API request with error handling and retries.

        Args:
            method (str): HTTP method (get, post, etc.)
            url (str): URL to request
            params (dict): Query parameters
            data (dict): Request body for POST requests
            retries (int): Number of retries on failure
            retry_delay (int): Delay between retries in seconds

        Returns:
            dict: Response JSON or empty dict on failure
        """
        for attempt in range(retries):
            try:
                if method.lower() == 'get':
                    response = self.session.get(url, params=params, timeout=30)
                elif method.lower() == 'post':
                    response = self.session.post(url, params=params, json=data, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if "Name" in str(e) and "Resolution" in str(e):
                    print(f"⚠️ DNS resolution error for {url}. The API endpoint may have changed.")
                    # Try alternative endpoint
                    if "portfolio.polymarket.com" in url:
                        alt_url = url.replace("portfolio.polymarket.com", "app.polymarket.com/api")
                        print(f"Trying alternative URL: {alt_url}")
                        url = alt_url
                        continue
                elif response.status_code == 401:
                    print(f"⚠️ Authentication error: {e}")
                    print("API key is required for this endpoint.")
                    return {}
                elif attempt < retries - 1:
                    print(f"Request failed: {e}, retrying in {retry_delay}s... (Attempt {attempt + 1}/{retries})")
                    time.sleep(retry_delay)
                else:
                    print(f"Request failed after {retries} attempts: {e}")
                    return {}
            except Exception as e:
                print(f"Error processing request: {e}")
                return {}

        return {}  # Return empty dict if all retries fail

    def get_markets(self, limit=100, status="open"):
        """
        Get list of markets from Polymarket.

        Args:
            limit (int): Maximum number of markets to return
            status (str): Filter by market status ('open', 'closed', 'resolved')

        Returns:
            list: List of market data
        """
        url = f"{self.portfolio_api}/markets"
        params = {
            "limit": limit,
            "status": status,
            "sort": "newest"
        }

        response_data = self._make_request('get', url, params=params)
        return response_data.get('markets', [])

    def get_market_details(self, market_id):
        """
        Get detailed information about a specific market.

        Args:
            market_id (str): Unique identifier for the market

        Returns:
            dict: Market details
        """
        url = f"{self.portfolio_api}/markets/{market_id}"
        return self._make_request('get', url)

    def get_maker_trades(self, limit=100, offset=0):
        """
        Get trades where the wallet was the maker.

        Args:
            limit (int): Maximum number of trades to return
            offset (int): Offset for pagination

        Returns:
            list: List of maker trades
        """
        if not self.wallet_address:
            print("⚠️ Wallet address is required to fetch maker trades")
            return []

        if not self.api_key:
            print("⚠️ API key is required to fetch maker trades")
            return []

        url = f"{self.clob_api}/trades"
        params = {
            "makerAddress": self.wallet_address.lower(),
            "limit": limit,
            "offset": offset
        }

        response_data = self._make_request('get', url, params=params)
        return response_data.get('trades', [])

    def get_taker_trades(self, limit=100, offset=0):
        """
        Get trades where the wallet was the taker.

        Args:
            limit (int): Maximum number of trades to return
            offset (int): Offset for pagination

        Returns:
            list: List of taker trades
        """
        if not self.wallet_address:
            print("⚠️ Wallet address is required to fetch taker trades")
            return []

        if not self.api_key:
            print("⚠️ API key is required to fetch taker trades")
            return []

        url = f"{self.clob_api}/trades"
        params = {
            "takerAddress": self.wallet_address.lower(),
            "limit": limit,
            "offset": offset
        }

        response_data = self._make_request('get', url, params=params)
        return response_data.get('trades', [])

    def get_all_trades(self, max_trades=1000):
        """
        Get all trades for the wallet address (both maker and taker).
        Uses pagination to fetch more trades if needed.

        Args:
            max_trades (int): Maximum number of trades to fetch in total

        Returns:
            list: Combined list of all trades
        """
        if not self.wallet_address:
            print("⚠️ Wallet address is required to fetch trades")
            return []

        all_trades = []
        page_size = 100

        # Fetch maker trades with pagination
        offset = 0
        maker_total = 0
        while len(all_trades) < max_trades:
            maker_trades = self.get_maker_trades(limit=page_size, offset=offset)
            if not maker_trades:
                break

            all_trades.extend(maker_trades)
            maker_total += len(maker_trades)
            offset += len(maker_trades)

            if len(maker_trades) < page_size:
                break

        print(f"Found {maker_total} trades where {self.wallet_address[:6]}...{self.wallet_address[-4:]} was the maker")

        # Fetch taker trades with pagination
        offset = 0
        taker_total = 0
        while len(all_trades) < max_trades:
            taker_trades = self.get_taker_trades(limit=page_size, offset=offset)
            if not taker_trades:
                break

            all_trades.extend(taker_trades)
            taker_total += len(taker_trades)
            offset += len(taker_trades)

            if len(taker_trades) < page_size:
                break

        print(f"Found {taker_total} trades where {self.wallet_address[:6]}...{self.wallet_address[-4:]} was the taker")

        # Sort by timestamp (newest first)
        all_trades.sort(key=lambda x: x.get('createdAt', ''), reverse=True)

        return all_trades[:max_trades]

    def get_portfolio(self):
        """
        Get the current portfolio for the wallet address.
        This includes open positions and their current values.

        Returns:
            dict: Portfolio summary
        """
        if not self.wallet_address:
            print("⚠️ Wallet address is required to fetch portfolio")
            return {}

        url = f"{self.portfolio_api}/portfolio/{self.wallet_address}"
        return self._make_request('get', url)

    def calculate_positions_summary(self):
        """
        Calculate a comprehensive summary of trading positions and P&L.

        Returns:
            dict: Positions summary with P&L metrics
        """
        if not self.wallet_address:
            print("⚠️ Wallet address is required to calculate positions")
            return {
                'wallet_address': None,
                'total_markets': 0,
                'total_trades': 0,
                'total_position_value': "0",
                'pl_metrics': {
                    'total_pl': 0,
                    'total_realized_pl': 0,
                    'total_unrealized_pl': 0
                },
                'positions': {}
            }

        # Get all trades
        all_trades = self.get_all_trades()

        # Get current portfolio for current prices
        portfolio = self.get_portfolio()

        # Process trades to calculate positions
        markets = {}

        for trade in all_trades:
            market_id = trade.get('marketId')
            if market_id not in markets:
                # Get market info
                market_info = self.get_market_details(market_id)
                markets[market_id] = {
                    'name': market_info.get('question', f"Market {market_id}"),
                    'trades': [],
                    'positions': {'Yes': {'size': 0}, 'No': {'size': 0}},
                    'total_trades': 0,
                    'pl_metrics': {'total_pl': 0, 'realized_pl': 0, 'unrealized_pl': 0},
                    'position_value': 0
                }

            # Add trade to market
            markets[market_id]['trades'].append(trade)
            markets[market_id]['total_trades'] += 1

            # Update positions based on trade
            outcome = trade.get('outcome', 'Yes')
            side = trade.get('side')
            amount = float(trade.get('amount', 0))
            price = float(trade.get('price', 0))

            # Determine if we're buying or selling
            is_maker = trade.get('makerAddress', '').lower() == self.wallet_address.lower()
            is_buy = (is_maker and side == 'sell') or (not is_maker and side == 'buy')

            # Update position size
            if is_buy:
                markets[market_id]['positions'][outcome]['size'] += amount
            else:
                markets[market_id]['positions'][outcome]['size'] -= amount

            # Store last trade time
            markets[market_id]['positions'][outcome]['last_trade_time'] = trade.get('createdAt')

            # Calculate P&L (simplified)
            # For accurate P&L, we need current market prices
            # This is just an estimate based on trade prices
            markets[market_id]['pl_metrics']['total_pl'] += amount * ((1 - price) if is_buy else price)

        # Update with current market prices from portfolio if available
        if portfolio and 'positions' in portfolio:
            for position in portfolio.get('positions', []):
                market_id = position.get('marketId')
                if market_id in markets:
                    current_value = float(position.get('value', 0))
                    markets[market_id]['position_value'] = current_value

        # Calculate summary metrics
        total_position_value = sum(m.get('position_value', 0) for m in markets.values())
        total_pl = sum(m.get('pl_metrics', {}).get('total_pl', 0) for m in markets.values())
        total_realized_pl = sum(m.get('pl_metrics', {}).get('realized_pl', 0) for m in markets.values())
        total_unrealized_pl = sum(m.get('pl_metrics', {}).get('unrealized_pl', 0) for m in markets.values())

        # Build the full summary
        summary = {
            'wallet_address': self.wallet_address,
            'total_markets': len(markets),
            'total_trades': sum(m.get('total_trades', 0) for m in markets.values()),
            'total_position_value': str(total_position_value),
            'pl_metrics': {
                'total_pl': total_pl,
                'total_realized_pl': total_realized_pl,
                'total_unrealized_pl': total_unrealized_pl
            },
            'positions': markets
        }

        return summary

    def export_trades_to_csv(self, filepath=None):
        """
        Export all trades to a CSV file for analysis.

        Args:
            filepath (str): Path to save the CSV file (optional)

        Returns:
            str: Path to the saved CSV file
        """
        trades = self.get_all_trades()

        if not trades:
            print("⚠️ No trades found to export")
            # Create empty DataFrame with expected columns
            df = pd.DataFrame(columns=[
                'id', 'marketId', 'makerAddress', 'takerAddress',
                'outcome', 'side', 'amount', 'price', 'createdAt'
            ])
        else:
            df = pd.DataFrame(trades)

        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            address_short = f"{self.wallet_address[:6]}_{self.wallet_address[-4:]}" if self.wallet_address else "no_wallet"
            filepath = f"polymarket_trades_{address_short}_{timestamp}.csv"

        df.to_csv(filepath, index=False)
        print(f"Exported {len(trades)} trades to {filepath}")

        return filepath

    def save_positions_summary(self, filepath=None):
        """
        Calculate and save positions summary to a JSON file.

        Args:
            filepath (str): Path to save the JSON file (optional)

        Returns:
            str: Path to the saved JSON file
        """
        summary = self.calculate_positions_summary()

        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            address_short = f"{self.wallet_address[:6]}_{self.wallet_address[-4:]}" if self.wallet_address else "no_wallet"
            filepath = f"polymarket_positions_{address_short}_{timestamp}.json"

        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"Saved positions summary to {filepath}")
        return filepath


# Example usage
if __name__ == "__main__":
    # Replace with your wallet address and API key
    WALLET_ADDRESS = "0x08E9Fa6d9De086eed6a83A8bE9A54ccC9478b776"
    API_KEY = None  # Add your API key here if you have one

    # Get API key from environment variable if available
    if not API_KEY:
        API_KEY = os.environ.get("POLYMARKET_API_KEY")

    print("\n" + "=" * 50)
    print(" POLYMARKET DATA FETCHER ")
    print("=" * 50 + "\n")

    # Create the data fetcher
    fetcher = PolymarketDataFetcher(wallet_address=WALLET_ADDRESS, api_key=API_KEY)

    # Display API key status
    if not API_KEY:
        print("⚠️ No API key provided - some functionality will be limited")
        print("To use all features, set the POLYMARKET_API_KEY environment variable")
        print("or update the API_KEY variable in the script.\n")

    # Get and display market data
    try:
        print("\nFetching recent markets...")
        markets = fetcher.get_markets(limit=5)

        if markets:
            print(f"\nRecent Markets:")
            for market in markets:
                print(f"- {market.get('question')} (Volume: ${float(market.get('volume', 0)):.2f})")
        else:
            print("No market data available")
    except Exception as e:
        print(f"Error getting market data: {e}")

    # Only proceed with trade analysis if we have an API key
    if API_KEY:
        # Get and analyze trades
        try:
            print("\nFetching trade data...")
            trades = fetcher.get_all_trades(max_trades=500)
            print(f"\nFound {len(trades)} total trades")

            # Export trades to CSV
            csv_path = fetcher.export_trades_to_csv()

            # Calculate and save positions summary
            summary_path = fetcher.save_positions_summary()

            # Print summary stats
            summary = fetcher.calculate_positions_summary()
            print(f"\nAccount Summary for {WALLET_ADDRESS[:6]}...{WALLET_ADDRESS[-4:]}")
            print(f"Total Markets: {summary['total_markets']}")
            print(f"Total Trades: {summary['total_trades']}")
            print(f"Total P&L: ${summary['pl_metrics']['total_pl']:.2f}")
            print(f"Total Position Value: ${float(summary['total_position_value']):.2f}")
        except Exception as e:
            print(f"Error analyzing trade data: {e}")
    else:
        print("\n⚠️ Skipping trade analysis - API key required")

    print("\n" + "=" * 50)
    print(" COMPLETED ")
    print("=" * 50 + "\n")