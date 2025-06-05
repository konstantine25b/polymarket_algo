#!/usr/bin/env python3
"""
Command-line interface for Polymarket Simulation Initialization.

Usage:
    python -m src.simulation.initialization [options]

Examples:
    python -m src.simulation.initialization --create --market "2024 Election" --balance 10000
    python -m src.simulation.initialization --list
    python -m src.simulation.initialization --info "run_20241215_143022"
"""

import argparse
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.simulation.initialization.run_initializer import RunInitializer


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Polymarket Simulation Initialization Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create a new simulation run
    python -m src.simulation.initialization --create --market "2024 Election" --balance 10000
    
    # Create with custom name
    python -m src.simulation.initialization --create --market "Crypto Predictions" --balance 5000 --name "crypto_v1"
    
    # List all runs
    python -m src.simulation.initialization --list
    
    # Get run information
    python -m src.simulation.initialization --info "run_20241215_143022"
    
    # Add position to existing run
    python -m src.simulation.initialization --add-position --run "my_run" --market-id "0x123" --market-name "Trump Wins" --shares 100 --price 0.65
    
    # Add position allowing negative balance
    python -m src.simulation.initialization --add-position --run "my_run" --market-id "0x456" --market-name "Biden Wins" --shares 200 --price 0.45 --allow-negative
    
    # Sell position
    python -m src.simulation.initialization --sell-position --run "my_run" --market-id "0x123" --shares 50 --price 0.70
    
    # Update market prices from JSON file
    python -m src.simulation.initialization --update-prices --run "my_run" --price-file "prices.json"
    
    # Update market prices from command line
    python -m src.simulation.initialization --update-prices --run "my_run" --price-data '{"0x123": 0.75, "0x456": 0.40}'
    
    # Add balance to a run
    python -m src.simulation.initialization --add-balance --run "my_run" --amount 1000 --description "Additional funding"
    
    # Remove balance from a run
    python -m src.simulation.initialization --remove-balance --run "my_run" --amount 500 --description "Withdrawal"
    
    # Remove balance allowing negative balance
    python -m src.simulation.initialization --remove-balance --run "my_run" --amount 2000 --allow-negative --description "Emergency withdrawal"
    
    # Create a market
    python -m src.simulation.initialization --create-market --run "my_run" --market-id "0x123abc" --market-name "Trump Wins 2024" --category "prediction" --initial-price 0.65 --bid-price 0.64 --ask-price 0.66
    
    # Update market prices (new format with bid/ask)
    python -m src.simulation.initialization --update-prices --run "my_run" --price-data '{"0x123abc": {"price": 0.70, "bid": 0.69, "ask": 0.71}}'
        """
    )
    
    # Main action group
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--create', action='store_true', help='Create a new simulation run')
    action_group.add_argument('--list', action='store_true', help='List all simulation runs')
    action_group.add_argument('--info', metavar='RUN_NAME', help='Get information about a specific run')
    action_group.add_argument('--add-position', action='store_true', help='Add a position to an existing run')
    action_group.add_argument('--sell-position', action='store_true', help='Sell shares from an existing position')
    action_group.add_argument('--update-prices', action='store_true', help='Update market prices for positions')
    action_group.add_argument('--add-balance', action='store_true', help='Add balance to an existing run')
    action_group.add_argument('--remove-balance', action='store_true', help='Remove balance from an existing run')
    action_group.add_argument('--create-market', action='store_true', help='Create a new market in an existing run')
    
    # Arguments for creating runs
    parser.add_argument('--market', help='Market name for the simulation (required with --create)')
    parser.add_argument('--balance', type=float, help='Initial balance (required with --create)')
    parser.add_argument('--name', help='Custom run name (optional with --create)')
    
    # Arguments for adding positions
    parser.add_argument('--run', help='Run name (required with --add-position, --sell-position, --update-prices)')
    parser.add_argument('--market-id', help='Market ID (required with --add-position, --sell-position)')
    parser.add_argument('--market-name', help='Market name (required with --add-position)')
    parser.add_argument('--shares', type=float, help='Number of shares (required with --add-position, --sell-position)')
    parser.add_argument('--price', type=float, help='Price per share (required with --add-position, --sell-position)')
    parser.add_argument('--allow-negative', action='store_true', help='Allow negative balance (optional with --add-position)')
    
    # Arguments for price updates
    parser.add_argument('--price-file', help='JSON file with price updates: {"market_id": price} (required with --update-prices)')
    parser.add_argument('--price-data', help='JSON string with price updates (alternative to --price-file)')
    
    # Arguments for balance management
    parser.add_argument('--amount', type=float, help='Amount to add or remove (required with --add-balance, --remove-balance)')
    parser.add_argument('--description', help='Description for the transaction (optional with --add-balance, --remove-balance)')
    
    # Arguments for creating markets
    parser.add_argument('--category', help='Market category (required with --create-market)')
    parser.add_argument('--initial-price', type=float, help='Initial market price (required with --create-market)')
    parser.add_argument('--bid-price', type=float, help='Initial bid price (required with --create-market)')
    parser.add_argument('--ask-price', type=float, help='Initial ask price (required with --create-market)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize the run manager
    initializer = RunInitializer()
    
    try:
        if args.create:
            # Validate required arguments
            if not args.market or args.balance is None:
                parser.error("--create requires --market and --balance")
            
            print(f"🚀 Creating new simulation run for '{args.market}'...")
            run_info = initializer.create_new_run(
                market_name=args.market,
                initial_balance=args.balance,
                run_name=args.name
            )
            print(f"✅ Run created successfully: {run_info['run_name']}")
            
        elif args.list:
            runs = initializer.list_runs()
            if runs:
                print(f"📁 Found {len(runs)} simulation runs:")
                for run in runs:
                    print(f"   • {run}")
            else:
                print("📁 No simulation runs found.")
                
        elif args.info:
            run_data = initializer.get_run_info(args.info)
            if run_data:
                print(f"📊 Run Information: {args.info}")
                print(f"   Market: {run_data['whole_market_name']}")
                print(f"   Run ID: {run_data['run_id']}")
                print(f"   Started: {run_data['start_time']}")
                print(f"   Initial Balance: ${run_data['initial_balance']:,.2f}")
                print(f"   Current Balance: ${run_data['current_balance']:,.2f}")
                print(f"   Balance of Shares (Market Value): ${run_data['balance_of_shares']:,.2f}")
                print(f"   Balance Invested: ${run_data.get('balance_invested', 0):,.2f}")
                print(f"   Total Balance: ${run_data['total_balance']:,.2f}")
                print(f"   Positions: {len(run_data['positions'])}")
                print(f"   Transactions: {len(run_data['transactions'])}")
                print(f"   Markets: {len(run_data.get('markets', []))}")
            else:
                print(f"❌ Run '{args.info}' not found.")
                sys.exit(1)
                
        elif args.add_position:
            # Validate required arguments
            required_args = [args.run, args.market_id, args.shares]
            if any(arg is None for arg in required_args):
                parser.error("--add-position requires --run, --market-id, and --shares")
            
            print(f"📈 Adding position to run '{args.run}'...")
            success = initializer.add_position(
                run_name=args.run,
                market_id=args.market_id,
                num_shares=args.shares,
                allow_negative_balance=args.allow_negative
            )
            
            if success:
                print("✅ Position added successfully!")
            else:
                print("❌ Failed to add position.")
                sys.exit(1)
                
        elif args.sell_position:
            # Validate required arguments
            required_args = [args.run, args.market_id, args.shares]
            if any(arg is None for arg in required_args):
                parser.error("--sell-position requires --run, --market-id, and --shares")
            
            print(f"📉 Selling position from run '{args.run}'...")
            success = initializer.sell_position(
                run_name=args.run,
                market_id=args.market_id,
                num_shares=args.shares
            )
            
            if success:
                print("✅ Position sold successfully!")
            else:
                print("❌ Failed to sell position.")
                sys.exit(1)
                
        elif args.update_prices:
            # Validate required arguments
            if not args.run or (not args.price_file and not args.price_data):
                parser.error("--update-prices requires --run and either --price-file or --price-data")
            
            try:
                import json
                if args.price_file:
                    with open(args.price_file, 'r') as f:
                        price_updates = json.load(f)
                else:
                    price_updates = json.loads(args.price_data)
                
                print(f"📊 Updating market prices for run '{args.run}'...")
                success = initializer.update_market_prices(
                    run_name=args.run,
                    price_updates=price_updates
                )
                
                if success:
                    print("✅ Prices updated successfully!")
                else:
                    print("❌ Failed to update prices.")
                    sys.exit(1)
                    
            except json.JSONDecodeError:
                print("❌ Invalid JSON format in price data.")
                sys.exit(1)
            except FileNotFoundError:
                print(f"❌ Price file '{args.price_file}' not found.")
                sys.exit(1)
                
        elif args.add_balance:
            # Validate required arguments
            if not args.run or args.amount is None:
                parser.error("--add-balance requires --run and --amount")
            
            description = args.description or "Manual balance addition"
            print(f"💰 Adding ${args.amount:,.2f} to run '{args.run}'...")
            success = initializer.add_balance(
                run_name=args.run,
                amount=args.amount,
                description=description
            )
            
            if success:
                print("✅ Balance added successfully!")
            else:
                print("❌ Failed to add balance.")
                sys.exit(1)
                
        elif args.remove_balance:
            # Validate required arguments
            if not args.run or args.amount is None:
                parser.error("--remove-balance requires --run and --amount")
            
            description = args.description or "Manual balance removal"
            print(f"💸 Removing ${args.amount:,.2f} from run '{args.run}'...")
            success = initializer.remove_balance(
                run_name=args.run,
                amount=args.amount,
                description=description,
                allow_negative=args.allow_negative
            )
            
            if success:
                print("✅ Balance removed successfully!")
            else:
                print("❌ Failed to remove balance.")
                sys.exit(1)
                
        elif args.create_market:
            # Validate required arguments
            if not args.run or not args.market_id or not args.market_name or not args.category or args.initial_price is None or args.bid_price is None or args.ask_price is None:
                parser.error("--create-market requires --run, --market-id, --market-name, --category, --initial-price, --bid-price, and --ask-price")
            
            description = args.description or f"Market for {args.market_name}"
            print(f"🏦 Creating new market in run '{args.run}'...")
            success = initializer.create_market(
                run_name=args.run,
                market_id=args.market_id,
                market_name=args.market_name,
                description=description,
                category=args.category,
                initial_price=args.initial_price,
                bid_price=args.bid_price,
                ask_price=args.ask_price
            )
            
            if success:
                print("✅ Market created successfully!")
            else:
                print("❌ Failed to create market.")
                sys.exit(1)
                
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 