"""
Main CLI interface for the ensemble tweet prediction model.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from prediction_algos.ensemble import EnsembleTweetPredictor


def main():
    parser = argparse.ArgumentParser(description='Ensemble Tweet Count Predictor')
    
    # Basic options
    parser.add_argument('--data-path', type=str, default=None,
                        help='Path to tweet data CSV file')
    parser.add_argument('--current-time', type=str, default=None,
                        help='Current time in YYYY-MM-DD HH:MM:SS format')
    parser.add_argument('--fast', action='store_true',
                        help='Use fast mode for quicker training')
    parser.add_argument('--plots', action='store_true',
                        help='Enable plot generation (disabled by default)')
    
    # Model weight controls - Updated defaults
    parser.add_argument('--neural-prophet-weight', type=float, default=0.15,
                        help='Weight for Neural Prophet model (0 to exclude)')
    parser.add_argument('--facebook-prophet-weight', type=float, default=0.40,
                        help='Weight for Facebook Prophet model (0 to exclude)')
    parser.add_argument('--timesfm-weight', type=float, default=0.40,
                        help='Weight for TimesFM model (0 to exclude)')
    parser.add_argument('--moving-average-weight', type=float, default=0.025,
                        help='Weight for moving average predictions (0 to exclude)')
    parser.add_argument('--linear-trend-weight', type=float, default=0.025,
                        help='Weight for linear trend predictions (0 to exclude)')
    
    # Legacy flags for backward compatibility
    parser.add_argument('--no-moving-average', action='store_true',
                        help='Disable moving average predictions (legacy)')
    parser.add_argument('--no-linear-trend', action='store_true',
                        help='Disable linear trend predictions (legacy)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle legacy flags - override weights if legacy flags are used
    if args.no_moving_average:
        args.moving_average_weight = 0.0
    if args.no_linear_trend:
        args.linear_trend_weight = 0.0
    
    # Validate that at least one method is enabled
    total_weight = (args.neural_prophet_weight + args.facebook_prophet_weight + 
                   args.timesfm_weight + args.moving_average_weight + args.linear_trend_weight)
    
    if total_weight <= 0:
        print("❌ Error: At least one prediction method must have weight > 0!")
        sys.exit(1)
    
    # Parse current time if provided
    current_time = None
    if args.current_time:
        try:
            current_time = datetime.strptime(args.current_time, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            print("❌ Error: Invalid time format. Use YYYY-MM-DD HH:MM:SS")
            sys.exit(1)
    
    try:
        print("🔥 Ensemble Tweet Count Predictor")
        print("=" * 50)
        
        # Display configuration - only show active methods
        print(f"📊 Model Weights:")
        if args.neural_prophet_weight > 0:
            print(f"   Neural Prophet: {args.neural_prophet_weight:.1%}")
        if args.facebook_prophet_weight > 0:
            print(f"   Facebook Prophet: {args.facebook_prophet_weight:.1%}")
        if args.timesfm_weight > 0:
            print(f"   TimesFM: {args.timesfm_weight:.1%}")
        if args.moving_average_weight > 0:
            print(f"   Moving Average: {args.moving_average_weight:.1%}")
        if args.linear_trend_weight > 0:
            print(f"   Linear Trend: {args.linear_trend_weight:.1%}")
        
        if args.fast:
            print("⚡ FAST MODE: Using optimized training")
        
        print()
        
        # Initialize ensemble predictor
        predictor = EnsembleTweetPredictor(
            data_path=args.data_path,
            save_plots=args.plots,
            use_fast_models=args.fast,
            neural_prophet_weight=args.neural_prophet_weight,
            facebook_prophet_weight=args.facebook_prophet_weight,
            timesfm_weight=args.timesfm_weight,
            moving_average_weight=args.moving_average_weight,
            linear_trend_weight=args.linear_trend_weight,
            include_moving_average=args.moving_average_weight > 0,
            include_linear_trend=args.linear_trend_weight > 0
        )
        
        # Prepare models
        predictor.prepare_models(fast_mode=args.fast)
        
        # Generate predictions
        prediction_summary = predictor.generate_predictions(current_time)
        
        # Print results
        predictor.print_prediction_summary(prediction_summary)
        
        # Generate plots
        if args.plots:
            predictor.plot_predictions(prediction_summary)
        
    except KeyboardInterrupt:
        print("\n🛑 Prediction interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 