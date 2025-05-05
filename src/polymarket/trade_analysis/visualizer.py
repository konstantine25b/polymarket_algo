import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from matplotlib.ticker import FuncFormatter
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class PolymarketTradeVisualizer:
    """
    A class to visualize Polymarket trade data with enhanced aesthetics and information.
    """
    
    def __init__(self, theme='dark_background', output_dir='.', dpi=300):
        """
        Initialize the visualizer with styling settings.
        
        Args:
            theme (str): Theme for matplotlib visualizations ('dark_background', 'darkgrid', etc)
            output_dir (str): Directory to save visualization files.
            dpi (int): Resolution for saved figures.
        """
        # Set output directory
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Set high-quality figure defaults
        self.dpi = dpi
        plt.style.use(theme)
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['savefig.dpi'] = self.dpi
        plt.rcParams['font.size'] = 12
        plt.rcParams['axes.titlesize'] = 16
        plt.rcParams['axes.labelsize'] = 14
        plt.rcParams['xtick.labelsize'] = 12
        plt.rcParams['ytick.labelsize'] = 12
        
        # Define custom color palettes
        self.outcome_colors = {
            'Yes': '#2ecc71',  # Green
            'No': '#e74c3c',   # Red
            'Unknown': '#3498db'  # Blue
        }
        
        self.side_colors = {
            'BUY': '#27ae60',   # Darker green
            'SELL': '#c0392b'   # Darker red
        }
        
        # Set custom color palettes
        self.palette = sns.color_palette("viridis", 10)
        
    def _format_price(self, x, pos):
        """Custom formatter for price values."""
        return f'${x:.2f}'
        
    def _format_date(self, ax, rotation=45):
        """Configure date formatting for the x-axis."""
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.get_xticklabels(), rotation=rotation, ha='right')
        
    def plot_price_history(self, df, market_name=None, save_file=True):
        """
        Plot an enhanced price history chart with volume bars.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades with 'match_time' and 'price' columns.
            market_name (str, optional): Name of the market for the plot title.
            save_file (bool): Whether to save the plot to a file.
            
        Returns:
            matplotlib.figure.Figure: The generated figure.
        """
        if 'match_time' not in df.columns or 'price' not in df.columns:
            raise ValueError("DataFrame must contain 'match_time' and 'price' columns")
        
        # Ensure match_time is datetime and price is float
        df = df.copy()
        if not pd.api.types.is_datetime64_dtype(df['match_time']):
            df['match_time'] = pd.to_datetime(df['match_time'])
        df['price'] = df['price'].astype(float)
        
        # Sort by time
        df = df.sort_values('match_time')
        
        # Create figure with two subplots (price and volume)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
        
        # Title setup
        title = f"Price History{' - ' + market_name if market_name else ''}"
        fig.suptitle(title, fontsize=18, y=0.98)
        
        # Price plot (top)
        if 'outcome' in df.columns:
            for outcome, group in df.groupby('outcome'):
                color = self.outcome_colors.get(outcome, '#3498db')
                ax1.plot(group['match_time'], group['price'], 'o-', label=outcome, 
                       linewidth=2, markersize=8, color=color, alpha=0.8)
                
                # Add price labels to the last point
                last_point = group.iloc[-1]
                ax1.annotate(f'${last_point["price"]:.2f}', 
                           xy=(last_point['match_time'], last_point['price']),
                           xytext=(10, 0), textcoords='offset points',
                           fontsize=12, color=color)
            ax1.legend(title='Outcome', loc='upper left', frameon=True, framealpha=0.9)
        else:
            ax1.plot(df['match_time'], df['price'], 'o-', linewidth=2, markersize=8, color='#3498db')
        
        # Format price axis
        ax1.yaxis.set_major_formatter(FuncFormatter(self._format_price))
        ax1.set_ylabel('Price (USDC)', fontsize=14)
        ax1.set_title('Price Over Time', fontsize=16, pad=10)
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # Volume plot (bottom)
        if 'size' in df.columns:
            df['size'] = df['size'].astype(float)
            
            if 'side' in df.columns:
                for side, group in df.groupby('side'):
                    color = self.side_colors.get(side, '#3498db')
                    ax2.bar(group['match_time'], group['size'], label=side, alpha=0.7, color=color)
                ax2.legend(title='Side', loc='upper left')
            else:
                ax2.bar(df['match_time'], df['size'], alpha=0.7, color='#3498db')
            
            ax2.set_ylabel('Volume (shares)', fontsize=14)
            ax2.set_title('Trading Volume', fontsize=16, pad=10)
            ax2.grid(True, alpha=0.3, linestyle='--')
        
        # Format x-axis dates
        self._format_date(ax2)
        ax2.set_xlabel('Time', fontsize=14)
        
        # Add price range and average in the text box
        price_stats = f"Price Range: ${df['price'].min():.2f} - ${df['price'].max():.2f}\n"
        price_stats += f"Average Price: ${df['price'].mean():.2f}\n"
        if 'size' in df.columns:
            price_stats += f"Total Volume: {df['size'].sum():.0f} shares"
            
        props = dict(boxstyle='round', facecolor='#2c3e50', alpha=0.7)
        ax1.text(0.02, 0.05, price_stats, transform=ax1.transAxes, fontsize=12,
                verticalalignment='bottom', bbox=props)
        
        plt.tight_layout()
        fig.subplots_adjust(hspace=0.1)
        
        # Save if requested
        if save_file:
            output_path = os.path.join(self.output_dir, 'price_history.png')
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            print(f"Price history plot saved to {output_path}")
        
        return fig
    
    def plot_volume_distribution(self, df, by='outcome', save_file=True):
        """
        Plot an enhanced distribution of trading volume.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades.
            by (str): Column to group by ('outcome', 'side', etc.).
            save_file (bool): Whether to save the plot to a file.
            
        Returns:
            matplotlib.figure.Figure: The generated figure.
        """
        if 'size' not in df.columns or by not in df.columns:
            raise ValueError(f"DataFrame must contain 'size' and '{by}' columns")
        
        # Ensure size is float
        df = df.copy()
        df['size'] = df['size'].astype(float)
        
        # Group and sum
        volume_by_group = df.groupby(by)['size'].sum().reset_index()
        volume_by_group = volume_by_group.sort_values('size', ascending=False)
        
        # Add percentage calculation
        total_volume = volume_by_group['size'].sum()
        volume_by_group['percentage'] = volume_by_group['size'] / total_volume * 100
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Get colors based on category
        colors = [self.outcome_colors.get(val, self.palette[i % len(self.palette)]) 
                 if by == 'outcome' else 
                 self.side_colors.get(val, self.palette[i % len(self.palette)]) 
                 if by == 'side' else 
                 self.palette[i % len(self.palette)] 
                 for i, val in enumerate(volume_by_group[by])]
        
        # Create bar plot
        bars = ax.bar(
            volume_by_group[by], 
            volume_by_group['size'],
            color=colors,
            alpha=0.8
        )
        
        # Add exact values and percentages on top of bars
        for bar, value, percentage in zip(bars, volume_by_group['size'], volume_by_group['percentage']):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2.,
                height + 0.1,
                f'{value:.1f}\n({percentage:.1f}%)',
                ha='center', 
                va='bottom',
                fontsize=12
            )
            
        # Formatting
        ax.set_title(f'Trading Volume by {by.capitalize()}', fontsize=18)
        ax.set_xlabel(by.capitalize(), fontsize=14)
        ax.set_ylabel('Volume (shares)', fontsize=14)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Summary text
        summary = f"Total Volume: {total_volume:.0f} shares\n"
        summary += f"Max Category: {volume_by_group.iloc[0][by]} ({volume_by_group.iloc[0]['size']:.1f} shares, {volume_by_group.iloc[0]['percentage']:.1f}%)"
        
        props = dict(boxstyle='round', facecolor='#2c3e50', alpha=0.7)
        ax.text(0.02, 0.95, summary, transform=ax.transAxes, fontsize=12,
               verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        # Save if requested
        if save_file:
            output_path = os.path.join(self.output_dir, f'volume_by_{by}.png')
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            print(f"Volume distribution plot saved to {output_path}")
        
        return fig
    
    def plot_price_distribution(self, df, save_file=True):
        """
        Plot an enhanced distribution of trade prices.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades with 'price' column.
            save_file (bool): Whether to save the plot to a file.
            
        Returns:
            matplotlib.figure.Figure: The generated figure.
        """
        if 'price' not in df.columns:
            raise ValueError("DataFrame must contain 'price' column")
        
        # Ensure price is float
        df = df.copy()
        df['price'] = df['price'].astype(float)
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # Histogram plot
        sns.histplot(data=df, x='price', kde=True, bins=15, ax=ax1, 
                    color='#3498db', edgecolor='white', alpha=0.7, line_kws={'linewidth': 2})
        
        ax1.set_title('Price Distribution Histogram', fontsize=18)
        ax1.set_xlabel('Price (USDC)', fontsize=14)
        ax1.set_ylabel('Frequency', fontsize=14)
        ax1.yaxis.grid(True, alpha=0.3, linestyle='--')
        ax1.xaxis.set_major_formatter(FuncFormatter(self._format_price))
        
        # Box plot (optional outcome split)
        if 'outcome' in df.columns:
            sns.boxplot(data=df, x='outcome', y='price', ax=ax2, 
                       palette=self.outcome_colors, width=0.5)
        else:
            sns.boxplot(data=df, y='price', ax=ax2, color='#3498db', width=0.5)
            ax2.set_xlabel('')
            
        ax2.set_title('Price Distribution Boxplot', fontsize=18)
        ax2.set_ylabel('Price (USDC)', fontsize=14)
        ax2.yaxis.set_major_formatter(FuncFormatter(self._format_price))
        ax2.grid(True, alpha=0.3, linestyle='--')
        
        # Add price statistics
        price_stats = f"Mean Price: ${df['price'].mean():.2f}\n"
        price_stats += f"Median Price: ${df['price'].median():.2f}\n"
        price_stats += f"Min Price: ${df['price'].min():.2f}\n"
        price_stats += f"Max Price: ${df['price'].max():.2f}\n"
        price_stats += f"Std Dev: ${df['price'].std():.3f}"
        
        props = dict(boxstyle='round', facecolor='#2c3e50', alpha=0.7)
        ax1.text(0.03, 0.95, price_stats, transform=ax1.transAxes, fontsize=12,
                verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        # Save if requested
        if save_file:
            output_path = os.path.join(self.output_dir, 'price_distribution.png')
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            print(f"Price distribution plot saved to {output_path}")
        
        return fig
    
    def plot_trade_heatmap(self, df, save_file=True):
        """
        Plot an enhanced heatmap of trading activity over time.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades with 'match_time' column.
            save_file (bool): Whether to save the plot to a file.
            
        Returns:
            matplotlib.figure.Figure: The generated figure.
        """
        if 'match_time' not in df.columns:
            raise ValueError("DataFrame must contain 'match_time' column")
        
        # Ensure match_time is datetime
        df = df.copy()
        if not pd.api.types.is_datetime64_dtype(df['match_time']):
            df['match_time'] = pd.to_datetime(df['match_time'])
        
        # Extract components for heatmap
        df['hour'] = df['match_time'].dt.hour
        df['weekday'] = df['match_time'].dt.strftime('%a')  # Day name abbreviated
        
        # Order by weekday (Monday first)
        day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        # Count trades for each weekday-hour combination
        activity_counts = df.groupby(['weekday', 'hour']).size().reset_index(name='counts')
        
        # Pivot data into a matrix format suitable for heatmap
        try:
            pivot_table = activity_counts.pivot(index='weekday', columns='hour', values='counts')
            
            # Reorder index to ensure days are in correct order
            weekday_order = [day for day in day_order if day in pivot_table.index]
            pivot_table = pivot_table.reindex(weekday_order)
            
        except Exception as e:
            # If pivot fails (e.g., single day of data), create an empty matrix
            print(f"Limited data for heatmap, creating simplified view: {e}")
            
            hours = list(range(24))
            days_in_data = sorted(df['weekday'].unique(), key=lambda x: day_order.index(x) if x in day_order else 99)
            
            pivot_table = pd.DataFrame(0, index=days_in_data, columns=hours)
            for _, row in activity_counts.iterrows():
                pivot_table.loc[row['weekday'], row['hour']] = row['counts']
        
        # Fill any missing hours with zeros
        pivot_table = pivot_table.fillna(0)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Create heatmap with custom colormap
        cmap = sns.color_palette("viridis", as_cmap=True)
        heatmap = sns.heatmap(
            pivot_table, 
            cmap=cmap,
            annot=True, 
            fmt='g',
            linewidths=0.5,
            ax=ax,
            cbar_kws={'label': 'Number of Trades'}
        )
        
        # Formatting
        ax.set_title('Trading Activity by Day and Hour', fontsize=18)
        ax.set_xlabel('Hour of Day', fontsize=14)
        ax.set_ylabel('Day of Week', fontsize=14)
        
        # Set x-ticks with AM/PM format
        hour_labels = []
        for h in range(24):
            if h == 0:
                hour_labels.append("12 AM")
            elif h < 12:
                hour_labels.append(f"{h} AM")
            elif h == 12:
                hour_labels.append("12 PM")
            else:
                hour_labels.append(f"{h-12} PM")
        
        # Only show every other hour label to avoid crowding
        ax.set_xticks(np.arange(0, 24, 2))
        ax.set_xticklabels([hour_labels[i] for i in range(0, 24, 2)])
        
        # Add summary statistics
        total_trades = int(pivot_table.sum().sum())
        max_hour = pivot_table.sum(axis=0).idxmax()
        max_hour_count = int(pivot_table.sum(axis=0).max())
        max_day = pivot_table.sum(axis=1).idxmax() if not pivot_table.sum(axis=1).empty else "N/A"
        max_day_count = int(pivot_table.sum(axis=1).max()) if not pivot_table.sum(axis=1).empty else 0
        
        summary = f"Total Trades: {total_trades}\n"
        summary += f"Most Active Hour: {hour_labels[max_hour]} ({max_hour_count} trades)\n"
        summary += f"Most Active Day: {max_day} ({max_day_count} trades)"
        
        props = dict(boxstyle='round', facecolor='#2c3e50', alpha=0.7)
        ax.text(1.02, 0.97, summary, transform=ax.transAxes, fontsize=12,
               verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        # Save if requested
        if save_file:
            output_path = os.path.join(self.output_dir, 'trading_heatmap.png')
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            print(f"Trading heatmap saved to {output_path}")
        
        return fig
        
    def create_dashboard(self, df, market_name=None, save_file=True):
        """
        Create a comprehensive dashboard of all visualizations.
        
        Args:
            df (pandas.DataFrame): DataFrame of trades.
            market_name (str, optional): Name of the market for the dashboard title.
            save_file (bool): Whether to save the plot to a file.
            
        Returns:
            matplotlib.figure.Figure: The generated figure.
        """
        # Create a large figure with subplots for each visualization
        fig = plt.figure(figsize=(20, 16))
        
        # Set the title
        title = f"Polymarket Trade Analysis Dashboard{' - ' + market_name if market_name else ''}"
        fig.suptitle(title, fontsize=24, y=0.98)
        
        # Create a grid of subplots
        gs = fig.add_gridspec(3, 2, height_ratios=[1.5, 1, 1])
        
        # Price History (top row, spans both columns)
        ax_price = fig.add_subplot(gs[0, :])
        
        # Ensure data is properly formatted
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_dtype(df_copy['match_time']):
            df_copy['match_time'] = pd.to_datetime(df_copy['match_time'])
        df_copy['price'] = df_copy['price'].astype(float)
        df_copy = df_copy.sort_values('match_time')
        
        # Plot price history
        if 'outcome' in df_copy.columns:
            for outcome, group in df_copy.groupby('outcome'):
                color = self.outcome_colors.get(outcome, '#3498db')
                ax_price.plot(group['match_time'], group['price'], 'o-', label=outcome, 
                             linewidth=2, markersize=6, color=color)
            ax_price.legend(title='Outcome', loc='best')
        else:
            ax_price.plot(df_copy['match_time'], df_copy['price'], 'o-', linewidth=2, markersize=6, color='#3498db')
            
        ax_price.set_title('Price History', fontsize=16)
        ax_price.set_ylabel('Price (USDC)', fontsize=14)
        ax_price.yaxis.set_major_formatter(FuncFormatter(self._format_price))
        ax_price.grid(True, alpha=0.3, linestyle='--')
        self._format_date(ax_price)
        
        # Volume by Outcome (middle row, left)
        ax_volume = fig.add_subplot(gs[1, 0])
        
        if 'outcome' in df_copy.columns and 'size' in df_copy.columns:
            df_copy['size'] = df_copy['size'].astype(float)
            volume_by_outcome = df_copy.groupby('outcome')['size'].sum().reset_index()
            
            # Set colors
            colors = [self.outcome_colors.get(outcome, self.palette[i % len(self.palette)]) 
                     for i, outcome in enumerate(volume_by_outcome['outcome'])]
            
            # Create bars
            bars = ax_volume.bar(volume_by_outcome['outcome'], volume_by_outcome['size'], color=colors)
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax_volume.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{height:.1f}', ha='center', va='bottom', fontsize=10)
                
            ax_volume.set_title('Volume by Outcome', fontsize=16)
            ax_volume.set_xlabel('Outcome', fontsize=14)
            ax_volume.set_ylabel('Volume (shares)', fontsize=14)
            ax_volume.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        # Price Distribution (middle row, right)
        ax_price_dist = fig.add_subplot(gs[1, 1])
        
        sns.histplot(data=df_copy, x='price', kde=True, ax=ax_price_dist, 
                    color='#3498db', edgecolor='white', alpha=0.7)
        
        ax_price_dist.set_title('Price Distribution', fontsize=16)
        ax_price_dist.set_xlabel('Price (USDC)', fontsize=14)
        ax_price_dist.set_ylabel('Frequency', fontsize=14)
        ax_price_dist.grid(True, alpha=0.3, linestyle='--')
        ax_price_dist.xaxis.set_major_formatter(FuncFormatter(self._format_price))
        
        # Trading Activity Heatmap (bottom row, spans both columns)
        ax_heatmap = fig.add_subplot(gs[2, :])
        
        # Extract components for heatmap
        df_copy['hour'] = df_copy['match_time'].dt.hour
        df_copy['weekday'] = df_copy['match_time'].dt.strftime('%a')
        
        # Order by weekday (Monday first)
        day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        # Count trades for each weekday-hour combination
        activity_counts = df_copy.groupby(['weekday', 'hour']).size().reset_index(name='counts')
        
        try:
            # Pivot data into a matrix format suitable for heatmap
            pivot_table = activity_counts.pivot(index='weekday', columns='hour', values='counts')
            
            # Reorder index to ensure days are in correct order
            weekday_order = [day for day in day_order if day in pivot_table.index]
            pivot_table = pivot_table.reindex(weekday_order)
            
            # Fill any missing hours with zeros
            pivot_table = pivot_table.fillna(0)
            
            # Create heatmap
            sns.heatmap(
                pivot_table, 
                cmap="viridis",
                annot=True, 
                fmt='g',
                linewidths=0.5,
                ax=ax_heatmap,
                cbar_kws={'label': 'Number of Trades'}
            )
        except:
            # Fallback if not enough data for pivot
            ax_heatmap.text(0.5, 0.5, "Insufficient data for heatmap", 
                         ha='center', va='center', fontsize=14)
            ax_heatmap.set_xticks([])
            ax_heatmap.set_yticks([])
        
        ax_heatmap.set_title('Trading Activity by Day and Hour', fontsize=16)
        ax_heatmap.set_xlabel('Hour of Day', fontsize=14)
        ax_heatmap.set_ylabel('Day of Week', fontsize=14)
        
        # Add summary statistics box
        summary = self._generate_summary_stats(df_copy)
        props = dict(boxstyle='round', facecolor='#2c3e50', alpha=0.7)
        fig.text(0.02, 0.96, summary, fontsize=12, verticalalignment='top', 
                bbox=props, transform=fig.transFigure)
        
        plt.tight_layout()
        fig.subplots_adjust(top=0.92, hspace=0.3, wspace=0.2)
        
        # Save if requested
        if save_file:
            output_path = os.path.join(self.output_dir, 'trade_dashboard.png')
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            print(f"Trade dashboard saved to {output_path}")
        
        return fig
    
    def _generate_summary_stats(self, df):
        """Generate summary statistics text for dashboard."""
        summary = "Trade Summary Statistics:\n"
        
        # Trade count
        summary += f"• Total Trades: {len(df)}\n"
        
        # Price stats
        if 'price' in df.columns:
            summary += f"• Price Range: ${df['price'].min():.2f} - ${df['price'].max():.2f}\n"
            summary += f"• Average Price: ${df['price'].mean():.2f}\n"
        
        # Volume stats
        if 'size' in df.columns:
            total_volume = df['size'].astype(float).sum()
            summary += f"• Total Volume: {total_volume:.1f} shares\n"
            
        # Side distribution
        if 'side' in df.columns:
            side_counts = df['side'].value_counts()
            if 'BUY' in side_counts:
                summary += f"• Buy Orders: {side_counts['BUY']} ({side_counts['BUY']/len(df)*100:.1f}%)\n"
            if 'SELL' in side_counts:
                summary += f"• Sell Orders: {side_counts['SELL']} ({side_counts['SELL']/len(df)*100:.1f}%)\n"
                
        # Time range
        if 'match_time' in df.columns:
            first_trade = df['match_time'].min().strftime('%Y-%m-%d %H:%M')
            last_trade = df['match_time'].max().strftime('%Y-%m-%d %H:%M')
            summary += f"• Time Period: {first_trade} to {last_trade}"
            
        return summary 