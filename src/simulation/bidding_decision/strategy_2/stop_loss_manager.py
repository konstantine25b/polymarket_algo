"""
Stop Loss Manager for Strategy 2 Simulation.
Implements stop loss functionality with configurable thresholds for both loss and gain management.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from src.simulation.initialization.run_initializer import RunInitializer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StopLossManager:
    """
    Manages stop loss functionality for simulation positions.
    
    Default thresholds:
    - Sell 50% at -40% loss (stop loss)
    - Sell 100% at -60% loss (full stop loss)
    - Sell 40% at +40% gain (profit taking)
    - Sell 40% at +80% gain (additional profit taking)
    """
    
    def __init__(self, 
                 loss_threshold_1: float = -40.0,
                 loss_sell_percentage_1: float = 50.0,
                 loss_threshold_2: float = -60.0,
                 loss_sell_percentage_2: float = 100.0,
                 gain_threshold_1: float = 40.0,
                 gain_sell_percentage_1: float = 40.0,
                 gain_threshold_2: float = 80.0,
                 gain_sell_percentage_2: float = 40.0,
                 debug: bool = False):
        """
        Initialize the StopLossManager with configurable thresholds.
        
        Args:
            loss_threshold_1: First loss threshold percentage (default: -40.0)
            loss_sell_percentage_1: Percentage to sell at first loss threshold (default: 50.0)
            loss_threshold_2: Second loss threshold percentage (default: -60.0)
            loss_sell_percentage_2: Percentage to sell at second loss threshold (default: 100.0)
            gain_threshold_1: First gain threshold percentage (default: 40.0)
            gain_sell_percentage_1: Percentage to sell at first gain threshold (default: 40.0)
            gain_threshold_2: Second gain threshold percentage (default: 80.0)
            gain_sell_percentage_2: Percentage to sell at second gain threshold (default: 40.0)
            debug: Whether to show detailed debugging information
        """
        self.loss_threshold_1 = loss_threshold_1
        self.loss_sell_percentage_1 = loss_sell_percentage_1
        self.loss_threshold_2 = loss_threshold_2
        self.loss_sell_percentage_2 = loss_sell_percentage_2
        self.gain_threshold_1 = gain_threshold_1
        self.gain_sell_percentage_1 = gain_sell_percentage_1
        self.gain_threshold_2 = gain_threshold_2
        self.gain_sell_percentage_2 = gain_sell_percentage_2
        self.debug = debug
        self.run_initializer = RunInitializer()
        
        if self.debug:
            print(f"Stop Loss Manager initialized with thresholds:")
            print(f"  Loss: {self.loss_threshold_1}% -> sell {self.loss_sell_percentage_1}%")
            print(f"  Loss: {self.loss_threshold_2}% -> sell {self.loss_sell_percentage_2}%")
            print(f"  Gain: {self.gain_threshold_1}% -> sell {self.gain_sell_percentage_1}%")
            print(f"  Gain: {self.gain_threshold_2}% -> sell {self.gain_sell_percentage_2}%")
    
    def get_positions_with_stop_loss_triggers(self, run_name: str) -> List[Dict[str, Any]]:
        """
        Get all positions that have triggered stop loss conditions.
        
        Args:
            run_name: Name of the simulation run
            
        Returns:
            List of positions with stop loss triggers
        """
        try:
            # Load simulation data
            json_file_path = self.run_initializer.base_runs_dir / run_name / "simulation_data.json"
            
            if not json_file_path.exists():
                logger.error(f"Simulation run '{run_name}' not found")
                return []
                
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            positions = data.get('positions', [])
            triggered_positions = []
            
            for position in positions:
                if position.get('position_status') != 'ACTIVE':
                    continue
                    
                win_loss_pct = position.get('win_loss_percentage', 0.0)
                num_shares = position.get('num_shares', 0.0)
                
                # Skip positions with minimal shares
                if num_shares <= 0.01:
                    continue
                
                # Check if any stop loss conditions are triggered
                stop_loss_action = self._determine_stop_loss_action(position)
                
                if stop_loss_action:
                    triggered_positions.append({
                        'position': position,
                        'action': stop_loss_action,
                        'current_win_loss': win_loss_pct
                    })
                    
                    if self.debug:
                        print(f"Stop loss triggered for {position['market_name']}: "
                              f"{win_loss_pct:.2f}% -> {stop_loss_action['reason']}")
            
            return triggered_positions
            
        except Exception as e:
            logger.error(f"Error getting positions with stop loss triggers: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return []
    
    def _determine_stop_loss_action(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Determine what stop loss action (if any) should be taken for a position.
        
        Args:
            position: Position dictionary with current market data
            
        Returns:
            Dict with stop loss action details, or None if no action needed
        """
        num_shares = position.get('num_shares', 0)
        win_loss_pct = position.get('win_loss_percentage', 0)
        stop_loss_history = position.get('stop_loss_history', [])
        
        # If no shares, no action needed
        if num_shares <= 0:
            return None
        
        # FIXED: Check if position was fully sold and then re-purchased
        # If so, we should allow new stop loss triggers regardless of old history
        was_fully_sold_then_rebought = self._was_position_fully_sold_then_rebought(position)
        
        # Check loss thresholds (more severe losses first)
        if win_loss_pct <= self.loss_threshold_2:
            # Check if we already sold at threshold 2 (only if not re-bought after full sell)
            if not was_fully_sold_then_rebought:
                threshold_2_sells = [h for h in stop_loss_history if h.get('threshold') == self.loss_threshold_2]
                if threshold_2_sells:
                    return None
            
            # Full position liquidation at severe loss
            sell_shares = num_shares * (self.loss_sell_percentage_2 / 100.0)
            return {
                'type': 'loss_stop',
                'threshold': self.loss_threshold_2,
                'sell_percentage': self.loss_sell_percentage_2,
                'sell_shares': sell_shares,
                'reason': f'Full stop loss at {self.loss_threshold_2}% loss'
            }
        
        elif win_loss_pct <= self.loss_threshold_1:
            # Check if we already sold at threshold 1 (only if not re-bought after full sell)
            if not was_fully_sold_then_rebought:
                threshold_1_sells = [h for h in stop_loss_history if h.get('threshold') == self.loss_threshold_1]
                if threshold_1_sells:
                    return None
            
            sell_shares = num_shares * (self.loss_sell_percentage_1 / 100.0)
            return {
                'type': 'loss_stop',
                'threshold': self.loss_threshold_1,
                'sell_percentage': self.loss_sell_percentage_1,
                'sell_shares': sell_shares,
                'reason': f'Partial stop loss at {self.loss_threshold_1}% loss'
            }
        
        # Check gain thresholds
        elif win_loss_pct >= self.gain_threshold_2:
            # Check if we already sold at threshold 2 (only if not re-bought after full sell)
            if not was_fully_sold_then_rebought:
                threshold_2_gains = [h for h in stop_loss_history if h.get('threshold') == self.gain_threshold_2]
                if threshold_2_gains:
                    return None
            
            sell_shares = num_shares * (self.gain_sell_percentage_2 / 100.0)
            return {
                'type': 'profit_taking',
                'threshold': self.gain_threshold_2,
                'sell_percentage': self.gain_sell_percentage_2,
                'sell_shares': sell_shares,
                'reason': f'Additional profit taking at {self.gain_threshold_2}% gain'
            }
        
        elif win_loss_pct >= self.gain_threshold_1:
            # Check if we already sold at threshold 1 (only if not re-bought after full sell)
            if not was_fully_sold_then_rebought:
                threshold_1_gains = [h for h in stop_loss_history if h.get('threshold') == self.gain_threshold_1]
                if threshold_1_gains:
                    return None
            
            sell_shares = num_shares * (self.gain_sell_percentage_1 / 100.0)
            return {
                'type': 'profit_taking',
                'threshold': self.gain_threshold_1,
                'sell_percentage': self.gain_sell_percentage_1,
                'sell_shares': sell_shares,
                'reason': f'Initial profit taking at {self.gain_threshold_1}% gain'
            }
        
        return None
    
    def _was_position_fully_sold_then_rebought(self, position: Dict[str, Any]) -> bool:
        """
        Check if a position was fully sold (100%) and then re-purchased.
        
        Args:
            position: Position dictionary
            
        Returns:
            True if position was fully sold then re-bought, False otherwise
        """
        stop_loss_history = position.get('stop_loss_history', [])
        transaction_history = position.get('transaction_history', [])
        
        # Find if there was ever a 100% sell in stop loss history
        full_sell_timestamp = None
        for action in stop_loss_history:
            if action.get('sell_percentage') == 100.0:
                full_sell_timestamp = action.get('timestamp')
                break
        
        # If no full sell, then it wasn't fully sold
        if not full_sell_timestamp:
            return False
        
        # Check if there are BUY transactions after the full sell timestamp
        for transaction in transaction_history:
            if (transaction.get('type') == 'BUY' and 
                transaction.get('timestamp', '') > full_sell_timestamp):
                return True
        
        return False
    
    def execute_stop_loss_orders(self, run_name: str, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Execute stop loss orders for all triggered positions.
        
        Args:
            run_name: Name of the simulation run
            dry_run: If True, only show what would be done without executing
            
        Returns:
            List of executed stop loss orders
        """
        triggered_positions = self.get_positions_with_stop_loss_triggers(run_name)
        executed_orders = []
        
        if not triggered_positions:
            if self.debug:
                print("No stop loss triggers found.")
            return []
        
        print(f"\n🛑 Stop Loss Analysis for run '{run_name}':")
        print("=" * 80)
        
        for trigger in triggered_positions:
            position = trigger['position']
            action = trigger['action']
            
            market_name = position['market_name']
            market_id = position['market_id']
            current_shares = position['num_shares']
            sell_shares = action['sell_shares']
            win_loss_pct = trigger['current_win_loss']
            
            print(f"Position: {market_name}")
            print(f"  Current P&L: {win_loss_pct:.2f}%")
            print(f"  Action: {action['reason']}")
            print(f"  Shares to sell: {sell_shares:.4f} of {current_shares:.4f} ({action['sell_percentage']:.1f}%)")
            
            if dry_run:
                print(f"  🔍 DRY RUN - Would execute stop loss order")
                executed_orders.append({
                    'market_id': market_id,
                    'market_name': market_name,
                    'shares_sold': sell_shares,
                    'action_type': action['type'],
                    'threshold': action['threshold'],
                    'dry_run': True
                })
            else:
                # Execute the actual sell order
                success = self._execute_stop_loss_sell(run_name, position, action)
                if success:
                    print(f"  ✅ Stop loss order executed successfully")
                    executed_orders.append({
                        'market_id': market_id,
                        'market_name': market_name,
                        'shares_sold': sell_shares,
                        'action_type': action['type'],
                        'threshold': action['threshold'],
                        'dry_run': False
                    })
                else:
                    print(f"  ❌ Failed to execute stop loss order")
            
            print()
        
        if executed_orders:
            print(f"📊 Stop Loss Summary: {len(executed_orders)} orders {'simulated' if dry_run else 'executed'}")
        
        return executed_orders
    
    def _execute_stop_loss_sell(self, run_name: str, position: Dict[str, Any], action: Dict[str, Any]) -> bool:
        """
        Execute a stop loss sell order for a specific position.
        
        Args:
            run_name: Name of the simulation run
            position: Position dictionary
            action: Stop loss action dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            market_id = position['market_id']
            sell_shares = action['sell_shares']
            
            # Add stop loss history to track this action
            if 'stop_loss_history' not in position:
                position['stop_loss_history'] = []
            
            stop_loss_record = {
                'timestamp': datetime.now().isoformat(),
                'threshold': action['threshold'],
                'action_type': action['type'],
                'sell_percentage': action['sell_percentage'],
                'shares_sold': sell_shares,
                'win_loss_at_execution': position.get('win_loss_percentage', 0.0),
                'reason': action['reason']
            }
            
            # Execute the sell order using the run initializer
            success = self.run_initializer.sell_position(run_name, market_id, sell_shares)
            
            if success:
                # Update the position's stop loss history
                self._update_position_stop_loss_history(run_name, market_id, stop_loss_record)
                
            return success
            
        except Exception as e:
            logger.error(f"Error executing stop loss sell: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def _update_position_stop_loss_history(self, run_name: str, market_id: str, stop_loss_record: Dict[str, Any]) -> None:
        """
        Update the position's stop loss history in the simulation data.
        
        Args:
            run_name: Name of the simulation run
            market_id: Market ID of the position
            stop_loss_record: Stop loss record to add
        """
        try:
            json_file_path = self.run_initializer.base_runs_dir / run_name / "simulation_data.json"
            
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            # Find and update the position
            for position in data.get('positions', []):
                if position.get('market_id') == market_id:
                    if 'stop_loss_history' not in position:
                        position['stop_loss_history'] = []
                    position['stop_loss_history'].append(stop_loss_record)
                    break
            
            # Save updated data
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error updating stop loss history: {e}")
    
    def print_stop_loss_summary(self, run_name: str) -> None:
        """
        Print a summary of all stop loss actions taken for a run.
        
        Args:
            run_name: Name of the simulation run
        """
        try:
            json_file_path = self.run_initializer.base_runs_dir / run_name / "simulation_data.json"
            
            if not json_file_path.exists():
                print(f"Simulation run '{run_name}' not found")
                return
                
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            positions = data.get('positions', [])
            total_stop_loss_actions = 0
            
            print(f"\n📋 Stop Loss History for run '{run_name}':")
            print("=" * 100)
            
            for position in positions:
                stop_loss_history = position.get('stop_loss_history', [])
                if stop_loss_history:
                    print(f"\n{position['market_name']}:")
                    for record in stop_loss_history:
                        timestamp = record.get('timestamp', 'Unknown')
                        reason = record.get('reason', 'Unknown')
                        shares_sold = record.get('shares_sold', 0.0)
                        win_loss = record.get('win_loss_at_execution', 0.0)
                        print(f"  {timestamp}: {reason}")
                        print(f"    Sold {shares_sold:.4f} shares at {win_loss:.2f}% P&L")
                        total_stop_loss_actions += 1
            
            if total_stop_loss_actions == 0:
                print("No stop loss actions have been taken yet.")
            else:
                print(f"\nTotal stop loss actions: {total_stop_loss_actions}")
                
        except Exception as e:
            logger.error(f"Error printing stop loss summary: {e}")
            if self.debug:
                import traceback
                traceback.print_exc() 