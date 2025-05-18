#!/usr/bin/env python3
"""
Scheduler for automating tweet fetching and prediction tasks.

This module provides functionality to periodically:
1. Fetch Elon Musk's tweets and store them in the database
2. Run the Polymarket predictor to update predictions
3. Run the auto-bidder to place orders based on statistical opportunities
4. Add the auto-seller to place sell orders based on statistical opportunities

Usage:
    python -m src.scheduler.scheduler [options]

Options:
    --interval MINUTES     Set the interval between runs (default: 20 minutes)
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
                        help='Interval between runs in minutes (default: 20)')
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

def get_polymarket_tweet_count():
    """Get the current tweet count from Polymarket website.
    
    Returns:
        int: The current tweet count or -1 if retrieval failed
    """
    logger.info("Getting tweet count from Polymarket...")
    
    cmd = [sys.executable, "-m", "src.xpath_scraper.NumberGetter"]
    
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if process.returncode != 0:
            logger.error(f"Failed to get tweet count: {process.stderr}")
            return -1
        
        output = process.stdout
        # Extract the tweet count using regex
        match = re.search(r"Tweet count: (\d+)", output)
        if match:
            count = int(match.group(1))
            logger.info(f"Retrieved tweet count from Polymarket: {count}")
            return count
        else:
            logger.error(f"Failed to parse tweet count from output: {output}")
            return -1
    except Exception as e:
        logger.error(f"Error getting tweet count: {e}")
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
    
    cmd = [sys.executable, "-m", "src.polymarket_predictor.tweet_predictor", "--verify-count"]
    
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
                except ValueError:
                    total_count = -1
            elif "tweets" in line and line.startswith("  202"):
                daily_counts.append(line.strip())
        
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
            return True, total_count
        else:
            logger.warning("Could not extract tweet count information from verification output")
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

def display_wallet_balance():
    """Display the wallet balance in a formatted way."""
    balance_info = check_wallet_balance()
    
    if balance_info["success"]:
        print("\n" + "=" * 50)
        print(f"WALLET BALANCE: {balance_info['wallet']}")
        print("=" * 50)
        print(f"MATIC Balance: {balance_info['matic_balance']} MATIC")
        print(f"USDC Balance:  {balance_info['usdc_balance']} USDC")
        print("=" * 50 + "\n")
    else:
        print("\n" + "=" * 50)
        print("ERROR CHECKING WALLET BALANCE")
        print(f"Error: {balance_info.get('error', 'Unknown error')}")
        print("=" * 50 + "\n")
    
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

def run_auto_seller(quiet=False, threshold=0.0, sell_below=0.0, dry_run=False, show_stats=True, debug=False):
    """Run the auto-seller to sell positions based on statistical opportunities.
    
    Args:
        quiet: Whether to suppress output
        threshold: Minimum opportunity percentage to sell positions
        sell_below: Sell positions with prediction below this percentage
        dry_run: Whether to run in dry run mode (don't place real orders)
        show_stats: Whether to show full statistics table
        debug: Whether to show detailed debugging information
    """
    logger.info(f"Starting auto-seller at {datetime.datetime.now()}")
    
    # Build the command to run
    cmd = [
        sys.executable, 
        "-m", 
        "src.bidding_decision.auto_bid.run_seller", 
        f"--threshold={threshold}",
        "--auto-sell"
    ]
    
    # Add sell-below parameter if specified
    if sell_below > 0.0:
        cmd.append(f"--sell-below={sell_below}")
        logger.info(f"Configured to sell positions with prediction below {sell_below}%")
    
    # Add dry run mode if requested
    if dry_run:
        cmd.append("--dry-run")
        logger.info("Running auto-seller in dry run mode (no real orders will be placed)")
    
    # Add no-stats flag if requested
    if not show_stats:
        cmd.append("--no-stats")
    
    # Add debug flag if requested
    if debug:
        cmd.append("--debug")
        logger.info("Running auto-seller with detailed debugging information")
    
    try:
        if quiet and not dry_run:  # Always show output in dry run mode
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                logger.error(f"Auto-seller failed with error: {process.stderr.decode()}")
            else:
                # Print the output even in quiet mode since this is the key result
                logger.info("Auto-seller completed successfully")
                output = process.stdout.decode()
                print("\n" + output)
        else:
            process = subprocess.run(cmd)
            if process.returncode != 0:
                logger.error("Auto-seller failed")
            else:
                logger.info("Auto-seller completed successfully")
    except Exception as e:
        logger.error(f"Error running auto-seller: {e}")
        return False
    
    return process.returncode == 0

def run_scheduled_jobs(args):
    """Run the configured jobs based on command-line arguments."""
    tweets_success = True
    prediction_success = True
    
    # Prepare the logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Run the tweet fetching job if configured
    if not args.predictions_only:
        if args.use_csv_getter:
            # Use TweetCSVGetter method
            logger.info("Using TweetCSVGetter method for tweet fetching")
            tweets_success = fetch_tweets_csv(quiet=args.quiet)
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
        
        # Verify tweet count after fetching if enabled
        if tweets_success and not args.no_tweet_verify:
            verification_success, db_count = verify_tweet_count(quiet=args.quiet)
            
            # Get the tweet count from Polymarket for comparison
            if verification_success and db_count > 0:
                polymarket_count = get_polymarket_tweet_count()
                
                if polymarket_count > 0:
                    # Compare the counts
                    if db_count != polymarket_count:
                        diff = abs(db_count - polymarket_count)
                        logger.warning(f"Tweet count mismatch: DB has {db_count}, Polymarket has {polymarket_count} (difference: {diff})")
                        print("\n" + "=" * 50)
                        print("⚠️ TWEET COUNT MISMATCH")
                        print("=" * 50)
                        print(f"Local database:   {db_count} tweets")
                        print(f"Polymarket site:  {polymarket_count} tweets")
                        print(f"Difference:       {diff} tweets")
                        print("=" * 50)
                        print("This might indicate missing tweets in your database or counting differences.")
                        print("=" * 50 + "\n")
                    else:
                        logger.info(f"Tweet counts match: Both DB and Polymarket show {db_count} tweets")
                        print("\n" + "=" * 50)
                        print("✅ TWEET COUNT MATCH")
                        print("=" * 50)
                        print(f"Both local database and Polymarket site show {db_count} tweets")
                        print("=" * 50 + "\n")
    
    # Run the prediction job if configured and tweet fetching succeeded (or was skipped)
    if not args.tweets_only and tweets_success:
        prediction_success = run_prediction(
            quiet=True,  # Always run prediction quietly since we'll show bidder output instead
            use_prophet=not args.no_prophet  # Use Prophet by default unless --no-prophet is specified
        )
        
        # Check wallet balance if needed
        if prediction_success and not args.no_bidding and not args.skip_balance_check:
            balance_info = display_wallet_balance()
            has_sufficient_balance = balance_info.get("success", False) and balance_info.get("usdc_balance", 0) >= args.min_usdc
            
            if not has_sufficient_balance and not args.dry_run:
                logger.warning(f"Insufficient USDC balance ({balance_info.get('usdc_balance', 0)} USDC) for auto-bidding. Minimum required: {args.min_usdc} USDC")
                logger.warning("Skipping auto-bidder due to insufficient USDC balance")
                print(f"\n⚠️ SKIPPING AUTO-BIDDER: Insufficient USDC balance ({balance_info.get('usdc_balance', 0)} USDC)")
                print(f"Minimum required: {args.min_usdc} USDC\n")
            elif prediction_success and not args.no_bidding:
                # Run the auto-bidder if we have sufficient balance or we're in dry run mode
                if has_sufficient_balance or args.dry_run:
                    run_auto_bidder(
                        quiet=args.quiet,
                        threshold=args.buy_threshold,
                        amount=args.amount,
                        dry_run=args.dry_run,
                        show_stats=not args.no_stats,
                        weighted_selection=args.weighted_selection,
                        min_prediction=args.min_prediction
                    )
        elif prediction_success and not args.no_bidding:
            # Skip balance check if requested
            run_auto_bidder(
                quiet=args.quiet,
                threshold=args.buy_threshold,
                amount=args.amount,
                dry_run=args.dry_run,
                show_stats=not args.no_stats,
                weighted_selection=args.weighted_selection,
                min_prediction=args.min_prediction
            )
            
        # Run the auto-seller if prediction succeeded and selling not disabled
        # (always run auto-seller regardless of balance)
        if prediction_success and not args.no_selling:
            run_auto_seller(
                quiet=args.quiet,
                threshold=args.sell_threshold,
                sell_below=args.sell_below,
                dry_run=args.dry_run,
                show_stats=not args.no_stats,
                debug=args.debug_seller
            )
    
    return tweets_success and prediction_success

def fetch_tweets_csv(quiet=False):
    """Fetch tweets using the TweetCSVGetter.
    
    This uses the XTracker.io method to download tweets as CSV and process them.
    
    Args:
        quiet: Whether to suppress output
    
    Returns:
        bool: Whether the tweet fetching was successful
    """
    logger.info(f"Starting tweet fetching with TweetCSVGetter at {datetime.datetime.now()}")
    
    cmd = [sys.executable, "-m", "src.xpath_scraper.TweetCSVGetter"]
    
    try:
        if quiet:
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                logger.error(f"Tweet CSV fetching failed with error: {process.stderr.decode()}")
            else:
                logger.info("Tweet CSV fetching completed successfully")
        else:
            process = subprocess.run(cmd)
            if process.returncode != 0:
                logger.error("Tweet CSV fetching failed")
            else:
                logger.info("Tweet CSV fetching completed successfully")
    except Exception as e:
        logger.error(f"Error running tweet CSV fetching: {e}")
        return False
    
    return process.returncode == 0

def main():
    """Main entry point for the scheduler."""
    args = setup_argparse()
    
    # Set log level based on verbosity
    if args.quiet:
        logger.setLevel(logging.WARNING)
    
    # Log the scheduler startup
    logger.info(f"Tweet scheduler starting with interval: {args.interval} minutes")
    
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
        else:
            logger.info("Auto-bidder will place REAL orders - use --dry-run to test without placing orders")
        if args.no_stats:
            logger.info("Full statistics table display is disabled")
            
    # Log auto-seller configuration
    if not args.tweets_only and not args.no_selling:
        logger.info(f"Will run auto-seller with threshold: {args.sell_threshold}%")
        if args.sell_below > 0.0:
            logger.info(f"Will sell positions with prediction below {args.sell_below}%")
        if args.dry_run:
            logger.info("Auto-seller running in DRY RUN mode - no real orders will be placed")
        else:
            logger.info("Auto-seller will place REAL orders - use --dry-run to test without placing orders")
        if args.debug_seller:
            logger.info("Detailed debugging is enabled for position seller")
    
    if args.run_once:
        logger.info("Running jobs once and exiting")
        run_scheduled_jobs(args)
        return 0
    
    try:
        while True:
            run_scheduled_jobs(args)
            logger.info(f"Sleeping for {args.interval} minutes until next run")
            time.sleep(args.interval * 60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 