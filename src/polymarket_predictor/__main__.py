#!/usr/bin/env python3
"""
Command-line interface for the Polymarket Tweet Predictor.
This allows the module to be run using "python -m src.polymarket_predictor"
"""

import sys
import argparse
from .tweet_predictor import predict_tweet_frame_probabilities, verify_tweet_count

def main():
    parser = argparse.ArgumentParser(description='Predict Elon Musk tweet count frame probabilities')
    parser.add_argument('--start', type=str, help='Start date/time (YYYY-MM-DD HH:MM:SS) in Eastern Time (ET)')
    parser.add_argument('--end', type=str, help='End date/time (YYYY-MM-DD HH:MM:SS) in Eastern Time (ET)')
    parser.add_argument('--file', type=str, help='Path to tweet data CSV file')
    parser.add_argument('--no-trend', action='store_true', help='Disable trend adjustment')
    parser.add_argument('--sims', type=int, default=1000, help='Number of Monte Carlo simulations')
    parser.add_argument('--current-count', type=int, help='Current tweet count (overrides auto-counting)')
    parser.add_argument('--force-count', action='store_true', help='Force using the provided count instead of auto-counting')
    parser.add_argument('--exact-count', type=int, help='Specify the exact number of tweets (overrides both auto-counting and --current-count)')
    parser.add_argument('--verify-count', action='store_true', help='Only verify tweet count in the specified date range without prediction')
    
    args = parser.parse_args()
    
    # For the specific Polymarket timeframe mentioned in the request
    if not args.start and not args.end:
        print("Using Polymarket's specified timeframe: April 11, 2025, 12:00 PM ET to April 18, 2025, 12:00 PM ET")
        args.start = "2025-04-11 12:00:00"  # 12:00 PM ET
        args.end = "2025-04-18 12:00:00"    # 12:00 PM ET
    
    # If verify-count flag is set, only verify the count and exit
    if args.verify_count:
        count = verify_tweet_count(args.start, args.end, args.file)
        print(f"\nVerified total tweet count: {count} (using ET timezone)")
        sys.exit(0)
    
    # If exact-count is provided, use it and force override
    current_count = None
    override_auto_count = args.force_count
    
    if args.exact_count is not None:
        current_count = args.exact_count
        override_auto_count = True
        print(f"Using exact tweet count specified: {current_count}")
    elif args.current_count is not None:
        current_count = args.current_count
    
    # Call the prediction function
    probabilities = predict_tweet_frame_probabilities(
        start_date_str=args.start,
        end_date_str=args.end,
        data_file=args.file,
        use_trend=not args.no_trend,
        num_simulations=args.sims,
        current_tweet_count=current_count,
        override_auto_count=override_auto_count
    )
    
    # Return the highest probability bracket
    if probabilities:
        max_frame = max(probabilities.items(), key=lambda x: x[1])
        print(f"\nMost likely outcome: {max_frame[0]} ({max_frame[1]:.1f}%)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 