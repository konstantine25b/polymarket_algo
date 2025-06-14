"""
Simulation AutoBidder implementation for Polymarket.
Analyzes statistical opportunities and places simulated orders based on the highest buy-only opportunity.
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any
import numpy as np
from pathlib import Path

from src.bidding_decision.stats.comparison import generate_comparison_table
from src.simulation.initialization.run_initializer import RunInitializer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_stats_table(df):
    """
    Print the full stats comparison table.
    
    Args:
        df: DataFrame with comparison data
    """
    # Set pandas display options to show all columns
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.float_format', '{:.2f}'.format)
    pd.set_option('display.precision', 2)
    
    # Determine which columns to show in the main display
    display_cols = [col for col in df.columns if col not in ['Token ID', 'Market ID']]
    
    print("\nComparison Table:")
    print(df[display_cols].to_string(index=False))
    
    # Show the threshold being used
    buy_only_col = [col for col in df.columns if col.startswith('Buy-Only')][0]
    threshold_value = float(buy_only_col.split('(')[1].split('%')[0])
    print(f"\nUsing threshold: {threshold_value}%")
    
    # Show token IDs in a cleaner format
    print("\nToken IDs:")
    data_rows = df[df['Range'] != 'EXPECTED VALUE']
    for _, row in data_rows.iterrows():
        if 'Token ID' in row and row['Token ID']:
            print(f"{row['Range']}: {row['Token ID']}")
    
    # Get expected value info
    ev_row = df[df['Range'] == 'EXPECTED VALUE'].iloc[0]
    print("\nExpected Values:")
    print(f"Prediction: {ev_row['Pred (%)']}%")
    print(f"Market: {ev_row['Mkt (%)']}%")
    print(f"Difference: {ev_row['Diff (%)']}%")

class SimulationBidder:
    """
    Automated bidder that uses statistical opportunities to place simulated buy orders.
    Replicates the exact logic of the real AutoBidder but operates on simulation JSON files.
    """
    
    def __init__(self, threshold: float = 0.0, order_amount: float = 10.0, 
                 use_weighted_selection: bool = False, min_prediction: float = 0.0, 
                 algorithm: str = 'enhanced_facebook_prophet', random_seed: int = 42,
                 debug: bool = False, show_eachalgo_distribution: bool = False):
        """
        Initialize the SimulationBidder.
        
        Args:
            threshold: Minimum opportunity percentage required to place an order (%)
            order_amount: Amount to bid in USD
            use_weighted_selection: If True, use weighted probability to select from multiple positive opportunities
            min_prediction: Minimum prediction percentage required to consider an opportunity (%)
            algorithm: Prediction algorithm to use (default: enhanced_facebook_prophet)
            random_seed: Random seed for reproducible results (default: 42)
            debug: Whether to show detailed debugging information
            show_eachalgo_distribution: Show probability distribution for each individual algorithm
        """
        self.threshold = threshold
        self.order_amount = order_amount
        self.use_weighted_selection = use_weighted_selection
        self.min_prediction = min_prediction
        self.algorithm = algorithm
        self.random_seed = random_seed
        self.debug = debug
        self.show_eachalgo_distribution = show_eachalgo_distribution
        self.run_initializer = RunInitializer()
        
    def find_best_opportunity(self, update_markets: bool = True, show_stats: bool = True) -> Optional[Dict[str, Any]]:
        """
        Find the best buy opportunity based on statistical analysis.
        Uses the same logic as the real AutoBidder.
        
        Args:
            update_markets: Whether to update market prices before analysis
            show_stats: Whether to display the full comparison table
            
        Returns:
            Dict containing opportunity details or None if no opportunity found
        """
        try:
            # Generate comparison table with the specified threshold and algorithm
            if self.debug:
                print(f"Generating comparison table with algorithm: {self.algorithm}, threshold: {self.threshold}%, random_seed: {self.random_seed}")
                
            df = generate_comparison_table(
                refresh=update_markets,
                use_prophet=True,
                algorithm=self.algorithm,
                threshold=self.threshold,
                silent=not show_stats,  # Show table unless explicitly disabled
                random_seed=self.random_seed,
                show_eachalgo_distribution=self.show_eachalgo_distribution
            )
            
            # Show the stats table if requested and not already shown
            if show_stats and not df.empty:
                print_stats_table(df)
            
            if df.empty:
                logger.info("No opportunities found in comparison table.")
                return None
                
            # Find the column name for buy-only opportunities
            buy_only_col = [col for col in df.columns if col.startswith('Buy-Only')][0]
            
            # Get only rows that are not EXPECTED VALUE
            data_rows = df[df['Range'] != 'EXPECTED VALUE'].copy()
            
            if data_rows.empty:
                logger.info("No specific range opportunities found.")
                return None
            
            # Filter for positive buy opportunities above the threshold
            positive_opps = data_rows[data_rows[buy_only_col] > 0].copy()
            
            # Check if there are any meaningful buy opportunities above the threshold
            if positive_opps.empty or positive_opps[buy_only_col].max() <= 0:
                logger.info(f"No buy opportunities found above threshold {self.threshold}%.")
                return None
                
            # Apply minimum prediction filter if set
            if self.min_prediction > 0:
                prev_count = len(positive_opps)
                positive_opps = positive_opps[positive_opps['Pred (%)'] >= self.min_prediction].copy()
                filtered_count = prev_count - len(positive_opps)
                
                if filtered_count > 0:
                    logger.info(f"Filtered out {filtered_count} opportunities below minimum prediction threshold of {self.min_prediction}%")
                
                if positive_opps.empty:
                    logger.info(f"No opportunities meet the minimum prediction threshold of {self.min_prediction}%")
                    return None
                
            best_row = None
            
            # Use weighted selection if enabled and there are multiple positive opportunities
            if self.use_weighted_selection and len(positive_opps) > 1:
                # Calculate weights based on opportunity values
                weights = positive_opps[buy_only_col].values
                # Normalize weights to probabilities
                probs = weights / weights.sum()
                
                # Select a row using weighted probabilities
                selected_idx = np.random.choice(positive_opps.index, p=probs)
                best_row = positive_opps.loc[selected_idx]
                
                logger.info(f"Using weighted selection from {len(positive_opps)} opportunities")
                logger.info(f"Selected opportunity: {best_row['Range']} with {best_row[buy_only_col]}% edge " +
                           f"(probability: {probs[positive_opps.index.get_loc(selected_idx)]:.2f})")
            else:
                # Find the row with the highest buy-only opportunity (original behavior)
                best_idx = positive_opps[buy_only_col].idxmax()
                best_row = positive_opps.loc[best_idx]
                
                logger.info(f"Selected highest opportunity: {best_row['Range']} with {best_row[buy_only_col]}% edge")
            
            # Extract information about the opportunity
            opportunity = {
                'range': best_row['Range'],
                'token_id': best_row['Token ID'],
                'prediction': best_row['Pred (%)'],
                'market': best_row['Mkt (%)'],
                'ask': best_row['Ask (%)'],
                'opportunity': best_row[buy_only_col],
                'difference': best_row['Diff (%)'],
                'threshold': self.threshold,
                'min_prediction': self.min_prediction,
                'algorithm': self.algorithm,
                'random_seed': self.random_seed,
                'selection_method': 'weighted' if self.use_weighted_selection else 'best',
                'total_opportunities': len(positive_opps)
            }
            
            if self.debug:
                print(f"DEBUG - Best opportunity details:")
                for key, value in opportunity.items():
                    print(f"  {key}: {value}")
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error finding opportunities: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None
    
    def place_simulated_order(self, run_name: str, opportunity: Dict[str, Any], dry_run: bool = False) -> bool:
        """
        Place a simulated market buy order for the given opportunity.
        
        Args:
            run_name: Name of the simulation run
            opportunity: Dict with opportunity details
            dry_run: If True, only show what would happen without executing
            
        Returns:
            bool: True if order placed successfully, False otherwise
        """
        if not opportunity or 'token_id' not in opportunity:
            logger.error("Invalid opportunity provided.")
            return False
            
        try:
            token_id = opportunity['token_id']
            range_name = opportunity['range']
            ask_price = opportunity['ask'] / 100.0  # Convert percentage to decimal
            
            # Calculate number of shares based on order amount and ask price
            shares_to_buy = self.order_amount / ask_price
            
            if dry_run:
                print(f"🔍 DRY RUN - Would place order:")
                print(f"   Market: {range_name} (Token ID: {token_id})")
                print(f"   Order amount: ${self.order_amount} USD")
                print(f"   Ask price: {opportunity['ask']}% (${ask_price:.4f})")
                print(f"   Shares to buy: {shares_to_buy:.2f}")
                print(f"   Opportunity edge: {opportunity['opportunity']:.1f}%")
                return True
            
            logger.info(f"Placing simulated buy order for {range_name} (token ID: {token_id})")
            logger.info(f"Order amount: ${self.order_amount} USD at {opportunity['ask']}% (~${ask_price:.4f} per share)")
            logger.info(f"Shares to buy: {shares_to_buy:.2f}")
            
            # Execute the simulated order using RunInitializer
            # Note: The add_position method automatically uses the market's current ask price
            success = self.run_initializer.add_position(
                run_name=run_name,
                market_id=token_id,
                num_shares=shares_to_buy,
                allow_negative_balance=False  # Don't allow negative balance by default
            )
            
            if success:
                logger.info(f"✅ Simulated order executed successfully")
                if self.debug:
                    print(f"DEBUG - Order details recorded in simulation run '{run_name}'")
                    print(f"DEBUG - Auto-bid description: {range_name} ({opportunity['opportunity']:.1f}% edge)")
                return True
            else:
                logger.error(f"❌ Failed to execute simulated order")
                return False
            
        except Exception as e:
            logger.error(f"Error placing simulated order: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def update_simulation_markets(self, run_name: str) -> bool:
        """
        Update market prices in the simulation run from real Polymarket data.
        
        Args:
            run_name: Name of the simulation run
            
        Returns:
            bool: True if markets updated successfully
        """
        try:
            logger.info(f"Updating market prices for simulation run: {run_name}")
            success = self.run_initializer.update_markets_from_polymarket(run_name)
            
            if success:
                logger.info("✅ Market prices updated successfully")
            else:
                logger.warning("⚠️ Market price update failed or partially failed")
                
            return success
            
        except Exception as e:
            logger.error(f"Error updating simulation markets: {e}")
            return False
    
    def auto_bid_simulation(self, run_name: str, update_markets: bool = True, dry_run: bool = False, show_stats: bool = True) -> bool:
        """
        Complete automated bidding process for simulation: update markets, find opportunities, and place order.
        
        Args:
            run_name: Name of the simulation run
            update_markets: Whether to update market prices before finding opportunities
            dry_run: If True, only show what would happen without executing
            show_stats: Whether to display the full comparison table
            
        Returns:
            bool: True if order placed successfully, False otherwise
        """
        try:
            # Check if run exists
            if not self.run_initializer.run_exists(run_name):
                logger.error(f"Simulation run '{run_name}' does not exist")
                return False
            
            if self.debug:
                print(f"DEBUG - Starting auto-bid simulation for run: {run_name}")
                print(f"DEBUG - Settings: threshold={self.threshold}%, amount=${self.order_amount}, weighted={self.use_weighted_selection}")
            
            # Step 1: Update market prices if requested
            if update_markets:
                if not dry_run:
                    self.update_simulation_markets(run_name)
                else:
                    print("🔍 DRY RUN - Would update market prices from Polymarket")
            
            # Step 2: Find the best opportunity
            logger.info("Analyzing market opportunities...")
            opportunity = self.find_best_opportunity(update_markets=False, show_stats=show_stats)  # Already updated above
            
            if not opportunity:
                logger.info("❌ No suitable opportunities found for bidding")
                return False
            
            # Step 3: Place the simulated order
            logger.info(f"💡 Found opportunity: {opportunity['range']} with {opportunity['opportunity']:.1f}% edge")
            success = self.place_simulated_order(run_name, opportunity, dry_run=dry_run)
            
            if success and not dry_run:
                logger.info("🎉 Simulation bidding completed successfully!")
            elif success and dry_run:
                logger.info("🔍 Dry run completed - no actual changes made")
                
            return success
            
        except Exception as e:
            logger.error(f"Error in auto-bid simulation: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def analyze_opportunities(self, update_markets: bool = True, show_stats: bool = True) -> Optional[pd.DataFrame]:
        """
        Analyze current market opportunities without placing any orders.
        
        Args:
            update_markets: Whether to update market prices before analysis
            show_stats: Whether to display the full comparison table
            
        Returns:
            DataFrame with opportunity analysis or None if failed
        """
        try:
            logger.info("Analyzing current market opportunities...")
            
            # Generate comparison table
            df = generate_comparison_table(
                refresh=update_markets,
                use_prophet=True,
                algorithm=self.algorithm,
                threshold=self.threshold,
                silent=not show_stats,
                random_seed=self.random_seed,
                show_eachalgo_distribution=self.show_eachalgo_distribution
            )
            
            # Show the stats table if requested and not already shown
            if show_stats and not df.empty:
                print_stats_table(df)
            
            if df.empty:
                logger.info("No opportunities found in comparison table.")
                return None
            
            # Filter to show only data rows (not EXPECTED VALUE)
            data_rows = df[df['Range'] != 'EXPECTED VALUE'].copy()
            
            if data_rows.empty:
                logger.info("No specific range opportunities found.")
                return None
            
            # Find buy-only opportunities column
            buy_only_col = [col for col in df.columns if col.startswith('Buy-Only')][0]
            
            # Sort by buy-only opportunity descending
            data_rows = data_rows.sort_values(by=buy_only_col, ascending=False)
            
            # Apply filters similar to find_best_opportunity
            positive_opps = data_rows[data_rows[buy_only_col] > 0].copy()
            
            if self.min_prediction > 0:
                positive_opps = positive_opps[positive_opps['Pred (%)'] >= self.min_prediction].copy()
            
            logger.info(f"Found {len(positive_opps)} positive opportunities above threshold {self.threshold}%")
            
            if self.debug and not positive_opps.empty:
                print(f"\nDEBUG - Top opportunities:")
                for i, (_, row) in enumerate(positive_opps.head(5).iterrows()):
                    print(f"  {i+1}. {row['Range']}: {row[buy_only_col]:.1f}% edge, {row['Pred (%)']}% prediction")
            
            return data_rows
            
        except Exception as e:
            logger.error(f"Error analyzing opportunities: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None 