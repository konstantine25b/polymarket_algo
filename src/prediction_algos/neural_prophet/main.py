"""
Main command-line interface for Neural Prophet tweet count predictor.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .predictor import NeuralTweetPredictor


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Neural Prophet Tweet Count Predictor')
    
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
        help='Use fast mode (30 epochs instead of 50)'
    )
    
    parser.add_argument(
        '--epochs',
        type=int,
        default=100,
        help='Number of training epochs for Neural Prophet (default: 100)'
    )
    
    parser.add_argument(
        '--learning-rate',
        type=float,
        default=0.1,
        help='Learning rate for Neural Prophet training (default: 0.1)'
    )
    
    parser.add_argument(
        '--n-lags',
        type=int,
        default=7,
        help='Number of lag features to use (default: 7)'
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
        predictor = NeuralTweetPredictor(
            data_path=args.data_path,
            save_plots=not args.no_plots
        )
        
        # Prepare model - fast or normal mode
        if args.fast:
            print("⚡ FAST MODE: 30 epochs, optimized for speed")
            predictor.prepare_model(epochs=30, learning_rate=0.2)
        else:
            print("🔵 NORMAL MODE: 50 epochs, enhanced accuracy")
            predictor.prepare_model()  # Use default 50 epochs
        
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
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 