import os
# Force matplotlib to not use any Xwindows backend before importing pyplot
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend that doesn't require a display
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import json
import logging
import numpy as np
import requests
from datetime import datetime
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import TradeParams
from src.constants import POLYMARKET_API_HOST

class PolymarketPositionTracker:
    """
    A class to track and analyze your current positions on Polymarket based on trade history.
    """
    
    def __init__(self, output_dir='output', log_level=logging.INFO, key=None):
        """
        Initialize the PolymarketPositionTracker with credentials.
        
        Args:
            output_dir (str): Directory to save output files.
            log_level: Logging level to use.
            key (str, optional): Wallet private key. If None, loads from environment.
        """
        # Set up output directory
        if output_dir is None:
            output_dir = 'output'
        
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_dir)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Set up logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('PolymarketPositionTracker')
        
        # Load environment variables if key not provided
        if not key:
            load_dotenv()
            key = os.getenv("WALLET_PRIVATE_KEY")
        key = "0xce0bfa9ca4fb4d80459172c711609cce995188b40215b8652f656e801ea60daf"
            
        if not key:
            raise ValueError("Wallet private key is required. Please provide it or set WALLET_PRIVATE_KEY in .env")
            
        # Initialize CLOB client
        host = "https://clob.polymarket.com"
        self.polymarket_api = POLYMARKET_API_HOST
        chain_id = POLYGON
        self.client = ClobClient(host, key=key, chain_id=chain_id)
        
        # Set up API credentials
        self.client.set_api_creds(self.client.create_or_derive_api_creds())
        
        # Get wallet address
        self.wallet_address = self.client.get_address()
        self.logger.info(f"Connected to Polymarket CLOB API with wallet: {self.wallet_address[:8]}...")
        
        # Cache for market info
        self.market_info_cache = {}
        
    def get_market_info(self, market_id):
        """
        Get market information from Polymarket API.
        
        Args:
            market_id (str): The market ID to fetch information for.
            
        Returns:
            dict: Market information including name, description, etc.
        """
        # Check cache first
        if market_id in self.market_info_cache:
            return self.market_info_cache[market_id]
            
        try:
            # Try multiple potential endpoints for market data
            endpoints = [
                f"{self.polymarket_api}/markets/{market_id}",
                f"{self.polymarket_api}/v2/markets/{market_id}",
                f"https://clob.polymarket.com/markets/{market_id}"  # Alternative endpoint
            ]
            
            for url in endpoints:
                response = requests.get(url)
                
                if response.status_code == 200:
                    market_data = response.json()
                    self.market_info_cache[market_id] = market_data
                    self.logger.debug(f"Successfully fetched market info for {market_id[:10]}...")
                    return market_data
                    
            # If we reach here, none of the endpoints worked
            # Create a fallback market info object
            fallback_market_info = {
                'question': f"Market {market_id[:10]}...",
                'market_id': market_id,
                'description': "Market information unavailable"
            }
            self.market_info_cache[market_id] = fallback_market_info
            self.logger.warning(f"Could not fetch market info for {market_id} from any endpoints")
            return fallback_market_info
        except Exception as e:
            self.logger.warning(f"Error fetching market info: {e}")
            # Create a fallback market info object
            fallback_market_info = {
                'question': f"Market {market_id[:10]}...",
                'market_id': market_id,
                'description': "Market information unavailable"
            }
            self.market_info_cache[market_id] = fallback_market_info
            return fallback_market_info
            
    def get_market_name(self, market_id):
        """
        Get the full name of a market.
        
        Args:
            market_id (str): The market ID to fetch the name for.
            
        Returns:
            str: Full market name or shortened market ID if not found.
        """
        market_info = self.get_market_info(market_id)
        # Try different potential field names for the market name
        for field in ['question', 'title', 'name', 'description']:
            if market_info and field in market_info and market_info[field]:
                return market_info[field]
        
        # If we couldn't find a suitable name, return a shortened version of the market ID
        # This makes it easier to read in tables and visualizations
        return f"Market {market_id[:16]}..."

    def get_my_trades(self):
        """
        Get all trades associated with the current wallet address.
        
        Returns:
            list: List of trade data dictionaries.
        """
        self.logger.info(f"Fetching trades for address: {self.wallet_address[:8]}...")
        
        # Get trades where you were the maker
        maker_params = TradeParams(maker_address=self.wallet_address)
        maker_trades = self.client.get_trades(maker_params)
        self.logger.info(f"Found {len(maker_trades)} trades where you were the maker")
        
        # Get all trades for now and filter locally - TradeParams doesn't support taker_address
        all_trades = self.client.get_trades(TradeParams())
        
        # Filter for trades where you were the taker
        # Compare by ID to avoid duplicates
        maker_ids = {trade.get('id') for trade in maker_trades}
        taker_trades = [
            trade for trade in all_trades 
            if trade.get('taker_address', '').lower() == self.wallet_address.lower() 
            and trade.get('id') not in maker_ids
        ]
        self.logger.info(f"Found {len(taker_trades)} trades where you were the taker")
        
        # Combine both sets of trades
        all_my_trades = maker_trades + taker_trades
        self.logger.info(f"Found {len(all_my_trades)} total trades")
        
        return all_my_trades
    
    def get_trades_by_market(self, market_id):
        """
        Get your trades for a specific market.
        
        Args:
            market_id (str): The market ID to filter trades by.
            
        Returns:
            list: List of trade data dictionaries for the specified market.
        """
        # Get trades where you were the maker for this market
        maker_params = TradeParams(maker_address=self.wallet_address, market=market_id)
        maker_trades = self.client.get_trades(maker_params)
        self.logger.info(f"Found {len(maker_trades)} maker trades for market {market_id}")
        
        # Get all trades for this market and filter for ones where you were the taker
        market_params = TradeParams(market=market_id)
        market_trades = self.client.get_trades(market_params)
        
        # Compare by ID to avoid duplicates
        maker_ids = {trade.get('id') for trade in maker_trades}
        taker_trades = [
            trade for trade in market_trades 
            if trade.get('taker_address', '').lower() == self.wallet_address.lower() 
            and trade.get('id') not in maker_ids
        ]
        self.logger.info(f"Found {len(taker_trades)} taker trades for market {market_id}")
        
        # Combine both sets
        all_trades = maker_trades + taker_trades
        self.logger.info(f"Found {len(all_trades)} total trades for market {market_id}")
        
        return all_trades
    
    def trades_to_dataframe(self, trades_data):
        """
        Convert trades data to a pandas DataFrame for analysis with gain/loss calculations.
        
        Args:
            trades_data (list): List of trade data dictionaries.
            
        Returns:
            pandas.DataFrame: DataFrame with trade data including gain/loss metrics.
        """
        if not trades_data:
            return pd.DataFrame()
            
        # Flatten any nested structures in the trade data
        flattened_trades = []
        
        for trade in trades_data:
            trade_copy = trade.copy()
            
            # Convert timestamps to datetime objects
            if 'match_time' in trade_copy:
                trade_copy['match_time'] = datetime.fromtimestamp(int(trade_copy['match_time']))
                
            # Extract maker/taker information to determine direction
            is_maker = self.wallet_address.lower() == trade_copy.get('maker_address', '').lower()
            is_taker = self.wallet_address.lower() == trade_copy.get('taker_address', '').lower()
            
            # Determine if we're buying or selling based on maker/taker and side
            trade_copy['is_maker'] = is_maker
            trade_copy['is_taker'] = is_taker
            
            if is_maker:
                # If I'm the maker, the side is as stated
                trade_copy['my_side'] = trade_copy.get('side')
            elif is_taker:
                # If I'm the taker, the side is the opposite of what's stated
                if trade_copy.get('side') == 'BUY':
                    trade_copy['my_side'] = 'SELL'
                else:
                    trade_copy['my_side'] = 'BUY'
            
            # Calculate position impact
            size = float(trade_copy.get('size', 0))
            price = float(trade_copy.get('price', 0))
            
            # Calculate dollar value
            dollar_value = price * size
            
            if trade_copy.get('my_side') == 'BUY':
                trade_copy['position_impact'] = size
                trade_copy['cost_basis'] = dollar_value
                # For buys, cost is negative (money spent)
                trade_copy['gain_loss_usd'] = -dollar_value
                trade_copy['percent_change'] = None  # Not applicable for initial buy
            else:
                trade_copy['position_impact'] = -size
                trade_copy['sale_value'] = dollar_value
                # For sells, gain is positive (money received)
                trade_copy['gain_loss_usd'] = dollar_value
                # We don't have previous cost basis here - calculated later
                trade_copy['percent_change'] = None  # Will be calculated later
            
            flattened_trades.append(trade_copy)
            
        df = pd.DataFrame(flattened_trades)
        
        # Calculate market-level gain/loss
        if not df.empty and 'market' in df.columns:
            # Group by market and calculate gain/loss for each market
            market_gains = {}
            
            for market_id, market_df in df.groupby('market'):
                # Sort by time to process in chronological order
                market_df = market_df.sort_values('match_time')
                
                # Track running cost basis and inventory for each outcome
                outcome_inventory = {}
                outcome_cost_basis = {}
                outcome_realized_pl = {}
                outcome_data_dict = {}  # Dictionary to store price and other data for each outcome
                
                # Initialize for tracking by outcome
                for outcome in market_df['outcome'].unique():
                    outcome_inventory[outcome] = 0
                    outcome_cost_basis[outcome] = 0
                    outcome_realized_pl[outcome] = 0
                    outcome_data_dict[outcome] = {'current_price': 0}  # Initialize with current price
                
                # Process each trade to update cost basis and calculate P&L
                for idx, row in market_df.iterrows():
                    outcome = row['outcome']
                    size = float(row['size'])
                    price = float(row['price'])
                    dollar_value = price * size
                    
                    # Update the current price for this outcome
                    outcome_data_dict[outcome]['current_price'] = price
                    
                    if row['my_side'] == 'BUY':
                        # For buys, add to inventory and cost basis
                        new_size = outcome_inventory[outcome] + size
                        new_cost = outcome_cost_basis[outcome] + dollar_value
                        
                        # Update average cost basis
                        outcome_inventory[outcome] = new_size
                        outcome_cost_basis[outcome] = new_cost
                        
                        # Update the row with the average cost basis
                        df.at[idx, 'avg_cost_basis'] = new_cost / new_size if new_size > 0 else 0
                        
                    else:  # SELL
                        if outcome_inventory[outcome] > 0:
                            # Calculate average cost basis per share
                            avg_cost_per_share = outcome_cost_basis[outcome] / outcome_inventory[outcome] if outcome_inventory[outcome] > 0 else 0
                            
                            # Calculate realized P&L for this trade
                            realized_pl = (price - avg_cost_per_share) * size
                            
                            # Update realized P&L
                            outcome_realized_pl[outcome] += realized_pl
                            
                            # Reduce inventory and cost basis proportionally
                            if size <= outcome_inventory[outcome]:
                                cost_reduction = (size / outcome_inventory[outcome]) * outcome_cost_basis[outcome]
                                outcome_inventory[outcome] -= size
                                outcome_cost_basis[outcome] -= cost_reduction
                            else:
                                # Selling more than we have (e.g., going short)
                                outcome_inventory[outcome] = -size + outcome_inventory[outcome]
                                outcome_cost_basis[outcome] = 0  # Reset cost basis when going short
                            
                            # Update the row with realized P&L
                            df.at[idx, 'gain_loss_usd'] = realized_pl
                            df.at[idx, 'percent_change'] = (price / avg_cost_per_share - 1) * 100 if avg_cost_per_share > 0 else None
                            df.at[idx, 'avg_cost_basis'] = avg_cost_per_share
                
                # Calculate total gain/loss for this market
                total_realized_pl = sum(outcome_realized_pl.values())
                
                # Calculate unrealized P&L safely
                unrealized_pl = 0
                for outcome in outcome_inventory.keys():
                    # Only calculate for outcomes where we have a position
                    if outcome_inventory[outcome] > 0:
                        # Get the latest price safely
                        current_price = outcome_data_dict[outcome]['current_price']
                        try:
                            filtered_df = df[df['market'] == market_id]
                            outcome_df = filtered_df[filtered_df['outcome'] == outcome]
                            if not outcome_df.empty:
                                current_price = float(outcome_df.iloc[-1]['price'])
                                outcome_data_dict[outcome]['current_price'] = current_price
                        except (IndexError, TypeError, ValueError) as e:
                            self.logger.warning(f"Error getting latest price for {outcome}: {e}")
                        
                        # Calculate unrealized P&L for this outcome
                        current_value = current_price * outcome_inventory[outcome]
                        outcome_unrealized_pl = current_value - outcome_cost_basis[outcome]
                        unrealized_pl += outcome_unrealized_pl
                
                # Store all outcome data in market_gains
                market_gains[market_id] = {
                    'realized_pl': total_realized_pl,
                    'unrealized_pl': unrealized_pl,
                    'total_pl': total_realized_pl + unrealized_pl,
                    'by_outcome': {outcome: {
                        'inventory': outcome_inventory[outcome],
                        'cost_basis': outcome_cost_basis[outcome],
                        'realized_pl': outcome_realized_pl[outcome],
                        'current_price': outcome_data_dict[outcome]['current_price']
                    } for outcome in outcome_inventory.keys()}
                }
            
            # Store market gains in the class instance for access by other methods
            self.market_gains = market_gains
            
            # Calculate total gain/loss across all markets
            total_realized_pl = sum([market['realized_pl'] for market in market_gains.values()])
            total_unrealized_pl = sum([market['unrealized_pl'] for market in market_gains.values()])
            
            self.total_gains = {
                'realized_pl': total_realized_pl,
                'unrealized_pl': total_unrealized_pl,
                'total_pl': total_realized_pl + total_unrealized_pl
            }
        
        return df
    
    def calculate_positions(self, df=None):
        """
        Calculate current positions based on trade history.
        
        Args:
            df (pandas.DataFrame, optional): DataFrame of trades. If None, fetches all trades.
            
        Returns:
            dict: Dictionary with position information grouped by market and outcome.
        """
        if df is None:
            trades = self.get_my_trades()
            df = self.trades_to_dataframe(trades)
            
        if df.empty:
            self.logger.warning("No trades found to calculate positions")
            return {}
            
        # Group by market and outcome to get position totals
        positions = {}
        
        # Ensure required columns exist
        required_cols = ['market', 'outcome', 'position_impact']
        if not all(col in df.columns for col in required_cols):
            self.logger.error(f"DataFrame missing required columns: {required_cols}")
            return positions
        
        # Group by market first
        market_groups = df.groupby('market')
        
        for market, market_df in market_groups:
            # Get full market name
            market_name = self.get_market_name(market)
            
            # Calculate position for each outcome within this market
            outcome_groups = market_df.groupby('outcome')
            
            market_positions = {}
            for outcome, outcome_df in outcome_groups:
                # Sum the position impacts
                position_size = outcome_df['position_impact'].sum()
                
                # Only include non-zero positions
                if position_size != 0:
                    market_positions[outcome] = {
                        'size': position_size,
                        'trades': len(outcome_df),
                        'last_trade_time': outcome_df['match_time'].max().isoformat() if 'match_time' in outcome_df.columns else None
                    }
            
            # Only include markets with at least one non-zero position
            if market_positions:
                positions[market] = {
                    'name': market_name,
                    'positions': market_positions,
                    'total_trades': len(market_df)
                }
        
        return positions
    
    def get_detailed_positions(self):
        """
        Get a comprehensive analysis of current positions.
        
        Returns:
            dict: Dictionary with detailed position information.
        """
        # Get all trades and convert to DataFrame
        trades = self.get_my_trades()
        df = self.trades_to_dataframe(trades)
        
        if df.empty:
            self.logger.warning("No trades found")
            return {'error': 'No trades found'}
        
        # Calculate basic positions
        positions = self.calculate_positions(df)
        
        # Enhance with additional metrics
        result = {
            'wallet_address': self.wallet_address,
            'total_markets': len(positions),
            'total_trades': len(df),
            'positions': positions,
            'last_updated': datetime.now().isoformat()
        }
        
        # Calculate some high-level stats
        market_count = len(positions)
        active_positions = sum(len(market_data['positions']) for market_data in positions.values())
        
        result['summary'] = {
            'active_markets': market_count,
            'active_positions': active_positions,
            'first_trade_time': df['match_time'].min().isoformat() if 'match_time' in df.columns and not df.empty else None,
            'last_trade_time': df['match_time'].max().isoformat() if 'match_time' in df.columns and not df.empty else None
        }
        
        return result
    
    def visualize_trade_history(self, trades_df=None, market_id=None, save=True, show=True):
        """
        Create visualization of trade history.
        
        Args:
            trades_df (pandas.DataFrame, optional): DataFrame of trades to visualize.
            market_id (str, optional): Filter trades for specific market ID.
            save (bool): Whether to save visualizations to files.
            show (bool): Whether to display the visualizations.
            
        Returns:
            dict: Paths to saved visualization files.
        """
        # Set up output directory for visualizations
        viz_dir = os.path.join(self.output_dir, 'visualizations')
        if not os.path.exists(viz_dir):
            os.makedirs(viz_dir)
            
        saved_files = {}
        
        # Get trades if not provided
        if trades_df is None:
            trades_list = self.get_my_trades()
            trades_df = self.trades_to_dataframe(trades_list)
            
        if trades_df.empty:
            self.logger.warning("No trades to visualize")
            return saved_files
            
        # Filter for specific market if requested
        if market_id:
            trades_df = trades_df[trades_df['market'] == market_id]
            if trades_df.empty:
                self.logger.warning(f"No trades found for market {market_id}")
                return saved_files
                
        # Sort by time
        if 'match_time' in trades_df.columns:
            trades_df = trades_df.sort_values('match_time')
        else:
            self.logger.warning("Trade data missing match_time column")
            return saved_files
            
        # Set up plot style
        plt.style.use('dark_background')
        
        # Create figure
        trade_fig, trade_ax = plt.subplots(figsize=(14, 8))
        
        # Group trades by market
        market_groups = trades_df.groupby('market')
        
        # Different colors for different markets
        colors = plt.cm.tab10.colors
        
        # Keep track of legend entries to avoid duplicates
        legend_entries = set()
        
        # Plot trades for each market
        for i, (market_id, market_trades) in enumerate(market_groups):
            color_idx = i % len(colors)
            market_color = colors[color_idx]
            
            # Get market name
            market_name = self.get_market_name(market_id)
            short_name = market_name[:30] + ('...' if len(market_name) > 30 else '')
            
            # Only add ID to the display name if it's not already in the market name
            if not market_name.endswith(market_id) and not market_name.startswith("Market "):
                market_display = f"{short_name} ({market_id[:16]}...)"
            else:
                market_display = short_name
            
            # Plot buy trades
            buys = market_trades[market_trades['my_side'] == 'BUY']
            if not buys.empty:
                # Convert to numeric to ensure plot works correctly
                buys['price_num'] = pd.to_numeric(buys['price'], errors='coerce')
                # Drop any NaN values
                buys = buys.dropna(subset=['price_num'])
                
                if not buys.empty:
                    # Create scatter with fixed size first
                    scatter = trade_ax.scatter(
                        buys['match_time'],
                        buys['price_num'],
                        marker='^',
                        s=100,  # Fixed size first
                        color=market_color,
                        alpha=0.7,
                        label=f"{market_display} - Buys" if market_display not in legend_entries else "_nolegend_"
                    )
                    
                    # Add market to legend entries
                    legend_entries.add(market_display)
                    
                    # Add annotations for each trade
                    for _, row in buys.iterrows():
                        trade_ax.annotate(
                            f"{row['outcome']} - {float(row['size']):.2f} @ ${float(row['price']):.2f}",
                            xy=(row['match_time'], row['price_num']),
                            xytext=(5, 5),
                            textcoords="offset points",
                            ha='left',
                            va='bottom',
                            fontsize=8,
                            color='white',
                            bbox=dict(boxstyle="round,pad=0.3", fc=market_color, alpha=0.3)
                        )
            
            # Plot sell trades
            sells = market_trades[market_trades['my_side'] == 'SELL']
            if not sells.empty:
                # Convert to numeric to ensure plot works correctly
                sells['price_num'] = pd.to_numeric(sells['price'], errors='coerce')
                # Drop any NaN values
                sells = sells.dropna(subset=['price_num'])
                
                if not sells.empty:
                    # Create scatter with fixed size
                    scatter = trade_ax.scatter(
                        sells['match_time'],
                        sells['price_num'],
                        marker='v',
                        s=100,  # Fixed size
                        color=market_color,
                        alpha=0.7,
                        label=f"{market_display} - Sells" if f"{market_display} - Sells" not in legend_entries else "_nolegend_"
                    )
                    
                    # Add to legend entries
                    legend_entries.add(f"{market_display} - Sells")
                    
                    # Add annotations for each trade
                    for _, row in sells.iterrows():
                        trade_ax.annotate(
                            f"{row['outcome']} - {float(row['size']):.2f} @ ${float(row['price']):.2f}",
                            xy=(row['match_time'], row['price_num']),
                            xytext=(5, -5),
                            textcoords="offset points",
                            ha='left',
                            va='top',
                            fontsize=8,
                            color='white',
                            bbox=dict(boxstyle="round,pad=0.3", fc=market_color, alpha=0.3)
                        )
        
        # Style the chart
        if market_id:
            if len(market_id) > 20:
                display_id = f"{market_id[:16]}..."
            else:
                display_id = market_id
            title = f"Trade History - {display_id}"
        else:
            title = "Complete Trade History"
        
        trade_ax.set_title(title, fontsize=16)
        trade_ax.set_xlabel('Date', fontsize=12)
        trade_ax.set_ylabel('Price', fontsize=12)
        
        # Add legend if we have entries
        if legend_entries:
            trade_ax.legend(title="Trades", loc="upper left")
            
        trade_ax.grid(True, alpha=0.3)
        
        # Format x-axis as dates
        trade_ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
        trade_ax.xaxis.set_major_locator(plt.matplotlib.dates.AutoDateLocator())
        plt.setp(trade_ax.xaxis.get_majorticklabels(), rotation=45)
        
        # Add a note about market IDs
        trade_ax.text(
            0.01, 0.01, 
            "Note: Hover over points to see trade details. Full market IDs available in position summary.",
            transform=trade_ax.transAxes, fontsize=8, alpha=0.7
        )
        
        # Save the chart
        if save:
            filename = f"trades_{market_id}" if market_id else "all_trades"
            trade_history_path = os.path.join(viz_dir, f"{filename}_history.png")
            plt.tight_layout()
            plt.savefig(trade_history_path, dpi=300, bbox_inches='tight')
            saved_files['trade_history'] = trade_history_path
            
        if show:
            plt.show()
        else:
            plt.close('all')
            
        return saved_files
        
    def visualize_positions_chart(self, positions=None, save=True, show=True):
        """
        Create a chart visualization of current positions.
        
        Args:
            positions (dict, optional): Position data to visualize. If None, fetches current positions.
            save (bool): Whether to save visualizations to files.
            show (bool): Whether to display the visualizations.
            
        Returns:
            dict: Paths to saved visualization files.
        """
        if positions is None:
            positions = self.get_detailed_positions()
            
        if 'error' in positions or not positions.get('positions'):
            self.logger.warning("No positions to visualize")
            return {}
            
        # Set up plot style
        plt.style.use('dark_background')
        
        # Create output directory for visualizations
        viz_dir = os.path.join(self.output_dir, 'visualizations')
        if not os.path.exists(viz_dir):
            os.makedirs(viz_dir)
            
        saved_files = {}
        
        # Collect position data
        position_data = []
        
        for market_id, market_data in positions['positions'].items():
            market_name = market_data['name']
            
            for outcome, position_data_item in market_data['positions'].items():
                position_data.append({
                    'market_id': market_id,
                    'market_name': market_name,
                    'outcome': outcome,
                    'size': position_data_item['size'],
                    'trades': position_data_item.get('trades', 0)
                })
                
        # Convert to DataFrame
        df = pd.DataFrame(position_data)
        
        if df.empty:
            self.logger.warning("No position data to visualize")
            return saved_files
            
        # Create a bubble chart of positions
        bubble_fig, bubble_ax = plt.subplots(figsize=(16, 10))
        
        # Group by market for coloring
        market_ids = df['market_id'].unique()
        colors = plt.cm.tab10.colors
        
        # Dictionary to map market ID to color
        color_map = {market_id: colors[i % len(colors)] for i, market_id in enumerate(market_ids)}
        
        # Create a scatter plot for each market
        for market_id in market_ids:
            market_df = df[df['market_id'] == market_id]
            market_name = market_df['market_name'].iloc[0]
            short_name = market_name[:30] + ('...' if len(market_name) > 30 else '')
            
            # Only add ID to the display name if it's not already in the market name
            if not market_name.endswith(market_id) and not market_name.startswith("Market "):
                display_name = f"{short_name} ({market_id[:16]}...)"
            else:
                display_name = short_name
            
            sizes = market_df['trades'] * 100  # Scale by number of trades
            sizes = sizes.clip(100, 2000)  # Min/max size
            
            # Create the scatter
            scatter = bubble_ax.scatter(
                range(len(market_df)),  # X position (just for spreading out points)
                market_df['size'],  # Y position (actual position size)
                s=sizes,  # Size based on number of trades
                color=color_map[market_id],
                alpha=0.7,
                label=display_name,
                edgecolors='white',
                linewidths=1
            )
            
            # Add labels for each position
            for i, (_, row) in enumerate(market_df.iterrows()):
                bubble_ax.annotate(
                    f"{row['outcome']}",
                    xy=(i, row['size']),
                    xytext=(0, 0),
                    textcoords="offset points",
                    ha='center',
                    va='center',
                    fontsize=10,
                    weight='bold',
                    color='white'
                )
                
                # Add position size below outcome
                bubble_ax.annotate(
                    f"{row['size']:.2f}",
                    xy=(i, row['size']),
                    xytext=(0, -18 if row['size'] > 0 else 18),  # Position above or below depending on sign
                    textcoords="offset points",
                    ha='center',
                    va='center',
                    fontsize=9,
                    color='white',
                    bbox=dict(boxstyle="round,pad=0.2", fc=color_map[market_id], alpha=0.3)
                )
                
        # Style the chart
        bubble_ax.set_title('Current Positions Overview', fontsize=16)
        bubble_ax.set_xlabel('', fontsize=12)
        bubble_ax.set_ylabel('Position Size (shares)', fontsize=12)
        
        # Remove x-axis ticks since they're meaningless
        bubble_ax.set_xticks([])
        
        # Add a zero line
        bubble_ax.axhline(y=0, color='white', linestyle='-', alpha=0.3)
        
        # Add legend
        bubble_ax.legend(title="Markets (bubble size = number of trades)", loc="upper left", bbox_to_anchor=(1, 1))
        
        # Add grid for y-axis only
        bubble_ax.grid(True, axis='y', alpha=0.3)
        
        # Save the chart
        if save:
            bubble_chart_path = os.path.join(viz_dir, "positions_bubble_chart.png")
            plt.tight_layout()
            plt.savefig(bubble_chart_path, dpi=300, bbox_inches='tight')
            saved_files['positions_bubble_chart'] = bubble_chart_path
            
        if show:
            plt.show()
        else:
            plt.close('all')
            
        return saved_files
    
    def visualize_positions(self, positions=None, save=True, show=True):
        """
        Create visualizations for position data.
        
        Args:
            positions (dict, optional): Position data to visualize. If None, fetches current positions.
            save (bool): Whether to save visualizations to files.
            show (bool): Whether to display the visualizations.
            
        Returns:
            dict: Paths to saved visualization files.
        """
        if positions is None:
            positions = self.get_detailed_positions()
            
        if 'error' in positions or not positions.get('positions'):
            self.logger.warning("No positions to visualize")
            return {}
            
        # Set up plot style
        plt.style.use('dark_background')
        
        # Create output directory for visualizations
        viz_dir = os.path.join(self.output_dir, 'visualizations')
        if not os.path.exists(viz_dir):
            os.makedirs(viz_dir)
            
        saved_files = {}
        
        # 1. Create a pie chart of positions by market
        market_fig, market_ax = plt.subplots(figsize=(12, 8))
        
        # Prepare data
        market_labels = []
        market_sizes = []
        for market_id, market_data in positions['positions'].items():
            # Sum the absolute value of all positions
            market_size = sum(abs(pos_data['size']) for pos_data in market_data['positions'].values())
            # Create a short display label but keep full ID for tooltip
            display_label = market_data['name'][:50] + ('...' if len(market_data['name']) > 50 else '')
            market_labels.append(display_label)
            market_sizes.append(market_size)
            
        # Create the pie chart
        wedges, texts, autotexts = market_ax.pie(
            market_sizes, 
            labels=None, 
            autopct='%1.1f%%',
            startangle=90,
            wedgeprops={'width': 0.5, 'edgecolor': 'w'}
        )
        
        # Style the pie chart
        plt.setp(autotexts, size=10, weight="bold")
        market_ax.set_title('Position Size by Market', fontsize=16)
        market_ax.legend(wedges, market_labels, title="Markets", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
        
        if save:
            market_pie_path = os.path.join(viz_dir, 'positions_by_market_pie.png')
            plt.tight_layout()
            plt.savefig(market_pie_path, dpi=300, bbox_inches='tight')
            saved_files['market_pie_chart'] = market_pie_path
            
        # 2. Create a horizontal bar chart of all positions
        position_fig, position_ax = plt.subplots(figsize=(16, max(8, len(positions['positions']) * 1.2)))
        
        # Prepare data
        all_position_labels = []
        all_position_sizes = []
        all_position_colors = []
        all_market_ids = []
        
        for market_id, market_data in positions['positions'].items():
            for outcome, position_data in market_data['positions'].items():
                # Create a display label with name and outcome
                display_label = f"{market_data['name'][:40]}... - {outcome}" if len(market_data['name']) > 40 else f"{market_data['name']} - {outcome}"
                position_size = position_data['size']
                all_position_labels.append(display_label)
                all_position_sizes.append(position_size)
                all_position_colors.append('green' if position_size > 0 else 'red')
                all_market_ids.append(market_id)
                
        # Sort by position size
        sorted_positions = sorted(zip(all_position_labels, all_position_sizes, all_position_colors, all_market_ids), 
                                   key=lambda x: abs(x[1]), reverse=True)
        
        # Unpack sorted data
        all_position_labels = [item[0] for item in sorted_positions]
        all_position_sizes = [item[1] for item in sorted_positions]
        all_position_colors = [item[2] for item in sorted_positions]
        all_market_ids = [item[3] for item in sorted_positions]
        
        # Create horizontal bar chart
        bars = position_ax.barh(all_position_labels, all_position_sizes, color=all_position_colors)
        
        # Add values to the end of each bar
        for i, bar in enumerate(bars):
            position_ax.text(
                bar.get_width() + (0.5 if bar.get_width() >= 0 else -3), 
                bar.get_y() + bar.get_height()/2, 
                f'{all_position_sizes[i]:.2f}',
                va='center',
                fontsize=10
            )
            
        # Style the chart
        position_ax.set_title('All Positions by Size', fontsize=16)
        position_ax.set_xlabel('Position Size (shares)', fontsize=12)
        position_ax.axvline(x=0, color='white', linestyle='-', alpha=0.3)
        position_ax.grid(True, alpha=0.2)
        
        # Add market IDs as annotations
        for i, (label, market_id) in enumerate(zip(all_position_labels, all_market_ids)):
            position_ax.annotate(
                f"Market ID: {market_id}",
                xy=(0, i),
                xytext=(-10, 0),
                textcoords="offset points",
                ha='right',
                va='center',
                fontsize=8,
                color='lightgray',
                alpha=0.7
            )
        
        if save:
            position_bar_path = os.path.join(viz_dir, 'all_positions_bar.png')
            plt.tight_layout()
            plt.savefig(position_bar_path, dpi=300, bbox_inches='tight')
            saved_files['position_bar_chart'] = position_bar_path
        
        # 3. Call the trade history visualization (simplified version)
        trades_list = self.get_my_trades()
        trades_df = self.trades_to_dataframe(trades_list)
        if not trades_df.empty:
            trade_history_files = self.visualize_trade_history(trades_df, save=save, show=False)
            saved_files.update(trade_history_files)
        
        # 4. Call the bubble chart visualization
        bubble_chart_files = self.visualize_positions_chart(positions, save=save, show=False)
        saved_files.update(bubble_chart_files)
        
        # 5. Create a position summary dashboard
        summary_fig = plt.figure(figsize=(16, 16))  # Increased height for trade history
        summary_fig.suptitle(f'Polymarket Position Summary - {positions["wallet_address"]}', 
                           fontsize=18, fontweight='bold')
        
        # Add text info
        summary_text = (
            f"Total Markets: {positions['total_markets']}\n"
            f"Total Trades: {positions['total_trades']}\n"
            f"Active Positions: {positions['summary']['active_positions']}\n"
            f"Last Updated: {positions['last_updated'][:19]}"
        )
        summary_fig.text(0.5, 0.97, summary_text, ha='center', fontsize=12, 
                       bbox=dict(facecolor='#333333', alpha=0.5, boxstyle='round,pad=1'))
        
        # Add pie chart
        summary_pie_ax = summary_fig.add_subplot(3, 2, 1)
        wedges, texts, autotexts = summary_pie_ax.pie(
            market_sizes, 
            labels=None, 
            autopct='%1.1f%%',
            startangle=90,
            wedgeprops={'width': 0.5, 'edgecolor': 'w'}
        )
        summary_pie_ax.set_title('Position Size by Market', fontsize=14)
        summary_pie_ax.legend(wedges, market_labels, title="Markets", loc="center left", 
                            bbox_to_anchor=(1, 0, 0.5, 1), fontsize=8)
        
        # Add horizontal bar for top positions
        top_positions = min(10, len(all_position_labels))
        summary_bar_ax = summary_fig.add_subplot(3, 2, 3)
        bars = summary_bar_ax.barh(
            all_position_labels[:top_positions], 
            all_position_sizes[:top_positions], 
            color=all_position_colors[:top_positions]
        )
        
        # Add values to bars
        for i, bar in enumerate(bars):
            summary_bar_ax.text(
                bar.get_width() + (0.5 if bar.get_width() >= 0 else -3), 
                bar.get_y() + bar.get_height()/2, 
                f'{all_position_sizes[i]:.2f}',
                va='center',
                fontsize=8
            )
            
        summary_bar_ax.set_title(f'Top {top_positions} Positions by Size', fontsize=14)
        summary_bar_ax.set_xlabel('Position Size (shares)', fontsize=10)
        summary_bar_ax.axvline(x=0, color='white', linestyle='-', alpha=0.3)
        summary_bar_ax.grid(True, alpha=0.2)
        
        # Add trade history to the dashboard if available
        if not trades_df.empty and 'match_time' in trades_df.columns:
            summary_trade_ax = summary_fig.add_subplot(3, 2, 5)
            
            # Plot trade history (simplified version)
            trades_by_date = trades_df.copy()
            trades_by_date['date'] = trades_by_date['match_time'].dt.date
            trade_counts = trades_by_date.groupby('date').size()
            
            dates = [datetime.combine(d, datetime.min.time()) for d in trade_counts.index]
            summary_trade_ax.bar(
                dates,
                trade_counts.values,
                color='skyblue',
                alpha=0.7
            )
            
            summary_trade_ax.set_title('Your Trade Activity', fontsize=14)
            summary_trade_ax.set_xlabel('Date', fontsize=10)
            summary_trade_ax.set_ylabel('Number of Trades', fontsize=10)
            summary_trade_ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
            summary_trade_ax.xaxis.set_major_locator(plt.matplotlib.dates.AutoDateLocator())
            plt.setp(summary_trade_ax.xaxis.get_majorticklabels(), rotation=45)
            summary_trade_ax.grid(True, alpha=0.2)
        
        # Add a table of all positions with full market IDs
        table_ax = summary_fig.add_subplot(1, 2, 2)
        table_ax.axis('off')
        
        table_data = []
        for market_id, market_data in positions['positions'].items():
            market_name = market_data.get('name', 'Unknown')
            
            # Get market gain data if available
            market_pl_data = self.market_gains.get(market_id, {}) if hasattr(self, 'market_gains') else {}
            market_realized_pl = market_pl_data.get('realized_pl', 0)
            market_unrealized_pl = market_pl_data.get('unrealized_pl', 0)
            
            # Add summary row for the market
            table_data.append({
                'Market ID': market_id,
                'Market Name': market_name,
                'Outcome': '[MARKET SUMMARY]',
                'Position Size': '',
                'Current Price': '',
                'Position Value': '',
                'Cost Basis': '',
                'Trades': sum(pos.get('trades', 0) for pos in market_data.get('positions', {}).values()),
                'Realized P&L': market_realized_pl,
                'Unrealized P&L': market_unrealized_pl,
                'Total P&L': market_realized_pl + market_unrealized_pl,
                'ROI (%)': '',
                'is_summary': True
            })
            
            # Add individual outcome rows
            for outcome, position_data in market_data.get('positions', {}).items():
                size = position_data.get('size', 0)
                trades_count = position_data.get('trades', 0)
                
                # Get outcome-specific P&L data
                outcome_data = market_pl_data.get('by_outcome', {}).get(outcome, {})
                cost_basis = outcome_data.get('cost_basis', 0)
                realized_pl = outcome_data.get('realized_pl', 0)
                
                # Calculate current value and unrealized P&L
                current_price = 0
                if hasattr(self, 'market_gains') and market_id in self.market_gains:
                    # Try to get most recent price from trades safely
                    try:
                        market_trades = self.get_trades_by_market(market_id)
                        market_df = self.trades_to_dataframe(market_trades)
                        if not market_df.empty and 'outcome' in market_df.columns and 'price' in market_df.columns:
                            outcome_trades = market_df[market_df['outcome'] == outcome]
                            if not outcome_trades.empty:
                                current_price = float(outcome_trades.iloc[-1]['price'])
                    except (IndexError, TypeError, ValueError) as e:
                        self.logger.warning(f"Error getting current price for {outcome}: {e}")
                        # Leave current_price as 0 if there's an error
                
                current_value = size * current_price
                unrealized_pl = current_value - cost_basis if size > 0 else 0
                
                # Calculate ROI
                roi = ((realized_pl + unrealized_pl) / cost_basis * 100) if cost_basis > 0 else None
                
                table_data.append({
                    'Market ID': "",  # No need to repeat for outcomes
                    'Market Name': "",  # No need to repeat for outcomes
                    'Outcome': outcome,
                    'Position Size': size,
                    'Current Price': current_price,
                    'Position Value': current_value,
                    'Cost Basis': cost_basis,
                    'Trades': trades_count,
                    'Realized P&L': realized_pl,
                    'Unrealized P&L': unrealized_pl,
                    'Total P&L': realized_pl + unrealized_pl,
                    'ROI (%)': roi,
                    'is_summary': False
                })
                
        # Convert to DataFrame
        if not table_data:
            print("No position data to export")
            return None
        
        df = pd.DataFrame(table_data)
        
        # Only include non-empty columns
        df = df.loc[:, df.columns[df.astype(bool).any()]]
        
        # Sort by market name and then by absolute position size (descending)
        df['sort_key'] = df.apply(lambda row: (row['Market Name'] if row['is_summary'] else '', 
                                             not row['is_summary'], 
                                             -abs(float(row['Position Size'].replace('$', '').replace(',', '')) 
                                                  if isinstance(row['Position Size'], str) and row['Position Size'] 
                                                  else 0)), axis=1)
        df = df.sort_values('sort_key')
        df = df.drop(columns=['sort_key', 'is_summary'])
        
        # Generate file path if not provided
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tables_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output', 'tables')
            os.makedirs(tables_dir, exist_ok=True)
            file_path = os.path.join(tables_dir, f"positions_table_{timestamp}.csv")
        
        # Export to CSV
        df.to_csv(file_path, index=False)
        print(f"Positions table exported to: {file_path}")
        
        # Generate summary file
        if hasattr(self, 'market_gains'):
            summary_path = file_path.replace('.csv', '_summary.csv')
            
            # Calculate totals
            total_position_value = sum([row['Position Value'] for row in table_data if pd.notnull(row['Position Value'])])
            total_realized_pl = sum([market_data.get('realized_pl', 0) for market_data in self.market_gains.values()])
            total_unrealized_pl = sum([market_data.get('unrealized_pl', 0) for market_data in self.market_gains.values()])
            total_pl = total_realized_pl + total_unrealized_pl
            
            # Calculate overall ROI
            total_cost = sum([market_data.get('by_outcome', {}).get(outcome, {}).get('cost_basis', 0) 
                            for market_id, market_data in self.market_gains.items() 
                            for outcome in market_data.get('by_outcome', {}).keys()])
            
            overall_roi = ((total_realized_pl + total_unrealized_pl) / total_cost) * 100 if total_cost > 0 else None
            
            # Create summary DataFrame
            summary_data = [
                {'Metric': 'Total Position Value', 'Value': total_position_value},
                {'Metric': 'Total Realized P&L', 'Value': total_realized_pl},
                {'Metric': 'Total Unrealized P&L', 'Value': total_unrealized_pl},
                {'Metric': 'Total P&L', 'Value': total_pl},
                {'Metric': 'Overall ROI (%)', 'Value': overall_roi}
            ]
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv(summary_path, index=False)
            print(f"Portfolio summary exported to: {summary_path}")
        
        return file_path
            
    def export_trades_by_market(self, trades=None, file_path=None):
        """
        Export historical trades grouped by market IDs to a CSV file with P&L information.
        
        Args:
            trades (list, optional): List of trade data. If None, fetches all trades.
            file_path (str, optional): Path to save the CSV file. If None, generates a default path.
        
        Returns:
            str: Path to the saved CSV file.
        """
        # Get trades if not provided
        if trades is None:
            trades = self.get_my_trades()
            
        if not trades:
            print("No trades to export")
            return None
        
        # Convert to DataFrame with P&L calculations
        df = self.trades_to_dataframe(trades)
        
        if df.empty:
            print("No trade data to export")
            return None
        
        # Add market name to the DataFrame
        df['market_name'] = df['market'].apply(self.get_market_name)
        
        # Format the DataFrame for export
        export_df = df.copy()
        
        # Format the match_time
        if 'match_time' in export_df.columns:
            export_df['time'] = export_df['match_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Select columns for export
        columns = [
            'market', 'market_name', 'outcome', 'time', 'price', 'size', 
            'my_side', 'position_impact', 'gain_loss_usd', 'percent_change', 'avg_cost_basis'
        ]
        
        # Only include columns that exist
        export_columns = [col for col in columns if col in export_df.columns]
        
        # Ensure market ID is included
        if 'market' not in export_columns:
            export_columns.insert(0, 'market')
        
        export_df = export_df[export_columns]
        
        # Generate file path if not provided
        if file_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            tables_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output', 'tables')
            os.makedirs(tables_dir, exist_ok=True)
            file_path = os.path.join(tables_dir, f"trades_by_market_{timestamp}.csv")
        
        # Export to CSV
        export_df.to_csv(file_path, index=False)
        print(f"Trades by market exported to: {file_path}")
        
        # Generate summary file with P&L by market
        if hasattr(self, 'market_gains'):
            summary_path = file_path.replace('.csv', '_summary.csv')
            
            # Prepare market summary data
            market_summary = []
            total_realized_pl = 0
            total_unrealized_pl = 0
            
            for market_id, market_data in self.market_gains.items():
                market_name = self.get_market_name(market_id)
                realized_pl = market_data.get('realized_pl', 0)
                unrealized_pl = market_data.get('unrealized_pl', 0)
                total_pl = realized_pl + unrealized_pl
                
                # Calculate market-level ROI
                market_cost = sum([data.get('cost_basis', 0) for data in market_data.get('by_outcome', {}).values()])
                roi = (total_pl / market_cost * 100) if market_cost > 0 else None
                
                total_realized_pl += realized_pl
                total_unrealized_pl += unrealized_pl
                
                market_summary.append({
                    'Market ID': market_id,
                    'Market Name': market_name,
                    'Trade Count': len(export_df[export_df['market'] == market_id]),
                    'Realized P&L': realized_pl,
                    'Unrealized P&L': unrealized_pl,
                    'Total P&L': total_pl,
                    'ROI (%)': roi,
                    'Cost Basis': market_cost
                })
            
            # Calculate overall totals
            total_pl = total_realized_pl + total_unrealized_pl
            total_cost = sum([market_data.get('by_outcome', {}).get(outcome, {}).get('cost_basis', 0) 
                            for market_id, market_data in self.market_gains.items() 
                            for outcome in market_data.get('by_outcome', {}).keys()])
            
            overall_roi = (total_pl / total_cost * 100) if total_cost > 0 else None
            
            # Add total row
            market_summary.append({
                'Market ID': 'TOTAL',
                'Market Name': 'Portfolio Summary',
                'Trade Count': len(export_df),
                'Realized P&L': total_realized_pl,
                'Unrealized P&L': total_unrealized_pl,
                'Total P&L': total_pl,
                'ROI (%)': overall_roi,
                'Cost Basis': total_cost
            })
            
            # Create summary DataFrame
            summary_df = pd.DataFrame(market_summary)
            
            # Sort by total P&L
            summary_df = summary_df.sort_values('Total P&L', ascending=False)
            
            # Export summary to CSV
            summary_df.to_csv(summary_path, index=False)
            print(f"Market P&L summary exported to: {summary_path}")
            
            # Generate outcome-level summary
            outcome_path = file_path.replace('.csv', '_outcomes.csv')
            
            # Prepare outcome summary data
            outcome_summary = []
            
            for market_id, market_data in self.market_gains.items():
                market_name = self.get_market_name(market_id)
                
                for outcome, data in market_data.get('by_outcome', {}).items():
                    inventory = data.get('inventory', 0)
                    cost_basis = data.get('cost_basis', 0)
                    realized_pl = data.get('realized_pl', 0)
                    
                    # Only include outcomes with non-zero inventory or realized P&L
                    if inventory != 0 or realized_pl != 0:
                        avg_cost = cost_basis / inventory if inventory > 0 else 0
                        
                        outcome_summary.append({
                            'Market ID': market_id,
                            'Market Name': market_name,
                            'Outcome': outcome,
                            'Inventory': inventory,
                            'Avg Cost': avg_cost,
                            'Cost Basis': cost_basis,
                            'Realized P&L': realized_pl
                        })
            
            # Create outcome DataFrame
            if outcome_summary:
                outcome_df = pd.DataFrame(outcome_summary)
                
                # Sort by market ID and then outcome
                outcome_df = outcome_df.sort_values(['Market ID', 'Outcome'])
                
                # Export outcome summary to CSV
                outcome_df.to_csv(outcome_path, index=False)
                print(f"Outcome-level summary exported to: {outcome_path}")
        
        return file_path
            
    def display_positions_table(self, positions=None, save_image=False, filename=None, show_full_references=True):
        """
        Display a table of current positions with P&L information.
        
        Args:
            positions (dict, optional): Position data to display. If None, fetches current positions.
            save_image (bool): Whether to save the table as an image
            filename (str, optional): Filename for the saved image. If None, generates a default name.
            show_full_references (bool): Whether to show full market names and IDs after the table
        
        Returns:
            pandas.DataFrame: DataFrame with position data.
        """
        if positions is None:
            positions = self.get_detailed_positions()
            
        if 'error' in positions:
            print(f"Error: {positions['error']}")
            return None
            
        # Create data for the table
        table_data = []
        total_position_value = 0
        
        # Keep a reference of full names and IDs for later display
        market_references = {}
        
        # Ensure we have a consistent ordering of markets
        market_ids = list(positions.get('positions', {}).keys())
        
        # Generate short IDs for each market
        market_id_mapping = {
            market_id: f"M{i+1}" for i, market_id in enumerate(market_ids)
        }
        
        # Process each market in order
        for market_idx, market_id in enumerate(market_ids):
            market_data = positions['positions'][market_id]
            market_name = market_data.get('name', 'Unknown')
            short_id = market_id_mapping[market_id]
            
            # Create a shortened market name
            # Extract the main part from Elon tweet market names
            if "Elon tweet" in market_name:
                short_name = market_name.split("Will Elon tweet")[1].split("times")[0].strip()
            else:
                # For other markets, just take first 15 chars
                short_name = market_name[:15] + "..." if len(market_name) > 15 else market_name
            
            # Store full reference for later
            market_references[short_id] = {
                'full_id': market_id,
                'full_name': market_name
            }
            
            # Get market gain data if available
            market_pl_data = self.market_gains.get(market_id, {}) if hasattr(self, 'market_gains') else {}
            market_realized_pl = market_pl_data.get('realized_pl', 0)
            market_unrealized_pl = market_pl_data.get('unrealized_pl', 0)
            market_total_pl = market_realized_pl + market_unrealized_pl
                
            # Calculate position value for the market
            market_position_value = sum(
                pos.get('size', 0) * 
                market_pl_data.get('by_outcome', {}).get(outcome, {}).get('current_price', 0) 
                for outcome, pos in market_data.get('positions', {}).items()
            )

            # Calculate cost basis for the market
            market_cost_basis = sum(
                market_pl_data.get('by_outcome', {}).get(outcome, {}).get('cost_basis', 0) 
                for outcome in market_data.get('positions', {}).keys()
            )

            # Calculate ROI if cost basis is positive
            market_roi = None
            if market_cost_basis > 0:
                market_roi = (market_total_pl / market_cost_basis) * 100
            
            # Process outcomes for this market (typically should only be 1 per market)
            for outcome, position_data in market_data.get('positions', {}).items():
                size = position_data.get('size', 0)
                trades_count = position_data.get('trades', 0)
                    
                # Get outcome-specific P&L data
                outcome_data = market_pl_data.get('by_outcome', {}).get(outcome, {})
                cost_basis = outcome_data.get('cost_basis', 0)
                realized_pl = outcome_data.get('realized_pl', 0)
                    
                # Calculate current value and unrealized P&L
                current_price = 0
                if hasattr(self, 'market_gains') and market_id in self.market_gains:
                    # Try to get current price from outcome_data first
                    if 'current_price' in outcome_data:
                        current_price = outcome_data.get('current_price', 0)
                    else:
                        # Try to get most recent price from trades safely
                        try:
                            market_trades = self.get_trades_by_market(market_id)
                            market_df = self.trades_to_dataframe(market_trades)
                            if not market_df.empty and 'outcome' in market_df.columns and 'price' in market_df.columns:
                                outcome_trades = market_df[market_df['outcome'] == outcome]
                                if not outcome_trades.empty:
                                    current_price = float(outcome_trades.iloc[-1]['price'])
                        except (IndexError, TypeError, ValueError) as e:
                            self.logger.warning(f"Error getting current price for {outcome}: {e}")
                            # Leave current_price as 0 if there's an error
                    
                current_value = size * current_price
                unrealized_pl = current_value - cost_basis if size > 0 else 0
                    
                # Calculate ROI
                roi = ((realized_pl + unrealized_pl) / cost_basis * 100) if cost_basis > 0 else None
                    
                total_position_value += current_value
                
                # Add a single row with market and outcome info combined
                table_data.append({
                    'Market ID': short_id,
                    'Market Name': short_name,
                    'Outcome': outcome,
                    'Position Size': size,
                    'Current Price': current_price,
                    'Position Value': current_value,
                    'Cost Basis': cost_basis,
                    'Trades': trades_count,
                    'Realized P&L': realized_pl,
                    'Unrealized P&L': unrealized_pl,
                    'Total P&L': realized_pl + unrealized_pl,
                    'ROI (%)': roi,
                    'market_sort': market_idx
                })
                    
        # Convert to DataFrame
        if not table_data:
            print("No position data to display")
            return None
            
        df = pd.DataFrame(table_data)
        
        # Remove any potential duplicate rows (should not happen with our logic, but just to be safe)
        df = df.drop_duplicates()
            
        # Only include non-empty columns
        df = df.loc[:, df.columns[df.astype(bool).any()]]
        
        # Sort by market order
        df = df.sort_values(by=['market_sort'], ascending=[True])
        
        # Ensure consistent column order
        desired_columns = [
            'Market ID', 'Market Name', 'Outcome', 'Position Size', 'Current Price', 
            'Position Value', 'Cost Basis', 'Trades', 'Realized P&L', 
            'Unrealized P&L', 'Total P&L', 'ROI (%)'
        ]
        
        # Get columns that exist in both the DataFrame and desired_columns
        ordered_columns = [col for col in desired_columns if col in df.columns]
        
        # Add any remaining columns not in desired_columns (excluding our internal columns)
        excluded_cols = ['market_sort']
        remaining_cols = [col for col in df.columns if col not in desired_columns and col not in excluded_cols]
        ordered_columns.extend(remaining_cols)
        
        # Reorder columns
        if ordered_columns:
            df = df[ordered_columns]
        
        # Format numeric columns for display
        format_columns = {
            'Position Size': lambda x: f"{float(x):.2f}" if pd.notnull(x) and x != '' else "",
            'Current Price': lambda x: f"${float(x):.4f}" if pd.notnull(x) and x != '' else "",
            'Position Value': lambda x: f"${float(x):.2f}" if pd.notnull(x) and x != '' else "",
            'Cost Basis': lambda x: f"${float(x):.2f}" if pd.notnull(x) and x != '' else "",
            'Realized P&L': lambda x: f"${float(x):.2f}" if pd.notnull(x) else "$0.00",
            'Unrealized P&L': lambda x: f"${float(x):.2f}" if pd.notnull(x) else "$0.00",
            'Total P&L': lambda x: f"${float(x):.2f}" if pd.notnull(x) else "$0.00",
            'ROI (%)': lambda x: f"{float(x):+.2f}%" if pd.notnull(x) else ""
        }
            
        # Apply formatting
        for col, formatter in format_columns.items():
            if col in df.columns:
                df[col] = df[col].apply(formatter)
            
        # Drop temporary columns
        df = df.drop(columns=['market_sort'], errors='ignore')
            
        # Set up display options for a cleaner output
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.expand_frame_repr', False)
            
        # Print header
        print("\nCURRENT POSITIONS TABLE:")
            
        # Print the table with clean formatting to avoid duplicate rows
        print(df.to_string(index=False))
            
        # Print summary
        active_positions = len(df)
        print(f"\nTotal positions: {active_positions}")
            
        # Calculate total values for P&L summary
        if hasattr(self, 'total_gains'):
            total_realized_pl = self.total_gains.get('realized_pl', 0)
            total_unrealized_pl = self.total_gains.get('unrealized_pl', 0)
            total_pl = total_realized_pl + total_unrealized_pl
                
            # Calculate overall ROI
            total_cost = sum([market_data.get('by_outcome', {}).get(outcome, {}).get('cost_basis', 0) 
                              for market_id, market_data in self.market_gains.items() 
                              for outcome in market_data.get('by_outcome', {}).keys()])
                
            # Print portfolio summary
            print("\nPORTFOLIO SUMMARY:")
            print(f"  Total Position Value: ${total_position_value:.2f}")
            print(f"  Total Realized P&L: ${total_realized_pl:.2f}")
            print(f"  Total Unrealized P&L: ${total_unrealized_pl:.2f}")
            print(f"  Total P&L: ${total_pl:.2f}")
                
            if total_cost > 0:
                overall_roi = (total_pl / total_cost) * 100
                print(f"  Overall ROI: {overall_roi:+.2f}%")
        
        # Print market reference guide if requested
        if show_full_references and market_references:
            print("\nMARKET REFERENCE GUIDE:")
            for short_id, ref_data in sorted(market_references.items()):
                print(f"  {short_id}: {ref_data['full_name']}")
                print(f"     ID: {ref_data['full_id']}")
        
        # Save image if requested
        if save_image:
            try:
                import matplotlib.pyplot as plt
                from matplotlib.table import Table
                
                # Create a figure and axis with the right size
                num_rows = len(df) + 3  # Add some extra rows for headers and padding
                fig_height = max(6, num_rows * 0.4)  # Adjust height based on number of rows
                fig, ax = plt.subplots(figsize=(15, fig_height))
                
                # Hide the axis
                ax.axis('off')
                ax.axis('tight')
                
                # Create a table with the DataFrame data
                table = ax.table(
                    cellText=df.values,
                    colLabels=df.columns,
                    loc='center',
                    cellLoc='center',
                    colColours=['#f2f2f2'] * len(df.columns),
                    colWidths=[0.1] * len(df.columns)
                )
                
                # Style the table
                table.auto_set_font_size(False)
                table.set_fontsize(9)
                table.scale(1, 1.5)
                
                # Add a title
                plt.title("Polymarket Position Table", fontsize=16, pad=20)
                
                # Add timestamp and portfolio summary at the bottom
                summary_text = f"Total P&L: ${total_pl:.2f} | ROI: {overall_roi:+.2f}% | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                fig.text(0.5, 0.01, summary_text, ha='center', fontsize=10)
                
                # Generate filename if not provided
                if filename is None:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    tables_dir = os.path.join(self.output_dir, 'tables')
                    os.makedirs(tables_dir, exist_ok=True)
                    filename = os.path.join(tables_dir, f"positions_table_{timestamp}.png")
                
                # Save the figure
                plt.tight_layout()
                plt.savefig(filename, dpi=150, bbox_inches='tight')
                plt.close()
                
                print(f"\nPosition table image saved to: {filename}")
                
            except ImportError:
                print("\nCould not save image. Matplotlib is required to save tables as images.")
            except Exception as e:
                print(f"\nError saving table image: {e}")
        
        return df

    def clear_market_cache(self):
        """
        Clear the market information cache.
        
        Returns:
            int: Number of cache entries cleared.
        """
        cache_size = len(self.market_info_cache)
        self.market_info_cache = {}
        self.logger.info(f"Cleared market cache ({cache_size} entries)")
        return cache_size 

    def get_simple_positions(self):
        """
        Get a simple dictionary of market IDs and share quantities.
        
        Returns:
            dict: Dictionary with market IDs as keys and a nested dictionary of outcome-to-quantity as values.
        """
        # Get position data
        positions = self.calculate_positions()
        
        if not positions:
            return {}
        
        # Create a simple dictionary structure
        simple_positions = {}
        
        for market_id, market_data in positions.items():
            outcome_positions = {}
            
            for outcome, position_data in market_data['positions'].items():
                # Just include the size (number of shares)
                outcome_positions[outcome] = position_data['size']
            
            simple_positions[market_id] = outcome_positions
            
        return simple_positions

    def get_positions_summary(self):
        """
        Get a simplified summary of current positions.
        
        This method provides a simpler overview compared to get_detailed_positions().
        
        Returns:
            dict: Dictionary with simplified position information.
        """
        # First get detailed positions
        detailed = self.get_detailed_positions()
        
        if 'error' in detailed:
            return detailed
        
        # Ensure we have P&L data calculated
        if not hasattr(self, 'market_gains'):
            trades = self.get_my_trades()
            self.trades_to_dataframe(trades)  # This will populate market_gains
        
        # Extract just what we need for a summary
        summary = {
            'wallet_address': detailed.get('wallet_address', self.wallet_address),
            'total_markets': detailed.get('total_markets', 0),
            'total_trades': detailed.get('total_trades', 0),
            'positions': {},
            'last_updated': detailed.get('last_updated', datetime.now().isoformat())
        }
        
        # Calculate total portfolio metrics
        total_position_value = 0
        total_realized_pl = 0
        total_unrealized_pl = 0
        
        if hasattr(self, 'market_gains'):
            for market_id, market_data in self.market_gains.items():
                total_realized_pl += market_data.get('realized_pl', 0)
                total_unrealized_pl += market_data.get('unrealized_pl', 0)
        
        # Include P&L metrics in the summary
        summary['pl_metrics'] = {
            'total_realized_pl': total_realized_pl,
            'total_unrealized_pl': total_unrealized_pl,
            'total_pl': total_realized_pl + total_unrealized_pl
        }
        
        # Only include markets with active positions
        for market_id, market_data in detailed.get('positions', {}).items():
            # Get P&L data for this market if available
            market_pl = {}
            if hasattr(self, 'market_gains') and market_id in self.market_gains:
                market_pl = {
                    'realized_pl': self.market_gains[market_id].get('realized_pl', 0),
                    'unrealized_pl': self.market_gains[market_id].get('unrealized_pl', 0),
                    'total_pl': self.market_gains[market_id].get('realized_pl', 0) + self.market_gains[market_id].get('unrealized_pl', 0)
                }
            
            # Add to summary
            summary['positions'][market_id] = {
                'name': market_data.get('name', ''),
                'positions': market_data.get('positions', {}),
                'total_trades': market_data.get('total_trades', 0),
                'pl_metrics': market_pl
            }
            
            # Calculate position value for this market
            market_position_value = 0
            for outcome, pos_data in market_data.get('positions', {}).items():
                size = pos_data.get('size', 0)
                # Try to get price from most recent trade safely
                current_price = 0
                if hasattr(self, 'market_gains') and market_id in self.market_gains:
                    try:
                        outcome_data = self.market_gains[market_id].get('by_outcome', {}).get(outcome, {})
                        if outcome_data and 'current_price' in outcome_data:
                            current_price = outcome_data.get('current_price', 0)
                        else:
                            # Try to get price from recent trades
                            market_trades = self.get_trades_by_market(market_id)
                            market_df = self.trades_to_dataframe(market_trades)
                            if not market_df.empty and 'outcome' in market_df.columns and 'price' in market_df.columns:
                                outcome_trades = market_df[market_df['outcome'] == outcome]
                                if not outcome_trades.empty:
                                    current_price = float(outcome_trades.iloc[-1]['price'])
                    except (IndexError, TypeError, ValueError) as e:
                        self.logger.warning(f"Error getting current price for {outcome}: {e}")
                        # Leave current_price as 0 if there's an error
                
                market_position_value += size * current_price
            
            summary['positions'][market_id]['position_value'] = market_position_value
            total_position_value += market_position_value
        
        summary['total_position_value'] = total_position_value
        
        return summary 

    def export_positions(self, positions=None, filename=None):
        """
        Export positions to a JSON file (alias for save_positions_to_file).
        
        Args:
            positions (dict, optional): Position data to save. If None, fetches current positions.
            filename (str, optional): Custom filename. If None, generates a timestamped filename.
            
        Returns:
            str: Path to the saved file.
        """
        return self.save_positions_to_file(positions, filename) 

    def print_detailed_positions(self, positions=None):
        """
        Print a detailed view of positions with P&L information.
        
        Args:
            positions (dict, optional): Position data to print. If None, fetches current positions.
            
        Returns:
            str: Formatted detailed positions text.
        """
        if positions is None:
            positions = self.get_detailed_positions()
            
        if 'error' in positions:
            print(f"Error: {positions['error']}")
            return None
        
        # Ensure P&L data is available
        if not hasattr(self, 'market_gains'):
            trades = self.get_my_trades()
            self.trades_to_dataframe(trades)
        
        # Create detailed output
        lines = [
            f"DETAILED POLYMARKET POSITIONS - {positions.get('wallet_address')}",
            f"Last Updated: {positions.get('last_updated')}",
            f"Active Markets: {positions.get('total_markets')}",
            f"Total Trades: {positions.get('total_trades')}",
            ""
        ]
        
        # Add portfolio summary if P&L data is available
        if hasattr(self, 'total_gains'):
            total_realized_pl = self.total_gains.get('realized_pl', 0)
            total_unrealized_pl = self.total_gains.get('unrealized_pl', 0)
            total_pl = self.total_gains.get('total_pl', 0)
            
            lines.extend([
                "PORTFOLIO P&L SUMMARY:",
                f"  Realized P&L: ${total_realized_pl:.2f}",
                f"  Unrealized P&L: ${total_unrealized_pl:.2f}",
                f"  Total P&L: ${total_pl:.2f}",
                ""
            ])
            
            # Calculate ROI if we have total cost basis
            total_cost = sum([market_data.get('by_outcome', {}).get(outcome, {}).get('cost_basis', 0) 
                            for market_id, market_data in self.market_gains.items() 
                            for outcome in market_data.get('by_outcome', {}).keys()])
            
            if total_cost > 0:
                roi = (total_pl / total_cost) * 100
                lines.append(f"  ROI: {roi:+.2f}%\n")
        
        # Add details for each market
        lines.append("CURRENT POSITIONS BY MARKET:")
        
        for market_id, market_data in positions.get('positions', {}).items():
            market_name = market_data.get('name')
            
            # Display market name and ID
            if market_name and not market_name.endswith(market_id):
                lines.append(f"\n{market_name} ({market_id}):")
            else:
                lines.append(f"\n{market_name}:")
            
            # Add market P&L summary if available
            if hasattr(self, 'market_gains') and market_id in self.market_gains:
                market_pl = self.market_gains[market_id]
                realized_pl = market_pl.get('realized_pl', 0)
                unrealized_pl = market_pl.get('unrealized_pl', 0)
                total_pl = realized_pl + unrealized_pl
                
                lines.append(f"  Market P&L Summary:")
                lines.append(f"    Realized: ${realized_pl:.2f}")
                lines.append(f"    Unrealized: ${unrealized_pl:.2f}")
                lines.append(f"    Total: ${total_pl:.2f}")
                
                # Calculate market ROI
                market_cost = sum([data.get('cost_basis', 0) for data in market_pl.get('by_outcome', {}).values()])
                if market_cost > 0:
                    market_roi = (total_pl / market_cost) * 100
                    lines.append(f"    ROI: {market_roi:+.2f}%")
                
                lines.append("")
            
            # Add position details
            lines.append("  Current Positions:")
            
            for outcome, position_data in market_data.get('positions', {}).items():
                size = position_data.get('size', 0)
                sign = '+' if size > 0 else ''
                trades_count = position_data.get('trades', 0)
                
                position_line = f"    • {outcome}: {sign}{size:.2f} shares ({trades_count} trades)"
                
                # Add P&L details for this outcome
                if hasattr(self, 'market_gains') and market_id in self.market_gains:
                    outcome_data = self.market_gains[market_id].get('by_outcome', {}).get(outcome, {})
                    if outcome_data:
                        realized_pl = outcome_data.get('realized_pl', 0)
                        cost_basis = outcome_data.get('cost_basis', 0)
                        
                        if size > 0 and cost_basis > 0:
                            avg_cost = cost_basis / size
                            position_line += f" | Avg Cost: ${avg_cost:.4f}"
                        
                        if realized_pl != 0:
                            position_line += f" | Realized P&L: ${realized_pl:.2f}"
                
                lines.append(position_line)
            
            lines.append("")  # Blank line after each market
        
        detailed_text = "\n".join(lines)
        print(detailed_text)
        return detailed_text 

    def display_trades_by_market(self, trades=None):
        """
        Display historical trades grouped by market IDs with profit/loss information.
        
        Args:
            trades (list, optional): List of trade data. If None, fetches all trades.
            
        Returns:
            pandas.DataFrame: DataFrame with trade data.
        """
        # Get trades if not provided
        if trades is None:
            trades = self.get_my_trades()
            
        if not trades:
            print("No trades to display")
            return None
            
        # Convert to DataFrame with P&L calculations
        df = self.trades_to_dataframe(trades)
        
        if df.empty:
            print("No trade data to display")
            return None
            
        # Add market name to the DataFrame
        df['market_name'] = df['market'].apply(self.get_market_name)
        
        # Format the match_time
        if 'match_time' in df.columns:
            df['time'] = df['match_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Format P&L columns
        for col in ['gain_loss_usd', 'percent_change', 'avg_cost_basis']:
            if col in df.columns:
                if col == 'percent_change':
                    # Filter out None values before formatting
                    mask = df[col].notnull()
                    df.loc[mask, col] = df.loc[mask, col].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "")
                elif col == 'gain_loss_usd':
                    df[col] = df[col].apply(lambda x: f"${x:.2f}" if pd.notnull(x) else "")
                elif col == 'avg_cost_basis':
                    df[col] = df[col].apply(lambda x: f"${x:.4f}" if pd.notnull(x) else "")
        
        # Select columns for display - ensure market ID is not truncated
        columns = [
            'market', 'outcome', 'time', 'price', 'size', 'my_side', 
            'gain_loss_usd', 'percent_change', 'avg_cost_basis'
        ]
        
        # Only include columns that exist
        display_columns = [col for col in columns if col in df.columns]
        
        # Print overview
        unique_markets = df['market'].nunique()
        total_trades = len(df)
        print(f"\nTRADES BY MARKET (Total: {total_trades} trades across {unique_markets} markets):\n")
        
        # Track overall P&L for summary
        total_realized_pl = 0
        total_unrealized_pl = 0
        
        # Loop through each unique market and display trades
        for market_id in df['market'].unique():
            market_df = df[df['market'] == market_id].copy()
            market_name = market_df['market_name'].iloc[0]
            
            # Display market header with full ID
            print(f"\n--- Market: {market_name} ({market_id}) ---")
            
            # Create a formatted table for this market's trades
            display_df = market_df[display_columns].copy()
            
            # Format price as currency
            if 'price' in display_df.columns:
                display_df['price'] = display_df['price'].apply(lambda x: f"${float(x):.4f}" if pd.notnull(x) else "")
            
            # Format size as number
            if 'size' in display_df.columns:
                display_df['size'] = display_df['size'].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) else "")
            
            # Rename columns for display
            column_renames = {
                'my_side': 'Side',
                'position_impact': 'Impact',
                'gain_loss_usd': 'P&L ($)',
                'percent_change': 'P&L (%)',
                'avg_cost_basis': 'Avg Cost',
                'time': 'Time',
                'outcome': 'Outcome',
                'price': 'Price',
                'size': 'Size'
            }
            
            # Only rename columns that exist
            rename_dict = {col: new_name for col, new_name in column_renames.items() 
                          if col in display_df.columns}
            
            display_df = display_df.rename(columns=rename_dict)
            
            # For cleaner display, don't show the market ID in each row
            if 'market' in display_df.columns:
                display_df = display_df.drop(columns=['market'])
            
            # Sort by time
            if 'Time' in display_df.columns:
                display_df = display_df.sort_values('Time')
            
            # Print the table
            pd.set_option('display.max_rows', None)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.expand_frame_repr', False)
            
            print(display_df.to_string(index=False))
            
            # Get market P&L metrics if available
            if hasattr(self, 'market_gains') and market_id in self.market_gains:
                market_pl = self.market_gains[market_id]
                market_realized_pl = market_pl.get('realized_pl', 0)
                market_unrealized_pl = market_pl.get('unrealized_pl', 0)
                total_market_pl = market_realized_pl + market_unrealized_pl
                
                # Update totals for overall summary
                total_realized_pl += market_realized_pl
                total_unrealized_pl += market_unrealized_pl
                
                # Print market P&L summary
                print("\nMarket P&L Summary:")
                print(f"  Realized P&L: ${market_realized_pl:.2f}")
                print(f"  Unrealized P&L: ${market_unrealized_pl:.2f}")
                print(f"  Total P&L: ${total_market_pl:.2f}")
                
                # Calculate and display ROI if possible
                market_cost = sum([data.get('cost_basis', 0) for data in market_pl.get('by_outcome', {}).values()])
                if market_cost > 0:
                    market_roi = (total_market_pl / market_cost) * 100
                    print(f"  ROI: {market_roi:+.2f}%")
        
        # Print overall portfolio P&L summary
        print("\nOVERALL PORTFOLIO P&L SUMMARY:")
        print(f"  Realized P&L: ${total_realized_pl:.2f}")
        print(f"  Unrealized P&L: ${total_unrealized_pl:.2f}")
        print(f"  Total P&L: ${total_realized_pl + total_unrealized_pl:.2f}")
        
        # Calculate overall ROI
        if hasattr(self, 'market_gains'):
            total_cost = sum([market_data.get('by_outcome', {}).get(outcome, {}).get('cost_basis', 0) 
                              for market_id, market_data in self.market_gains.items() 
                              for outcome in market_data.get('by_outcome', {}).keys()])
            
            if total_cost > 0:
                overall_roi = ((total_realized_pl + total_unrealized_pl) / total_cost) * 100
                print(f"  ROI: {overall_roi:+.2f}%")
        
        return df

    def print_positions_summary(self, positions_dict):
        """
        Visualize important metrics from Polymarket trading data.

        Args:
            positions_dict (dict): Dictionary containing trading data with the structure
                                   provided in the example.
        """
        # Extract basic metrics
        wallet_address = positions_dict.get('wallet_address', 'Unknown')
        total_markets = positions_dict.get('total_markets', 0)
        total_trades = positions_dict.get('total_trades', 0)
        total_pl = positions_dict.get('pl_metrics', {}).get('total_pl', 0)
        realized_pl = positions_dict.get('pl_metrics', {}).get('total_realized_pl', 0)
        unrealized_pl = positions_dict.get('pl_metrics', {}).get('total_unrealized_pl', 0)
        total_position_value = float(positions_dict.get('total_position_value', 0))

        # Extract market positions
        markets_data = positions_dict.get('positions', {})

        # Create figure with subplots
        plt.style.use('ggplot')
        fig = plt.figure(figsize=(15, 12))
        fig.suptitle(f"Polymarket Trading Dashboard - {wallet_address[:6]}...{wallet_address[-4:]}",
                    fontsize=16, fontweight='bold')

        # 1. Overview metrics
        ax1 = fig.add_subplot(3, 2, 1)
        metrics = ['Total Markets', 'Total Trades', 'Total P&L', 'Realized P&L', 'Unrealized P&L']
        values = [total_markets, total_trades, total_pl, realized_pl, unrealized_pl]

        colors = ['#3778bf' if v >= 0 else '#e15759' for v in values]
        ax1.bar(metrics, values, color=colors)
        ax1.set_title('Account Overview')
        ax1.set_ylabel('Value')
        plt.xticks(rotation=45, ha='right')

        # 2. P&L by market
        ax2 = fig.add_subplot(3, 2, 2)
        market_names = []
        market_pls = []

        for market_id, market_data in markets_data.items():
            market_names.append(market_data.get('name', market_id)[:20] + '...')
            market_pls.append(market_data.get('pl_metrics', {}).get('total_pl', 0))

        # Sort by P&L
        sorted_indices = np.argsort(market_pls)
        sorted_names = [market_names[i] for i in sorted_indices]
        sorted_pls = [market_pls[i] for i in sorted_indices]

        colors = ['#3778bf' if pl >= 0 else '#e15759' for pl in sorted_pls]
        ax2.barh(sorted_names, sorted_pls, color=colors)
        ax2.set_title('P&L by Market')
        ax2.set_xlabel('Profit/Loss')

        # 3. Position sizes by market
        ax3 = fig.add_subplot(3, 2, 3)
        market_names = []
        position_sizes = []

        for market_id, market_data in markets_data.items():
            name = market_data.get('name', market_id)[:20] + '...'

            # Get the position size (assuming 'Yes' position for simplicity)
            pos_size = 0
            if 'positions' in market_data and 'Yes' in market_data['positions']:
                pos_size = float(market_data['positions']['Yes'].get('size', 0))

            market_names.append(name)
            position_sizes.append(pos_size)

        # Sort by position size
        sorted_indices = np.argsort(position_sizes)[-10:]  # Top 10 positions
        sorted_names = [market_names[i] for i in sorted_indices]
        sorted_sizes = [position_sizes[i] for i in sorted_indices]

        ax3.barh(sorted_names, sorted_sizes)
        ax3.set_title('Top Position Sizes (Yes positions)')
        ax3.set_xlabel('Position Size')

        # 4. Trade activity over time
        ax4 = fig.add_subplot(3, 2, 4)
        trade_dates = []
        trade_counts = {}

        for market_id, market_data in markets_data.items():
            if 'positions' in market_data and 'Yes' in market_data['positions']:
                trade_time_str = market_data['positions']['Yes'].get('last_trade_time', '')
                if trade_time_str:
                    trade_date = datetime.strptime(trade_time_str.split('T')[0], '%Y-%m-%d').date()
                    trade_dates.append(trade_date)
                    trade_counts[trade_date] = trade_counts.get(trade_date, 0) + 1

        if trade_dates:
            dates = sorted(list(trade_counts.keys()))
            counts = [trade_counts[date] for date in dates]

            ax4.plot(dates, counts, marker='o', linestyle='-')
            ax4.set_title('Trading Activity by Date')
            ax4.set_xlabel('Date')
            ax4.set_ylabel('Number of Trades')
            ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45, ha='right')

        # 5. Pie chart of position values
        ax5 = fig.add_subplot(3, 2, 5)
        market_names = []
        position_values = []

        for market_id, market_data in markets_data.items():
            pos_value = float(market_data.get('position_value', 0))
            if pos_value > 0.001:  # Filter out very small positions
                name = market_data.get('name', market_id).split('?')[0][:15] + '...'
                market_names.append(name)
                position_values.append(pos_value)

        # If there are too many markets, group smaller ones
        if len(market_names) > 7:
            sorted_indices = np.argsort(position_values)
            top_indices = sorted_indices[-6:]
            other_value = sum(position_values[i] for i in sorted_indices[:-6])

            pie_names = [market_names[i] for i in top_indices] + ['Other Markets']
            pie_values = [position_values[i] for i in top_indices] + [other_value]
        else:
            pie_names = market_names
            pie_values = position_values

        ax5.pie(pie_values, labels=pie_names, autopct='%1.1f%%', startangle=90)
        ax5.set_title('Portfolio Composition by Position Value')

        # 6. Market type distribution (extracting from market names)
        ax6 = fig.add_subplot(3, 2, 6)
        market_types = {}

        for market_id, market_data in markets_data.items():
            name = market_data.get('name', '')
            if "Elon tweet" in name:
                market_types["Elon Tweets"] = market_types.get("Elon Tweets", 0) + 1
            # Add more categories as needed
            else:
                market_types["Other"] = market_types.get("Other", 0) + 1

        types = list(market_types.keys())
        counts = list(market_types.values())

        ax6.bar(types, counts)
        ax6.set_title('Market Type Distribution')
        ax6.set_ylabel('Count')

        # Save plots to files instead of displaying them
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        output_path1 = os.path.join(os.getcwd(), "polymarket_dashboard.png")
        fig.savefig(output_path1, dpi=300, bbox_inches='tight')
        print(f"Saved dashboard visualization to: {output_path1}")
        plt.close(fig)

        # Create second figure for trade details
        fig2 = plt.figure(figsize=(12, 8))
        fig2.suptitle("Trade Details Analysis", fontsize=16, fontweight='bold')

        # 1. Trades per market
        ax1 = fig2.add_subplot(2, 2, 1)
        market_names = []
        trade_counts = []

        for market_id, market_data in markets_data.items():
            name = market_data.get('name', market_id)[:20] + '...'
            market_names.append(name)
            trade_counts.append(market_data.get('total_trades', 0))

        # Sort by trade count
        sorted_indices = np.argsort(trade_counts)[-10:]  # Top 10 by trades
        sorted_names = [market_names[i] for i in sorted_indices]
        sorted_counts = [trade_counts[i] for i in sorted_indices]

        ax1.barh(sorted_names, sorted_counts)
        ax1.set_title('Markets by Number of Trades')
        ax1.set_xlabel('Number of Trades')

        # 2. Avg P&L per trade by market
        ax2 = fig2.add_subplot(2, 2, 2)
        market_names = []
        avg_pls = []

        for market_id, market_data in markets_data.items():
            name = market_data.get('name', market_id)[:20] + '...'
            trades = market_data.get('total_trades', 0)
            pl = market_data.get('pl_metrics', {}).get('total_pl', 0)

            if trades > 0:
                avg_pl = pl / trades
                market_names.append(name)
                avg_pls.append(avg_pl)

        # Sort by avg P&L
        sorted_indices = np.argsort(avg_pls)
        sorted_names = [market_names[i] for i in sorted_indices]
        sorted_avg_pls = [avg_pls[i] for i in sorted_indices]

        colors = ['#3778bf' if pl >= 0 else '#e15759' for pl in sorted_avg_pls]
        ax2.barh(sorted_names, sorted_avg_pls, color=colors)
        ax2.set_title('Average P&L per Trade by Market')
        ax2.set_xlabel('Avg P&L per Trade')

        # 3. Scatter plot of position size vs P&L
        ax3 = fig2.add_subplot(2, 2, 3)
        sizes = []
        pls = []
        labels = []

        for market_id, market_data in markets_data.items():
            name = market_data.get('name', market_id).split('?')[0][:15]
            if 'positions' in market_data and 'Yes' in market_data['positions']:
                size = float(market_data['positions']['Yes'].get('size', 0))
                pl = market_data.get('pl_metrics', {}).get('total_pl', 0)

                sizes.append(size)
                pls.append(pl)
                labels.append(name)

        colors = ['#3778bf' if p >= 0 else '#e15759' for p in pls]
        ax3.scatter(sizes, pls, c=colors, alpha=0.7)

        # Annotate points with large P&L or size
        for i, (x, y, label) in enumerate(zip(sizes, pls, labels)):
            if abs(y) > max(abs(np.array(pls))) * 0.3 or x > max(sizes) * 0.3:
                ax3.annotate(label, (x, y), fontsize=8)

        ax3.set_title('Position Size vs P&L')
        ax3.set_xlabel('Position Size')
        ax3.set_ylabel('P&L')
        ax3.axhline(y=0, color='k', linestyle='-', alpha=0.3)

        # 4. P&L distribution histogram
        ax4 = fig2.add_subplot(2, 2, 4)
        all_pls = [market_data.get('pl_metrics', {}).get('total_pl', 0)
                   for market_id, market_data in markets_data.items()]

        ax4.hist(all_pls, bins=10, alpha=0.7, color='#3778bf')
        ax4.set_title('P&L Distribution')
        ax4.set_xlabel('P&L')
        ax4.set_ylabel('Frequency')

        # Save second figure to file
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        output_path2 = os.path.join(os.getcwd(), "polymarket_trade_details.png")
        fig2.savefig(output_path2, dpi=300, bbox_inches='tight')
        print(f"Saved trade details visualization to: {output_path2}")
        plt.close(fig2)

        print("Visualization complete! Check the output files in your current directory.")
        print(output_path1, output_path2)
        return output_path1, output_path2