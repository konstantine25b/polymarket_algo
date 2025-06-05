"""
Simulation PositionSeller implementation for Polymarket.
Analyzes simulated positions and the comparison table to identify which positions to sell.
"""

import logging
import pandas as pd
import json
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from src.bidding_decision.stats.comparison import generate_comparison_table
from src.simulation.initialization.run_initializer import RunInitializer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimulationSeller:
    """
    Position analyzer that identifies which simulated positions should be sold
    based on statistical opportunities.
    """
    
    def __init__(self, threshold: float = 0.0, sell_below: float = 0.0, debug: bool = False, active_market_only: bool = False):
        """
        Initialize the SimulationSeller.
        
        Args:
            threshold: Minimum opportunity percentage (%)
            sell_below: Sell positions with prediction below this percentage (%)
            debug: Whether to show detailed debugging information
            active_market_only: Only analyze positions for the active market
        """
        self.threshold = threshold
        self.sell_below = sell_below
        self.debug = debug
        self.active_market_only = active_market_only
        self.run_initializer = RunInitializer()
        
    def get_simulation_positions(self, run_name: str) -> Dict[str, Any]:
        """
        Get current positions from the simulation run.
        
        Args:
            run_name: Name of the simulation run
            
        Returns:
            Dict containing positions data or empty dict if failed
        """
        try:
            # Load simulation data
            json_file_path = self.run_initializer.base_runs_dir / run_name / "simulation_data.json"
            
            if not json_file_path.exists():
                logger.error(f"Simulation run '{run_name}' not found")
                return {}
                
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            positions = data.get('positions', [])
            
            # Convert to format similar to real position tracker
            # Group by market_id and sum quantities
            position_dict = {}
            for pos in positions:
                market_id = pos['market_id']
                quantity = pos['num_shares']  # Fixed: use 'num_shares' instead of 'quantity'
                
                if quantity > 0.01:  # Filter minimum quantities like real system
                    if market_id not in position_dict:
                        position_dict[market_id] = quantity
                    else:
                        position_dict[market_id] += quantity
            
            return position_dict
            
        except Exception as e:
            logger.error(f"Error getting simulation positions: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return {}
    
    def get_market_name_from_simulation(self, run_name: str, market_id: str) -> str:
        """
        Get market name for a given market ID from simulation data.
        
        Args:
            run_name: Name of the simulation run
            market_id: Market ID to look up
            
        Returns:
            Market name or market_id if not found
        """
        try:
            json_file_path = self.run_initializer.base_runs_dir / run_name / "simulation_data.json"
            
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            markets = data.get('markets', [])
            for market in markets:
                if market['market_id'] == market_id:
                    return market['market_name']
            
            return market_id  # Fallback to ID if name not found
            
        except Exception as e:
            logger.error(f"Error getting market name: {e}")
            return market_id
    
    def get_all_positions_with_stats(self, run_name: str, update_markets: bool = True) -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
        """
        Get all current positions with their statistical information from the comparison table.
        
        Args:
            run_name: Name of the simulation run
            update_markets: Whether to update market prices before analysis
            
        Returns:
            Tuple containing:
            - List of position dictionaries with statistical information
            - The full comparison DataFrame for reference
        """
        # Get current positions from simulation
        positions = self.get_simulation_positions(run_name)
        
        if self.debug:
            print(f"\nDEBUG - Simulation positions from '{run_name}':")
            for market_id, quantity in positions.items():
                market_name = self.get_market_name_from_simulation(run_name, market_id)
                print(f"  {market_name} ({market_id}): {quantity:.4f} shares")
        
        if not positions:
            if self.debug:
                print("No positions with quantity >= 0.01 found in simulation.")
            return [], pd.DataFrame()
            
        # Generate comparison table with the specified threshold
        logger.info(f"Generating comparison table with threshold: {self.threshold}%")
        df = generate_comparison_table(
            refresh=update_markets,
            use_prophet=True,
            threshold=self.threshold,
            silent=True  # Silent to avoid duplicate output
        )
        
        if df.empty:
            logger.info("Failed to generate comparison table.")
            return [], df
            
        # Find the column names for buy-only and sell-only opportunities
        buy_only_col = [col for col in df.columns if col.startswith('Buy-Only')][0]
        sell_only_col = [col for col in df.columns if col.startswith('Sell-Only')][0]
        
        # Get only rows that are not EXPECTED VALUE
        data_rows = df[df['Range'] != 'EXPECTED VALUE'].copy()
        
        if data_rows.empty:
            logger.info("No specific range opportunities found in comparison table.")
            return [], df
        
        # Debug: print the comparison table ranges
        comparison_ranges = data_rows['Range'].tolist()
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
            if self.debug:
                print(f"DEBUG - Processing range: {range_name}, token_id: {token_id}, prediction: {prediction}%")
            
            # Check for positions matching this token_id
            for market_id, quantity in positions.items():
                if market_id == token_id:  # Direct match on token ID
                    market_name = self.get_market_name_from_simulation(run_name, market_id)
                    
                    if self.debug:
                        print(f"DEBUG - Found position match: {market_name} (ID: {market_id}), quantity: {quantity}")
                    
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
                    if self.debug:
                        print(f"  Should sell: {should_sell}, Reason: {sell_reason}")
                        print(f"  Sell criteria: sell_only_value={sell_only_value}, prediction={prediction}, sell_below={self.sell_below}")
                    
                    # Add position to the list
                    position_info = {
                        'market_id': market_id,
                        'market_name': market_name,
                        'range': range_name,
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
                        'sell_reason': sell_reason,
                        'outcome': 'Yes'  # For compatibility with real system display
                    }
                    all_positions.append(position_info)
                    
                    if self.debug:
                        print(f"  Added position to list: quantity: {quantity}, should_sell: {should_sell}")
        
        # Debug summary
        sell_positions = [p for p in all_positions if p['should_sell']]
        logger.info(f"Positions marked for selling: {len(sell_positions)} out of {len(all_positions)} total")
        
        if self.debug:
            print(f"\nDEBUG - Summary: Found {len(all_positions)} positions, {len(sell_positions)} recommended for selling")
            for pos in all_positions:
                print(f"DEBUG - Position: {pos['range']}, qty: {pos['quantity']:.4f}, should_sell: {pos['should_sell']}")
        
        return all_positions, df
    
    def get_positions_to_sell(self, run_name: str, update_markets: bool = True) -> List[Dict[str, Any]]:
        """
        Identify positions that should be sold based on comparison table data.
        
        Args:
            run_name: Name of the simulation run
            update_markets: Whether to update market prices before analysis
            
        Returns:
            List of positions recommended for selling
        """
        all_positions, _ = self.get_all_positions_with_stats(run_name, update_markets)
        
        # Filter to only positions that should be sold
        positions_to_sell = [pos for pos in all_positions if pos['should_sell']]
        
        return positions_to_sell
    
    def print_all_positions(self, run_name: str, all_positions: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Print a detailed table of all current positions with their statistics.
        
        Args:
            run_name: Name of the simulation run
            all_positions: Optional list of positions (will fetch if None)
        """
        if all_positions is None:
            all_positions, _ = self.get_all_positions_with_stats(run_name)
        
        if not all_positions:
            print("\n📊 No positions found in simulation run.")
            return
            
        print(f"\n📊 All Positions in Simulation Run '{run_name}':")
        print("=" * 140)
        print(f"{'Range':<30} {'Outcome':<8} {'Qty':<10} {'Pred %':<8} {'Mkt %':<8} {'Bid %':<8} {'Buy Opp':<10} {'Sell Opp':<10} {'Should Sell':<12} {'Reason':<25}")
        print("-" * 140)
        
        for pos in all_positions:
            should_sell_text = "✅ YES" if pos['should_sell'] else "❌ NO"
            reason = pos['sell_reason'] or "None"
            
            print(f"{pos['range']:<30} {pos['outcome']:<8} {pos['quantity']:<10.4f} {pos['prediction']:<8.1f} {pos['market_price']:<8.1f} "
                  f"{pos['bid_price']:<8.1f} {pos['buy_only_value']:<10.1f} {pos['sell_only_value']:<10.1f} "
                  f"{should_sell_text:<12} {reason:<25}")
        
        print("-" * 140)
        sell_count = sum(1 for pos in all_positions if pos['should_sell'])
        total_value = sum(pos['quantity'] * pos['bid_price'] / 100 for pos in all_positions)
        print(f"Total Positions: {len(all_positions)} | Recommended to Sell: {sell_count} | Estimated Value: ${total_value:.2f}")
    
    def print_sell_recommendations(self, run_name: str, positions_to_sell: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Print a detailed table of positions recommended for selling.
        
        Args:
            run_name: Name of the simulation run
            positions_to_sell: Optional list of positions to sell (will fetch if None)
        """
        if positions_to_sell is None:
            positions_to_sell = self.get_positions_to_sell(run_name)
        
        if not positions_to_sell:
            print(f"\n🎯 No positions recommended for selling in simulation run '{run_name}'.")
            return
            
        print(f"\n🎯 Sell Recommendations for Simulation Run '{run_name}':")
        print("=" * 140)
        print(f"{'Range':<30} {'Outcome':<8} {'Qty':<10} {'Pred %':<8} {'Bid %':<8} {'Sell Opp':<10} {'Est. Value':<12} {'Reason':<25}")
        print("-" * 140)
        
        total_value = 0
        for pos in positions_to_sell:
            estimated_value = pos['quantity'] * pos['bid_price'] / 100
            total_value += estimated_value
            
            print(f"{pos['range']:<30} {pos['outcome']:<8} {pos['quantity']:<10.4f} {pos['prediction']:<8.1f} {pos['bid_price']:<8.1f} "
                  f"{pos['sell_only_value']:<10.1f} ${estimated_value:<11.2f} {pos['sell_reason']:<25}")
        
        print("-" * 140)
        print(f"Total Positions to Sell: {len(positions_to_sell)} | Estimated Total Value: ${total_value:.2f}")
    
    def execute_sell_orders(self, run_name: str, positions_to_sell: Optional[List[Dict[str, Any]]] = None, 
                                    dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Execute simulated sell orders for the recommended positions.
        
        Args:
            run_name: Name of the simulation run
            positions_to_sell: Optional list of positions to sell (will fetch if None)
            dry_run: If True, only show what would happen without executing
            
        Returns:
            List of executed sell order details
        """
        if positions_to_sell is None:
            positions_to_sell = self.get_positions_to_sell(run_name)
        
        if not positions_to_sell:
            logger.info("No positions to sell.")
            return []
        
        executed_orders = []
        
        for pos in positions_to_sell:
            try:
                market_id = pos['market_id']
                quantity = pos['quantity']
                bid_price = pos['bid_price'] / 100.0  # Convert percentage to decimal
                estimated_value = quantity * bid_price
                
                if dry_run:
                    print(f"🔍 DRY RUN - Would sell position:")
                    print(f"   Market: {pos['range']} (Token ID: {market_id})")
                    print(f"   Outcome: {pos['outcome']}")
                    print(f"   Quantity: {quantity:.4f} shares")
                    print(f"   Bid price: {pos['bid_price']:.1f}% (${bid_price:.4f} per share)")
                    print(f"   Estimated proceeds: ${estimated_value:.2f}")
                    print(f"   Reason: {pos['sell_reason']}")
                    print()
                    
                    executed_orders.append({
                        'market_id': market_id,
                        'range': pos['range'],
                        'quantity': quantity,
                        'price': bid_price,
                        'proceeds': estimated_value,
                        'reason': pos['sell_reason'],
                        'dry_run': True
                    })
                    continue
                
                logger.info(f"Executing simulated sell order for {pos['range']}")
                logger.info(f"Selling {quantity:.4f} shares at {pos['bid_price']:.1f}% (~${bid_price:.4f} per share)")
                logger.info(f"Estimated proceeds: ${estimated_value:.2f}")
                
                # Execute the simulated sell using RunInitializer
                success = self.run_initializer.sell_position(
                    run_name=run_name,
                    market_id=market_id,
                    num_shares=quantity
                )
                
                if success:
                    logger.info(f"✅ Simulated sell order executed successfully")
                    
                    executed_orders.append({
                        'market_id': market_id,
                        'range': pos['range'],
                        'quantity': quantity,
                        'price': bid_price,
                        'proceeds': estimated_value,
                        'reason': pos['sell_reason'],
                        'success': True
                    })
                else:
                    logger.error(f"❌ Failed to execute simulated sell order for {pos['range']}")
                    executed_orders.append({
                        'market_id': market_id,
                        'range': pos['range'],
                        'quantity': quantity,
                        'price': bid_price,
                        'proceeds': estimated_value,
                        'reason': pos['sell_reason'],
                        'success': False
                    })
                    
            except Exception as e:
                logger.error(f"Error executing sell order for {pos['range']}: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
        
        # Summary
        successful_orders = [order for order in executed_orders if order.get('success', False)]
        total_proceeds = sum(order['proceeds'] for order in successful_orders)
        
        if not dry_run:
            logger.info(f"🎉 Executed {len(successful_orders)} sell orders successfully")
            logger.info(f"💰 Total proceeds: ${total_proceeds:.2f}")
        else:
            logger.info(f"🔍 Dry run: Would execute {len(executed_orders)} sell orders")
            total_dry_proceeds = sum(order['proceeds'] for order in executed_orders)
            logger.info(f"💰 Estimated total proceeds: ${total_dry_proceeds:.2f}")
        
        return executed_orders
    
    def analyze_positions(self, run_name: str, update_markets: bool = True) -> bool:
        """
        Analyze current positions without executing any sells.
        
        Args:
            run_name: Name of the simulation run
            update_markets: Whether to update market prices before analysis
            
        Returns:
            bool: True if analysis completed successfully
        """
        try:
            logger.info(f"Analyzing positions for simulation run: {run_name}")
            
            # Update markets if requested
            if update_markets:
                self.run_initializer.update_markets_from_polymarket(run_name)
            
            # Get all positions with stats
            all_positions, df = self.get_all_positions_with_stats(run_name, update_markets=False)
            
            if not all_positions:
                logger.info("No positions found for analysis.")
                return True
            
            # Print summaries
            self.print_all_positions(run_name, all_positions)
            self.print_sell_recommendations(run_name, [pos for pos in all_positions if pos['should_sell']])
            
            return True
            
        except Exception as e:
            logger.error(f"Error analyzing positions: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False

    def print_stats_table(self, df):
        """
        Print the full stats comparison table - matches real auto_bid format.
        
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
        sell_only_col = [col for col in df.columns if col.startswith('Sell-Only')][0]
        threshold_value = float(sell_only_col.split('(')[1].split('%')[0])
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

    def execute_selling_strategy(self, run_name: str, update_markets: bool = True, show_stats: bool = True, 
                                auto_sell: bool = False, dry_run: bool = False) -> bool:
        """
        Execute the complete selling strategy matching real auto_bid behavior.
        
        Args:
            run_name: Name of the simulation run
            update_markets: Whether to update market prices before analysis
            show_stats: Whether to show the comparison table
            auto_sell: Whether to execute sell orders automatically
            dry_run: Whether to run in dry-run mode
            
        Returns:
            bool: True if successful
        """
        try:
            # Update markets from Polymarket first (like real auto_bid)
            if update_markets:
                logger.info("Updating market prices from Polymarket...")
                success = self.run_initializer.update_markets_from_polymarket(run_name)
                if not success:
                    logger.error("Failed to update market prices")
                    return False
            
            # Generate and display comparison table (like real auto_bid)
            if show_stats:
                logger.info(f"Generating comparison table with threshold: {self.threshold}%")
                comparison_df = generate_comparison_table(
                    refresh=False,  # Already updated above
                    use_prophet=True,
                    threshold=self.threshold,
                    silent=True  # Suppress built-in output
                )
                
                if not comparison_df.empty:
                    self.print_stats_table(comparison_df)
                else:
                    logger.warning("Failed to generate comparison table")
            
            # Get all positions with stats
            all_positions, _ = self.get_all_positions_with_stats(run_name, update_markets=False)
            
            # Apply active market filtering if requested
            if self.active_market_only:
                # This would require constants import - for now just log the intent
                logger.info("Active market filtering requested (feature needs constants implementation)")
                print("Note: Active market filtering not yet implemented in simulation")
            
            # Filter to positions that should be sold
            positions_to_sell = [pos for pos in all_positions if pos.get('should_sell', False)]
            
            if auto_sell:
                # Execute sell orders automatically
                if positions_to_sell:
                    self.execute_sell_orders(run_name, positions_to_sell, dry_run=dry_run)
                else:
                    print(f"\nNo positions recommended for selling with threshold {self.threshold:.1f}%")
                    if self.sell_below > 0:
                        print(f"or prediction below {self.sell_below}%.")
                    
                    # Show all positions even if none to sell
                    if all_positions:
                        print(f"\nAll positions in simulation run '{run_name}':")
                        for position in all_positions:
                            market_name = self.get_market_name_from_simulation(run_name, position['market_id'])
                            print(f"  {market_name} - {position['outcome']}: {position['quantity']:.6f} shares")
            else:
                # Just show recommendations
                if positions_to_sell:
                    self.print_sell_recommendations(run_name, positions_to_sell)
                else:
                    print(f"\nNo positions recommended for selling with threshold {self.threshold:.1f}%")
                    if self.sell_below > 0:
                        print(f"or prediction below {self.sell_below}%.")
                    
                    # Show all positions even if none to sell
                    if all_positions:
                        print(f"\nAll positions in simulation run '{run_name}':")
                        for position in all_positions:
                            market_name = self.get_market_name_from_simulation(run_name, position['market_id'])
                            print(f"  {market_name} - {position['outcome']}: {position['quantity']:.6f} shares")
            
            # Log summary
            num_positions = len(positions_to_sell)
            if num_positions > 0:
                logger.info(f"Positions marked for selling: {num_positions} out of {len(all_positions)} total")
            else:
                logger.info(f"Positions marked for selling: 0 out of {len(all_positions)} total")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in selling strategy: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False 