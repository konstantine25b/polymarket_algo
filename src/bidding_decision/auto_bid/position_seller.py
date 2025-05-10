"""
PositionSeller implementation for Polymarket.
Analyzes your current positions and the comparison table to identify which positions to sell.
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
import json
import datetime

from src.bidding_decision.stats.comparison import generate_comparison_table
from src.polymarket.my_positions.position_tracker import PolymarketPositionTracker
from src.polymarket.bidding.sell.market.run import run_market_sell

# Configure logging
# Default to INFO level, but this can be overridden in the main function
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
    
    def __init__(self, threshold: float = 0.0, sell_below: float = 0.0, debug: bool = False):
        """
        Initialize the PositionSeller.
        
        Args:
            threshold: Minimum opportunity percentage (%)
            sell_below: Sell positions with prediction below this percentage (%)
            debug: Whether to show detailed debugging information
        """
        self.threshold = threshold
        self.sell_below = sell_below
        self.debug = debug
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
        
        # Debug: Print out the raw positions data
        logger.debug(f"Raw positions from position_tracker: {json.dumps(positions, indent=2)}")
        if self.debug:
            print(f"\nDEBUG - Raw positions from API:\n{json.dumps(positions, indent=2)}")
        
        # Filter positions with values <= 0.01 (Polymarket's minimum order size)
        non_zero_positions = {}
        filtered_out = {}
        for market_id, outcomes in positions.items():
            valid_outcomes = {outcome: qty for outcome, qty in outcomes.items() if qty >= 0.01}
            filtered_outcomes = {outcome: qty for outcome, qty in outcomes.items() if 0 < qty < 0.01}
            
            if valid_outcomes:
                non_zero_positions[market_id] = valid_outcomes
            
            if filtered_outcomes:
                filtered_out[market_id] = filtered_outcomes
        
        # Debug: Print positions after filtering out too small quantities
        logger.debug(f"Positions after filtering for minimum size (>= 0.01): {json.dumps(non_zero_positions, indent=2)}")
        if self.debug:
            print(f"\nDEBUG - Positions after filtering (qty >= 0.01):\n{json.dumps(non_zero_positions, indent=2)}")
            if filtered_out:
                print(f"\nDEBUG - Positions filtered out (0 < qty < 0.01):\n{json.dumps(filtered_out, indent=2)}")
        
        if not non_zero_positions:
            if self.debug:
                print("No positions with quantity >= 0.01 found in your account.")
            return [], pd.DataFrame()
            
        # Generate comparison table with the specified threshold
        logger.info(f"Generating comparison table with threshold: {self.threshold}%")
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
        
        # Debug: print the comparison table ranges
        comparison_ranges = data_rows['Range'].tolist()
        logger.debug(f"Ranges in comparison table: {comparison_ranges}")
        if self.debug:
            print(f"\nDEBUG - Ranges in comparison table: {comparison_ranges}")
        
        # Collect all positions with their stats
        all_positions = []
        
        for _, row in data_rows.iterrows():
            range_name = row['Range']
            buy_only_value = row[buy_only_col]
            sell_only_value = row[sell_only_col]
            token_id = row['Token ID']
            prediction = row['Pred (%)']
            
            # Debug info for this range
            logger.debug(f"Processing range: {range_name}, token_id: {token_id}, prediction: {prediction}%")
            
            # Check for all range_name entries in position names
            for market_id, outcomes in non_zero_positions.items():
                market_name = self.position_tracker.get_market_name(market_id)
                
                # Debug: Check if the market name contains the range
                if range_name in market_name:
                    logger.debug(f"Found match for range '{range_name}' in market '{market_name}' (ID: {market_id})")
                    if self.debug:
                        print(f"\nDEBUG - Found match: Range '{range_name}' in market '{market_name}'")
                    
                    for outcome, quantity in outcomes.items():
                        logger.debug(f"  Position: {outcome}, quantity: {quantity}")
                        if self.debug:
                            print(f"DEBUG - Position details: {outcome}, quantity: {quantity}")
                        
                        # Determine if the position should be sold based on criteria:
                        # 1. Has a positive sell opportunity (after threshold)
                        # 2. OR model prediction is below sell_below threshold
                        should_sell = (sell_only_value > 0 and quantity > 0) or \
                                     (self.sell_below > 0 and prediction < self.sell_below and quantity > 0)
                        
                        sell_reason = None
                        if sell_only_value > 0 and quantity > 0:
                            sell_reason = 'Positive sell opportunity'
                        elif self.sell_below > 0 and prediction < self.sell_below and quantity > 0:
                            sell_reason = 'Low prediction below threshold'
                            
                        # Debug the selling decision
                        logger.debug(f"  Should sell: {should_sell}, Reason: {sell_reason}")
                        logger.debug(f"  Sell criteria: sell_only_value={sell_only_value}, prediction={prediction}, sell_below={self.sell_below}")
                        
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
                            'sell_reason': sell_reason
                        }
                        all_positions.append(position_info)
                        
                        # Debug the added position
                        logger.debug(f"  Added position to list: {outcome}, quantity: {quantity}, should_sell: {should_sell}")
                else:
                    logger.debug(f"No match for range '{range_name}' in market '{market_name}'")
        
        # Debug summary
        logger.debug(f"Total positions processed: {len(all_positions)}")
        sell_positions = [p for p in all_positions if p['should_sell']]
        logger.info(f"Positions marked for selling: {len(sell_positions)}")
        
        if self.debug:
            print(f"\nDEBUG - Summary: Found {len(all_positions)} positions, {len(sell_positions)} recommended for selling")
            for pos in all_positions:
                print(f"DEBUG - Position: {pos['range']} ({pos['outcome']}), qty: {pos['quantity']}, should_sell: {pos['should_sell']}")
        
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
        
        # Debug: List positions that will be sold
        logger.info(f"Positions marked for selling: {len(positions_to_sell)}")
        if positions_to_sell:
            for pos in positions_to_sell:
                logger.debug(f"Will sell: {pos['range']} ({pos['outcome']}), qty: {pos['quantity']}, reason: {pos['sell_reason']}")
        
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
            if self.debug:
                print(f"  Last Updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
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
                    # Check for not enough balance / allowance error
                    elif "not enough balance" in error_message.lower() or "allowance" in error_message.lower():
                        print("Note: You may have sold this position elsewhere or the position may have been closed.")
                        print("This error indicates that your available position balance has changed since it was last checked.")
                    
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
    parser.add_argument('--debug', action='store_true',
                      help='Show detailed debugging information')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
        logging.getLogger().setLevel(logging.INFO)
    
    # Create the position seller with debug flag
    seller = PositionSeller(threshold=args.threshold, sell_below=args.sell_below, debug=args.debug)
    
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