import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path

# Import Polymarket price fetching
try:
    from src.polymarket.order_book.get_prices import get_prices
    POLYMARKET_AVAILABLE = True
except ImportError:
    POLYMARKET_AVAILABLE = False
    print("⚠️  Polymarket order book module not available. Real market initialization will be disabled.")


class RunInitializer:
    """
    Initializes new simulation runs for Polymarket trading.
    
    Creates a new run directory with a structured JSON file containing
    all necessary simulation data including balances, positions, and transactions.
    """
    
    def __init__(self, base_runs_dir: Optional[str] = None):
        """
        Initialize the RunInitializer.
        
        Args:
            base_runs_dir: Base directory where run folders will be created.
                          If None, uses ../runs relative to this file's location.
        """
        if base_runs_dir is None:
            # Get the directory of this file and set runs directory relative to it
            current_file_dir = Path(__file__).parent
            self.base_runs_dir = current_file_dir.parent / "runs"
        else:
            self.base_runs_dir = Path(base_runs_dir)
    
    def create_new_run(
        self,
        market_name: str,
        initial_balance: float,
        run_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new simulation run with all required data structures.
        
        Args:
            market_name: Name of the whole market for this simulation
            initial_balance: Starting balance for the simulation (can be 0)
            run_name: Optional custom name for the run. If None, generates timestamp-based name
            
        Returns:
            Dict containing the run configuration and file path
        """
        # Generate run ID and name
        run_id = str(uuid.uuid4())
        if run_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_name = f"run_{timestamp}"
        
        # Create run directory
        run_dir = self.base_runs_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Get current timestamp
        start_time = datetime.now().isoformat()
        
        # Initialize run data structure
        run_data = {
            "whole_market_name": market_name,
            "run_id": run_id,
            "run_name": run_name,
            "start_time": start_time,
            "current_balance": initial_balance,
            "initial_balance": initial_balance,
            "total_balance": initial_balance,
            "balance_of_shares": 0.0,
            "balance_invested": 0.0,
            "shares": [],  # List of {"market_id": str, "market_name": str, "num_shares": int}
            "transactions": [],  # List of all transactions
            "total_balances": [  # Time series of total balances
                {
                    "timestamp": start_time,
                    "total_balance": initial_balance,
                    "current_balance": initial_balance,
                    "balance_of_shares": 0.0,
                    "balance_invested": 0.0
                }
            ],
            "positions": [],  # List of current positions with detailed info
            "markets": []  # List of all markets: {"market_id": str, "market_name": str, "description": str, "category": str}
        }
        
        # Save to JSON file
        json_file_path = run_dir / "simulation_data.json"
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully created new simulation run:")
        print(f"   📁 Directory: {run_dir}")
        print(f"   🆔 Run ID: {run_id}")
        print(f"   📛 Run Name: {run_name}")
        print(f"   💰 Initial Balance: ${initial_balance:,.2f}")
        print(f"   📄 Data file: {json_file_path}")
        
        return {
            "run_id": run_id,
            "run_name": run_name,
            "run_directory": str(run_dir),
            "json_file_path": str(json_file_path),
            "initial_data": run_data
        }
    
    def create_market(
        self,
        run_name: str,
        market_id: str,
        market_name: str,
        description: str,
        category: str,
        initial_price: float,
        bid_price: float,
        ask_price: float
    ) -> bool:
        """
        Create a new market for the simulation run.
        
        Args:
            run_name: Name of the run to update
            market_id: Unique identifier for the market
            market_name: Human-readable name of the market
            description: Description of the market
            category: Category of the market (e.g., "prediction", "sports")
            initial_price: Initial price of the share (must be >= 0)
            bid_price: Current bid price (price to sell at, must be >= 0)
            ask_price: Current ask price (price to buy at, must be >= 0)
            
        Returns:
            bool: True if market was created successfully
        """
        # Validate that prices are not negative (0 is allowed)
        if initial_price < 0:
            print(f"❌ Initial price cannot be negative. Got: {initial_price}")
            return False
        
        if bid_price < 0:
            print(f"❌ Bid price cannot be negative. Got: {bid_price}")
            return False
        
        if ask_price < 0:
            print(f"❌ Ask price cannot be negative. Got: {ask_price}")
            return False
        
        json_file_path = self.base_runs_dir / run_name / "simulation_data.json"
        
        if not json_file_path.exists():
            print(f"❌ Run '{run_name}' not found!")
            return False
        
        # Load existing data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            run_data = json.load(f)
        
        # Check if market already exists
        market_exists = any(market["market_id"] == market_id for market in run_data.get("markets", []))
        if market_exists:
            print(f"❌ Market '{market_id}' already exists!")
            return False
        
        # Create timestamp
        timestamp = datetime.now().isoformat()
        
        # Create market entry with price tracking
        market_entry = {
            "market_id": market_id,
            "market_name": market_name,
            "description": description,
            "category": category,
            "initial_price": initial_price,
            "current_price": initial_price,  # Initially same as initial price
            "current_bid": bid_price,
            "current_ask": ask_price,
            "price_history": [
                {
                    "timestamp": timestamp,
                    "price": initial_price,
                    "bid": bid_price,
                    "ask": ask_price
                }
            ]
        }
        
        run_data["markets"].append(market_entry)
        
        # Save updated data
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created market '{market_name}' ({market_id})")
        print(f"   📊 Initial Price: ${initial_price:.4f}")
        print(f"   💰 Bid: ${bid_price:.4f} | Ask: ${ask_price:.4f}")
        print(f"   📁 Category: {category}")
        
        return True
    
    def add_position(
        self,
        run_name: str,
        market_id: str,
        num_shares: float,
        allow_negative_balance: bool = False
    ) -> bool:
        """
        Add a new position to an existing run or update existing position.
        Market must exist before positions can be created.
        Purchases are made at the current ask price.
        
        Args:
            run_name: Name of the run to update
            market_id: Unique identifier for the market (must exist)
            num_shares: Number of shares purchased (can be fractional, must be positive)
            allow_negative_balance: Whether to allow transactions that result in negative balance
            
        Returns:
            bool: True if position was added successfully
        """
        json_file_path = self.base_runs_dir / run_name / "simulation_data.json"
        
        if not json_file_path.exists():
            print(f"❌ Run '{run_name}' not found!")
            return False

        # Check for zero or negative shares
        if num_shares <= 0:
            print(f"❌ Invalid share amount: {num_shares}. Must be positive.")
            return False
        
        # Load existing data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            run_data = json.load(f)
        
        # Find the market
        market = None
        for m in run_data.get("markets", []):
            if m["market_id"] == market_id:
                market = m
                break
        
        if market is None:
            print(f"❌ Market '{market_id}' not found! Please create the market first.")
            return False
        
        # Use ask price for buying
        purchase_price = market["current_ask"]
        market_name = market["market_name"]
        
        # Calculate total cost
        total_cost = num_shares * purchase_price
        
        # Check if transaction would result in negative balance
        if not allow_negative_balance and run_data["current_balance"] < total_cost:
            print(f"❌ Insufficient funds! Available: ${run_data['current_balance']:,.2f}, Required: ${total_cost:,.2f}")
            return False
        
        # Check if position already exists
        existing_position_idx = None
        existing_share_idx = None
        
        for idx, position in enumerate(run_data["positions"]):
            if position["market_id"] == market_id:
                existing_position_idx = idx
                break
        
        for idx, share in enumerate(run_data["shares"]):
            if share["market_id"] == market_id:
                existing_share_idx = idx
                break
        
        # Create buy transaction record for position history
        buy_transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": "BUY",
            "num_shares": num_shares,
            "price_per_share": purchase_price,
            "total_amount": total_cost
        }
        
        if existing_position_idx is not None:
            # Update existing position
            existing_position = run_data["positions"][existing_position_idx]
            
            # Ensure transaction_history exists for backward compatibility
            if "transaction_history" not in existing_position:
                existing_position["transaction_history"] = []
            
            old_shares = existing_position["num_shares"]
            old_total_invested = existing_position["total_invested"]
            
            new_total_shares = old_shares + num_shares
            new_total_invested = old_total_invested + total_cost
            
            # Calculate current value based on current market price (for potential selling)
            current_value_if_sold = new_total_shares * market["current_bid"]
            
            # Calculate win/loss percentage based on current market price vs average cost
            average_cost_per_share = new_total_invested / new_total_shares
            current_market_value = new_total_shares * market["current_price"]
            win_loss_percentage = ((current_market_value - new_total_invested) / new_total_invested) * 100 if new_total_invested > 0 else 0
            
            # Add transaction to position history
            existing_position["transaction_history"].append(buy_transaction)
            
            # Update position
            run_data["positions"][existing_position_idx].update({
                "num_shares": new_total_shares,
                "current_price_per_share": market["current_price"],  # Always match market price
                "current_total_price": current_market_value,
                "current_value_if_sold": current_value_if_sold,
                "total_invested": new_total_invested,
                "win_loss_percentage": win_loss_percentage,
                "position_status": "ACTIVE"  # Ensure status is active
                # Note: initial_price_per_share and initial_total_price stay the same
            })
            
            # Update shares entry
            if existing_share_idx is not None:
                run_data["shares"][existing_share_idx]["num_shares"] = new_total_shares
            else:
                # This shouldn't happen, but handle it just in case
                share_entry = {
                    "market_id": market_id,
                    "market_name": market_name,
                    "num_shares": new_total_shares
                }
                run_data["shares"].append(share_entry)
            
            print(f"📈 Updated existing position for {market_name} ({market_id})")
            print(f"   Previous shares: {old_shares}, Added: {num_shares}, Total: {new_total_shares}")
            print(f"   Purchase price (ask): ${purchase_price:.4f}")
            print(f"   Total invested: ${new_total_invested:.2f}")
        else:
            # Create new position
            share_entry = {
                "market_id": market_id,
                "market_name": market_name,
                "num_shares": num_shares
            }
            run_data["shares"].append(share_entry)
            
            # Calculate current value based on market price and bid price
            current_market_value = num_shares * market["current_price"]
            current_value_if_sold = num_shares * market["current_bid"]
            win_loss_percentage = ((current_market_value - total_cost) / total_cost) * 100 if total_cost > 0 else 0
            
            position_entry = {
                "market_id": market_id,
                "market_name": market_name,
                "current_price_per_share": market["current_price"],  # Match market price
                "num_shares": num_shares,
                "current_total_price": current_market_value,
                "current_value_if_sold": current_value_if_sold,
                "initial_price_per_share": purchase_price,  # This should never change
                "initial_total_price": total_cost,  # This should never change
                "total_invested": total_cost,
                "win_loss_percentage": win_loss_percentage,
                "transaction_history": [buy_transaction],  # Track all buy/sell transactions
                "position_status": "ACTIVE"  # Ensure status is active
            }
            run_data["positions"].append(position_entry)
            
            print(f"📈 Created new position for {market_name} ({market_id})")
            print(f"   Shares: {num_shares}, Purchase price (ask): ${purchase_price:.4f}")
            print(f"   Total invested: ${total_cost:.2f}")
        
        # Update balances
        run_data["current_balance"] -= total_cost
        
        # Recalculate balance_invested based on total invested amounts
        total_invested_in_shares = sum(pos["total_invested"] for pos in run_data["positions"])
        run_data["balance_invested"] = total_invested_in_shares
        
        # Calculate current market value of all positions for balance_of_shares
        total_current_value = sum(pos["current_total_price"] for pos in run_data["positions"])
        run_data["balance_of_shares"] = total_current_value
        
        # Calculate new total balance (current_balance + current market value of all positions)
        run_data["total_balance"] = run_data["current_balance"] + total_current_value
        
        # Add transaction record
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": "BUY",
            "market_id": market_id,
            "market_name": market_name,
            "num_shares": num_shares,
            "price_per_share": purchase_price,
            "total_amount": total_cost
        }
        run_data["transactions"].append(transaction)
        
        # Add balance snapshot
        balance_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "total_balance": run_data["total_balance"],
            "current_balance": run_data["current_balance"],
            "balance_of_shares": run_data["balance_of_shares"],
            "balance_invested": run_data["balance_invested"],
            "total_market_value": total_current_value
        }
        run_data["total_balances"].append(balance_snapshot)
        
        # Save updated data
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
        
        print(f"   💰 Transaction cost: ${total_cost:,.2f}")
        print(f"   💵 Remaining balance: ${run_data['current_balance']:,.2f}")
        print(f"   📊 Total balance: ${run_data['total_balance']:,.2f}")
        
        return True
    
    def sell_position(
        self,
        run_name: str,
        market_id: str,
        num_shares: float
    ) -> bool:
        """
        Sell shares from an existing position.
        Sales are made at the current bid price.
        
        Args:
            run_name: Name of the run to update
            market_id: Unique identifier for the market
            num_shares: Number of shares to sell (can be fractional, must be positive)
            
        Returns:
            bool: True if position was sold successfully
        """
        json_file_path = self.base_runs_dir / run_name / "simulation_data.json"
        
        if not json_file_path.exists():
            print(f"❌ Run '{run_name}' not found!")
            return False

        # Check for zero or negative shares
        if num_shares <= 0:
            print(f"❌ Invalid share amount: {num_shares}. Must be positive.")
            return False
        
        # Load existing data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            run_data = json.load(f)
        
        # Find the market
        market = None
        for m in run_data.get("markets", []):
            if m["market_id"] == market_id:
                market = m
                break
        
        if market is None:
            print(f"❌ Market '{market_id}' not found!")
            return False
        
        # Use bid price for selling
        sell_price_per_share = market["current_bid"]
        
        # Find existing position
        existing_position_idx = None
        existing_share_idx = None
        
        for idx, position in enumerate(run_data["positions"]):
            if position["market_id"] == market_id:
                existing_position_idx = idx
                break
        
        for idx, share in enumerate(run_data["shares"]):
            if share["market_id"] == market_id:
                existing_share_idx = idx
                break
        
        if existing_position_idx is None:
            print(f"❌ No position found for market {market_id}")
            return False
        
        existing_position = run_data["positions"][existing_position_idx]
        current_shares = existing_position["num_shares"]
        
        # Ensure transaction_history exists for backward compatibility
        if "transaction_history" not in existing_position:
            existing_position["transaction_history"] = []
        
        if num_shares > current_shares:
            print(f"❌ Cannot sell {num_shares} shares. Only {current_shares} shares available.")
            return False
        
        # Calculate sale proceeds using bid price
        sale_proceeds = num_shares * sell_price_per_share
        
        # Calculate the proportional cost basis for the shares being sold
        total_invested = existing_position["total_invested"]
        cost_basis_per_share = total_invested / current_shares
        cost_basis_sold = num_shares * cost_basis_per_share
        
        # Create sell transaction record for position history
        sell_transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": "SELL",
            "num_shares": num_shares,
            "price_per_share": sell_price_per_share,
            "total_amount": sale_proceeds,
            "cost_basis": cost_basis_sold,
            "profit_loss": sale_proceeds - cost_basis_sold
        }
        
        if num_shares == current_shares:
            # Selling entire position - add final sell transaction but keep position record
            existing_position["transaction_history"].append(sell_transaction)
            
            # Calculate total P&L for the closed position
            total_pnl = self._calculate_position_total_pnl(existing_position["transaction_history"])
            
            # Update position to show 0 shares but keep historical data
            existing_position.update({
                "num_shares": 0.0,
                "current_price_per_share": market["current_price"],
                "current_total_price": 0.0,
                "current_value_if_sold": 0.0,
                "total_invested": 0.0,  # Reset since position is closed
                "win_loss_percentage": 0.0,  # Position is closed
                "position_status": "CLOSED",  # Mark as closed
                "total_pnl": total_pnl["net_pnl"],  # Store total P&L
                "total_pnl_percentage": total_pnl["net_pnl_percentage"]  # Store total P&L %
            })
            
            # Remove shares entry completely when selling entire position
            if existing_share_idx is not None:
                run_data["shares"].pop(existing_share_idx)
            
            print(f"📉 Sold entire position for market {market_id} (position kept for history)")
            print(f"   🏁 Position CLOSED - Total P&L: ${total_pnl['net_pnl']:,.2f} ({total_pnl['net_pnl_percentage']:+.2f}%)")
            print(f"   📊 Total bought: {total_pnl['total_bought']} shares for ${total_pnl['total_cost']:,.2f}")
            print(f"   📊 Total sold: {total_pnl['total_sold']} shares for ${total_pnl['total_proceeds']:,.2f}")
        else:
            # Partial sale - add transaction and update position
            existing_position["transaction_history"].append(sell_transaction)
            
            remaining_shares = current_shares - num_shares
            remaining_total_invested = total_invested - cost_basis_sold
            
            # Calculate current values for remaining position
            current_market_value = remaining_shares * market["current_price"]
            current_value_if_sold = remaining_shares * market["current_bid"]
            win_loss_percentage = ((current_market_value - remaining_total_invested) / remaining_total_invested) * 100 if remaining_total_invested > 0 else 0
            
            run_data["positions"][existing_position_idx].update({
                "num_shares": remaining_shares,
                "current_price_per_share": market["current_price"],
                "current_total_price": current_market_value,
                "current_value_if_sold": current_value_if_sold,
                "total_invested": remaining_total_invested,
                "win_loss_percentage": win_loss_percentage,
                "position_status": "ACTIVE"  # Ensure status is active
                # initial_price_per_share and initial_total_price remain unchanged
            })
            
            if existing_share_idx is not None:
                run_data["shares"][existing_share_idx]["num_shares"] = remaining_shares
            
            print(f"📉 Sold {num_shares} shares from market {market_id}")
            print(f"   Remaining shares: {remaining_shares}")
        
        # Update balances
        run_data["current_balance"] += sale_proceeds
        
        # Recalculate balance_invested based on remaining total invested amounts
        total_invested_in_shares = sum(pos["total_invested"] for pos in run_data["positions"])
        run_data["balance_invested"] = total_invested_in_shares
        
        # Calculate current market value of all positions for balance_of_shares
        total_current_value = sum(pos["current_total_price"] for pos in run_data["positions"])
        run_data["balance_of_shares"] = total_current_value
        
        # Calculate new total balance (current_balance + current market value of all positions)
        run_data["total_balance"] = run_data["current_balance"] + total_current_value
        
        # Add transaction record
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": "SELL",
            "market_id": market_id,
            "market_name": existing_position["market_name"],
            "num_shares": num_shares,
            "price_per_share": sell_price_per_share,
            "total_amount": sale_proceeds,
            "cost_basis": cost_basis_sold,
            "profit_loss": sale_proceeds - cost_basis_sold
        }
        run_data["transactions"].append(transaction)
        
        # Add balance snapshot
        balance_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "total_balance": run_data["total_balance"],
            "current_balance": run_data["current_balance"],
            "balance_of_shares": run_data["balance_of_shares"],
            "balance_invested": run_data["balance_invested"],
            "total_market_value": total_current_value
        }
        run_data["total_balances"].append(balance_snapshot)
        
        # Save updated data
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
        
        profit_loss = sale_proceeds - cost_basis_sold
        print(f"   💰 Sale proceeds (bid): ${sale_proceeds:,.2f}")
        print(f"   📊 Profit/Loss: ${profit_loss:,.2f}")
        print(f"   💵 New balance: ${run_data['current_balance']:,.2f}")
        print(f"   📊 Total balance: ${run_data['total_balance']:,.2f}")
        
        return True
    
    def update_market_prices(
        self,
        run_name: str,
        price_updates: Dict[str, Dict[str, float]]
    ) -> bool:
        """
        Update current market prices for positions.
        
        Args:
            run_name: Name of the run to update
            price_updates: Dict mapping market_id to price dict with keys:
                          {"price": float, "bid": float, "ask": float}
                          All price values must be >= 0
            
        Returns:
            bool: True if prices were updated successfully
        """
        json_file_path = self.base_runs_dir / run_name / "simulation_data.json"
        
        if not json_file_path.exists():
            print(f"❌ Run '{run_name}' not found!")
            return False
        
        # Validate all price updates before applying any changes
        for market_id, price_data in price_updates.items():
            if "price" in price_data and price_data["price"] < 0:
                print(f"❌ Price cannot be negative for market '{market_id}'. Got: {price_data['price']}")
                return False
            
            if "bid" in price_data and price_data["bid"] < 0:
                print(f"❌ Bid price cannot be negative for market '{market_id}'. Got: {price_data['bid']}")
                return False
            
            if "ask" in price_data and price_data["ask"] < 0:
                print(f"❌ Ask price cannot be negative for market '{market_id}'. Got: {price_data['ask']}")
                return False
        
        # Load existing data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            run_data = json.load(f)
        
        updated_markets = 0
        timestamp = datetime.now().isoformat()
        
        # Update market prices and add to price history
        for market in run_data["markets"]:
            market_id = market["market_id"]
            if market_id in price_updates:
                price_data = price_updates[market_id]
                
                old_price = market["current_price"]
                old_bid = market["current_bid"]
                old_ask = market["current_ask"]
                
                # Update current prices
                market["current_price"] = price_data["price"]
                market["current_bid"] = price_data["bid"]
                market["current_ask"] = price_data["ask"]
                
                # Add to price history
                market["price_history"].append({
                    "timestamp": timestamp,
                    "price": price_data["price"],
                    "bid": price_data["bid"],
                    "ask": price_data["ask"]
                })
                
                updated_markets += 1
                print(f"📊 Updated {market['market_name']}:")
                print(f"   Price: ${old_price:.4f} → ${price_data['price']:.4f}")
                print(f"   Bid: ${old_bid:.4f} → ${price_data['bid']:.4f}")
                print(f"   Ask: ${old_ask:.4f} → ${price_data['ask']:.4f}")
        
        # Update all positions based on new market prices
        total_current_value = 0
        for position in run_data["positions"]:
            market_id = position["market_id"]
            
            # Find the market for this position
            market = None
            for m in run_data["markets"]:
                if m["market_id"] == market_id:
                    market = m
                    break
            
            if market:
                # Update position with current market data
                position["current_price_per_share"] = market["current_price"]
                position["current_total_price"] = position["num_shares"] * market["current_price"]
                position["current_value_if_sold"] = position["num_shares"] * market["current_bid"]
                
                # Recalculate win/loss percentage based on current market price vs total invested
                total_invested = position["total_invested"]
                current_market_value = position["current_total_price"]
                position["win_loss_percentage"] = ((current_market_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0
                
                total_current_value += current_market_value
        
        # Update total balance with current market values
        run_data["total_balance"] = run_data["current_balance"] + total_current_value
        
        # Update balance_of_shares to current market value and balance_invested to total invested
        run_data["balance_of_shares"] = total_current_value
        total_invested_in_shares = sum(pos["total_invested"] for pos in run_data["positions"])
        run_data["balance_invested"] = total_invested_in_shares
        
        # Add balance snapshot
        balance_snapshot = {
            "timestamp": timestamp,
            "total_balance": run_data["total_balance"],
            "current_balance": run_data["current_balance"],
            "balance_of_shares": run_data["balance_of_shares"],
            "balance_invested": run_data["balance_invested"],
            "total_market_value": total_current_value
        }
        run_data["total_balances"].append(balance_snapshot)
        
        # Save updated data
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Updated prices for {updated_markets} markets")
        print(f"💰 New total balance: ${run_data['total_balance']:,.2f}")
        print(f"📈 Total market value: ${total_current_value:,.2f}")
        
        return True
    
    def add_balance(
        self,
        run_name: str,
        amount: float,
        description: str = "Manual balance addition"
    ) -> bool:
        """
        Add balance to an existing run.
        
        Args:
            run_name: Name of the run to update
            amount: Amount to add (must be positive)
            description: Description for the transaction
            
        Returns:
            bool: True if balance was added successfully
        """
        if amount <= 0:
            print(f"❌ Amount must be positive. Got: ${amount}")
            return False
            
        json_file_path = self.base_runs_dir / run_name / "simulation_data.json"
        
        if not json_file_path.exists():
            print(f"❌ Run '{run_name}' not found!")
            return False
        
        # Load existing data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            run_data = json.load(f)
        
        # Update balances
        run_data["current_balance"] += amount
        run_data["total_balance"] += amount
        
        # Add transaction record
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": "BALANCE_ADD",
            "description": description,
            "amount": amount,
            "balance_after": run_data["current_balance"]
        }
        run_data["transactions"].append(transaction)
        
        # Add balance snapshot
        balance_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "total_balance": run_data["total_balance"],
            "current_balance": run_data["current_balance"],
            "balance_of_shares": run_data["balance_of_shares"],
            "balance_invested": run_data["balance_invested"]
        }
        run_data["total_balances"].append(balance_snapshot)
        
        # Save updated data
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Added ${amount:,.2f} to run '{run_name}'")
        print(f"   📝 Description: {description}")
        print(f"   💵 New balance: ${run_data['current_balance']:,.2f}")
        print(f"   💰 New total balance: ${run_data['total_balance']:,.2f}")
        
        return True
    
    def remove_balance(
        self,
        run_name: str,
        amount: float,
        description: str = "Manual balance removal",
        allow_negative: bool = False
    ) -> bool:
        """
        Remove balance from an existing run.
        
        Args:
            run_name: Name of the run to update
            amount: Amount to remove (must be positive)
            description: Description for the transaction
            allow_negative: Whether to allow negative balance
            
        Returns:
            bool: True if balance was removed successfully
        """
        if amount <= 0:
            print(f"❌ Amount must be positive. Got: ${amount}")
            return False
            
        json_file_path = self.base_runs_dir / run_name / "simulation_data.json"
        
        if not json_file_path.exists():
            print(f"❌ Run '{run_name}' not found!")
            return False
        
        # Load existing data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            run_data = json.load(f)
        
        # Check if removal would result in negative balance
        new_balance = run_data["current_balance"] - amount
        if not allow_negative and new_balance < 0:
            print(f"❌ Insufficient funds! Available: ${run_data['current_balance']:,.2f}, Requested: ${amount:,.2f}")
            return False
        
        # Update balances
        run_data["current_balance"] -= amount
        run_data["total_balance"] -= amount
        
        # Add transaction record
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": "BALANCE_REMOVE",
            "description": description,
            "amount": amount,
            "balance_after": run_data["current_balance"]
        }
        run_data["transactions"].append(transaction)
        
        # Add balance snapshot
        balance_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "total_balance": run_data["total_balance"],
            "current_balance": run_data["current_balance"],
            "balance_of_shares": run_data["balance_of_shares"],
            "balance_invested": run_data["balance_invested"]
        }
        run_data["total_balances"].append(balance_snapshot)
        
        # Save updated data
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Removed ${amount:,.2f} from run '{run_name}'")
        print(f"   📝 Description: {description}")
        print(f"   💵 New balance: ${run_data['current_balance']:,.2f}")
        print(f"   💰 New total balance: ${run_data['total_balance']:,.2f}")
        
        return True
    
    def list_runs(self) -> List[str]:
        """
        List all existing simulation runs.
        
        Returns:
            List of run names
        """
        if not self.base_runs_dir.exists():
            return []
        
        runs = []
        for item in self.base_runs_dir.iterdir():
            if item.is_dir() and (item / "simulation_data.json").exists():
                runs.append(item.name)
        
        return sorted(runs)
    
    def get_run_info(self, run_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific run.
        
        Args:
            run_name: Name of the run
            
        Returns:
            Dict with run information or None if not found
        """
        json_file_path = self.base_runs_dir / run_name / "simulation_data.json"
        
        if not json_file_path.exists():
            return None
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _calculate_position_total_pnl(self, transaction_history: List[Dict]) -> Dict[str, float]:
        """
        Calculate total profit/loss for a position based on its transaction history.
        
        Args:
            transaction_history: List of buy/sell transactions
            
        Returns:
            Dict with total_bought, total_sold, total_cost, total_proceeds, net_pnl
        """
        total_bought = 0.0
        total_sold = 0.0
        total_cost = 0.0
        total_proceeds = 0.0
        
        for transaction in transaction_history:
            if transaction["type"] == "BUY":
                total_bought += transaction["num_shares"]
                total_cost += transaction["total_amount"]
            elif transaction["type"] == "SELL":
                total_sold += transaction["num_shares"]
                total_proceeds += transaction["total_amount"]
        
        net_pnl = total_proceeds - total_cost
        
        return {
            "total_bought": total_bought,
            "total_sold": total_sold,
            "total_cost": total_cost,
            "total_proceeds": total_proceeds,
            "net_pnl": net_pnl,
            "net_pnl_percentage": (net_pnl / total_cost * 100) if total_cost > 0 else 0.0
        }
    
    def initialize_markets_from_polymarket(
        self,
        run_name: str,
        category: str = "prediction"
    ) -> bool:
        """
        Initialize markets for a simulation run using real Polymarket data.
        Fetches current market data and creates markets with current prices.
        
        Args:
            run_name: Name of the run to add markets to
            category: Category to assign to all markets (default: "prediction")
            
        Returns:
            bool: True if markets were initialized successfully
        """
        if not POLYMARKET_AVAILABLE:
            print("❌ Polymarket order book module is not available!")
            print("   Make sure the polymarket module is properly installed.")
            return False
        
        json_file_path = self.base_runs_dir / run_name / "simulation_data.json"
        
        if not json_file_path.exists():
            print(f"❌ Run '{run_name}' not found!")
            return False
        
        print("🔄 Fetching real Polymarket data...")
        
        # Get real market prices from Polymarket
        market_data = get_prices()
        
        if not market_data:
            print("❌ Failed to fetch Polymarket data!")
            return False
        
        print(f"✅ Found {len(market_data)} active markets from Polymarket")
        
        # Load existing run data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            run_data = json.load(f)
        
        created_markets = 0
        skipped_markets = 0
        
        for token_id, data in market_data.items():
            market_name = data.get('question', 'Unknown Market')
            market_id_from_data = data.get('market_id', token_id)
            buy_price = data.get('BUY')
            sell_price = data.get('SELL')
            
            # Skip if prices are not available
            if buy_price is None or sell_price is None:
                print(f"⚠️  Skipping {market_name} - missing price data")
                skipped_markets += 1
                continue
            
            # Convert prices to float and validate
            try:
                buy_price = float(buy_price)
                sell_price = float(sell_price)
                
                if buy_price < 0 or sell_price < 0:
                    print(f"⚠️  Skipping {market_name} - invalid prices (negative)")
                    skipped_markets += 1
                    continue
                    
            except (ValueError, TypeError):
                print(f"⚠️  Skipping {market_name} - invalid price format")
                skipped_markets += 1
                continue
            
            # Use token_id as market_id to ensure uniqueness
            market_id = token_id
            
            # Check if market already exists
            market_exists = any(market["market_id"] == market_id for market in run_data.get("markets", []))
            if market_exists:
                print(f"⚠️  Skipping {market_name} - already exists")
                skipped_markets += 1
                continue
            
            # Calculate mid price for initial and current price
            mid_price = (buy_price + sell_price) / 2
            
            # Create timestamp
            timestamp = datetime.now().isoformat()
            
            # Create market entry
            market_entry = {
                "market_id": market_id,
                "market_name": market_name,
                "description": f"Polymarket prediction: {market_name}",
                "category": category,
                "initial_price": mid_price,
                "current_price": mid_price,
                "current_bid": buy_price,  # BUY price is what we can sell at (bid)
                "current_ask": sell_price,  # SELL price is what we need to pay to buy (ask)
                "price_history": [
                    {
                        "timestamp": timestamp,
                        "price": mid_price,
                        "bid": buy_price,
                        "ask": sell_price
                    }
                ]
            }
            
            run_data["markets"].append(market_entry)
            created_markets += 1
            
            print(f"✅ Added market: {market_name}")
            print(f"   📊 Mid Price: ${mid_price:.4f}")
            print(f"   💰 Bid: ${buy_price:.4f} | Ask: ${sell_price:.4f}")
        
        # Save updated data
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Market initialization complete!")
        print(f"   ✅ Created: {created_markets} markets")
        print(f"   ⚠️  Skipped: {skipped_markets} markets")
        print(f"   📁 Run: {run_name}")
        
        return True
    
    def update_markets_from_polymarket(
        self,
        run_name: str
    ) -> bool:
        """
        Update existing market prices using real Polymarket data.
        Markets that no longer exist on Polymarket will be marked as inactive with 0 prices.
        
        Args:
            run_name: Name of the run to update markets for
            
        Returns:
            bool: True if markets were updated successfully
        """
        if not POLYMARKET_AVAILABLE:
            print("❌ Polymarket order book module is not available!")
            print("   Make sure the polymarket module is properly installed.")
            return False
        
        json_file_path = self.base_runs_dir / run_name / "simulation_data.json"
        
        if not json_file_path.exists():
            print(f"❌ Run '{run_name}' not found!")
            return False
        
        print("🔄 Fetching real Polymarket data to update existing markets...")
        
        # Get real market prices from Polymarket
        market_data = get_prices()
        
        if market_data is None:
            print("❌ Failed to fetch Polymarket data!")
            return False
        
        print(f"✅ Found {len(market_data)} active markets from Polymarket")
        
        # Load existing run data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            run_data = json.load(f)
        
        existing_markets = run_data.get("markets", [])
        if not existing_markets:
            print("⚠️  No existing markets found in this run to update!")
            return True
        
        updated_markets = 0
        inactive_markets = 0
        timestamp = datetime.now().isoformat()
        
        for market in existing_markets:
            market_id = market["market_id"]
            market_name = market["market_name"]
            
            # Check if this market exists in current Polymarket data
            if market_id in market_data:
                # Market is still active - update with real prices
                data = market_data[market_id]
                buy_price = data.get('BUY')
                sell_price = data.get('SELL')
                
                # Validate prices
                if buy_price is None or sell_price is None:
                    print(f"⚠️  Marking {market_name} as inactive - missing price data")
                    # Mark as inactive
                    old_price = market["current_price"]
                    old_bid = market["current_bid"]
                    old_ask = market["current_ask"]
                    
                    market["current_price"] = 0.0
                    market["current_bid"] = 0.0
                    market["current_ask"] = 0.0
                    market["market_status"] = "INACTIVE"
                    
                    # Add to price history
                    market["price_history"].append({
                        "timestamp": timestamp,
                        "price": 0.0,
                        "bid": 0.0,
                        "ask": 0.0,
                        "status": "INACTIVE",
                        "reason": "Missing price data"
                    })
                    
                    print(f"   📊 Marked as INACTIVE: {market_name}")
                    print(f"   💰 Previous - Price: ${old_price:.4f}, Bid: ${old_bid:.4f}, Ask: ${old_ask:.4f}")
                    inactive_markets += 1
                    continue
                
                try:
                    buy_price = float(buy_price)
                    sell_price = float(sell_price)
                    
                    if buy_price < 0 or sell_price < 0:
                        print(f"⚠️  Marking {market_name} as inactive - invalid prices (negative)")
                        # Mark as inactive
                        market["current_price"] = 0.0
                        market["current_bid"] = 0.0
                        market["current_ask"] = 0.0
                        market["market_status"] = "INACTIVE"
                        
                        market["price_history"].append({
                            "timestamp": timestamp,
                            "price": 0.0,
                            "bid": 0.0,
                            "ask": 0.0,
                            "status": "INACTIVE",
                            "reason": "Invalid prices (negative)"
                        })
                        
                        inactive_markets += 1
                        continue
                        
                except (ValueError, TypeError):
                    print(f"⚠️  Marking {market_name} as inactive - invalid price format")
                    # Mark as inactive
                    market["current_price"] = 0.0
                    market["current_bid"] = 0.0
                    market["current_ask"] = 0.0
                    market["market_status"] = "INACTIVE"
                    
                    market["price_history"].append({
                        "timestamp": timestamp,
                        "price": 0.0,
                        "bid": 0.0,
                        "ask": 0.0,
                        "status": "INACTIVE",
                        "reason": "Invalid price format"
                    })
                    
                    inactive_markets += 1
                    continue
                
                # Update with valid prices
                old_price = market["current_price"]
                old_bid = market["current_bid"]
                old_ask = market["current_ask"]
                
                # Calculate mid price
                mid_price = (buy_price + sell_price) / 2
                
                # Update market data
                market["current_price"] = mid_price
                market["current_bid"] = buy_price  # BUY price is what we can sell at (bid)
                market["current_ask"] = sell_price  # SELL price is what we need to pay to buy (ask)
                market["market_status"] = "ACTIVE"
                
                # Add to price history
                market["price_history"].append({
                    "timestamp": timestamp,
                    "price": mid_price,
                    "bid": buy_price,
                    "ask": sell_price,
                    "status": "ACTIVE"
                })
                
                print(f"✅ Updated {market_name}")
                print(f"   📊 Price: ${old_price:.4f} → ${mid_price:.4f}")
                print(f"   💰 Bid: ${old_bid:.4f} → ${buy_price:.4f}")
                print(f"   💰 Ask: ${old_ask:.4f} → ${sell_price:.4f}")
                
                updated_markets += 1
                
            else:
                # Market no longer exists on Polymarket - mark as inactive
                old_price = market["current_price"]
                old_bid = market["current_bid"]
                old_ask = market["current_ask"]
                
                market["current_price"] = 0.0
                market["current_bid"] = 0.0
                market["current_ask"] = 0.0
                market["market_status"] = "INACTIVE"
                
                # Add to price history
                market["price_history"].append({
                    "timestamp": timestamp,
                    "price": 0.0,
                    "bid": 0.0,
                    "ask": 0.0,
                    "status": "INACTIVE",
                    "reason": "Market no longer available on Polymarket"
                })
                
                print(f"⚠️  Marked as INACTIVE: {market_name} (no longer available on Polymarket)")
                print(f"   📊 Previous - Price: ${old_price:.4f}, Bid: ${old_bid:.4f}, Ask: ${old_ask:.4f}")
                inactive_markets += 1
        
        # Update all positions based on new market prices
        total_current_value = 0
        for position in run_data["positions"]:
            position_market_id = position["market_id"]
            
            # Find the market for this position
            market = None
            for m in run_data["markets"]:
                if m["market_id"] == position_market_id:
                    market = m
                    break
            
            if market:
                # Update position with current market data
                position["current_price_per_share"] = market["current_price"]
                position["current_total_price"] = position["num_shares"] * market["current_price"]
                position["current_value_if_sold"] = position["num_shares"] * market["current_bid"]
                
                # Recalculate win/loss percentage based on current market price vs total invested
                total_invested = position["total_invested"]
                current_market_value = position["current_total_price"]
                position["win_loss_percentage"] = ((current_market_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0
                
                total_current_value += current_market_value
        
        # Update total balance with current market values
        run_data["total_balance"] = run_data["current_balance"] + total_current_value
        
        # Update balance_of_shares to current market value and balance_invested to total invested
        run_data["balance_of_shares"] = total_current_value
        total_invested_in_shares = sum(pos["total_invested"] for pos in run_data["positions"])
        run_data["balance_invested"] = total_invested_in_shares
        
        # Add balance snapshot
        balance_snapshot = {
            "timestamp": timestamp,
            "total_balance": run_data["total_balance"],
            "current_balance": run_data["current_balance"],
            "balance_of_shares": run_data["balance_of_shares"],
            "balance_invested": run_data["balance_invested"],
            "total_market_value": total_current_value
        }
        run_data["total_balances"].append(balance_snapshot)
        
        # Save updated data
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Market update complete!")
        print(f"   ✅ Updated: {updated_markets} active markets")
        print(f"   ⚠️  Inactive: {inactive_markets} markets")
        print(f"   💰 New total balance: ${run_data['total_balance']:,.2f}")
        print(f"   📈 Total market value: ${total_current_value:,.2f}")
        print(f"   📁 Run: {run_name}")
        
        return True 