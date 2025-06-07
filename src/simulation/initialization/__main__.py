#!/usr/bin/env python3
"""
Command-line interface for simulation run initialization.

Usage examples:
    python -m src.simulation.initialization --create --market-name "Election Prediction" --balance 1000
    python -m src.simulation.initialization --list
    python -m src.simulation.initialization --info test_run
    python -m src.simulation.initialization --init-markets-from-polymarket test_run
"""

import argparse
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.simulation.initialization.run_initializer import RunInitializer


def main():
    parser = argparse.ArgumentParser(
        description="Initialize and manage Polymarket simulation runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Create new run:
    python -m src.simulation.initialization --create --market-name "Election Prediction" --balance 1000

  List all runs:
    python -m src.simulation.initialization --list

  Get run info:
    python -m src.simulation.initialization --info my_run

  Initialize markets from Polymarket:
    python -m src.simulation.initialization --init-markets-from-polymarket my_run

  Update markets from Polymarket:
    python -m src.simulation.initialization --update-markets-from-polymarket my_run

  Add position:
    python -m src.simulation.initialization --add-position my_run market123 100

  Sell position:
    python -m src.simulation.initialization --sell-position my_run market123 50

  Update prices:
    python -m src.simulation.initialization --update-prices my_run market123 0.75 0.74 0.76

  Add balance:
    python -m src.simulation.initialization --add-balance my_run 500

  Remove balance:
    python -m src.simulation.initialization --remove-balance my_run 200
        """
    )
    
    # Main commands
    parser.add_argument('--create', action='store_true', help='Create a new simulation run')
    parser.add_argument('--list', action='store_true', help='List all simulation runs')
    parser.add_argument('--info', metavar='RUN_NAME', help='Get information about a run')
    parser.add_argument('--init-markets-from-polymarket', metavar='RUN_NAME', 
                       help='Initialize markets for a run using real Polymarket data')
    parser.add_argument('--update-markets-from-polymarket', metavar='RUN_NAME', 
                       help='Update existing market prices using real Polymarket data')
    
    # Position management
    parser.add_argument('--add-position', nargs=3, metavar=('RUN_NAME', 'MARKET_ID', 'NUM_SHARES'),
                       help='Add position to a run')
    parser.add_argument('--sell-position', nargs=3, metavar=('RUN_NAME', 'MARKET_ID', 'NUM_SHARES'),
                       help='Sell position from a run')
    
    # Price updates
    parser.add_argument('--update-prices', nargs=5, metavar=('RUN_NAME', 'MARKET_ID', 'PRICE', 'BID', 'ASK'),
                       help='Update market prices')
    
    # Balance management
    parser.add_argument('--add-balance', nargs=2, metavar=('RUN_NAME', 'AMOUNT'),
                       help='Add balance to a run')
    parser.add_argument('--remove-balance', nargs=2, metavar=('RUN_NAME', 'AMOUNT'),
                       help='Remove balance from a run')
    
    # Options for --create
    parser.add_argument('--market-name', metavar='NAME', 
                       help='Market name for new run (required with --create)')
    parser.add_argument('--balance', type=float, default=0.0,
                       help='Initial balance for new run (default: 0)')
    parser.add_argument('--run-name', metavar='NAME',
                       help='Custom name for new run (default: auto-generated)')
    
    # Options for market initialization
    parser.add_argument('--category', default='prediction', 
                       help='Category for initialized markets (default: prediction)')
    
    # General options
    parser.add_argument('--allow-negative', action='store_true',
                       help='Allow negative balance in transactions')
    parser.add_argument('--description', default='',
                       help='Description for balance transactions')
    
    args = parser.parse_args()
    
    # Check if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    initializer = RunInitializer()
    
    # Handle different commands
    if args.create:
        if not args.market_name:
            print("❌ --market-name is required when creating a new run")
            sys.exit(1)
        
        result = initializer.create_new_run(
            market_name=args.market_name,
            initial_balance=args.balance,
            run_name=args.run_name
        )
        
    elif args.list:
        runs = initializer.list_runs()
        if runs:
            print(f"📋 Found {len(runs)} simulation runs:")
            for run in runs:
                print(f"   📁 {run}")
        else:
            print("📋 No simulation runs found")
    
    elif args.info:
        run_data = initializer.get_run_info(args.info)
        if run_data:
            print(f"📊 Run Information: {args.info}")
            print(f"   🆔 Run ID: {run_data.get('run_id', 'N/A')}")
            print(f"   🏪 Market: {run_data.get('whole_market_name', 'N/A')}")
            print(f"   📅 Start Time: {run_data.get('start_time', 'N/A')}")
            print(f"   💰 Current Balance: ${run_data.get('current_balance', 0):,.2f}")
            print(f"   💵 Initial Balance: ${run_data.get('initial_balance', 0):,.2f}")
            print(f"   📈 Total Balance: ${run_data.get('total_balance', 0):,.2f}")
            print(f"   📊 Balance of Shares: ${run_data.get('balance_of_shares', 0):,.2f}")
            print(f"   💼 Balance Invested: ${run_data.get('balance_invested', 0):,.2f}")
            
            # Display new portfolio metrics
            win_loss_pct = run_data.get('win_loss_percentage', 0)
            win_loss_if_sold_pct = run_data.get('win_loss_percentage_if_sold_now', 0)
            total_if_sold = run_data.get('total_balance_if_all_positions_sold', 0)
            
            print(f"   📈 Win/Loss %: {win_loss_pct:+.2f}% (market prices)")
            print(f"   💰 Win/Loss % if sold now: {win_loss_if_sold_pct:+.2f}% (bid prices)")
            print(f"   🏦 Total balance if all sold: ${total_if_sold:,.2f}")
            
            markets = run_data.get('markets', [])
            positions = run_data.get('positions', [])
            transactions = run_data.get('transactions', [])
            
            print(f"   🏪 Markets: {len(markets)}")
            print(f"   📈 Positions: {len(positions)}")
            print(f"   💳 Transactions: {len(transactions)}")
            
            if positions:
                print(f"\n   📊 Active Positions:")
                for pos in positions:
                    if pos.get('position_status') == 'ACTIVE' and pos.get('num_shares', 0) > 0:
                        win_loss = pos.get('win_loss_percentage', 0)
                        win_loss_str = f"{win_loss:+.2f}%" if win_loss != 0 else "0.00%"
                        print(f"      • {pos.get('market_name', 'Unknown')}: {pos.get('num_shares', 0)} shares")
                        print(f"        💰 Invested: ${pos.get('total_invested', 0):,.2f}")
                        print(f"        📊 Current Value: ${pos.get('current_total_price', 0):,.2f}")
                        print(f"        📈 P&L: {win_loss_str}")
        else:
            print(f"❌ Run '{args.info}' not found")
    
    elif args.init_markets_from_polymarket:
        success = initializer.initialize_markets_from_polymarket(
            run_name=args.init_markets_from_polymarket,
            category=args.category
        )
        if not success:
            sys.exit(1)
    
    elif args.update_markets_from_polymarket:
        success = initializer.update_markets_from_polymarket(
            run_name=args.update_markets_from_polymarket
        )
        if not success:
            sys.exit(1)
    
    elif args.add_position:
        run_name, market_id, num_shares_str = args.add_position
        try:
            num_shares = float(num_shares_str)
            success = initializer.add_position(
                run_name=run_name,
                market_id=market_id,
                num_shares=num_shares,
                allow_negative_balance=args.allow_negative
            )
            if not success:
                sys.exit(1)
        except ValueError:
            print(f"❌ Invalid number of shares: {num_shares_str}")
            sys.exit(1)
    
    elif args.sell_position:
        run_name, market_id, num_shares_str = args.sell_position
        try:
            num_shares = float(num_shares_str)
            success = initializer.sell_position(
                run_name=run_name,
                market_id=market_id,
                num_shares=num_shares
            )
            if not success:
                sys.exit(1)
        except ValueError:
            print(f"❌ Invalid number of shares: {num_shares_str}")
            sys.exit(1)
    
    elif args.update_prices:
        run_name, market_id, price_str, bid_str, ask_str = args.update_prices
        try:
            price = float(price_str)
            bid = float(bid_str)
            ask = float(ask_str)
            
            price_updates = {
                market_id: {
                    "price": price,
                    "bid": bid,
                    "ask": ask
                }
            }
            
            success = initializer.update_market_prices(
                run_name=run_name,
                price_updates=price_updates
            )
            if not success:
                sys.exit(1)
        except ValueError:
            print(f"❌ Invalid prices. All values must be numeric.")
            sys.exit(1)
    
    elif args.add_balance:
        run_name, amount_str = args.add_balance
        try:
            amount = float(amount_str)
            description = args.description if args.description else "Manual balance addition"
            success = initializer.add_balance(
                run_name=run_name,
                amount=amount,
                description=description
            )
            if not success:
                sys.exit(1)
        except ValueError:
            print(f"❌ Invalid amount: {amount_str}")
            sys.exit(1)
    
    elif args.remove_balance:
        run_name, amount_str = args.remove_balance
        try:
            amount = float(amount_str)
            description = args.description if args.description else "Manual balance removal"
            success = initializer.remove_balance(
                run_name=run_name,
                amount=amount,
                description=description,
                allow_negative=args.allow_negative
            )
            if not success:
                sys.exit(1)
        except ValueError:
            print(f"❌ Invalid amount: {amount_str}")
            sys.exit(1)
    
    else:
        print("❌ No valid command specified. Use --help for usage information.")
        sys.exit(1)


if __name__ == "__main__":
    main() 