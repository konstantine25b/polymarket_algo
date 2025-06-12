#!/usr/bin/env python3

"""
Command-line interface for the simulation bidding strategy.

Usage examples:
    python -m src.simulation.bidding_decision.strategy_1 --run test_run --threshold 3.0 --amount 25.0
    python -m src.simulation.bidding_decision.strategy_1 --run test_run --algorithm ensemble --random-seed 42
    python -m src.simulation.bidding_decision.strategy_1 --sell test_run --threshold 2.0 --auto-sell --algorithm enhanced_facebook_prophet
    python -m src.simulation.bidding_decision.strategy_1 --analyze test_run --debug --algorithm neural_prophet
"""

import argparse
import sys
import logging
from .simulation_bidder import SimulationBidder
from .simulation_seller import SimulationSeller

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Simulation Bidding Strategy - Execute bidding/selling decisions on simulated runs"
    )
    
    # Primary action commands (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        '--run', 
        metavar='RUN_NAME',
        help='Execute bidding strategy on the specified simulation run'
    )
    action_group.add_argument(
        '--sell', 
        metavar='RUN_NAME',
        help='Analyze and show selling opportunities for the specified simulation run'
    )
    action_group.add_argument(
        '--analyze', 
        metavar='RUN_NAME',
        help='Analyze opportunities and positions without executing any trades'
    )
    action_group.add_argument(
        '--analyze-opportunities',
        action='store_true',
        help='Analyze current market opportunities without any simulation run'
    )
    
    # Algorithm parameters
    parser.add_argument(
        '--algorithm', 
        type=str, 
        default='enhanced_facebook_prophet',
        help='Prediction algorithm to use: prophet, facebook_prophet, enhanced_facebook_prophet, '
             'neural_prophet, enhanced_neural_prophet, timesfm, enhanced_timesfm, ensemble '
             '(default: enhanced_facebook_prophet)'
    )
    parser.add_argument(
        '--random-seed', 
        type=int, 
        default=42,
        help='Random seed for reproducible results (default: 42)'
    )
    
    # Bidding/opportunity parameters
    parser.add_argument(
        '--threshold', 
        type=float, 
        default=0.0,
        metavar='PERCENT',
        help='Minimum opportunity percentage required (default: 0.0%%)'
    )
    parser.add_argument(
        '--amount', 
        type=float, 
        default=10.0,
        metavar='DOLLARS',
        help='Order amount in USD (default: $10.00)'
    )
    parser.add_argument(
        '--weighted-selection', 
        action='store_true',
        help='Use weighted selection instead of highest opportunity'
    )
    parser.add_argument(
        '--min-prediction', 
        type=float, 
        default=0.0,
        metavar='PERCENT',
        help='Minimum prediction percentage required (default: 0.0%%)'
    )
    
    # Selling parameters
    parser.add_argument(
        '--sell-below', 
        type=float, 
        default=0.0,
        metavar='PERCENT',
        help='Sell positions with prediction below this percentage (default: 0.0%%)'
    )
    parser.add_argument(
        '--auto-sell', 
        action='store_true',
        help='Automatically execute sell orders for recommended positions'
    )
    parser.add_argument(
        '--active-market-only', 
        action='store_true',
        help='Only sell positions for the active market (current time frame)'
    )
    
    # Market update options
    parser.add_argument(
        '--no-update', 
        action='store_true',
        help='Skip updating market prices from Polymarket'
    )
    parser.add_argument(
        '--update-only', 
        action='store_true',
        help='Only update market prices, do not place any orders'
    )
    
    # Execution options
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would happen without executing any trades'
    )
    parser.add_argument(
        '--no-stats', 
        action='store_true',
        help='Skip displaying the full comparison table'
    )
    
    # Debug and display options
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='Enable detailed debugging output'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--quiet', 
        action='store_true',
        help='Reduce output to essential information only'
    )
    
    args = parser.parse_args()
    
    # Set logging level based on options
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif args.verbose or args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Handle different action types
        if args.run:
            # Execute bidding strategy
            bidder = SimulationBidder(
                threshold=args.threshold,
                order_amount=args.amount,
                use_weighted_selection=args.weighted_selection,
                min_prediction=args.min_prediction,
                algorithm=args.algorithm,
                random_seed=args.random_seed,
                debug=args.debug
            )
            
            if args.update_only:
                # Only update markets, don't place orders
                print(f"Updating markets for simulation run: {args.run}")
                success = bidder.update_simulation_markets(args.run)
                if success:
                    print("✅ Market update completed successfully")
                else:
                    print("❌ Market update failed")
                sys.exit(0 if success else 1)
            
            # Execute full bidding strategy
            update_markets = not args.no_update
            show_stats = not args.no_stats
            
            print(f"🎯 Executing bidding strategy on simulation run: {args.run}")
            print(f"Using prediction algorithm: {args.algorithm} with random seed: {args.random_seed}")
            if args.dry_run:
                print("🔍 DRY RUN MODE - No actual trades will be executed")
            
            print(f"Parameters: threshold={args.threshold}%, amount=${args.amount}, " +
                  f"weighted_selection={args.weighted_selection}, min_prediction={args.min_prediction}%")
            
            success = bidder.auto_bid_simulation(
                run_name=args.run,
                update_markets=update_markets,
                dry_run=args.dry_run,
                show_stats=show_stats
            )
            
            sys.exit(0 if success else 1)
            
        elif args.sell:
            # Execute selling strategy - now matches real auto_bid behavior
            seller = SimulationSeller(
                threshold=args.threshold,
                sell_below=args.sell_below,
                algorithm=args.algorithm,
                random_seed=args.random_seed,
                debug=args.debug,
                active_market_only=args.active_market_only
            )
            
            if args.update_only:
                # Only update markets, don't sell positions
                print(f"Updating markets for simulation run: {args.sell}")
                success = seller.run_initializer.update_markets_from_polymarket(args.sell)
                if success:
                    print("✅ Market update completed successfully")
                else:
                    print("❌ Market update failed")
                sys.exit(0 if success else 1)
            
            # Always update markets first (like real auto_bid)
            update_markets = not args.no_update
            show_stats = not args.no_stats
            
            print(f"💰 Executing selling strategy on simulation run: {args.sell}")
            if args.dry_run:
                print("🔍 DRY RUN MODE - No actual trades will be executed")
            
            print(f"Parameters: threshold={args.threshold}%, sell_below={args.sell_below}%")
            if args.active_market_only:
                print("Filtering for active market only")
            
            # Execute the selling strategy with proper table display and market updates
            success = seller.execute_selling_strategy(
                run_name=args.sell,
                update_markets=update_markets,
                show_stats=show_stats,
                auto_sell=args.auto_sell,
                dry_run=args.dry_run
            )
            
            sys.exit(0 if success else 1)
            
        elif args.analyze:
            # Analyze positions and opportunities for a specific run
            update_markets = not args.no_update
            
            print(f"📊 Analyzing simulation run: {args.analyze}")
            
            # Analyze with both bidder and seller
            bidder = SimulationBidder(
                threshold=args.threshold,
                order_amount=args.amount,
                use_weighted_selection=args.weighted_selection,
                min_prediction=args.min_prediction,
                algorithm=args.algorithm,
                random_seed=args.random_seed,
                debug=args.debug
            )
            
            seller = SimulationSeller(
                threshold=args.threshold,
                sell_below=args.sell_below,
                algorithm=args.algorithm,
                random_seed=args.random_seed,
                debug=args.debug,
                active_market_only=args.active_market_only
            )
            
            # Show opportunities analysis
            print("\n" + "="*80)
            print("OPPORTUNITY ANALYSIS")
            print("="*80)
            
            show_stats = not args.no_stats
            df = bidder.analyze_opportunities(update_markets=update_markets, show_stats=show_stats)
            
            # Show position analysis
            print("\n" + "="*80)
            print("POSITION ANALYSIS")
            print("="*80)
            
            success = seller.analyze_positions(args.analyze, update_markets=False)  # Already updated above
            
            sys.exit(0 if success else 1)
            
        elif args.analyze_opportunities:
            # Analyze market opportunities without any simulation run
            bidder = SimulationBidder(
                threshold=args.threshold,
                order_amount=args.amount,
                use_weighted_selection=args.weighted_selection,
                min_prediction=args.min_prediction,
                algorithm=args.algorithm,
                random_seed=args.random_seed,
                debug=args.debug
            )
            
            print("📊 Analyzing current market opportunities")
            print(f"Parameters: threshold={args.threshold}%, min_prediction={args.min_prediction}%")
            
            update_markets = not args.no_update
            show_stats = not args.no_stats
            
            df = bidder.analyze_opportunities(update_markets=update_markets, show_stats=show_stats)
            
            if df is not None:
                print("✅ Opportunity analysis completed")
            else:
                print("❌ No opportunities found or analysis failed")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 