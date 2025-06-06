#!/usr/bin/env python3
"""
Scheduler for automating tweet fetching and prediction tasks.

This module provides functionality to periodically:
1. Fetch Elon Musk's tweets and store them in the database
2. Run the Polymarket predictor to update predictions
3. Run the auto-bidder to place orders based on statistical opportunities
4. Add the auto-seller to place sell orders based on statistical opportunities
5. Run simulation mode using the simulation framework

Usage:
    python -m src.scheduler.scheduler [options]

Options:
    --interval MINUTES     Set the interval between runs (default: 20 minutes)
    --tweet-interval MINUTES Interval between tweet fetching runs in minutes (overrides global interval)
    --buy-interval MINUTES  Interval between auto-bidder runs in minutes (overrides global interval)
    --sell-interval MINUTES Interval between auto-seller runs in minutes (overrides global interval)
    --tweets-only          Only run the tweet fetching job
    --predictions-only     Only run the prediction job
    --max-tweets N         Set maximum number of tweets to fetch (default: 40)
    --no-debug             Disable debug mode for tweet fetching
    --run-once             Run jobs once and exit
    --quiet                Reduce output verbosity
    --no-incremental       Disable incremental fetching (not recommended)
    --initial-batch N      Initial batch size for incremental fetching (default: 40)
    --max-batch N          Maximum batch size for incremental fetching (default: 200)
    --no-prophet           Disable Prophet algorithm for predictions (use standard algorithm instead)
    --no-bidding           Don't run the auto-bidder
    --no-selling           Don't run the auto-seller
    --no-buy               Run auto-bidder but don't execute buy orders (show opportunities only)
    --no-sell              Run auto-seller but don't execute sell orders (show opportunities only)
    --buy-threshold FLOAT  Minimum opportunity percentage to place buy orders (default: 0.0)
    --sell-threshold FLOAT Minimum opportunity percentage to place sell orders (default: 0.0)
    --amount FLOAT         Amount to bid in USDC (default: 1.0)
    --dry-run              Run auto-bidder and auto-seller in dry run mode (don't place real orders)
    --no-stats             Don't show full statistics table
    --weighted-selection   Use weighted selection for buy opportunities instead of choosing the best
    --skip-balance-check   Skip checking wallet balance before running auto-bidder
    --min-usdc FLOAT       Minimum USDC balance required to run auto-bidder (default: 1.0)
    --no-tweet-verify      Skip verifying and displaying tweet counts after fetching
    --sell-below FLOAT     Automatically sell positions with prediction below this percentage (default: 0.0)
    --min-prediction FLOAT Only bid on opportunities with prediction percentage at or above this value (default: 0.0)
    --debug-seller         Show detailed debugging information for position seller
    --use-csv-getter       Use TweetCSVGetter instead of Apify for fetching tweets
    --get-tweet-count-first Get tweet count from website before fetching and verify database count after fetching
    --max-count-retries    Maximum number of retries for tweet count retrieval (default: 3)
    --show-positions       Show all current positions when running
    --show-active-positions Show positions for active market when running
    --simulate RUN_NAME    Run in simulation mode using the specified simulation run
    --strategy STRATEGY    Strategy to use for simulation (default: strategy_1)
    --sim-balance FLOAT    Initial balance for new simulation runs (default: 1000.0)
"""

import argparse
import time
import subprocess
import sys
import logging
import datetime
import os
import re
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(__file__).parent.parent / "logs" / "scheduler.log"
        )
    ]
)
logger = logging.getLogger("tweet_scheduler")

def setup_argparse():
    """Set up command line argument parsing."""
    parser = argparse.ArgumentParser(description='Schedule tweet fetching and prediction jobs')
    parser.add_argument('--interval', type=int, default=20,
                        help='Global interval between runs in minutes (default: 20)')
    parser.add_argument('--tweet-interval', type=int, default=None,
                        help='Interval between tweet fetching runs in minutes (overrides global interval)')
    parser.add_argument('--buy-interval', type=int, default=None,
                        help='Interval between auto-bidder runs in minutes (overrides global interval)')
    parser.add_argument('--sell-interval', type=int, default=None,
                        help='Interval between auto-seller runs in minutes (overrides global interval)')
    parser.add_argument('--tweets-only', action='store_true',
                        help='Only run the tweet fetching job')
    parser.add_argument('--predictions-only', action='store_true',
                        help='Only run the prediction job')
    parser.add_argument('--max-tweets', type=int, default=40,
                        help='Maximum number of tweets to fetch (default: 40)')
    parser.add_argument('--no-debug', action='store_true',
                        help='Disable debug mode for tweet fetching')
    parser.add_argument('--run-once', action='store_true',
                        help='Run jobs once and exit')
    parser.add_argument('--quiet', action='store_true',
                        help='Reduce output verbosity')
    parser.add_argument('--no-incremental', action='store_true',
                        help='Disable incremental fetching (not recommended)')
    parser.add_argument('--initial-batch', type=int, default=40,
                        help='Initial batch size for incremental fetching (default: 40)')
    parser.add_argument('--max-batch', type=int, default=200,
                        help='Maximum batch size for incremental fetching (default: 200)')
    parser.add_argument('--no-prophet', action='store_true',
                        help='Disable Prophet algorithm for predictions (use standard algorithm instead)')
    parser.add_argument('--no-bidding', action='store_true',
                        help="Don't run the auto-bidder")
    parser.add_argument('--no-selling', action='store_true',
                        help="Don't run the auto-seller")
    parser.add_argument('--no-buy', action='store_true',
                        help="Run auto-bidder but don't execute buy orders (show opportunities only)")
    parser.add_argument('--no-sell', action='store_true',
                        help="Run auto-seller but don't execute sell orders (show opportunities only)")
    parser.add_argument('--buy-threshold', type=float, default=0.0,
                        help='Minimum opportunity percentage to place buy orders (default: 0.0)')
    parser.add_argument('--sell-threshold', type=float, default=0.0,
                        help='Minimum opportunity percentage to place sell orders (default: 0.0)')
    parser.add_argument('--amount', type=float, default=1.0,
                        help='Amount to bid in USDC (default: 1.0)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run auto-bidder and auto-seller in dry run mode (don\'t place real orders)')
    parser.add_argument('--no-stats', action='store_true',
                        help="Don't show full statistics table")
    parser.add_argument('--weighted-selection', action='store_true',
                        help='Use weighted selection for buy opportunities instead of choosing the best')
    parser.add_argument('--skip-balance-check', action='store_true',
                        help='Skip checking wallet balance before running auto-bidder')
    parser.add_argument('--min-usdc', type=float, default=1.0,
                        help='Minimum USDC balance required to run auto-bidder (default: 1.0)')
    parser.add_argument('--no-tweet-verify', action='store_true',
                        help='Skip verifying and displaying tweet counts after fetching')
    parser.add_argument('--sell-below', type=float, default=0.0,
                        help='Automatically sell positions with prediction below this percentage (default: 0.0)')
    parser.add_argument('--min-prediction', type=float, default=0.0,
                        help='Only bid on opportunities with prediction percentage at or above this value (default: 0.0)')
    parser.add_argument('--debug-seller', action='store_true',
                        help='Show detailed debugging information for position seller')
    parser.add_argument('--use-csv-getter', action='store_true',
                        help='Use TweetCSVGetter instead of Apify for fetching tweets')
    parser.add_argument('--get-tweet-count-first', action='store_true',
                        help='Get tweet count from website before fetching and verify database count after fetching')
    parser.add_argument('--max-count-retries', type=int, default=3,
                        help='Maximum number of retries for tweet count retrieval (default: 3)')
    parser.add_argument('--show-positions', action='store_true',
                        help='Show all current positions when running')
    parser.add_argument('--show-active-positions', action='store_true',
                        help='Show positions for active market when running')
    parser.add_argument('--simulate', type=str, default=None,
                        help='Run in simulation mode using the specified simulation run')
    parser.add_argument('--strategy', type=str, default='strategy_1',
                        help='Strategy to use for simulation (default: strategy_1)')
    parser.add_argument('--sim-balance', type=float, default=1000.0,
                        help='Initial balance for new simulation runs (default: 1000.0)')
    return parser.parse_args()

def fetch_tweets(max_tweets=40, debug=True, quiet=False, use_incremental=True, initial_batch=40, max_batch=200):
    """Fetch tweets and store them in the database."""
    logger.info(f"Starting tweet fetching job at {datetime.datetime.now()}")
    
    # Base command with the recommended configuration
    cmd = [
        sys.executable, "-m", "src.apify.get_elon_tweets",
        "--max-tweets", str(max_tweets),
        "--use-client",
        "--add-to-db"
    ]
    
    if debug:
        cmd.append("--debug")
    
    # Use incremental fetching by default (unless explicitly disabled)
    if use_incremental:
        cmd.append("--incremental")
        cmd.extend(["--initial-batch", str(initial_batch)])
        cmd.extend(["--max-batch", str(max_batch)])
        cmd.extend(["--batch-increment", "20"])  # Use default increment
        cmd.extend(["--incremental-attempts", "3"])  # Reasonable default
        logger.info("Using incremental fetching for reliable tweet collection")
    else:
        logger.warning("Incremental fetching is disabled - this may result in gaps in the tweet timeline")
    
    try:
        if quiet:
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                logger.error(f"Tweet fetching failed with error: {process.stderr.decode()}")
            else:
                logger.info("Tweet fetching completed successfully")
        else:
            process = subprocess.run(cmd)
            if process.returncode != 0:
                logger.error("Tweet fetching failed")
            else:
                logger.info("Tweet fetching completed successfully")
    except Exception as e:
        logger.error(f"Error running tweet fetching: {e}")
        return False
    
    return process.returncode == 0

def get_polymarket_tweet_count(max_retries=3):
    """Get the current tweet count from Polymarket website.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        int: The current tweet count or -1 if retrieval failed after all retries
    """
    logger.info(f"Getting tweet count from Polymarket (max retries: {max_retries})...")
    
    cmd = [sys.executable, "-m", "src.xpath_scraper.NumberGetter"]
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt}/{max_retries} to get tweet count")
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode != 0:
                logger.warning(f"Attempt {attempt}/{max_retries} failed with error: {process.stderr}")
                if attempt < max_retries:
                    logger.info(f"Retrying in 3 seconds...")
                    time.sleep(3)
                    continue
                else:
                    logger.error(f"All {max_retries} attempts to get tweet count failed")
                    return -1
            
            output = process.stdout
            # Extract the tweet count using regex
            match = re.search(r"Tweet count: (\d+)", output)
            if match:
                count = int(match.group(1))
                logger.info(f"Retrieved tweet count from Polymarket: {count}")
                return count
            else:
                logger.warning(f"Attempt {attempt}/{max_retries}: Failed to parse tweet count from output: {output}")
                if attempt < max_retries:
                    logger.info(f"Retrying in 3 seconds...")
                    time.sleep(3)
                    continue
                else:
                    logger.error(f"All {max_retries} attempts to parse tweet count failed")
                    return -1
                    
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{max_retries}: Error getting tweet count: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in 3 seconds...")
                time.sleep(3)
                continue
            else:
                logger.error(f"All {max_retries} attempts to get tweet count failed with exception: {e}")
                return -1
    
    return -1

def verify_tweet_count(quiet=False):
    """Verify and display the tweet count for the current market week.
    
    This runs a simplified version of the tweet_predictor --verify-count command
    to show the total number of tweets for the current market week and the daily breakdown.
    
    Args:
        quiet: Whether to suppress output
    
    Returns:
        bool: Whether the verification was successful
        int: The total tweet count from the database or -1 if not found
    """
    logger.info("Verifying tweet count for current market week...")
    
    # Add --no-cache flag to force fresh data loading
    cmd = [sys.executable, "-m", "src.polymarket_predictor.tweet_predictor", "--verify-count", "--no-cache"]
    
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if process.returncode != 0:
            logger.error(f"Tweet count verification failed with error: {process.stderr}")
            return False, -1
        
        # Extract and display the relevant information about tweet counts
        output = process.stdout
        
        # Parse the output to extract total tweet count and daily counts
        total_count = None
        daily_counts = []
        
        for line in output.split('\n'):
            if "Total tweets in range:" in line:
                total_count_str = line.split(":")[-1].strip()
                try:
                    total_count = int(total_count_str)
                    logger.info(f"Parsed total tweet count from database: {total_count}")
                except ValueError:
                    logger.error(f"Failed to parse tweet count as integer: '{total_count_str}'")
                    total_count = -1
            elif "tweets" in line and line.startswith("  202"):
                daily_counts.append(line.strip())
                logger.debug(f"Found daily count: {line.strip()}")
        
        # Display the tweet count information
        if total_count is not None:
            print("\n" + "=" * 50)
            print("TWEET COUNT VERIFICATION")
            print("=" * 50)
            print(f"Total tweets this week: {total_count}")
            print("\nDaily tweet counts:")
            for count in daily_counts:
                print(f"  {count}")
            print("=" * 50 + "\n")
            
            logger.info(f"Tweet count verification complete: {total_count} total tweets this week")
            logger.info(f"Daily breakdown: {len(daily_counts)} days with tweets")
            for count in daily_counts:
                logger.debug(f"  {count}")
            return True, total_count
        else:
            logger.warning("Could not extract tweet count information from verification output")
            logger.debug(f"Verification output: {output}")
            return False, -1
            
    except Exception as e:
        logger.error(f"Error verifying tweet count: {e}")
        return False, -1

def check_tweet_count_consistency():
    """Compare the tweet count from local DB with Polymarket website.
    
    Returns:
        tuple: (bool, int, int) - Whether counts match, DB count, Polymarket count
    """
    logger.info("Checking tweet count consistency between local DB and Polymarket...")
    
    # Get count from Polymarket website
    polymarket_count = get_polymarket_tweet_count()
    
    if polymarket_count == -1:
        logger.error("Failed to get tweet count from Polymarket website")
        return False, -1, -1
    
    # Just display the count for now, we'll compare in the verify_tweet_count function
    logger.info(f"Polymarket website tweet count: {polymarket_count}")
    
    return True, -1, polymarket_count

def run_prediction(quiet=False, use_prophet=True):
    """Run the Polymarket predictor to update predictions.
    
    Args:
        quiet: Whether to suppress output
        use_prophet: Whether to use the Prophet algorithm (default: True)
    """
    logger.info(f"Starting prediction job at {datetime.datetime.now()}")
    
    cmd = [sys.executable, "-m", "src.polymarket_predictor"]
    
    # Use Prophet algorithm by default
    if use_prophet:
        cmd.append("--prophet")
        logger.info("Using Prophet-based prediction algorithm")
    
    try:
        if quiet:
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                logger.error(f"Prediction failed with error: {process.stderr.decode()}")
            else:
                logger.info("Prediction completed successfully")
        else:
            process = subprocess.run(cmd)
            if process.returncode != 0:
                logger.error("Prediction failed")
            else:
                logger.info("Prediction completed successfully")
    except Exception as e:
        logger.error(f"Error running prediction: {e}")
        return False
    
    return process.returncode == 0

def check_wallet_balance():
    """Check the wallet's MATIC and USDC balance.
    
    Returns:
        dict: A dictionary containing wallet balance information
    """
    logger.info("Checking wallet balance...")
    
    cmd = [sys.executable, "-m", "src.polymarket.balance.balance_cli", "--json"]
    
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if process.returncode != 0:
            logger.error(f"Balance checking failed with error: {process.stderr}")
            return {"success": False, "error": process.stderr, "usdc_balance": 0, "matic_balance": 0}
        
        # Parse the JSON output
        import json
        balance_info = json.loads(process.stdout)
        
        # Log and return the balance info
        logger.info(f"Wallet balance: {balance_info['matic_balance']} MATIC, {balance_info['usdc_balance']} USDC")
        return balance_info
    except Exception as e:
        logger.error(f"Error checking wallet balance: {e}")
        return {"success": False, "error": str(e), "usdc_balance": 0, "matic_balance": 0}

def initialize_simulation_run(run_name, balance, strategy="strategy_1"):
    """Initialize a new simulation run if it doesn't exist.
    
    Args:
        run_name: Name of the simulation run
        balance: Initial balance for the simulation
        strategy: Strategy to use (default: strategy_1)
    
    Returns:
        bool: Whether initialization was successful
    """
    logger.info(f"Initializing simulation run: {run_name} with balance: ${balance}")
    
    # Check if run already exists
    check_cmd = [
        sys.executable, "-m", "src.simulation.initialization",
        "--info", run_name
    ]
    
    try:
        process = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Check if the output contains "not found" to determine if run exists
        if "not found" not in process.stdout:
            logger.info(f"Simulation run '{run_name}' already exists, skipping initialization")
            return True
    except Exception as e:
        logger.debug(f"Error checking existing run (expected if run doesn't exist): {e}")
    
    # Create new simulation run
    create_cmd = [
        sys.executable, "-m", "src.simulation.initialization",
        "--create", 
        "--market-name", f"Scheduler Simulation - {strategy}",
        "--balance", str(balance),
        "--run-name", run_name
    ]
    
    try:
        logger.info("Creating new simulation run...")
        process = subprocess.run(create_cmd)
        if process.returncode != 0:
            logger.error("Failed to create simulation run")
            return False
            
        logger.info("Simulation run created successfully")
    except Exception as e:
        logger.error(f"Error creating simulation run: {e}")
        return False
    
    # Initialize markets from Polymarket
    init_markets_cmd = [
        sys.executable, "-m", "src.simulation.initialization",
        "--init-markets-from-polymarket", run_name
    ]
    
    try:
        logger.info("Initializing markets from Polymarket...")
        process = subprocess.run(init_markets_cmd)
        if process.returncode != 0:
            logger.error("Failed to initialize markets")
            return False
            
        logger.info("Markets initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing markets: {e}")
        return False

def run_simulation_bidder(run_name, strategy="strategy_1", threshold=0.0, amount=1.0, dry_run=False, 
                         show_stats=True, weighted_selection=False, min_prediction=0.0, quiet=False):
    """Run the simulation bidder for the specified strategy.
    
    Args:
        run_name: Name of the simulation run
        strategy: Strategy to use (default: strategy_1)
        threshold: Minimum opportunity percentage to place bids
        amount: Amount to bid in USD
        dry_run: Whether to run in dry run mode
        show_stats: Whether to show full statistics table
        weighted_selection: Whether to use weighted selection
        min_prediction: Minimum prediction percentage required
        quiet: Whether to suppress output
    
    Returns:
        bool: Whether the bidding was successful
    """
    logger.info(f"Running simulation bidder for run '{run_name}' with strategy '{strategy}'")
    
    cmd = [
        sys.executable, "-m", f"src.simulation.bidding_decision.{strategy}",
        "--run", run_name,
        f"--threshold={threshold}",
        f"--amount={amount}"
    ]
    
    if dry_run:
        cmd.append("--dry-run")
        
    if not show_stats:
        cmd.append("--no-stats")
        
    if weighted_selection:
        cmd.append("--weighted-selection")
        
    if min_prediction > 0:
        cmd.append(f"--min-prediction={min_prediction}")
    
    try:
        if quiet and not dry_run:  # Always show output in dry run mode
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                logger.error(f"Simulation bidder failed with error: {process.stderr.decode()}")
            else:
                logger.info("Simulation bidder completed successfully")
                output = process.stdout.decode()
                print("\n" + output)
        else:
            process = subprocess.run(cmd)
            if process.returncode != 0:
                logger.error("Simulation bidder failed")
            else:
                logger.info("Simulation bidder completed successfully")
    except Exception as e:
        logger.error(f"Error running simulation bidder: {e}")
        return False
    
    return process.returncode == 0

def run_simulation_seller(run_name, strategy="strategy_1", threshold=0.0, sell_below=0.0, dry_run=False,
                         show_stats=True, debug=False, quiet=False):
    """Run the simulation seller for the specified strategy.
    
    Args:
        run_name: Name of the simulation run
        strategy: Strategy to use (default: strategy_1)
        threshold: Minimum opportunity percentage to sell positions
        sell_below: Sell positions with prediction below this percentage
        dry_run: Whether to run in dry run mode
        show_stats: Whether to show full statistics table
        debug: Whether to show detailed debugging information
        quiet: Whether to suppress output
    
    Returns:
        bool: Whether the selling was successful
    """
    logger.info(f"Running simulation seller for run '{run_name}' with strategy '{strategy}'")
    
    cmd = [
        sys.executable, "-m", f"src.simulation.bidding_decision.{strategy}",
        "--sell", run_name,
        f"--threshold={threshold}"
    ]
    
    if not dry_run:
        cmd.append("--auto-sell")
    else:
        cmd.append("--dry-run")
    
    if sell_below > 0.0:
        cmd.append(f"--sell-below={sell_below}")
    
    if debug:
        cmd.append("--debug")
        cmd.append("--verbose")
    
    if not show_stats:
        cmd.append("--no-stats")
    
    # Focus on active market only
    cmd.append("--active-market-only")
    
    try:
        process = subprocess.run(cmd, check=True)
        logger.info("Simulation seller completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Simulation seller failed with error code {e.returncode}")
        return False

def display_simulation_info(run_name):
    """Display information about the simulation run.
    
    Args:
        run_name: Name of the simulation run
    """
    print(f"\n🎯 SIMULATION RUN: {run_name}")
    print("=" * 60)
    
    cmd = [
        sys.executable, "-m", "src.simulation.initialization",
        "--info", run_name
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"❌ Could not retrieve information for simulation run: {run_name}")

def display_wallet_balance():
    """Display the wallet balance in a formatted way."""
    balance_info = check_wallet_balance()
    
    if balance_info["success"]:
        print("\n" + "=" * 60)
        print(f"💼 WALLET BALANCE: {balance_info['wallet']}")
        print("=" * 60)
        print(f"💰 MATIC Balance: {balance_info['matic_balance']} MATIC")
        print(f"💲 USDC Balance:  {balance_info['usdc_balance']} USDC")
        print("=" * 60 + "\n")
    else:
        print("\n" + "=" * 60)
        print("❌ ERROR CHECKING WALLET BALANCE")
        print(f"Error: {balance_info.get('error', 'Unknown error')}")
        print("=" * 60 + "\n")
    
    return balance_info

def run_auto_bidder(quiet=False, threshold=0.0, amount=1.0, dry_run=False, show_stats=True, weighted_selection=False, min_prediction=0.0):
    """Run the auto-bidder to place orders based on statistical opportunities.
    
    Args:
        quiet: Whether to suppress output
        threshold: Minimum opportunity percentage to place bids
        amount: Amount to bid in USDC
        dry_run: Whether to run in dry run mode (don't place real orders)
        show_stats: Whether to show full statistics table
        weighted_selection: Whether to use weighted selection instead of choosing the best opportunity
        min_prediction: Minimum prediction percentage required to consider an opportunity
    """
    logger.info(f"Starting auto-bidder at {datetime.datetime.now()}")
    
    # Build the command to run
    cmd = [
        sys.executable, 
        "-m", 
        "src.bidding_decision.auto_bid.run", 
        f"--threshold={threshold}",
        f"--amount={amount}"
    ]
    
    # Add dry run mode if requested
    if dry_run:
        cmd.append("--dry-run")
        logger.info("Running auto-bidder in dry run mode (no real orders will be placed)")
    
    # Add no-stats flag if requested
    if not show_stats:
        cmd.append("--no-stats")
        
    # Add weighted selection if requested
    if weighted_selection:
        cmd.append("--weighted-selection")
        logger.info("Using weighted selection for buy opportunities")
        
    # Add minimum prediction threshold if specified
    if min_prediction > 0:
        cmd.append(f"--min-prediction={min_prediction}")
        logger.info(f"Using minimum prediction threshold of {min_prediction}% for buy opportunities")
    
    try:
        if quiet and not dry_run:  # Always show output in dry run mode
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                logger.error(f"Auto-bidder failed with error: {process.stderr.decode()}")
            else:
                # Print the output even in quiet mode since this is the key result
                logger.info("Auto-bidder completed successfully")
                output = process.stdout.decode()
                print("\n" + output)
        else:
            process = subprocess.run(cmd)
            if process.returncode != 0:
                logger.error("Auto-bidder failed")
            else:
                logger.info("Auto-bidder completed successfully")
    except Exception as e:
        logger.error(f"Error running auto-bidder: {e}")
        return False
    
    return process.returncode == 0

def run_auto_seller(quiet=False, threshold=0.0, sell_below=0.0, dry_run=False, show_stats=True, debug=False, show_positions=True, show_active_positions=True):
    """Run the auto-seller to sell positions based on statistical opportunities.
    
    Args:
        quiet: Whether to suppress output
        threshold: Minimum opportunity percentage to sell positions
        sell_below: Sell positions with prediction below this percentage
        dry_run: Whether to run in dry run mode (don't place real orders)
        show_stats: Whether to show full statistics table
        debug: Whether to show detailed debugging information
        show_positions: Whether to show all positions
        show_active_positions: Whether to show active market positions
    """
    logger.info(f"Starting auto-seller at {datetime.datetime.now()}")
    
    # First display all positions if requested
    if show_positions and show_active_positions:
        print("\n" + "=" * 50)
        print("POSITIONS INFORMATION")
        print("=" * 50)
        
        # Run the position display command with the combined flag
        position_cmd = [
            sys.executable,
            "-m",
            "src.polymarket.my_positions.cli",
            "--simple-and-active-positions"
        ]
        
        try:
            subprocess.run(position_cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to display positions: {e}")
            # Continue with the rest of the function even if this fails
    else:
        # First display all positions if requested
        if show_positions:
            print("\n" + "=" * 50)
            print("CURRENT POSITIONS")
            print("=" * 50)
            
            # Run the position display command
            position_cmd = [
                sys.executable,
                "-m",
                "src.polymarket.my_positions.cli",
                "--simple-positions"
            ]
            
            try:
                subprocess.run(position_cmd, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to display positions: {e}")
                # Continue with the rest of the function even if this fails
        
        # Now display active market positions separately if requested
        if show_active_positions:
            print("\n" + "=" * 50)
            print("ACTIVE MARKET POSITIONS")
            print("=" * 50)
            
            # Run the position display command with the new active-positions flag
            active_position_cmd = [
                sys.executable,
                "-m",
                "src.polymarket.my_positions.cli",
                "--active-positions"
            ]
            
            try:
                subprocess.run(active_position_cmd, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to display active market positions: {e}")
                # Continue with the rest of the function even if this fails
    
    # Skip the explicit comparison table generation since the auto-seller will generate it
    print("\n" + "=" * 50)
    print("SELL RECOMMENDATIONS")
    print("=" * 50)
    
    # Build the command to run
    cmd = [
        sys.executable, 
        "-m", 
        "src.bidding_decision.auto_bid.run_seller",
        f"--threshold={threshold}"
    ]
    
    # Add the auto-sell flag to execute orders
    if not dry_run:
        cmd.append("--auto-sell")
    else:
        cmd.append("--dry-run")
    
    # Add sell-below threshold if specified
    if sell_below > 0.0:
        cmd.append(f"--sell-below={sell_below}")
    
    # Only add verbose flag if explicitly requested with debug
    if debug:
        cmd.append("--verbose")
    
    # Add debug flag if requested
    if debug:
        cmd.append("--debug")
    
    # Disable stats if requested
    if not show_stats:
        cmd.append("--no-stats")
    
    # Add flag to focus on active market only
    cmd.append("--active-market-only")
    
    # Run the command
    try:
        subprocess.run(cmd, check=True)
        logger.info("Auto-seller completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Auto-seller failed with error code {e.returncode}")
        if not quiet and e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False

def run_scheduled_jobs(args):
    """Run the configured jobs based on command-line arguments."""
    tweets_success = True
    prediction_success = True
    
    # Prepare the logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Get tweet count from Polymarket website first if requested
    polymarket_count = -1
    db_count = -1
    skip_tweet_fetching = False
    
    # Check if we're running tweets (not predictions_only) and if it's not a specialized auto-bidder or auto-seller run
    running_tweets = not args.predictions_only and not getattr(args, '_component_run', False)
    
    # Check if we're only checking counts without forcing fetching
    only_checking_counts = getattr(args, '_only_check_counts', False)
    
    if running_tweets and args.get_tweet_count_first:
        logger.info("Getting tweet count from Polymarket before fetching tweets")
        polymarket_count = get_polymarket_tweet_count(max_retries=args.max_count_retries)
        
        if polymarket_count > 0:
            logger.info(f"Successfully retrieved tweet count from Polymarket: {polymarket_count}")
            print("\n" + "=" * 60)
            print("CURRENT TWEET COUNT FROM POLYMARKET")
            print("=" * 60)
            print(f"Current tweet count: {polymarket_count}")
            print("=" * 60 + "\n")
            
            # Verify local database count to compare
            logger.info("Checking local database tweet count for comparison")
            verification_success, db_count = verify_tweet_count(quiet=args.quiet)
            
            if verification_success and db_count > 0:
                logger.info(f"Successfully retrieved tweet count from database: {db_count}")
                # Compare the counts
                if db_count == polymarket_count:
                    logger.info(f"Tweet counts match exactly: DB={db_count}, Polymarket={polymarket_count}")
                    print("\n" + "=" * 60)
                    print("✅ TWEET COUNT MATCH - SKIPPING TWEET FETCHING")
                    print("=" * 60)
                    print(f"📊 Both local database and Polymarket site show {db_count} tweets")
                    print("🔄 Skipping tweet fetching as counts already match")
                    print("=" * 60 + "\n")
                    skip_tweet_fetching = True
                else:
                    diff = abs(db_count - polymarket_count)
                    logger.info(f"Tweet counts don't match: DB={db_count}, Polymarket={polymarket_count}, Difference={diff}")
                    
                    # If we're only checking counts, don't force fetching
                    if only_checking_counts:
                        logger.info(f"Count mismatch detected - fetching tweets to update database")
                        print("\n" + "=" * 60)
                        print("⚠️ TWEET COUNT MISMATCH - FETCHING TWEETS")
                        print("=" * 60)
                        print(f"📊 Local database:   {db_count} tweets")
                        print(f"📊 Polymarket site:  {polymarket_count} tweets")
                        print(f"🔄 Difference:       {diff} tweets")
                        print("🔄 Fetching tweets to update the database")
                        print("=" * 60 + "\n")
                        skip_tweet_fetching = False
                    else:
                        print("\n" + "=" * 60)
                        print("⚠️ TWEET COUNT MISMATCH - PROCEEDING WITH TWEET FETCHING")
                        print("=" * 60)
                        print(f"📊 Local database:   {db_count} tweets")
                        print(f"📊 Polymarket site:  {polymarket_count} tweets")
                        print(f"🔄 Difference:       {diff} tweets")
                        print("🔄 Will fetch tweets to update the database")
                        print("=" * 60 + "\n")
            else:
                logger.warning(f"Failed to get tweet count from database, verification_success={verification_success}, db_count={db_count}")
                print("\n" + "=" * 60)
                print("⚠️ WARNING: COULD NOT VERIFY LOCAL DATABASE TWEET COUNT")
                print("=" * 60)
                print("Continuing with tweet fetching...")
                print("=" * 60 + "\n")
                
                # If we're only checking counts, don't force fetching
                if only_checking_counts:
                    logger.info("Only checking counts, not forcing tweet fetching despite verification failure")
                    skip_tweet_fetching = True
        else:
            logger.warning(f"Failed to get tweet count from Polymarket website, polymarket_count={polymarket_count}")
            print("\n" + "=" * 60)
            print("⚠️ WARNING: COULD NOT GET TWEET COUNT FROM POLYMARKET")
            print("=" * 60)
            print("Continuing with tweet fetching...")
            print("=" * 60 + "\n")
            
            # If we're only checking counts, don't force fetching
            if only_checking_counts:
                logger.info("Only checking counts, not forcing tweet fetching despite retrieval failure")
                skip_tweet_fetching = True
    
    # Run the tweet fetching job if configured and not skipped
    if running_tweets and not skip_tweet_fetching:
        if args.use_csv_getter:            # Use TweetCSVGetter method with retries
            logger.info("Using TweetCSVGetter method for tweet fetching")
            tweets_success = fetch_tweets_csv(quiet=args.quiet, max_retries=3)
            
            # If CSV getter failed after all retries, fall back to Apify
            if not tweets_success:
                logger.warning("CSV getter failed after all retries, falling back to Apify method")
                print("\n" + "=" * 60)
                print("⚠️ CSV GETTER FAILED - FALLING BACK TO APIFY")
                print("=" * 60)
                print("Will attempt to fetch tweets using the Apify method instead")
                print("=" * 60 + "\n")
                
                # Use default Apify method as fallback
                tweets_success = fetch_tweets(
                    max_tweets=args.max_tweets,
                    debug=not args.no_debug,
                    quiet=args.quiet,
                    use_incremental=not args.no_incremental,
                    initial_batch=args.initial_batch,
                    max_batch=args.max_batch
                )
        else:
            # Use default Apify method
            tweets_success = fetch_tweets(
                max_tweets=args.max_tweets,
                debug=not args.no_debug,
                quiet=args.quiet,
                use_incremental=not args.no_incremental,
                initial_batch=args.initial_batch,
                max_batch=args.max_batch
            )
        
        # Verify tweet count after fetching if enabled and we didn't skip fetching
        if tweets_success and not args.no_tweet_verify:
            logger.info("Verifying tweet count after fetching")
            verification_success, db_count_after = verify_tweet_count(quiet=args.quiet)
            
            # Get the tweet count from Polymarket for comparison if we haven't already or if we need an updated count
            if verification_success and db_count_after > 0:
                logger.info(f"Post-fetch database count: {db_count_after}")
                # Check if we need to get a fresh count from Polymarket
                get_fresh_count = True
                
                if polymarket_count <= 0 and args.get_tweet_count_first:
                    # Already tried and failed to get count before, no need to try again
                    logger.warning("Skipping Polymarket tweet count verification as it failed earlier")
                    get_fresh_count = False
                elif db_count_after == db_count and polymarket_count > 0:
                    # DB count didn't change and we already have a Polymarket count
                    logger.info(f"Using previously fetched Polymarket count ({polymarket_count}) as database count didn't change ({db_count} → {db_count_after})")
                    get_fresh_count = False
                
                if get_fresh_count:
                    logger.info("Getting fresh Polymarket tweet count for post-fetch verification")
                    polymarket_count = get_polymarket_tweet_count(max_retries=args.max_count_retries)
                    logger.info(f"Fresh Polymarket count: {polymarket_count}")
                
                if polymarket_count > 0:
                    # Compare the counts
                    if db_count_after != polymarket_count:
                        diff = abs(db_count_after - polymarket_count)
                        logger.warning(f"Post-fetch tweet count mismatch: DB={db_count_after}, Polymarket={polymarket_count}, Difference={diff}")
                        
                        # Try up to 3 more times to get a matching count
                        logger.info(f"Retrying Polymarket tweet count verification up to 3 more times")
                        match_found = False
                        
                        for retry in range(1, 4):  # 3 retries
                            logger.info(f"Post-fetch verification retry {retry}/3")
                            time.sleep(3)  # Wait a bit before retrying
                            retry_polymarket_count = get_polymarket_tweet_count(max_retries=1)  # Single attempt per retry
                            
                            if retry_polymarket_count > 0:
                                logger.info(f"Retry {retry}/3 Polymarket count: {retry_polymarket_count}")
                                
                                if db_count_after == retry_polymarket_count:
                                    logger.info(f"Match found on retry {retry}/3: DB={db_count_after}, Polymarket={retry_polymarket_count}")
                                    print("\n" + "=" * 60)
                                    print(f"✅ TWEET COUNT MATCH (on retry {retry}/3)")
                                    print("=" * 60)
                                    print(f"📊 Both local database and Polymarket site show {db_count_after} tweets")
                                    print("🔄 Skipping tweet fetching as counts already match")
                                    print("=" * 60 + "\n")
                                    match_found = True
                                    break
                            else:
                                logger.warning(f"Retry {retry}/3 failed to get Polymarket tweet count")
                        
                        # If all retries failed, show warning but continue
                        if not match_found:
                            print("\n" + "=" * 60)
                            print("⚠️ TWEET COUNT MISMATCH (after 3 retries)")
                            print("=" * 60)
                            print(f"📊 Local database:   {db_count_after} tweets")
                            print(f"📊 Polymarket site:  {polymarket_count} tweets")
                            print(f"🔄 Difference:       {diff} tweets")
                            print("=" * 60)
                            print("This might indicate missing tweets in your database or counting differences.")
                            
                            # Try to fetch tweets again up to 3 times using CSV getter
                            print("Attempting to re-fetch tweets 3 more times to resolve the mismatch...")
                            print("=" * 60 + "\n")
                            
                            retry_success = False
                            for retry_fetch in range(1, 4):  # 3 retries
                                logger.info(f"Re-fetching tweets attempt {retry_fetch}/3")
                                print(f"\nRe-fetching tweets, attempt {retry_fetch}/3...")
                                
                                if args.use_csv_getter:
                                    retry_tweets_success = fetch_tweets_csv(quiet=args.quiet, max_retries=1)
                                else:
                                    retry_tweets_success = fetch_tweets(
                                        max_tweets=args.max_tweets,
                                        debug=not args.no_debug,
                                        quiet=args.quiet,
                                        use_incremental=not args.no_incremental,
                                        initial_batch=args.initial_batch,
                                        max_batch=args.max_batch
                                    )
                                
                                if retry_tweets_success:
                                    # Verify tweet count after re-fetching
                                    logger.info(f"Verifying tweet count after re-fetch attempt {retry_fetch}")
                                    reverify_success, reverify_db_count = verify_tweet_count(quiet=args.quiet)
                                    
                                    if reverify_success and reverify_db_count > 0:
                                        # Get a fresh Polymarket count
                                        reverify_polymarket_count = get_polymarket_tweet_count(max_retries=1)
                                        
                                        if reverify_polymarket_count > 0 and reverify_db_count == reverify_polymarket_count:
                                            logger.info(f"Tweet count match after re-fetch attempt {retry_fetch}: DB={reverify_db_count}, Polymarket={reverify_polymarket_count}")
                                            print("\n" + "=" * 60)
                                            print(f"✅ TWEET COUNT MATCH (after re-fetch attempt {retry_fetch}/3)")
                                            print("=" * 60)
                                            print(f"📊 Both local database and Polymarket site show {reverify_db_count} tweets")
                                            print("🔄 Skipping tweet fetching as counts already match")
                                            print("=" * 60 + "\n")
                                            retry_success = True
                                            break
                                        else:
                                            diff = abs(reverify_db_count - reverify_polymarket_count) if reverify_polymarket_count > 0 else "unknown"
                                            logger.warning(f"Tweet count still mismatched after re-fetch attempt {retry_fetch}: DB={reverify_db_count}, Polymarket={reverify_polymarket_count}, Difference={diff}")
                                    else:
                                        logger.warning(f"Failed to verify tweet count after re-fetch attempt {retry_fetch}")
                                else:
                                    logger.warning(f"Re-fetch attempt {retry_fetch}/3 failed")
                            
                            # If all re-fetch attempts failed, try Apify as a last resort
                            if not retry_success:
                                if args.use_csv_getter:  # Only fall back if we're not already using Apify
                                    logger.warning("All re-fetch attempts failed, falling back to Apify method")
                                    print("\n" + "=" * 60)
                                    print("⚠️ ALL RE-FETCH ATTEMPTS FAILED - FALLING BACK TO APIFY")
                                    print("=" * 60)
                                    print("Will attempt to fetch tweets using the Apify method as a last resort")
                                    print("=" * 60 + "\n")
                                    
                                    # Use default Apify method as fallback
                                    apify_success = fetch_tweets(
                                        max_tweets=args.max_tweets,
                                        debug=not args.no_debug,
                                        quiet=args.quiet,
                                        use_incremental=not args.no_incremental,
                                        initial_batch=args.initial_batch,
                                        max_batch=args.max_batch
                                    )
                                    
                                    if apify_success:
                                        # Final verification
                                        logger.info("Verifying tweet count after Apify fallback")
                                        final_verify_success, final_db_count = verify_tweet_count(quiet=args.quiet)
                                        final_polymarket_count = get_polymarket_tweet_count(max_retries=1)
                                        
                                        if final_verify_success and final_db_count > 0 and final_polymarket_count > 0:
                                            if final_db_count == final_polymarket_count:
                                                logger.info(f"Tweet count match after Apify fallback: DB={final_db_count}, Polymarket={final_polymarket_count}")
                                                print("\n" + "=" * 60)
                                                print("✅ TWEET COUNT MATCH AFTER APIFY FALLBACK")
                                                print("=" * 60)
                                                print(f"📊 Both local database and Polymarket site show {final_db_count} tweets")
                                                print("🔄 Skipping tweet fetching as counts already match")
                                                print("=" * 60 + "\n")
                                            else:
                                                diff = abs(final_db_count - final_polymarket_count)
                                                logger.warning(f"Tweet count still mismatched after Apify fallback: DB={final_db_count}, Polymarket={final_polymarket_count}, Difference={diff}")
                                                print("\n" + "=" * 60)
                                                print("⚠️ TWEET COUNT STILL MISMATCHED AFTER APIFY FALLBACK")
                                                print("=" * 60)
                                                print(f"📊 Local database:   {final_db_count} tweets")
                                                print(f"📊 Polymarket site:  {final_polymarket_count} tweets")
                                                print(f"🔄 Difference:       {diff} tweets")
                                                print("=" * 60)
                                                print("Could not resolve the tweet count mismatch. Continuing with the process anyway.")
                                                print("=" * 60 + "\n")
                                    else:
                                        logger.error("Apify fallback also failed to fetch tweets")
                                else:
                                    # We're already using Apify, just continue with the process
                                    print("\n" + "=" * 60)
                                    print("⚠️ TWEET COUNT MISMATCH PERSISTS")
                                    print("=" * 60)
                                    print("Could not resolve the tweet count mismatch. Continuing with the process anyway.")
                                    print("=" * 60 + "\n")
                            
                            # Continue with the rest of the process anyway.
                            print("Continuing with the rest of the process...")
                            print("=" * 60 + "\n")
                    else:
                        logger.info(f"Post-fetch tweet counts match exactly: DB={db_count_after}, Polymarket={polymarket_count}")
                        print("\n" + "=" * 60)
                        print("✅ TWEET COUNT MATCH")
                        print("=" * 60)
                        print(f"📊 Both local database and Polymarket site show {db_count_after} tweets")
                        print("🔄 Skipping tweet fetching as counts already match")
                        print("=" * 60 + "\n")
            else:
                logger.warning(f"Post-fetch verification failed: verification_success={verification_success}, db_count_after={db_count_after}")
    else:
        # If we skipped tweet fetching, log it
        if skip_tweet_fetching:
            logger.info(f"Skipped tweet fetching as counts already matched (DB={db_count}, Polymarket={polymarket_count})")
    
    # Run the prediction job if configured and tweet fetching succeeded (or was skipped)
    if not args.tweets_only and (tweets_success or skip_tweet_fetching or getattr(args, '_component_run', False)):
        # For component-specific runs, ensure we run prediction
        if getattr(args, '_component_run', False):
            logger.info("Running prediction for component-specific run")
            
        prediction_success = run_prediction(
            quiet=True,  # Always run prediction quietly since we'll show bidder output instead
            use_prophet=not args.no_prophet  # Use Prophet by default unless --no-prophet is specified
        )
        
        # Handle simulation mode
        if args.simulate:
            # Initialize simulation run if needed
            if not initialize_simulation_run(args.simulate, args.sim_balance, args.strategy):
                logger.error("Failed to initialize simulation run")
                return False
            
            # Display simulation info
            display_simulation_info(args.simulate)
            
            # Run simulation bidder if bidding not disabled
            if prediction_success and not args.no_bidding:
                # If --no-buy is specified, force dry run mode
                effective_dry_run = args.dry_run or args.no_buy
                
                # Log the appropriate mode
                if args.no_buy and not args.dry_run:
                    logger.info("Running simulation bidder in no-buy mode (opportunities will be shown but no orders placed)")
                
                run_simulation_bidder(
                    run_name=args.simulate,
                    strategy=args.strategy,
                    threshold=args.buy_threshold,
                    amount=args.amount,
                    dry_run=effective_dry_run,
                    show_stats=not args.no_stats,
                    weighted_selection=args.weighted_selection,
                    min_prediction=args.min_prediction,
                    quiet=args.quiet
                )
                
            # Run simulation seller if selling not disabled
            if prediction_success and not args.no_selling:
                # If --no-sell is specified, force dry run mode
                effective_dry_run = args.dry_run or args.no_sell
                
                # Log the appropriate mode
                if args.no_sell and not args.dry_run:
                    logger.info("Running simulation seller in no-sell mode (opportunities will be shown but no orders placed)")
                
                run_simulation_seller(
                    run_name=args.simulate,
                    strategy=args.strategy,
                    threshold=args.sell_threshold,
                    sell_below=args.sell_below,
                    dry_run=effective_dry_run,
                    show_stats=not args.no_stats,
                    debug=args.debug_seller,
                    quiet=args.quiet
                )
        else:
            # Normal mode - real bidding and selling
            # Check wallet balance if needed
            if prediction_success and not args.no_bidding and not args.skip_balance_check:
                balance_info = display_wallet_balance()
                has_sufficient_balance = balance_info.get("success", False) and balance_info.get("usdc_balance", 0) >= args.min_usdc
                
                if not has_sufficient_balance and not args.dry_run and not args.no_buy:
                    logger.warning(f"Insufficient USDC balance ({balance_info.get('usdc_balance', 0)} USDC) for auto-bidding. Minimum required: {args.min_usdc} USDC")
                    logger.warning("Skipping auto-bidder due to insufficient USDC balance")
                    print("\n" + "=" * 60)
                    print(f"⚠️ SKIPPING AUTO-BIDDER: Insufficient USDC balance")
                    print("=" * 60)
                    print(f"💲 Current balance: {balance_info.get('usdc_balance', 0)} USDC")
                    print(f"💲 Minimum required: {args.min_usdc} USDC")
                    print("=" * 60 + "\n")
                elif prediction_success and not args.no_bidding:
                    # Run the auto-bidder if we have sufficient balance or we're in dry run mode or no-buy mode
                    if has_sufficient_balance or args.dry_run or args.no_buy:
                        # If --no-buy is specified, force dry run mode
                        effective_dry_run = args.dry_run or args.no_buy
                        
                        # Log the appropriate mode
                        if args.no_buy and not args.dry_run:
                            logger.info("Running auto-bidder in no-buy mode (opportunities will be shown but no orders placed)")
                        
                        run_auto_bidder(
                            quiet=args.quiet,
                            threshold=args.buy_threshold,
                            amount=args.amount,
                            dry_run=effective_dry_run,
                            show_stats=not args.no_stats,
                            weighted_selection=args.weighted_selection,
                            min_prediction=args.min_prediction
                        )
            elif prediction_success and not args.no_bidding:
                # Skip balance check if requested
                # If --no-buy is specified, force dry run mode
                effective_dry_run = args.dry_run or args.no_buy
                
                # Log the appropriate mode
                if args.no_buy and not args.dry_run:
                    logger.info("Running auto-bidder in no-buy mode (opportunities will be shown but no orders placed)")
                
                run_auto_bidder(
                    quiet=args.quiet,
                    threshold=args.buy_threshold,
                    amount=args.amount,
                    dry_run=effective_dry_run,
                    show_stats=not args.no_stats,
                    weighted_selection=args.weighted_selection,
                    min_prediction=args.min_prediction
                )
                
            # Run the auto-seller if prediction succeeded and selling not disabled
            # (always run auto-seller regardless of balance)
            if prediction_success and not args.no_selling:
                # If --no-sell is specified, force dry run mode
                effective_dry_run = args.dry_run or args.no_sell
                
                # Log the appropriate mode
                if args.no_sell and not args.dry_run:
                    logger.info("Running auto-seller in no-sell mode (opportunities will be shown but no orders placed)")
                
                run_auto_seller(
                    quiet=args.quiet,
                    threshold=args.sell_threshold,
                    sell_below=args.sell_below,
                    dry_run=effective_dry_run,
                    show_stats=not args.no_stats,
                    debug=args.debug_seller,
                    show_positions=args.show_positions,
                    show_active_positions=args.show_active_positions
                )
    
    return tweets_success and prediction_success or skip_tweet_fetching

def fetch_tweets_csv(quiet=False, max_retries=3):
    """Fetch tweets using the TweetCSVGetter.
    
    This uses the XTracker.io method to download tweets as CSV and process them.
    
    Args:
        quiet: Whether to suppress output
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        bool: Whether the tweet fetching was successful
    """
    logger.info(f"Starting tweet fetching with TweetCSVGetter at {datetime.datetime.now()}")
    
    cmd = [sys.executable, "-m", "src.xpath_scraper.TweetCSVGetter"]
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"CSV getter attempt {attempt}/{max_retries}")
            
            if quiet:
                process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if process.returncode != 0:
                    error_msg = process.stderr.decode()
                    logger.warning(f"Tweet CSV fetching attempt {attempt}/{max_retries} failed with error: {error_msg}")
                    if attempt < max_retries:
                        logger.info(f"Retrying in 5 seconds...")
                        time.sleep(5)
                        continue
                    else:
                        logger.error(f"All {max_retries} attempts to fetch tweets via CSV getter failed")
                        return False
                else:
                    logger.info(f"Tweet CSV fetching completed successfully on attempt {attempt}")
                    return True
            else:
                process = subprocess.run(cmd)
                if process.returncode != 0:
                    logger.warning(f"Tweet CSV fetching attempt {attempt}/{max_retries} failed")
                    if attempt < max_retries:
                        logger.info(f"Retrying in 5 seconds...")
                        time.sleep(5)
                        continue
                    else:
                        logger.error(f"All {max_retries} attempts to fetch tweets via CSV getter failed")
                        return False
                else:
                    logger.info(f"Tweet CSV fetching completed successfully on attempt {attempt}")
                    return True
        except Exception as e:
            logger.warning(f"Error during CSV fetching attempt {attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in 5 seconds...")
                time.sleep(5)
            else:
                logger.error(f"All {max_retries} attempts to fetch tweets via CSV getter failed with exception: {e}")
                return False
    
    return False

def main():
    """Main entry point for the scheduler."""
    args = setup_argparse()
    
    # Set log level based on verbosity
    if args.quiet:
        logger.setLevel(logging.WARNING)
    
    # Set component-specific intervals or use global interval as default
    tweet_interval = args.tweet_interval if args.tweet_interval is not None else args.interval
    buy_interval = args.buy_interval if args.buy_interval is not None else args.interval
    sell_interval = args.sell_interval if args.sell_interval is not None else args.interval
    
    # Display a clear startup banner
    print("\n" + "=" * 80)
    if args.simulate:
        print("🎯 POLYMARKET SIMULATION SCHEDULER STARTING")
        print("=" * 80)
        print(f"🎮 Simulation run:       {args.simulate}")
        print(f"🧠 Strategy:             {args.strategy}")
        print(f"💰 Initial balance:      ${args.sim_balance}")
    else:
        print("🤖 POLYMARKET AUTOMATED SCHEDULER STARTING")
    print("=" * 80)
    print(f"📊 Tweet checking interval: {tweet_interval} minutes")
    print(f"💰 Auto-bidder interval:    {buy_interval} minutes")
    print(f"💸 Auto-seller interval:    {sell_interval} minutes")
    if args.dry_run:
        print("🔒 Running in DRY RUN mode - no real orders will be placed")
    if args.simulate:
        print("🎯 Running in SIMULATION mode - using simulation framework")
    print("=" * 80 + "\n")
    
    # Log the scheduler startup
    logger.info(f"Tweet scheduler starting with global interval: {args.interval} minutes")
    if args.tweet_interval is not None:
        logger.info(f"Tweet fetching interval: {tweet_interval} minutes")
    if args.buy_interval is not None:
        logger.info(f"Auto-bidder interval: {buy_interval} minutes")
    if args.sell_interval is not None:
        logger.info(f"Auto-seller interval: {sell_interval} minutes")
    
    # Log simulation mode if enabled
    if args.simulate:
        logger.info(f"Running in SIMULATION mode")
        logger.info(f"Simulation run: {args.simulate}")
        logger.info(f"Simulation strategy: {args.strategy}")
        logger.info(f"Initial balance for new runs: ${args.sim_balance}")
    
    if args.tweets_only:
        logger.info("Configured to run tweet fetching only")
    elif args.predictions_only:
        logger.info("Configured to run predictions only")
    
    # Log tweet fetching method
    if not args.predictions_only:
        if args.use_csv_getter:
            logger.info("Using TweetCSVGetter for tweet fetching (XTracker.io method)")
        else:
            logger.info("Using Apify method for tweet fetching")
            
            # Log tweet count pre-check setting
            if args.get_tweet_count_first:
                logger.info(f"Will get tweet count from Polymarket first (max retries: {args.max_count_retries})")
            else:
                logger.info("Will not pre-check tweet count from Polymarket")
    
    # Log which prediction algorithm will be used
    if not args.tweets_only and not args.no_prophet:
        logger.info("Using Prophet-based prediction algorithm (--no-prophet to disable)")
    elif not args.tweets_only:
        logger.info("Using standard prediction algorithm")
    
    # Log tweet verification setting
    if not args.predictions_only and not args.no_tweet_verify:
        logger.info("Tweet count verification is enabled")
    elif not args.predictions_only:
        logger.info("Tweet count verification is disabled (--no-tweet-verify)")
    
    # Log auto-bidder configuration
    if not args.tweets_only and not args.no_bidding:
        logger.info(f"Will run auto-bidder with threshold: {args.buy_threshold}%")
        logger.info(f"Bid amount: {args.amount} USDC")
        if args.min_prediction > 0:
            logger.info(f"Will only bid on opportunities with prediction ≥ {args.min_prediction}%")
        if not args.skip_balance_check:
            logger.info(f"Will check USDC balance before bidding (min required: {args.min_usdc} USDC)")
        else:
            logger.info("Balance checking is disabled (--skip-balance-check)")
        if args.weighted_selection:
            logger.info("Using weighted selection for buy opportunities")
        if args.dry_run:
            logger.info("Auto-bidder running in DRY RUN mode - no real orders will be placed")
        elif args.no_buy:
            logger.info("Auto-bidder running in NO-BUY mode - opportunities will be shown but no orders placed")
        else:
            logger.info("Auto-bidder will place REAL orders - use --dry-run or --no-buy to test without placing orders")
        if args.no_stats:
            logger.info("Full statistics table display is disabled")
            
    # Log auto-seller configuration
    if not args.tweets_only and not args.no_selling:
        logger.info(f"Will run auto-seller with threshold: {args.sell_threshold}%")
        if args.sell_below > 0.0:
            logger.info(f"Will sell positions with prediction below {args.sell_below}%")
        if args.dry_run:
            logger.info("Auto-seller running in DRY RUN mode - no real orders will be placed")
        elif args.no_sell:
            logger.info("Auto-seller running in NO-SELL mode - opportunities will be shown but no orders placed")
        else:
            logger.info("Auto-seller will place REAL orders - use --dry-run or --no-sell to test without placing orders")
        if args.debug_seller:
            logger.info("Detailed debugging is enabled for position seller")
        
        # Log position display settings
        if args.show_positions:
            logger.info("Will display all current positions")
        if args.show_active_positions:
            logger.info("Will display active market positions")
        if not args.show_positions and not args.show_active_positions:
            logger.info("Position display is disabled (use --show-positions or --show-active-positions to enable)")
    
    if args.run_once:
        logger.info("Running jobs once and exiting")
        run_scheduled_jobs(args)
        return 0
    
    try:
        # Initialize timers for each component
        last_tweet_run = 0
        last_buy_run = 0
        last_sell_run = 0
        
        while True:
            current_time = time.time()
            
            # Check if it's time to run each component
            run_tweets = not args.predictions_only and (current_time - last_tweet_run >= tweet_interval * 60)
            run_buy = not args.tweets_only and not args.no_bidding and (current_time - last_buy_run >= buy_interval * 60)
            run_sell = not args.tweets_only and not args.no_selling and (current_time - last_sell_run >= sell_interval * 60)
            
            # Custom configuration to run specific components based on their intervals
            custom_args = argparse.Namespace(**vars(args))
            
            if run_tweets:
                # Add clear visual separator and timestamp for tweet checking
                current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print("\n" + "=" * 80)
                print(f"🔍 TWEET COUNT CHECK - SCHEDULED INTERVAL ({tweet_interval}m) - {current_time_str}")
                print("=" * 80)
                
                logger.info(f"Running scheduled tweet count check (interval: {tweet_interval}m)")
                # Only check tweet counts, don't force fetching
                custom_args = argparse.Namespace(**vars(args))
                custom_args.no_bidding = True
                custom_args.no_selling = True
                custom_args._component_run = False
                custom_args._only_check_counts = False  # Changed from True to False - fetch tweets if needed
                run_scheduled_jobs(custom_args)
                last_tweet_run = current_time
            
            if run_buy:
                # Add clear visual separator and timestamp for auto-bidder
                current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print("\n" + "=" * 80)
                print(f"💰 AUTO-BIDDER - SCHEDULED INTERVAL ({buy_interval}m) - {current_time_str}")
                print("=" * 80)
                
                # Always check and fetch tweets before buying
                logger.info(f"Running auto-bidder (interval: {buy_interval}m)")
                
                # First check and fetch tweets if needed
                if not run_tweets:  # Only if we haven't just run the tweet checking
                    print("\n" + "-" * 60)
                    print("📊 PRE-BIDDING TWEET CHECK")
                    print("-" * 60)
                    logger.info("Running tweet checking and fetching before auto-bidder")
                    tweet_args = argparse.Namespace(**vars(args))
                    tweet_args.no_bidding = True
                    tweet_args.no_selling = True
                    tweet_args._component_run = False
                    tweet_args._only_check_counts = False  # Check and fetch if needed
                    run_scheduled_jobs(tweet_args)
                
                # Then run the auto-bidder
                print("\n" + "-" * 60)
                print("🤖 EXECUTING AUTO-BIDDER")
                print("-" * 60)
                custom_args = argparse.Namespace(**vars(args))
                custom_args.predictions_only = True
                custom_args.no_selling = True
                custom_args.no_bidding = False
                custom_args._component_run = True  # This is a component-specific run
                run_scheduled_jobs(custom_args)
                last_buy_run = current_time
            
            if run_sell:
                # Add clear visual separator and timestamp for auto-seller
                current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print("\n" + "=" * 80)
                print(f"💸 AUTO-SELLER - SCHEDULED INTERVAL ({sell_interval}m) - {current_time_str}")
                print("=" * 80)
                
                # Always check and fetch tweets before selling
                logger.info(f"Running auto-seller (interval: {sell_interval}m)")
                
                # First check and fetch tweets if needed
                if not run_tweets and not run_buy:  # Only if we haven't just run tweet checking or buying
                    print("\n" + "-" * 60)
                    print("📊 PRE-SELLING TWEET CHECK")
                    print("-" * 60)
                    logger.info("Running tweet checking and fetching before auto-seller")
                    tweet_args = argparse.Namespace(**vars(args))
                    tweet_args.no_bidding = True
                    tweet_args.no_selling = True
                    tweet_args._component_run = False
                    tweet_args._only_check_counts = False  # Check and fetch if needed
                    run_scheduled_jobs(tweet_args)
                
                # Then run the auto-seller
                print("\n" + "-" * 60)
                print("🤖 EXECUTING AUTO-SELLER")
                print("-" * 60)
                custom_args = argparse.Namespace(**vars(args))
                custom_args.predictions_only = True
                custom_args.no_bidding = True
                custom_args.no_selling = False
                custom_args._component_run = True  # This is a component-specific run
                run_scheduled_jobs(custom_args)
                last_sell_run = current_time
                
            # Add a clear visual separator for the sleep period
            next_event = min(
                last_tweet_run + tweet_interval * 60,
                last_buy_run + buy_interval * 60,
                last_sell_run + sell_interval * 60
            )
            next_component = ""
            seconds_to_next = next_event - current_time
            minutes_to_next = seconds_to_next / 60
            
            if next_event == last_tweet_run + tweet_interval * 60:
                next_component = f"Tweet Check ({tweet_interval}m interval)"
            elif next_event == last_buy_run + buy_interval * 60:
                next_component = f"Auto-Bidder ({buy_interval}m interval)"
            elif next_event == last_sell_run + sell_interval * 60:
                next_component = f"Auto-Seller ({sell_interval}m interval)"
                
            print("\n" + "=" * 80)
            print(f"⏱️  SLEEPING - Next run in {minutes_to_next:.1f} minutes - {next_component}")
            print("=" * 80 + "\n")
            
            # Sleep for the remaining time until the next component is due
            time.sleep(max(0, next_event - current_time))
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 