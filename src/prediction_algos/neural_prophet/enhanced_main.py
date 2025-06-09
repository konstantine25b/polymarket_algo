"""
Main command-line interface for Enhanced Neural Prophet tweet count predictor.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .enhanced_predictor import EnhancedNeuralTweetPredictor


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Enhanced Neural Prophet Tweet Count Predictor')
    
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
        # Initialize enhanced predictor
        predictor = EnhancedNeuralTweetPredictor(
            data_path=args.data_path,
            save_plots=not args.no_plots
        )
        
        # Generate enhanced predictions
        predictions = predictor.generate_enhanced_predictions(current_time)
        
        # Print enhanced summary
        predictor.print_enhanced_summary(predictions)
        
        # Create enhanced plots if enabled
        if not args.no_plots:
            predictor.plot_enhanced_predictions(predictions)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 