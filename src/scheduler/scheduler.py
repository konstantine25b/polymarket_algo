#!/usr/bin/env python3
"""
Scheduler for automating tweet fetching and prediction tasks.

This module provides functionality to periodically:
1. Fetch Elon Musk's tweets and store them in the database
2. Run the Polymarket predictor to update predictions
3. Run the bidding decision stats to compare predictions with market data and display token IDs

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
    --no-stats             Don't run the bidding decision stats comparison
    --threshold FLOAT      Minimum opportunity percentage to include in results (default: 0.0)
    --enhanced-viz         Generate enhanced visualization with stats

Notes:
    Token IDs are displayed by default in the bidding stats output to facilitate trading on Polymarket.
"""

import argparse
import time
import subprocess
import sys
import logging
import datetime
import os
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
    parser.add_argument('--no-stats', action='store_true',
                        help="Don't run the bidding decision stats comparison")
    parser.add_argument('--threshold', type=float, default=0.0,
                        help='Minimum opportunity percentage to include in results (default: 0.0)')
    parser.add_argument('--enhanced-viz', action='store_true',
                        help='Generate enhanced visualization with stats')
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

def run_bidding_decision_stats(quiet=False, use_prophet=True, threshold=0.0, enhanced_viz=False):
    """Run the bidding decision stats to compare predictions with market data.
    
    Args:
        quiet: Whether to suppress output
        use_prophet: Whether to use the Prophet algorithm
        threshold: Minimum opportunity percentage to include in results
        enhanced_viz: Whether to generate enhanced visualization
    """
    logger.info(f"Starting bidding decision stats comparison at {datetime.datetime.now()}")
    
    # Build the command to run
    cmd = [sys.executable, "-m", "src.bidding_decision.stats", "--visualize", f"--threshold={threshold}", "--show-tokens"]
    
    # Add enhanced visualization if requested
    if enhanced_viz:
        cmd.append("--enhanced-viz")
    
    # Use the same Prophet setting as predictions
    if not use_prophet:
        cmd.append("--no-prophet")
    
    try:
        if quiet:
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode != 0:
                logger.error(f"Bidding decision stats failed with error: {process.stderr.decode()}")
            else:
                # Print the output even in quiet mode since this is the key result
                logger.info("Bidding decision stats completed successfully")
                output = process.stdout.decode()
                # Extract the key parts of the output (only show the Best Trading Opportunity section if it exists)
                if "Best Trading Opportunity:" in output:
                    start_idx = output.find("Comparison Table:")
                    end_idx = len(output)
                    if start_idx != -1:
                        relevant_output = output[start_idx:end_idx]
                        print("\n" + relevant_output)
                else:
                    print("\n" + output)
        else:
            process = subprocess.run(cmd)
            if process.returncode != 0:
                logger.error("Bidding decision stats failed")
            else:
                logger.info("Bidding decision stats completed successfully")
    except Exception as e:
        logger.error(f"Error running bidding decision stats: {e}")
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
        tweets_success = fetch_tweets(
            max_tweets=args.max_tweets,
            debug=not args.no_debug,
            quiet=args.quiet,
            use_incremental=not args.no_incremental,
            initial_batch=args.initial_batch,
            max_batch=args.max_batch
        )
    
    # Run the prediction job if configured and tweet fetching succeeded (or was skipped)
    if not args.tweets_only and tweets_success:
        prediction_success = run_prediction(
            quiet=True,  # Always run prediction quietly since we'll show stats instead
            use_prophet=not args.no_prophet  # Use Prophet by default unless --no-prophet is specified
        )
        
        # Run the bidding decision stats if prediction succeeded and stats not disabled
        if prediction_success and not args.no_stats:
            run_bidding_decision_stats(
                quiet=args.quiet,
                use_prophet=not args.no_prophet,
                threshold=args.threshold,
                enhanced_viz=args.enhanced_viz
            )
    
    return tweets_success and prediction_success

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
    
    # Log which prediction algorithm will be used
    if not args.tweets_only and not args.no_prophet:
        logger.info("Using Prophet-based prediction algorithm (--no-prophet to disable)")
    elif not args.tweets_only:
        logger.info("Using standard prediction algorithm")
    
    # Log stats configuration
    if not args.tweets_only and not args.no_stats:
        logger.info(f"Will run bidding decision stats with threshold: {args.threshold}%")
        logger.info("Token IDs will be displayed with trading opportunities for easier Polymarket trading")
        if args.enhanced_viz:
            logger.info("Enhanced visualization enabled for bidding decision stats")
    
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