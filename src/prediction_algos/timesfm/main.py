"""
Main command-line interface for TimesFM tweet count predictor.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .predictor import TimesFMTweetPredictor


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='TimesFM Foundation Model Tweet Count Predictor')
    
    parser.add_argument(
        '--data-path',
        type=str,
        help='Path to the CSV file containing tweet data'
    )
    
    parser.add_argument(
        '--current-time',
        type=str,
        help='Current time for prediction (format: "YYYY-MM-DD HH:MM:SS")'
    )
    
    parser.add_argument(
        '--no-plots',
        action='store_true',
        help='Disable plot generation'
    )
    
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Use fast mode (reduced context length and sampling)'
    )
    
    parser.add_argument(
        '--context-len',
        type=int,
        default=64,
        help='Context length for TimesFM model (default: 64)'
    )
    
    parser.add_argument(
        '--num-samples',
        type=int,
        default=100,
        help='Number of sampling iterations (default: 100)'
    )
    
    parser.add_argument(
        '--model-name',
        type=str,
        default='timesfm-1.0-200m',
        help='TimesFM model variant to use (default: timesfm-1.0-200m)'
    )
    
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Parse current time if provided
    current_time = None
    if args.current_time:
        try:
            current_time = datetime.strptime(args.current_time, "%Y-%m-%d %H:%M:%S")
            print(f"Using specified current time: {current_time}")
        except ValueError:
            print("Error: Invalid time format. Use 'YYYY-MM-DD HH:MM:SS'")
            return 1
    
    try:
        # Initialize predictor
        predictor = TimesFMTweetPredictor(
            data_path=args.data_path,
            save_plots=not args.no_plots
        )
        
        # Prepare model - fast or normal mode
        if args.fast:
            print("⚡ FAST MODE: Reduced context and sampling for speed")
            predictor.prepare_model(
                context_len=48,
                horizon_len=7,
                num_samples=50,
                quantiles=[0.1, 0.9],
                model_name=args.model_name
            )
        else:
            print("🔵 NORMAL MODE: Standard TimesFM configuration")
            predictor.prepare_model(
                context_len=args.context_len,
                horizon_len=7,
                num_samples=args.num_samples,
                quantiles=[0.1, 0.9],
                model_name=args.model_name
            )
        
        # Generate predictions
        predictions = predictor.generate_predictions(current_time)
        
        # Print summary
        predictor.print_prediction_summary(predictions)
        
        # Create plots if enabled
        if not args.no_plots:
            predictor.plot_predictions(predictions)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 