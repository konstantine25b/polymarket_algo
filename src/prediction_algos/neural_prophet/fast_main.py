"""
Ultra-fast command-line interface for single Neural Prophet tweet count predictor.
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
    parser = argparse.ArgumentParser(description='Ultra-Fast Neural Prophet Tweet Count Predictor')
    
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
        help='Use ultra-fast settings (15 epochs, ~5 seconds)'
    )
    
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Use fast settings (30 epochs, ~30 seconds)'
    )
    
    parser.add_argument(
        '--normal',
        action='store_true',
        help='Use normal settings (50 epochs, ~60 seconds) - DEFAULT'
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
        
        # Prepare model with ultra-fast, fast, or normal settings
        if args.ultra_fast:
            print("🚀 ULTRA-FAST MODE: 15 epochs, LR=0.4, minimal features")
            predictor.prepare_model(
                epochs=15,
                learning_rate=0.4,
                yearly_seasonality=False,  # Disable for max speed
                weekly_seasonality=True,   # Keep only weekly
                daily_seasonality=False,   # Disable
            )
        elif args.fast:
            print("⚡ FAST MODE: 30 epochs, LR=0.2, optimized features")
            predictor.prepare_model(
                epochs=30,
                learning_rate=0.2,
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=False,
            )
        else:
            print("🔵 NORMAL MODE: 50 epochs, LR=0.15, enhanced features")
            # Use the default normal settings (50 epochs)
            predictor.prepare_model()
        
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