#!/usr/bin/env python3
"""
Main script to run Elon Musk tweet count predictions using Facebook Prophet.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from prediction_algos.facebook_prophet import TweetPredictor


def main():
    """Main function to run tweet predictions."""
    parser = argparse.ArgumentParser(
        description="Predict Elon Musk tweet counts for Polymarket time frames using Facebook Prophet"
    )
    
    parser.add_argument(
        '--data-path', 
        type=str, 
        default=None,
        help='Path to tweet data CSV file (default: uses path from constants.py)'
    )
    
    parser.add_argument(
        '--no-plots', 
        action='store_true',
        help='Disable saving prediction plots'
    )
    
    parser.add_argument(
        '--current-time',
        type=str,
        default=None,
        help='Current time for prediction context (format: YYYY-MM-DD HH:MM:SS)'
    )
    
    parser.add_argument(
        '--changepoint-prior',
        type=float,
        default=0.05,
        help='Prophet changepoint prior scale (default: 0.05)'
    )
    
    parser.add_argument(
        '--seasonality-prior',
        type=float,
        default=10.0,
        help='Prophet seasonality prior scale (default: 10.0)'
    )
    
    parser.add_argument(
        '--random-seed',
        type=int,
        default=42,
        help='Random seed for reproducible results (default: 42)'
    )
    
    args = parser.parse_args()
    
    # Parse current time if provided
    current_time = None
    if args.current_time:
        try:
            current_time = datetime.strptime(args.current_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print(f"Error: Invalid time format. Use YYYY-MM-DD HH:MM:SS")
            sys.exit(1)
    
    # Initialize predictor
    print("Initializing Tweet Predictor...")
    predictor = TweetPredictor(
        data_path=args.data_path,
        save_plots=not args.no_plots
    )
    
    # Set random seed if the predictor supports it
    if hasattr(predictor, 'set_random_seed'):
        predictor.set_random_seed(args.random_seed)
    
    try:
        # Prepare model with custom parameters
        print("Preparing Prophet model...")
        predictor.prepare_model(
            changepoint_prior_scale=args.changepoint_prior,
            seasonality_prior_scale=args.seasonality_prior
        )
        
        # Generate predictions
        print("Generating predictions...")
        predictions = predictor.generate_predictions(current_time=current_time)
        
        # Print summary
        predictor.print_prediction_summary(predictions)
        
        # Create plots
        if not args.no_plots:
            print("\nGenerating prediction plots...")
            predictor.plot_predictions(predictions)
        
        print("\nPrediction completed successfully!")
        
    except Exception as e:
        print(f"Error during prediction: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 