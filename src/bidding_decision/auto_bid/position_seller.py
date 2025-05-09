"""
PositionSeller implementation for Polymarket.
Analyzes your current positions and the comparison table to identify which positions to sell.
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple

from src.bidding_decision.stats.comparison import generate_comparison_table
from src.polymarket.my_positions.position_tracker import PolymarketPositionTracker
from src.polymarket.bidding.sell.market.run import run_market_sell

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
    
    def __init__(self, threshold: float = 0.0, sell_below: float = 0.0):
        """
        Initialize the PositionSeller.
        
        Args:
            threshold: Minimum opportunity percentage (%)
            sell_below: Sell positions with prediction below this percentage (%)
        """
        self.threshold = threshold
        self.sell_below = sell_below
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
            prediction = row['Pred (%)']
            
            # Check for all range_name entries in position names
            for market_id, outcomes in positions.items():
                market_name = self.position_tracker.get_market_name(market_id)
                
                # Check if the market name contains the range
                if range_name in market_name:
                    for outcome, quantity in outcomes.items():
                        # Determine if the position should be sold based on criteria:
                        # 1. Has a positive sell opportunity (after threshold)
                        # 2. OR model prediction is below sell_below threshold
                        should_sell = (sell_only_value > 0 and quantity > 0) or \
                                     (self.sell_below > 0 and prediction < self.sell_below and quantity > 0)
                        
                        # Add position to the list regardless of opportunity value
                        position_info = {
                            'market_id': market_id,
                            'market_name': market_name,
                            'range': range_name,
                            'outcome': outcome,
                            'quantity': quantity,
                            'token_id': token_id,
                            'market_price': row['Mkt (%)'],
                            'prediction': prediction,
                            'difference': row['Diff (%)'],
                            'bid_price': row['Bid (%)'],
                            'ask_price': row['Ask (%)'],
                            'spread': row['Spread (%)'],
                            'buy_only_value': buy_only_value,
                            'sell_only_value': sell_only_value,
                            'should_sell': should_sell,
                            'sell_reason': 'Positive sell opportunity' if sell_only_value > 0 else 
                                        ('Low prediction below threshold' if prediction < self.sell_below else None)
                        }
                        all_positions.append(position_info)
        
        return all_positions, df
    
    def get_positions_to_sell(self) -> List[Dict[str, Any]]:
        """
        Identify positions that should be sold based on comparison table data.
        Positions are recommended for selling when they have:
        1. A positive sell opportunity (Buy-Only = 0.0, indicating they have no buy opportunity), or
        2. A model prediction below the sell_below threshold
        
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
        
        print(f"\nALL YOUR CURRENT POSITIONS (THRESHOLD: {self.threshold}%):")
        if self.sell_below > 0:
            print(f"SELL BELOW: {self.sell_below}%")
        print("============================")
        
        # Sort positions by should_sell (true first), then by range name
        sorted_positions = sorted(
            all_positions, 
            key=lambda pos: (-int(pos['should_sell']), pos['range'])
        )
        
        for position in sorted_positions:
            # Highlight positions that should be sold
            highlight = ""
            if position['should_sell']:
                highlight = f" (RECOMMENDED TO SELL - {position['sell_reason']})"
                
            print(f"\n{position['market_name']} ({position['range']}){highlight}:")
            print(f"  Outcome: {position['outcome']}")
            print(f"  Quantity: {position['quantity']:.6f} shares")
            print(f"  Token ID: {position['token_id']}")
            print(f"  Current Price: Bid {position['bid_price']:.2f}% / Ask {position['ask_price']:.2f}% (Spread: {position['spread']:.2f}%)")
            print(f"  Your Model's Prediction: {position['prediction']:.2f}%")
            print(f"  Difference: {position['difference']:.2f}%")
            print(f"  Buy-Only Opportunity: {position['buy_only_value']:.2f}% (after threshold)")
            print(f"  Sell-Only Opportunity: {position['sell_only_value']:.2f}% (after threshold)")
        
        # Print a summary of positions to sell
        positions_to_sell = [pos for pos in sorted_positions if pos['should_sell']]
        if positions_to_sell:
            print(f"\nSUMMARY: You have {len(positions_to_sell)} positions recommended for selling.")
            # Count by reason
            by_opportunity = sum(1 for pos in positions_to_sell if pos['sell_reason'] == 'Positive sell opportunity')
            by_low_pred = sum(1 for pos in positions_to_sell if pos['sell_reason'] == 'Low prediction below threshold')
            if by_opportunity > 0:
                print(f"  - {by_opportunity} positions with positive sell opportunity above {self.threshold}% threshold")
            if by_low_pred > 0:
                print(f"  - {by_low_pred} positions with prediction below {self.sell_below}% threshold")
        else:
            print(f"\nSUMMARY: None of your positions are currently recommended for selling.")
    
    def print_sell_recommendations(self, positions_to_sell: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Print recommendations for positions to sell in a readable format.
        
        Args:
            positions_to_sell: List of positions to sell. If None, will be fetched.
        """
        if positions_to_sell is None:
            positions_to_sell = self.get_positions_to_sell()
        
        if not positions_to_sell:
            print(f"\nNo positions recommended for selling with threshold {self.threshold}%")
            if self.sell_below > 0:
                print(f"or prediction below {self.sell_below}%.")
            return
        
        print(f"\nPOSITIONS RECOMMENDED FOR SELLING:")
        if self.threshold > 0:
            print(f"Threshold for sell opportunity: {self.threshold}%")
        if self.sell_below > 0:
            print(f"Threshold for low prediction: {self.sell_below}%")
        print("==================================")
        
        # Sort by reason
        positions_to_sell = sorted(positions_to_sell, key=lambda pos: pos['sell_reason'])
        
        for position in positions_to_sell:
            print(f"\n{position['market_name']} ({position['range']}):")
            print(f"  Outcome: {position['outcome']}")
            print(f"  Quantity: {position['quantity']:.6f} shares")
            print(f"  Token ID: {position['token_id']}")
            print(f"  Current Bid Price: {position['bid_price']:.2f}%")
            print(f"  Your Model's Prediction: {position['prediction']:.2f}%")
            print(f"  Difference: {position['difference']:.2f}%")
            
            # Print reason-specific details
            if position['sell_reason'] == 'Positive sell opportunity':
                print(f"  Sell Opportunity: {position['sell_only_value']:.2f}% (after applying {self.threshold}% threshold)")
                print(f"  Reason: Position is overvalued compared to your model's prediction")
            elif position['sell_reason'] == 'Low prediction below threshold':
                print(f"  Reason: Model prediction ({position['prediction']:.2f}%) is below the {self.sell_below}% threshold")
            
        # Print summary by reason
        by_opportunity = sum(1 for pos in positions_to_sell if pos['sell_reason'] == 'Positive sell opportunity')
        by_low_pred = sum(1 for pos in positions_to_sell if pos['sell_reason'] == 'Low prediction below threshold')
        
        print("\nSELL RECOMMENDATION SUMMARY:")
        if by_opportunity > 0:
            print(f"  - {by_opportunity} positions with positive sell opportunity (overvalued)")
        if by_low_pred > 0:
            print(f"  - {by_low_pred} positions with prediction below the {self.sell_below}% threshold")
        
    def execute_sell_orders(self, positions_to_sell: Optional[List[Dict[str, Any]]] = None, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Execute sell orders for all positions recommended for selling.
        
        Args:
            positions_to_sell: List of positions to sell. If None, will be fetched.
            dry_run: If True, show what would be done but don't execute actual sells
            
        Returns:
            List of results for executed sell orders
        """
        if positions_to_sell is None:
            positions_to_sell = self.get_positions_to_sell()
            
        if not positions_to_sell:
            print(f"\nNo positions to sell.")
            return []
        
        # Filter out positions with quantities less than 0.01
        valid_positions = []
        skipped_positions = []
        
        for position in positions_to_sell:
            if position['quantity'] < 0.01:
                skipped_positions.append(position)
            else:
                valid_positions.append(position)
        
        if skipped_positions:
            print(f"\nSkipping {len(skipped_positions)} positions with quantity less than 0.01 (Polymarket minimum):")
            for position in skipped_positions:
                print(f"  - {position['range']}: {position['quantity']:.6f} shares (below minimum)")
        
        if not valid_positions:
            print("\nNo valid positions to sell after filtering for minimum quantity (0.01).")
            return []
            
        print(f"\nExecuting sell orders for {len(valid_positions)} positions...")
        results = []
        
        for position in valid_positions:
            token_id = position['token_id']
            quantity = position['quantity']
            
            # Round the quantity to 6 decimal places to avoid precision issues
            quantity = round(quantity, 6)
            
            print(f"\nSelling {quantity:.6f} shares of {position['range']} (Token ID: {token_id})")
            print(f"Expected sale price: {position['bid_price']:.2f}%")
            print(f"Reason: {position['sell_reason']}")
            
            if position['sell_reason'] == 'Positive sell opportunity':
                print(f"Sell opportunity: {position['sell_only_value']:.2f}% (after applying {self.threshold}% threshold)")
            elif position['sell_reason'] == 'Low prediction below threshold':
                print(f"Model prediction ({position['prediction']:.2f}%) is below the {self.sell_below}% threshold")
            
            if dry_run:
                print("DRY RUN - No actual sell order executed")
                results.append({
                    'position': position,
                    'status': 'dry_run',
                    'message': 'Skipped execution in dry run mode'
                })
            else:
                try:
                    # Execute the market sell order using the imported run_market_sell function
                    response = run_market_sell(token_id, quantity)
                    print("Sell order executed successfully!")
                    print(f"Response: {response}")
                    
                    results.append({
                        'position': position,
                        'status': 'success',
                        'response': response
                    })
                except Exception as e:
                    error_message = str(e)
                    print(f"Error executing sell order: {error_message}")
                    
                    # Check for specific error about invalid amounts
                    if "invalid amounts" in error_message.lower() or "must be higher than 0" in error_message.lower():
                        print("Note: Polymarket requires a minimum order size (typically 0.01 shares).")
                        print("This error can occur if the actual order size is too small after fees or other adjustments.")
                    # Check for insufficient funds error
                    elif "insufficient" in error_message.lower() or "funds" in error_message.lower():
                        print("Note: You may have insufficient funds to complete this transaction.")
                        print("Make sure your wallet has enough USDC to cover the transaction fees.")
                    # Check for slippage errors
                    elif "slippage" in error_message.lower() or "price" in error_message.lower():
                        print("Note: The market price may have changed since the order was generated.")
                        print("Try again or adjust your threshold to account for market volatility.")
                    
                    results.append({
                        'position': position,
                        'status': 'error',
                        'error': error_message
                    })
        
        # Print summary
        successful_sells = sum(1 for r in results if r['status'] == 'success')
        if dry_run:
            print(f"\nDRY RUN SUMMARY: Would have sold {len(valid_positions)} positions")
        else:
            print(f"\nSELL ORDER SUMMARY: Successfully sold {successful_sells} out of {len(valid_positions)} positions")
            
        return results

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
    parser.add_argument('--auto-sell', action='store_true',
                      help='Automatically execute sell orders for recommended positions')
    parser.add_argument('--dry-run', action='store_true',
                      help='Show what would be sold but don\'t execute actual sell orders')
    parser.add_argument('--sell-below', type=float, default=0.0,
                      help='Sell positions with prediction below this percentage (default: 0.0)')
    
    args = parser.parse_args()
    
    # Set logging level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)
    
    # Create the position seller
    seller = PositionSeller(threshold=args.threshold, sell_below=args.sell_below)
    
    # Get positions to sell
    positions_to_sell = seller.get_positions_to_sell()
    
    if args.auto_sell:
        # Execute sell orders (with dry run mode if specified)
        seller.execute_sell_orders(positions_to_sell, dry_run=args.dry_run)
    elif args.sell_only:
        # Just show sell recommendations
        seller.print_sell_recommendations(positions_to_sell)
    else:
        # Show all positions with recommendations
        all_positions, _ = seller.get_all_positions_with_stats()
        seller.print_all_positions(all_positions)
        
        # Print a summary if there are positions to sell
        if positions_to_sell:
            print(f"\nFound {len(positions_to_sell)} positions to sell out of {len(all_positions)} total positions.")
    
    return len(positions_to_sell)

if __name__ == "__main__":
    main() 