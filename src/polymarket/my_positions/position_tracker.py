import os
import pandas as pd
import json
import logging
import matplotlib.pyplot as plt
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
                    self.logger.info(f"Successfully fetched market info for {market_id[:10]}...")
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
        Convert trades data to a pandas DataFrame for analysis.
        
        Args:
            trades_data (list): List of trade data dictionaries.
            
        Returns:
            pandas.DataFrame: DataFrame with trade data.
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
            if trade_copy.get('my_side') == 'BUY':
                trade_copy['position_impact'] = size
            else:
                trade_copy['position_impact'] = -size
                
            flattened_trades.append(trade_copy)
            
        return pd.DataFrame(flattened_trades)
    
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
            market_name = market_data['name'][:30] + ('...' if len(market_data['name']) > 30 else '')
            for outcome, position_data in market_data['positions'].items():
                size = position_data['size']
                size_formatted = f"{size:.2f}"
                trades = position_data['trades']
                table_data.append([market_name, outcome, size_formatted, trades, market_id])
                
        # Sort by absolute position size
        table_data.sort(key=lambda x: abs(float(x[2])), reverse=True)
        
        # Create table with market IDs
        table = table_ax.table(
            cellText=[[row[0], row[1], row[2], row[3], row[4]] for row in table_data],
            colLabels=['Market', 'Outcome', 'Size', 'Trades', 'Market ID'],
            loc='center',
            cellLoc='center',
            colWidths=[0.25, 0.1, 0.1, 0.05, 0.45]  # Increase width for Market ID column
        )
        
        # Style table
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.5)
        
        for (i, j), cell in table.get_celld().items():
            if i == 0:  # Header row
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#444444')
            elif j == 2:  # Size column
                size_val = float(table_data[i-1][2])
                cell.set_facecolor('#004400' if size_val > 0 else '#440000')
            elif j == 4:  # Market ID column - ensure it's readable
                cell.set_text_props(fontsize=6)  # Small but readable size for market IDs
        
        table_ax.set_title('All Positions with Market IDs', fontsize=14)
        
        if save:
            summary_path = os.path.join(viz_dir, 'position_summary_dashboard.png')
            plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust to leave room for the title
            plt.savefig(summary_path, dpi=300, bbox_inches='tight')
            saved_files['position_summary'] = summary_path
        
        if show:
            plt.show()
        else:
            plt.close('all')
            
        # Return paths to saved files
        return saved_files
        
    def visualize_market_trades(self, market_id, save=True, show=True):
        """
        Visualize trades for a specific market.
        
        Args:
            market_id (str): Market ID to visualize trades for.
            save (bool): Whether to save visualizations to files.
            show (bool): Whether to display the visualizations.
        
        Returns:
            dict: Paths to saved visualization files.
        """
        if not market_id:
            self.logger.error("Market ID is required for market trade visualization")
            return {}
            
        # Get trades for this market
        trades = self.get_trades_by_market(market_id)
        trades_df = self.trades_to_dataframe(trades)
        
        if trades_df.empty:
            self.logger.warning(f"No trades found for market {market_id}")
            return {}
            
        # Use the trade history visualization with market filter
        return self.visualize_trade_history(trades_df, market_id=market_id, save=save, show=show)
    
    def save_positions_to_file(self, positions=None, filename=None):
        """
        Save positions to a JSON file.
        
        Args:
            positions (dict, optional): Position data to save. If None, fetches current positions.
            filename (str, optional): Custom filename. If None, generates a timestamped filename.
            
        Returns:
            str: Path to the saved file.
        """
        if positions is None:
            positions = self.get_detailed_positions()
            
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"polymarket_positions_{timestamp}.json"
            
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(positions, f, indent=2)
                
            self.logger.info(f"Positions saved to {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving positions to file: {e}")
            return None
    
    def print_positions_summary(self, positions=None):
        """
        Print a human-readable summary of current positions.
        
        Args:
            positions (dict, optional): Position data to print. If None, fetches current positions.
            
        Returns:
            str: Formatted summary text.
        """
        if positions is None:
            positions = self.get_detailed_positions()
            
        if 'error' in positions:
            return f"Error: {positions['error']}"
            
        # Create summary text
        lines = [
            f"POLYMARKET POSITIONS SUMMARY - {positions.get('wallet_address')}",
            f"Last Updated: {positions.get('last_updated')}",
            f"Active Markets: {positions.get('total_markets')}",
            f"Total Trades: {positions.get('total_trades')}",
            "",
            "CURRENT POSITIONS:"
        ]
        
        # Add details for each market
        for market_id, market_data in positions.get('positions', {}).items():
            market_name = market_data.get('name')
            
            # Display market name and ID (avoiding duplication if the market name already contains the ID)
            if market_name and not market_name.endswith(market_id):
                lines.append(f"\n{market_name} ({market_id}):")
            else:
                lines.append(f"\n{market_name}:")
            
            for outcome, position_data in market_data.get('positions', {}).items():
                size = position_data.get('size', 0)
                sign = '+' if size > 0 else ''
                trades_count = position_data.get('trades', 0)
                lines.append(f"  • {outcome}: {sign}{size:.2f} shares ({trades_count} trades)")
            
        summary = "\n".join(lines)
        print(summary)
        return summary

    def export_positions_table(self, positions=None, filepath=None):
        """
        Export positions data as a formatted table to a CSV file.
        
        Args:
            positions (dict, optional): Position data to export. If None, fetches current positions.
            filepath (str, optional): Path to save the CSV file. If None, uses a default path.
            
        Returns:
            str: Path to the saved file.
        """
        if positions is None:
            positions = self.get_detailed_positions()
            
        if 'error' in positions:
            self.logger.error(f"Error exporting positions table: {positions['error']}")
            return None
            
        # Create output directory
        csv_dir = os.path.join(self.output_dir, 'tables')
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir)
            
        # Default filepath if not provided
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join(csv_dir, f"positions_table_{timestamp}.csv")
            
        # Collect position data
        table_data = []
        
        for market_id, market_data in positions.get('positions', {}).items():
            market_name = market_data.get('name', 'Unknown')
            
            for outcome, position_data in market_data.get('positions', {}).items():
                size = position_data.get('size', 0)
                trades_count = position_data.get('trades', 0)
                last_trade_time = position_data.get('last_trade_time', '')
                
                # Remove timezone info for better CSV compatibility
                if last_trade_time:
                    last_trade_time = last_trade_time.split('+')[0].split('Z')[0]
                
                table_data.append({
                    'market_id': market_id,
                    'market_name': market_name,
                    'outcome': outcome,
                    'position_size': size,
                    'trades_count': trades_count,
                    'last_trade_time': last_trade_time
                })
                
        # Convert to DataFrame
        if not table_data:
            self.logger.warning("No position data to export")
            return None
            
        df = pd.DataFrame(table_data)
        
        # Sort by absolute position size (descending)
        df['abs_size'] = df['position_size'].abs()
        df = df.sort_values('abs_size', ascending=False)
        df = df.drop(columns=['abs_size'])
        
        # Save to CSV
        try:
            df.to_csv(filepath, index=False)
            self.logger.info(f"Positions table exported to {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving positions table: {e}")
            return None
            
    def export_trades_by_market(self, trades=None, filepath=None):
        """
        Export historical trades grouped by market IDs to a CSV file.
        
        Args:
            trades (list, optional): List of trade data. If None, fetches all trades.
            filepath (str, optional): Path to save the CSV file. If None, uses a default path.
            
        Returns:
            str: Path to the saved file.
        """
        # Get trades if not provided
        if trades is None:
            trades = self.get_my_trades()
            
        if not trades:
            self.logger.warning("No trades to export")
            return None
            
        # Convert to DataFrame
        df = self.trades_to_dataframe(trades)
        
        if df.empty:
            self.logger.warning("No trade data to export")
            return None
            
        # Create output directory
        csv_dir = os.path.join(self.output_dir, 'tables')
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir)
            
        # Default filepath if not provided
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join(csv_dir, f"trades_by_market_{timestamp}.csv")
            
        # Add market name to the DataFrame
        df['market_name'] = df['market'].apply(self.get_market_name)
        
        # Format timestamp for better readability
        if 'match_time' in df.columns:
            df['match_time_str'] = df['match_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Select and order columns for the export
        columns = [
            'market', 'market_name', 'outcome', 'match_time_str', 'price', 'size', 
            'my_side', 'position_impact', 'is_maker', 'is_taker'
        ]
        
        # Only include columns that exist
        export_columns = [col for col in columns if col in df.columns]
        
        # Add additional columns if they exist
        for col in df.columns:
            if col not in export_columns and not col.startswith('match_time'):
                export_columns.append(col)
                
        # Sort by market and timestamp
        df = df.sort_values(['market', 'match_time'])
        
        # Export to CSV
        try:
            df[export_columns].to_csv(filepath, index=False)
            self.logger.info(f"Trades by market exported to {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving trades table: {e}")
            return None
            
    def display_positions_table(self, positions=None):
        """
        Display positions as a formatted table in the console.
        
        Args:
            positions (dict, optional): Position data to display. If None, fetches current positions.
            
        Returns:
            pandas.DataFrame: DataFrame with position data.
        """
        if positions is None:
            positions = self.get_detailed_positions()
            
        if 'error' in positions:
            print(f"Error: {positions['error']}")
            return None
            
        # Collect position data
        table_data = []
        
        for market_id, market_data in positions.get('positions', {}).items():
            market_name = market_data.get('name', 'Unknown')
            
            # If the market name already contains or is derived from the ID, don't duplicate it
            if market_name.endswith(market_id) or market_name.startswith("Market "):
                display_market_id = ""  # Empty string to avoid duplication
            else:
                display_market_id = market_id
            
            short_market_name = market_name[:60] + '...' if len(market_name) > 60 else market_name
            
            for outcome, position_data in market_data.get('positions', {}).items():
                size = position_data.get('size', 0)
                trades_count = position_data.get('trades', 0)
                
                table_data.append({
                    'Market ID': display_market_id,
                    'Market Name': short_market_name,
                    'Outcome': outcome,
                    'Position Size': size,
                    'Trades': trades_count
                })
                
        # Convert to DataFrame
        if not table_data:
            print("No position data to display")
            return None
            
        df = pd.DataFrame(table_data)
        
        # Only include non-empty columns
        df = df.loc[:, df.columns[df.astype(bool).any()]]
        
        # Sort by absolute position size (descending)
        df['abs_size'] = df['Position Size'].abs()
        df = df.sort_values('abs_size', ascending=False)
        df = df.drop(columns=['abs_size'])
        
        # Format the table
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.expand_frame_repr', False)
        
        # Print the table
        print("\nCURRENT POSITIONS TABLE:\n")
        print(df)
        print(f"\nTotal positions: {len(df)}")
        
        return df
        
    def display_trades_by_market(self, trades=None):
        """
        Display historical trades grouped by market IDs in the console.
        
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
            
        # Convert to DataFrame
        df = self.trades_to_dataframe(trades)
        
        if df.empty:
            print("No trade data to display")
            return None
            
        # Add market name to the DataFrame
        df['market_name'] = df['market'].apply(self.get_market_name)
        
        # Format the DataFrame for display
        display_df = df.copy()
        
        # Format match_time
        if 'match_time' in display_df.columns:
            display_df['Time'] = display_df['match_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
        # Format market ID and name - don't truncate market ID
        display_df['Market ID'] = display_df['market']
        display_df['Market Name'] = display_df['market_name'].apply(lambda x: x[:40] + '...' if len(x) > 40 else x)
        
        # Select columns for display
        columns = [
            'Market ID', 'Market Name', 'outcome', 'Time', 'price', 'size', 
            'my_side', 'position_impact'
        ]
        
        # Rename columns
        column_mapping = {
            'outcome': 'Outcome',
            'price': 'Price',
            'size': 'Size',
            'my_side': 'Side',
            'position_impact': 'Impact'
        }
        
        for old, new in column_mapping.items():
            if old in display_df.columns:
                display_df[new] = display_df[old]
                
        # Only include columns that exist
        display_columns = [col for col in columns if col in display_df.columns]
        
        # Format the table
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.expand_frame_repr', False)
        
        # Group by market and display
        markets = display_df['Market ID'].unique()
        
        print(f"\nTRADES BY MARKET (Total: {len(df)} trades across {len(markets)} markets):\n")
        
        for market_id in markets:
            market_df = display_df[display_df['Market ID'] == market_id]
            market_name = market_df['Market Name'].iloc[0]
            
            # Format the header to avoid duplicate market IDs
            if market_name.endswith(market_id) or market_name.startswith("Market "):
                print(f"\n--- Market: {market_name} ---")
            else:
                print(f"\n--- Market: {market_name} ({market_id}) ---")
            
            # Don't display the Market ID column since it's already in the header
            display_cols = [col for col in display_columns if col != 'Market ID']
            print(market_df[display_cols].sort_values('Time'))
            print(f"Total: {len(market_df)} trades\n")
            
        return df 