"""
PositionSeller implementation for Polymarket.
Analyzes your current positions and the comparison table to identify which positions to sell.
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple

from src.bidding_decision.stats.comparison import generate_comparison_table
from src.polymarket.my_positions.position_tracker import PolymarketPositionTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PositionSeller:
    """
    Position analyzer that identifies which positions should be sold
    based on statistical opportunities.
    """
    
    def __init__(self, threshold: float = 0.0):
        """
        Initialize the PositionSeller.
        
        Args:
            threshold: Minimum opportunity percentage (%)
        """
        self.threshold = threshold
        self.position_tracker = PolymarketPositionTracker()
        
    def get_all_positions_with_stats(self) -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
        """
        Get all current positions with their statistical information from the comparison table.
        
        Returns:
            Tuple containing:
            - List of position dictionaries with statistical information
            - The full comparison DataFrame for reference
        """
        # Get current positions
        positions = self.position_tracker.get_simple_positions()
        
        if not positions:
            logger.info("No positions found in your account.")
            return [], pd.DataFrame()
            
        # Generate comparison table with the specified threshold
        df = generate_comparison_table(
            refresh=True,
            use_prophet=True,
            threshold=self.threshold
        )
        
        if df.empty:
            logger.info("Failed to generate comparison table.")
            return [], df
            
        # Find the column name for buy-only opportunities
        buy_only_col = [col for col in df.columns if col.startswith('Buy-Only')][0]
        sell_only_col = [col for col in df.columns if col.startswith('Sell-Only')][0]
        
        # Get only rows that are not EXPECTED VALUE
        data_rows = df[df['Range'] != 'EXPECTED VALUE'].copy()
        
        if data_rows.empty:
            logger.info("No specific range opportunities found in comparison table.")
            return [], df
        
        # Collect all positions with their stats
        all_positions = []
        
        for _, row in data_rows.iterrows():
            range_name = row['Range']
            buy_only_value = row[buy_only_col]
            sell_only_value = row[sell_only_col]
            token_id = row['Token ID']
            
            # Check for all range_name entries in position names
            for market_id, outcomes in positions.items():
                market_name = self.position_tracker.get_market_name(market_id)
                
                # Check if the market name contains the range
                if range_name in market_name:
                    for outcome, quantity in outcomes.items():
                        # Add position to the list regardless of opportunity value
                        position_info = {
                            'market_id': market_id,
                            'market_name': market_name,
                            'range': range_name,
                            'outcome': outcome,
                            'quantity': quantity,
                            'token_id': token_id,
                            'market_price': row['Mkt (%)'],
                            'prediction': row['Pred (%)'],
                            'difference': row['Diff (%)'],
                            'bid_price': row['Bid (%)'],
                            'ask_price': row['Ask (%)'],
                            'spread': row['Spread (%)'],
                            'buy_only_value': buy_only_value,
                            'sell_only_value': sell_only_value,
                            'should_sell': buy_only_value == 0 and quantity > 0
                        }
                        all_positions.append(position_info)
        
        return all_positions, df
    
    def get_positions_to_sell(self) -> List[Dict[str, Any]]:
        """
        Identify positions that should be sold based on comparison table data.
        Positions are recommended for selling when they have Buy-Only = 0.0, meaning
        they have no buy opportunity and should likely be sold.
        
        Returns:
            List of dictionaries with details about positions to sell
        """
        all_positions, _ = self.get_all_positions_with_stats()
        
        # Filter for positions that should be sold
        positions_to_sell = [pos for pos in all_positions if pos['should_sell']]
        
        return positions_to_sell
    
    def print_all_positions(self, all_positions: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Print information about all current positions with their statistical data.
        
        Args:
            all_positions: List of all positions with stats. If None, will be fetched.
        """
        if all_positions is None:
            all_positions, _ = self.get_all_positions_with_stats()
        
        if not all_positions:
            print("\nNo positions found in your account.")
            return
        
        print("\nALL YOUR CURRENT POSITIONS:")
        print("============================")
        
        # Sort positions by should_sell (true first), then by range name
        sorted_positions = sorted(
            all_positions, 
            key=lambda pos: (-int(pos['should_sell']), pos['range'])
        )
        
        for position in sorted_positions:
            # Highlight positions that should be sold
            highlight = " (RECOMMENDED TO SELL)" if position['should_sell'] else ""
            print(f"\n{position['market_name']} ({position['range']}){highlight}:")
            print(f"  Outcome: {position['outcome']}")
            print(f"  Quantity: {position['quantity']:.6f} shares")
            print(f"  Token ID: {position['token_id']}")
            print(f"  Current Price: Bid {position['bid_price']:.2f}% / Ask {position['ask_price']:.2f}% (Spread: {position['spread']:.2f}%)")
            print(f"  Your Model's Prediction: {position['prediction']:.2f}%")
            print(f"  Difference: {position['difference']:.2f}%")
            print(f"  Buy-Only Opportunity: {position['buy_only_value']:.2f}%")
            print(f"  Sell-Only Opportunity: {position['sell_only_value']:.2f}%")
        
        # Print a summary of positions to sell
        positions_to_sell = [pos for pos in sorted_positions if pos['should_sell']]
        if positions_to_sell:
            print("\nSUMMARY: You have", len(positions_to_sell), "positions recommended for selling.")
        else:
            print("\nSUMMARY: None of your positions are currently recommended for selling.")
    
    def print_sell_recommendations(self, positions_to_sell: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Print recommendations for positions to sell in a readable format.
        
        Args:
            positions_to_sell: List of positions to sell. If None, will be fetched.
        """
        if positions_to_sell is None:
            positions_to_sell = self.get_positions_to_sell()
        
        if not positions_to_sell:
            print("\nNo positions recommended for selling.")
            return
        
        print("\nPOSITIONS RECOMMENDED FOR SELLING:")
        print("==================================")
        
        for position in positions_to_sell:
            print(f"\n{position['market_name']} ({position['range']}):")
            print(f"  Outcome: {position['outcome']}")
            print(f"  Quantity: {position['quantity']:.6f} shares")
            print(f"  Token ID: {position['token_id']}")
            print(f"  Current Bid Price: {position['bid_price']:.2f}%")
            print(f"  Your Model's Prediction: {position['prediction']:.2f}%")
            print(f"  Difference: {position['difference']:.2f}%")
            
        print("\nNote: These positions are recommended for selling because they")
        print("have zero buy opportunity in the comparison table, which suggests")
        print("they are overvalued compared to your model's predictions.")

def main():
    """Command-line entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Identify which positions should be sold based on comparison data')
    parser.add_argument('--threshold', type=float, default=0.0, 
                      help='Minimum opportunity percentage (default: 0.0)')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    parser.add_argument('--sell-only', action='store_true',
                      help='Show only positions to sell, not all positions')
    
    args = parser.parse_args()
    
    # Set logging level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)
    
    # Create the position seller
    seller = PositionSeller(threshold=args.threshold)
    
    if args.sell_only:
        # Get and print sell recommendations only
        positions_to_sell = seller.get_positions_to_sell()
        seller.print_sell_recommendations(positions_to_sell)
    else:
        # Get and print all positions
        all_positions, _ = seller.get_all_positions_with_stats()
        seller.print_all_positions(all_positions)
    
    # Return the number of positions found
    positions_to_sell = seller.get_positions_to_sell()
    return len(positions_to_sell)

if __name__ == "__main__":
    main() 