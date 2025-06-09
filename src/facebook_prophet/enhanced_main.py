#!/usr/bin/env python3
"""
Enhanced main script to run improved Elon Musk tweet count predictions.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from facebook_prophet import EnhancedTweetPredictor


def main():
    """Main function to run enhanced tweet predictions."""
    parser = argparse.ArgumentParser(
        description="Enhanced Elon Musk tweet count predictions using multiple forecasting methods"
    )
    
    parser.add_argument(
        '--data-path', 
        type=str, 
        default=None,
        help='Path to tweet data CSV file (default: uses path from constants.py)'
    )
    
    parser.add_argument(
        '--current-time',
        type=str,
        default=None,
        help='Current time for prediction context (format: YYYY-MM-DD HH:MM:SS)'
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
    
    # Initialize enhanced predictor
    print("Initializing Enhanced Tweet Predictor...")
    predictor = EnhancedTweetPredictor(data_path=args.data_path)
    
    try:
        # Generate enhanced predictions
        print("Generating enhanced predictions...")
        predictions = predictor.generate_enhanced_predictions(current_time=current_time)
        
        # Print enhanced summary
        predictor.print_enhanced_summary(predictions)
        
        print("\nEnhanced prediction completed successfully!")
        
    except Exception as e:
        print(f"Error during prediction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 