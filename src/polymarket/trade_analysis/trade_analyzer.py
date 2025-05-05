import os
import pandas as pd
import json
from datetime import datetime, date, timedelta
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import TradeParams
from dotenv import load_dotenv
import numpy as np
import logging
from .visualizer import PolymarketTradeVisualizer


class PolymarketTradeAnalyzer:
    """
    A class to analyze Polymarket trade data using the CLOB API.
    """
    
    def __init__(self, output_dir='.', log_level=logging.INFO, key=None):
        """
        Initialize the PolymarketTradeAnalyzer with credentials.
        
        Args:
            output_dir (str): Directory to save output files.
            log_level: Logging level to use.
            key (str, optional): Wallet private key. If None, loads from environment.
        """
        # Set up output directory
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Set up logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('PolymarketTradeAnalyzer')
        
        # Initialize visualizer
        self.visualizer = PolymarketTradeVisualizer(
            theme='dark_background',
            output_dir=output_dir,
            dpi=300
        )
        
        # Load environment variables if key not provided
        if not key:
            load_dotenv()
            key = os.getenv("WALLET_PRIVATE_KEY")
            
        if not key:
            raise ValueError("Wallet private key is required. Please provide it or set WALLET_PRIVATE_KEY in .env")
            
        # Initialize CLOB client
        host = "https://clob.polymarket.com"
        chain_id = POLYGON
        self.client = ClobClient(host, key=key, chain_id=chain_id)
        
        # Set up API credentials
        self.client.set_api_creds(self.client.create_or_derive_api_creds())
        
        # Get wallet address
        self.wallet_address = self.client.get_address()
        self.logger.info(f"Connected to Polymarket CLOB API with wallet: {self.wallet_address[:8]}...")
        
    def get_trades_by_maker(self, maker_address=None):
        """
        Get trades by maker address.
        
        Args:
            maker_address (str, optional): Maker address to filter trades by.
                                          If None, uses the current wallet address.
        
        Returns:
            list: List of trade data dictionaries.
        """
        if not maker_address:
            maker_address = self.wallet_address
            
        self.logger.info(f"Fetching trades for maker: {maker_address[:8]}...")
        trade_params = TradeParams(maker_address=maker_address)
        return self.client.get_trades(trade_params)
    
    def get_trades_by_market(self, market_id):
        """
        Get trades for a specific market.
        
        Args:
            market_id (str): Market ID to filter trades by.
        
        Returns:
            list: List of trade data dictionaries.
        """
        trade_params = TradeParams(market=market_id)
        return self.client.get_trades(trade_params)
    
    def get_trades_to_dataframe(self, trades_data):
        """
        Convert trades data to a pandas DataFrame for analysis.
        
        Args:
            trades_data (list): List of trade data dictionaries.
            
        Returns:
            pandas.DataFrame: DataFrame with trade data.
        """
        # Flatten any nested structures in the trade data
        flattened_trades = []
        
        for trade in trades_data:
            trade_copy = trade.copy()
            
            # Convert timestamps to datetime objects
            if 'match_time' in trade_copy:
                trade_copy['match_time'] = datetime.fromtimestamp(int(trade_copy['match_time']))
            if 'last_update' in trade_copy:
                trade_copy['last_update'] = datetime.fromtimestamp(int(trade_copy['last_update']))
                
            # Extract maker order information
            if 'maker_orders' in trade_copy and trade_copy['maker_orders']:
                maker_order = trade_copy['maker_orders'][0]
                for key, value in maker_order.items():
                    trade_copy[f'maker_{key}'] = value
                del trade_copy['maker_orders']
                
            flattened_trades.append(trade_copy)
            
        return pd.DataFrame(flattened_trades)
    
    def analyze_trade_prices(self, df):
        """
        Analyze trade prices from a DataFrame of trades.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades.
            
        Returns:
            dict: Dictionary with price analysis results.
        """
        # Convert price to float for analysis
        df['price_float'] = df['price'].astype(float)
        
        analysis = {
            'mean_price': df['price_float'].mean(),
            'median_price': df['price_float'].median(),
            'min_price': df['price_float'].min(),
            'max_price': df['price_float'].max(),
            'price_volatility': df['price_float'].std(),
            'price_by_outcome': df.groupby('outcome')['price_float'].mean().to_dict()
        }
        
        return analysis
    
    def analyze_trade_volume(self, df):
        """
        Analyze trade volume from a DataFrame of trades.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades.
            
        Returns:
            dict: Dictionary with volume analysis results.
        """
        # Convert size to float for analysis
        df['size_float'] = df['size'].astype(float)
        
        analysis = {
            'total_volume': df['size_float'].sum(),
            'mean_trade_size': df['size_float'].mean(),
            'max_trade_size': df['size_float'].max(),
            'volume_by_outcome': df.groupby('outcome')['size_float'].sum().to_dict(),
            'volume_by_side': df.groupby('side')['size_float'].sum().to_dict()
        }
        
        return analysis
    
    def analyze_trade_timing(self, df):
        """
        Analyze trade timing from a DataFrame of trades.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades with datetime columns.
            
        Returns:
            dict: Dictionary with timing analysis results.
        """
        if 'match_time' not in df.columns:
            return {'error': 'No timestamp data available for analysis'}
        
        # Sort by match_time
        df = df.sort_values('match_time')
        
        # Calculate time differences between consecutive trades
        df['time_diff'] = df['match_time'].diff().dt.total_seconds()
        
        # Convert dates to strings for JSON serialization
        trade_count_by_day = df.groupby(df['match_time'].dt.date).size().to_dict()
        # Convert date keys to strings to make them JSON serializable
        trade_count_by_day_serializable = {str(k): v for k, v in trade_count_by_day.items()}
        
        analysis = {
            'first_trade_time': df['match_time'].min().isoformat(),
            'last_trade_time': df['match_time'].max().isoformat(),
            'avg_time_between_trades': df['time_diff'].mean(),
            'max_time_between_trades': df['time_diff'].max(),
            'trade_count_by_day': trade_count_by_day_serializable
        }
        
        return analysis
    
    def get_comprehensive_analysis(self, trades_data):
        """
        Get comprehensive analysis of trade data.
        
        Args:
            trades_data (list): List of trade data dictionaries.
            
        Returns:
            dict: Dictionary with comprehensive analysis results.
        """
        # Convert to DataFrame for analysis
        df = self.get_trades_to_dataframe(trades_data)
        
        if df.empty:
            return {'error': 'No trade data available for analysis'}
        
        # Gather analysis results
        analysis = {
            'trade_count': len(df),
            'unique_markets': df['market'].nunique(),
            'unique_assets': df['asset_id'].nunique(),
            'side_distribution': df['side'].value_counts().to_dict(),
            'outcome_distribution': df['outcome'].value_counts().to_dict(),
            'price_analysis': self.analyze_trade_prices(df),
            'volume_analysis': self.analyze_trade_volume(df),
            'timing_analysis': self.analyze_trade_timing(df),
            'status_distribution': df['status'].value_counts().to_dict()
        }
        
        return analysis
    
    def preprocess_trades(self, trades):
        """
        Preprocess trade data for analysis.
        
        Args:
            trades (list): List of trade dictionaries.
            
        Returns:
            pandas.DataFrame: Preprocessed trade data.
        """
        if not trades:
            self.logger.warning("No trades provided for preprocessing")
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(trades)
        
        # Convert match_time to datetime
        if 'match_time' in df.columns:
            df['match_time'] = pd.to_datetime(df['match_time'])
            
        # Convert numeric columns
        numeric_cols = ['price', 'size']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        # Sort by time
        if 'match_time' in df.columns:
            df = df.sort_values('match_time')
            
        # Log basic info
        self.logger.info(f"Preprocessed {len(df)} trades")
        if len(df) > 0 and 'match_time' in df.columns:
            self.logger.info(f"Time range: {df['match_time'].min()} to {df['match_time'].max()}")
            
        return df
    
    def analyze_price_movement(self, df, window=None):
        """
        Analyze price movement over time.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades.
            window (str, optional): Time window for resampling (e.g., '1H', '1D').
            
        Returns:
            dict: Dictionary with price movement analysis.
        """
        if 'match_time' not in df.columns or 'price' not in df.columns:
            self.logger.error("DataFrame must contain 'match_time' and 'price' columns")
            return {}
            
        if len(df) == 0:
            self.logger.warning("Empty DataFrame provided for price movement analysis")
            return {}
            
        analysis = {}
        
        # Basic price stats
        analysis['price_min'] = df['price'].min()
        analysis['price_max'] = df['price'].max()
        analysis['price_mean'] = df['price'].mean()
        analysis['price_median'] = df['price'].median()
        analysis['price_std'] = df['price'].std()
        analysis['price_current'] = df.iloc[-1]['price'] if not df.empty else None
        
        # Price changes
        if len(df) > 1:
            analysis['price_start'] = df.iloc[0]['price']
            analysis['price_end'] = df.iloc[-1]['price']
            analysis['price_change'] = analysis['price_end'] - analysis['price_start']
            analysis['price_change_pct'] = (analysis['price_change'] / analysis['price_start']) * 100 if analysis['price_start'] != 0 else 0
            
            # 24h change if data spans at least 24 hours
            time_diff = df['match_time'].max() - df['match_time'].min()
            if time_diff >= timedelta(hours=24):
                cutoff_time = df['match_time'].max() - timedelta(hours=24)
                df_24h = df[df['match_time'] >= cutoff_time]
                if not df_24h.empty:
                    analysis['price_24h_start'] = df_24h.iloc[0]['price']
                    analysis['price_24h_end'] = df_24h.iloc[-1]['price']
                    analysis['price_24h_change'] = analysis['price_24h_end'] - analysis['price_24h_start']
                    analysis['price_24h_change_pct'] = (analysis['price_24h_change'] / analysis['price_24h_start']) * 100 if analysis['price_24h_start'] != 0 else 0
        
        # Resampled data if window is provided
        if window and len(df) > 1:
            try:
                resampled = df.set_index('match_time').resample(window)['price'].agg(['mean', 'min', 'max', 'std'])
                resampled = resampled.dropna()
                
                if not resampled.empty:
                    analysis['resampled_window'] = window
                    analysis['resampled_periods'] = len(resampled)
                    analysis['resampled_data'] = resampled.to_dict('index')
                    
                    # Calculate volatility (average of standard deviations)
                    analysis['price_volatility'] = resampled['std'].mean()
            except Exception as e:
                self.logger.error(f"Error resampling data: {e}")
        
        # Summary statistics text
        analysis['summary'] = self._format_price_analysis(analysis)
        
        return analysis
    
    def analyze_volume(self, df):
        """
        Analyze trading volume.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades.
            
        Returns:
            dict: Dictionary with volume analysis.
        """
        if 'size' not in df.columns:
            self.logger.error("DataFrame must contain 'size' column")
            return {}
            
        if len(df) == 0:
            self.logger.warning("Empty DataFrame provided for volume analysis")
            return {}
            
        analysis = {}
        
        # Basic volume stats
        analysis['total_volume'] = df['size'].sum()
        analysis['avg_trade_size'] = df['size'].mean()
        analysis['min_trade_size'] = df['size'].min()
        analysis['max_trade_size'] = df['size'].max()
        analysis['median_trade_size'] = df['size'].median()
        analysis['trade_count'] = len(df)
        
        # Volume by time periods if match_time is available
        if 'match_time' in df.columns:
            # Get time range
            time_range = df['match_time'].max() - df['match_time'].min()
            days = time_range.total_seconds() / (60 * 60 * 24)
            
            if days > 0:
                analysis['avg_daily_volume'] = analysis['total_volume'] / days
                analysis['avg_daily_trades'] = analysis['trade_count'] / days
            
            # Last 24 hours
            if time_range >= timedelta(hours=24):
                cutoff_time = df['match_time'].max() - timedelta(hours=24)
                df_24h = df[df['match_time'] >= cutoff_time]
                analysis['volume_24h'] = df_24h['size'].sum() if not df_24h.empty else 0
                analysis['trades_24h'] = len(df_24h)
        
        # Volume by outcome if outcome is available
        if 'outcome' in df.columns:
            outcome_volumes = df.groupby('outcome')['size'].agg(['sum', 'count']).to_dict('index')
            analysis['volume_by_outcome'] = outcome_volumes
            
            # Create percentage breakdown
            total = df['size'].sum()
            if total > 0:
                analysis['volume_pct_by_outcome'] = {
                    outcome: data['sum'] / total * 100 
                    for outcome, data in outcome_volumes.items()
                }
        
        # Volume by side if side is available
        if 'side' in df.columns:
            side_volumes = df.groupby('side')['size'].agg(['sum', 'count']).to_dict('index')
            analysis['volume_by_side'] = side_volumes
            
            # Create percentage breakdown
            total = df['size'].sum()
            if total > 0:
                analysis['volume_pct_by_side'] = {
                    side: data['sum'] / total * 100 
                    for side, data in side_volumes.items()
                }
                
        # Buy/sell imbalance if available
        if 'side' in df.columns and set(df['side'].unique()) >= {'BUY', 'SELL'}:
            buy_volume = df[df['side'] == 'BUY']['size'].sum()
            sell_volume = df[df['side'] == 'SELL']['size'].sum()
            total_volume = buy_volume + sell_volume
            
            if total_volume > 0:
                analysis['buy_pct'] = buy_volume / total_volume * 100
                analysis['sell_pct'] = sell_volume / total_volume * 100
                
                # Buy/sell ratio (>1 means more buys than sells)
                if sell_volume > 0:
                    analysis['buy_sell_ratio'] = buy_volume / sell_volume
                else:
                    analysis['buy_sell_ratio'] = float('inf')
        
        # Format summary text
        analysis['summary'] = self._format_volume_analysis(analysis)
        
        return analysis
    
    def analyze_trading_patterns(self, df):
        """
        Analyze trading patterns and timing.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades.
            
        Returns:
            dict: Dictionary with trading pattern analysis.
        """
        if 'match_time' not in df.columns:
            self.logger.error("DataFrame must contain 'match_time' column")
            return {}
            
        if len(df) == 0:
            self.logger.warning("Empty DataFrame provided for trading pattern analysis")
            return {}
            
        analysis = {}
        
        # Extract time components
        df = df.copy()
        df['hour'] = df['match_time'].dt.hour
        df['day_of_week'] = df['match_time'].dt.dayofweek
        df['day_name'] = df['match_time'].dt.day_name()
        df['date'] = df['match_time'].dt.date
        
        # Trading frequency by hour
        hour_counts = df.groupby('hour').size()
        analysis['trades_by_hour'] = hour_counts.to_dict()
        analysis['peak_hour'] = hour_counts.idxmax()
        analysis['peak_hour_trades'] = hour_counts.max()
        
        # Trading frequency by day of week
        day_counts = df.groupby(['day_of_week', 'day_name']).size().reset_index()
        day_counts = day_counts.sort_values('day_of_week')
        analysis['trades_by_day'] = {
            day_name: count for _, day_name, count in day_counts.values
        }
        
        if not day_counts.empty:
            peak_day_idx = day_counts[0].idxmax()
            analysis['peak_day'] = day_counts.iloc[peak_day_idx]['day_name']
            analysis['peak_day_trades'] = day_counts.iloc[peak_day_idx][0]
        
        # Activity over time
        date_counts = df.groupby('date').size()
        analysis['active_days'] = len(date_counts)
        analysis['avg_trades_per_active_day'] = date_counts.mean()
        analysis['max_trades_in_a_day'] = date_counts.max()
        analysis['min_trades_in_a_day'] = date_counts.min()
        
        # Time gaps analysis
        if len(df) > 1:
            df_sorted = df.sort_values('match_time')
            time_diffs = df_sorted['match_time'].diff().dropna()
            
            analysis['avg_time_between_trades'] = time_diffs.mean().total_seconds() / 60  # in minutes
            analysis['max_time_between_trades'] = time_diffs.max().total_seconds() / 60  # in minutes
            analysis['min_time_between_trades'] = time_diffs.min().total_seconds() / 60  # in minutes
            
            # Detect periods of high activity
            high_activity_threshold = time_diffs.quantile(0.25)  # 25th percentile as threshold
            high_activity_periods = (time_diffs <= high_activity_threshold).sum()
            analysis['high_activity_periods'] = high_activity_periods
            
            # Detect periods of inactivity
            inactivity_threshold = time_diffs.quantile(0.75)  # 75th percentile as threshold
            inactivity_periods = (time_diffs >= inactivity_threshold).sum()
            analysis['inactivity_periods'] = inactivity_periods
        
        # Format summary text
        analysis['summary'] = self._format_pattern_analysis(analysis)
        
        return analysis
    
    def prepare_visualizations(self, df, market_name=None, save_files=True):
        """
        Prepare a set of visualizations for the trade data.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades.
            market_name (str, optional): Name of the market for visualization titles.
            save_files (bool): Whether to save visualizations to files.
            
        Returns:
            dict: Dictionary with visualization filenames or objects.
        """
        if len(df) == 0:
            self.logger.warning("Empty DataFrame provided for visualizations")
            return {}
        
        visualizations = {}
        
        try:
            # 1. Price history visualization
            self.logger.info("Creating price history visualization")
            price_viz = self.visualizer.plot_price_history(
                df=df,
                market_name=market_name,
                save_file=save_files
            )
            visualizations['price_history'] = price_viz
            
            # 2. Price distribution
            self.logger.info("Creating price distribution visualization")
            price_dist_viz = self.visualizer.plot_price_distribution(
                df=df,
                save_file=save_files
            )
            visualizations['price_distribution'] = price_dist_viz
            
            # 3. Volume by outcome if available
            if 'outcome' in df.columns and 'size' in df.columns:
                self.logger.info("Creating volume by outcome visualization")
                volume_outcome_viz = self.visualizer.plot_volume_distribution(
                    df=df,
                    by='outcome',
                    save_file=save_files
                )
                visualizations['volume_by_outcome'] = volume_outcome_viz
            
            # 4. Volume by side if available
            if 'side' in df.columns and 'size' in df.columns:
                self.logger.info("Creating volume by side visualization")
                volume_side_viz = self.visualizer.plot_volume_distribution(
                    df=df,
                    by='side',
                    save_file=save_files
                )
                visualizations['volume_by_side'] = volume_side_viz
            
            # 5. Trading heatmap
            self.logger.info("Creating trading heatmap visualization")
            heatmap_viz = self.visualizer.plot_trade_heatmap(
                df=df,
                save_file=save_files
            )
            visualizations['trading_heatmap'] = heatmap_viz
            
            # 6. Comprehensive dashboard
            self.logger.info("Creating comprehensive dashboard")
            dashboard_viz = self.visualizer.create_dashboard(
                df=df,
                market_name=market_name,
                save_file=save_files
            )
            visualizations['dashboard'] = dashboard_viz
            
            # Map of files saved
            if save_files:
                visualizations['files'] = {
                    'price_history': os.path.join(self.output_dir, 'price_history.png'),
                    'price_distribution': os.path.join(self.output_dir, 'price_distribution.png'),
                    'trading_heatmap': os.path.join(self.output_dir, 'trading_heatmap.png'),
                    'dashboard': os.path.join(self.output_dir, 'trade_dashboard.png')
                }
                
                if 'outcome' in df.columns and 'size' in df.columns:
                    visualizations['files']['volume_by_outcome'] = os.path.join(self.output_dir, 'volume_by_outcome.png')
                    
                if 'side' in df.columns and 'size' in df.columns:
                    visualizations['files']['volume_by_side'] = os.path.join(self.output_dir, 'volume_by_side.png')
            
        except Exception as e:
            self.logger.error(f"Error creating visualizations: {e}")
        
        return visualizations
    
    def analyze_all(self, trades, market_name=None, create_visualizations=True):
        """
        Perform complete analysis on trade data.
        
        Args:
            trades (list): List of trade dictionaries.
            market_name (str, optional): Name of the market for reporting.
            create_visualizations (bool): Whether to create visualizations.
            
        Returns:
            dict: Dictionary with all analysis results.
        """
        df = self.preprocess_trades(trades)
        
        if len(df) == 0:
            self.logger.warning("No valid trades to analyze")
            return {"error": "No valid trades for analysis"}
        
        analysis = {
            "market_name": market_name,
            "trade_count": len(df),
            "time_range": {
                "start": df['match_time'].min().isoformat() if 'match_time' in df.columns else None,
                "end": df['match_time'].max().isoformat() if 'match_time' in df.columns else None
            }
        }
        
        # Price analysis
        if 'price' in df.columns and 'match_time' in df.columns:
            self.logger.info("Analyzing price movements")
            analysis['price'] = self.analyze_price_movement(df, window='1D')
        
        # Volume analysis
        if 'size' in df.columns:
            self.logger.info("Analyzing trading volume")
            analysis['volume'] = self.analyze_volume(df)
        
        # Trading patterns analysis
        if 'match_time' in df.columns:
            self.logger.info("Analyzing trading patterns")
            analysis['patterns'] = self.analyze_trading_patterns(df)
        
        # Create visualizations if requested
        if create_visualizations:
            self.logger.info("Creating visualizations")
            analysis['visualizations'] = self.prepare_visualizations(df, market_name)
        
        # Save analysis to file
        self._save_analysis_to_file(analysis)
        
        return analysis
    
    def _save_analysis_to_file(self, analysis):
        """Save analysis results to a JSON file."""
        try:
            import json
            from datetime import datetime
            
            # Create a timestamp for the filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            market_suffix = ''
            
            if analysis.get('market_name'):
                # Clean market name for filename
                market_suffix = '_' + ''.join(c for c in analysis['market_name'] if c.isalnum() or c in '_ -').replace(' ', '_')
            
            filename = f"analysis{market_suffix}_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            # Convert non-serializable objects to strings
            class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, (datetime, pd.Timestamp)):
                        return obj.isoformat()
                    return super(DateTimeEncoder, self).default(obj)
            
            # Remove visualization objects (keep only filenames)
            analysis_copy = analysis.copy()
            if 'visualizations' in analysis_copy:
                viz_copy = analysis_copy['visualizations'].copy()
                for key in list(viz_copy.keys()):
                    if key != 'files' and not isinstance(viz_copy[key], (str, int, float, bool, type(None))):
                        viz_copy.pop(key)
                analysis_copy['visualizations'] = viz_copy
            
            with open(filepath, 'w') as f:
                json.dump(analysis_copy, f, indent=2, cls=DateTimeEncoder)
            
            self.logger.info(f"Analysis saved to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving analysis to file: {e}")
    
    def _format_price_analysis(self, analysis):
        """Format price analysis as readable text."""
        lines = [
            "PRICE ANALYSIS:",
            f"- Current Price: ${analysis.get('price_current', 'N/A'):.4f}",
            f"- Price Range: ${analysis.get('price_min', 'N/A'):.4f} to ${analysis.get('price_max', 'N/A'):.4f}",
            f"- Average Price: ${analysis.get('price_mean', 'N/A'):.4f}"
        ]
        
        if 'price_change' in analysis:
            change_sign = '+' if analysis['price_change'] >= 0 else ''
            lines.append(f"- Overall Change: {change_sign}{analysis['price_change']:.4f} ({change_sign}{analysis['price_change_pct']:.2f}%)")
        
        if 'price_24h_change' in analysis:
            change_sign = '+' if analysis['price_24h_change'] >= 0 else ''
            lines.append(f"- 24h Change: {change_sign}{analysis['price_24h_change']:.4f} ({change_sign}{analysis['price_24h_change_pct']:.2f}%)")
        
        if 'price_volatility' in analysis:
            lines.append(f"- Price Volatility: {analysis['price_volatility']:.4f}")
        
        return '\n'.join(lines)
    
    def _format_volume_analysis(self, analysis):
        """Format volume analysis as readable text."""
        lines = [
            "VOLUME ANALYSIS:",
            f"- Total Volume: {analysis.get('total_volume', 'N/A'):.2f} shares",
            f"- Number of Trades: {analysis.get('trade_count', 'N/A')}",
            f"- Average Trade Size: {analysis.get('avg_trade_size', 'N/A'):.2f} shares"
        ]
        
        if 'avg_daily_volume' in analysis:
            lines.append(f"- Average Daily Volume: {analysis['avg_daily_volume']:.2f} shares")
        
        if 'volume_24h' in analysis:
            lines.append(f"- 24h Volume: {analysis['volume_24h']:.2f} shares")
        
        if 'buy_sell_ratio' in analysis:
            if analysis['buy_sell_ratio'] == float('inf'):
                lines.append(f"- Buy/Sell Ratio: All buys (no sells)")
            else:
                lines.append(f"- Buy/Sell Ratio: {analysis['buy_sell_ratio']:.2f} (higher means more buys)")
        
        if 'volume_pct_by_outcome' in analysis:
            lines.append("- Volume by Outcome:")
            for outcome, pct in analysis['volume_pct_by_outcome'].items():
                lines.append(f"  • {outcome}: {pct:.2f}%")
        
        return '\n'.join(lines)
    
    def _format_pattern_analysis(self, analysis):
        """Format trading pattern analysis as readable text."""
        lines = [
            "TRADING PATTERN ANALYSIS:",
            f"- Peak Trading Hour: {analysis.get('peak_hour', 'N/A')}:00 ({analysis.get('peak_hour_trades', 'N/A')} trades)"
        ]
        
        if 'peak_day' in analysis:
            lines.append(f"- Peak Trading Day: {analysis['peak_day']} ({analysis.get('peak_day_trades', 'N/A')} trades)")
        
        if 'avg_time_between_trades' in analysis:
            lines.append(f"- Average Time Between Trades: {analysis['avg_time_between_trades']:.2f} minutes")
        
        if 'max_time_between_trades' in analysis:
            lines.append(f"- Longest Gap Between Trades: {analysis['max_time_between_trades']:.2f} minutes")
        
        if 'active_days' in analysis:
            lines.append(f"- Active Trading Days: {analysis['active_days']}")
            lines.append(f"- Average Trades per Day: {analysis['avg_trades_per_active_day']:.2f}")
        
        return '\n'.join(lines) 