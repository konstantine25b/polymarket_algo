"""
AutoBidder implementation for Polymarket.
Analyzes statistical opportunities and places orders based on the highest buy-only opportunity.
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any

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
    
    def __init__(self, threshold: float = 0.0, order_amount: float = 1.0):
        """
        Initialize the AutoBidder.
        
        Args:
            threshold: Minimum opportunity percentage required to place an order (%)
            order_amount: Amount to bid in USDC
        """
        self.threshold = threshold
        self.order_amount = order_amount
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
    
    def find_best_opportunity(self) -> Optional[Dict[str, Any]]:
        """
        Find the best buy opportunity based on statistical analysis.
        
        Returns:
            Dict containing opportunity details or None if no opportunity found
        """
        if not self.client:
            logger.error("Not connected to Polymarket. Call connect() first.")
            return None
            
        try:
            # Generate comparison table with the specified threshold
            df = generate_comparison_table(
                refresh=True,
                use_prophet=True,
                threshold=self.threshold
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
            
            # Check if there are any meaningful buy opportunities above the threshold
            if data_rows[buy_only_col].max() <= 0:
                logger.info(f"No buy opportunities found above threshold {self.threshold}%.")
                return None
                
            # Find the row with the highest buy-only opportunity
            best_idx = data_rows[buy_only_col].idxmax()
            best_row = data_rows.loc[best_idx]
            
            # Only proceed if there's a meaningful buy opportunity above the threshold
            if best_row[buy_only_col] <= 0:
                logger.info(f"No buy opportunities found above threshold {self.threshold}%.")
                return None
                
            # Extract information about the opportunity
            opportunity = {
                'range': best_row['Range'],
                'token_id': best_row['Token ID'],
                'prediction': best_row['Pred (%)'],
                'market': best_row['Mkt (%)'],
                'ask': best_row['Ask (%)'],
                'opportunity': best_row[buy_only_col],
                'difference': best_row['Diff (%)'],
                'threshold': self.threshold  # Add threshold for reference
            }
            
            logger.info(f"Found best opportunity: {opportunity['range']} with {opportunity['opportunity']}% edge (threshold: {self.threshold}%)")
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