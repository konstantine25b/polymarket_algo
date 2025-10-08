"""
AutoBidder implementation for Polymarket.
Analyzes statistical opportunities and places orders based on the highest buy-only opportunity.
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any
import random
import numpy as np
import time

from src.bidding_decision.stats.comparison import generate_comparison_table
from src.polymarket.bidding import PolymarketClient
from src.polymarket.bidding.buy.market import MarketBuyOrder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoBidder:
    """
    Automated bidder that uses statistical opportunities to place market buy orders.
    """
    
    def __init__(self, threshold: float = 0.0, order_amount: float = 1.0, use_weighted_selection: bool = False, min_prediction: float = 0.0, algorithm: str = "prophet", random_seed: int = 42, show_eachalgo_distribution: bool = False):
        """
        Initialize the AutoBidder.
        
        Args:
            threshold: Minimum opportunity percentage required to place an order (%)
            order_amount: Amount to bid in USDC
            use_weighted_selection: If True, use weighted probability to select from multiple positive opportunities
                                   rather than always selecting the best one
            min_prediction: Minimum prediction percentage required to consider an opportunity (%)
            algorithm: Prediction algorithm to use
            random_seed: Random seed for reproducible predictions
            show_eachalgo_distribution: Whether to show individual algorithm distributions
        """
        self.threshold = threshold
        self.order_amount = order_amount
        self.use_weighted_selection = use_weighted_selection
        self.min_prediction = min_prediction
        self.algorithm = algorithm
        self.random_seed = random_seed
        self.show_eachalgo_distribution = show_eachalgo_distribution
        self.client = None
        
    def connect(self, private_key: Optional[str] = None):
        """
        Connect to Polymarket using the provided private key or from environment.
        
        Args:
            private_key: Wallet private key (optional, will load from .env if not provided)
        """
        try:
            self.client = PolymarketClient(private_key=private_key)
            logger.info(f"Connected to Polymarket with wallet: {self.client.get_wallet_address()}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Polymarket: {e}")
            return False
    
    def find_best_opportunity(self, comparison_df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """
        Find the best buy opportunity based on statistical analysis.
        
        Args:
            comparison_df: Pre-generated comparison DataFrame (optional, will generate if not provided)
        
        Returns:
            Dict containing opportunity details or None if no opportunity found
        """
        if not self.client:
            logger.error("Not connected to Polymarket. Call connect() first.")
            return None
            
        try:
            # Use provided DataFrame or generate a new one
            if comparison_df is not None:
                df = comparison_df
            else:
                # Generate comparison table with the specified threshold
                df = generate_comparison_table(
                    refresh=True,
                    use_prophet=True,
                    threshold=self.threshold,
                    algorithm=self.algorithm,
                    random_seed=self.random_seed,
                    show_eachalgo_distribution=self.show_eachalgo_distribution
                )
            
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
            selected_probability = None
            selection_method_used = None
            
            # Use weighted selection if enabled and there are multiple positive opportunities
            if self.use_weighted_selection and len(positive_opps) > 1:
                # Use separate random generator for weighted choice to avoid interference from prediction algorithms
                # Create a new random generator instance with current time as seed for true randomness
                selection_rng = np.random.RandomState(int(time.time() * 1000000) % 2**32)
                
                # Calculate weights based on opportunity values
                weights = positive_opps[buy_only_col].values
                # Normalize weights to probabilities
                probs = weights / weights.sum()
                
                # Select a row using weighted probabilities with separate random generator
                selected_idx = selection_rng.choice(positive_opps.index, p=probs)
                best_row = positive_opps.loc[selected_idx]
                selected_probability = probs[positive_opps.index.get_loc(selected_idx)]
                selection_method_used = 'weighted'
                
                logger.info(f"Using weighted selection from {len(positive_opps)} opportunities")
                logger.info(f"Selected opportunity: {best_row['Range']} with {best_row[buy_only_col]}% edge " +
                           f"(prediction: {best_row['Pred (%)']}%, selection probability: {selected_probability:.2f})")
            else:
                # Find the row with the highest buy-only opportunity (original behavior)
                best_idx = positive_opps[buy_only_col].idxmax()
                best_row = positive_opps.loc[best_idx]
                selection_method_used = 'best'
                
                logger.info(f"Selected highest opportunity: {best_row['Range']} with {best_row[buy_only_col]}% edge " +
                           f"(prediction: {best_row['Pred (%)']}%)")
            
            # Extract information about the opportunity
            opportunity = {
                'range': best_row['Range'],
                'token_id': best_row['Token ID'],
                'prediction': best_row['Pred (%)'],
                'market': best_row['Mkt (%)'],
                'ask': best_row['Ask (%)'],
                'opportunity': best_row[buy_only_col],
                'difference': best_row['Diff (%)'],
                'threshold': self.threshold,  # Add threshold for reference
                'min_prediction': self.min_prediction,  # Add min_prediction for reference
                'selection_method': selection_method_used,
                'total_opportunities': len(positive_opps)
            }
            
            # Add probability if weighted selection was used
            if selected_probability is not None:
                opportunity['probability'] = selected_probability
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error finding opportunities: {e}")
            return None
    
    def place_order(self, opportunity: Dict[str, Any]) -> bool:
        """
        Place a market buy order for the given opportunity.
        
        Args:
            opportunity: Dict with opportunity details
            
        Returns:
            bool: True if order placed successfully, False otherwise
        """
        if not self.client:
            logger.error("Not connected to Polymarket. Call connect() first.")
            return False
            
        if not opportunity or 'token_id' not in opportunity:
            logger.error("Invalid opportunity provided.")
            return False
            
        try:
            # Create market buy order
            market_buy = MarketBuyOrder(self.client)
            
            # Execute the order
            token_id = opportunity['token_id']
            
            logger.info(f"Placing market buy order for {opportunity['range']} (token ID: {token_id})")
            logger.info(f"Order amount: {self.order_amount} USDC at market price (~{opportunity['ask']}%)")
            
            response = market_buy.execute_order(token_id, self.order_amount)
            logger.info(f"Order placed successfully: {response}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return False
    
    def auto_bid(self, private_key: Optional[str] = None) -> bool:
        """
        Complete automated bidding process: connect, find opportunities, and place order.
        
        Args:
            private_key: Wallet private key (optional, will load from .env if not provided)
            
        Returns:
            bool: True if bid placed successfully, False otherwise
        """
        # Connect to Polymarket
        if not self.connect(private_key):
            return False
            
        # Find best opportunity
        opportunity = self.find_best_opportunity()
        if not opportunity:
            logger.info("No suitable opportunities found for bidding.")
            return False
            
        # Place the order
        success = self.place_order(opportunity)
        return success 