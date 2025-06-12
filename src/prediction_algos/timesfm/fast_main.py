"""
Ultra-fast command-line interface for TimesFM tweet count predictor.
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
    parser = argparse.ArgumentParser(description='Ultra-Fast TimesFM Foundation Model Tweet Count Predictor')
    
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
        '--ultra-fast',
        action='store_true',
        help='Use ultra-fast settings (32 context, 10 samples, ~3 seconds)'
    )
    
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Use fast settings (48 context, 50 samples, ~10 seconds)'
    )
    
    parser.add_argument(
        '--normal',
        action='store_true',
        help='Use normal settings (64 context, 100 samples, ~20 seconds) - DEFAULT'
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
        
        # Prepare model with ultra-fast, fast, or normal settings
        if args.ultra_fast:
            print("🚀 ULTRA-FAST MODE: 32 context, 10 samples, minimal processing")
            predictor.prepare_model(
                context_len=32,
                horizon_len=7,
                num_samples=10,
                quantiles=[0.1, 0.9],
                model_name="timesfm-1.0-200m"
            )
        elif args.fast:
            print("⚡ FAST MODE: 48 context, 50 samples, optimized performance")
            predictor.prepare_model(
                context_len=48,
                horizon_len=7,
                num_samples=50,
                quantiles=[0.1, 0.9],
                model_name="timesfm-1.0-200m"
            )
        else:
            print("🔵 NORMAL MODE: 64 context, 100 samples, balanced accuracy")
            # Use the default normal settings
            predictor.prepare_model(
                context_len=64,
                horizon_len=7,
                num_samples=100,
                quantiles=[0.1, 0.9],
                model_name="timesfm-1.0-200m"
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