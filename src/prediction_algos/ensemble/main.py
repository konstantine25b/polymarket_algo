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
    parser.add_argument('--no-plots', action='store_true',
                        help='Disable plot generation')
    
    # Model weight controls
    parser.add_argument('--neural-prophet-weight', type=float, default=0.33,
                        help='Weight for Neural Prophet model (0 to exclude)')
    parser.add_argument('--facebook-prophet-weight', type=float, default=0.34,
                        help='Weight for Facebook Prophet model (0 to exclude)')
    parser.add_argument('--timesfm-weight', type=float, default=0.33,
                        help='Weight for TimesFM model (0 to exclude)')
    
    # Additional prediction methods
    parser.add_argument('--no-moving-average', action='store_true',
                        help='Disable moving average predictions')
    parser.add_argument('--no-linear-trend', action='store_true',
                        help='Disable linear trend predictions')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate weights
    total_weight = args.neural_prophet_weight + args.facebook_prophet_weight + args.timesfm_weight
    has_additional_methods = not args.no_moving_average or not args.no_linear_trend
    
    if total_weight <= 0 and not has_additional_methods:
        print("❌ Error: At least one model weight must be greater than 0, or additional methods must be enabled!")
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
        
        # Display configuration
        print(f"📊 Model Weights:")
        if args.neural_prophet_weight > 0:
            print(f"   Neural Prophet: {args.neural_prophet_weight:.3f}")
        else:
            print(f"   Neural Prophet: DISABLED")
        
        if args.facebook_prophet_weight > 0:
            print(f"   Facebook Prophet: {args.facebook_prophet_weight:.3f}")
        else:
            print(f"   Facebook Prophet: DISABLED")
        
        if args.timesfm_weight > 0:
            print(f"   TimesFM: {args.timesfm_weight:.3f}")
        else:
            print(f"   TimesFM: DISABLED")
        
        additional_methods = []
        if not args.no_moving_average:
            additional_methods.append("Moving Average")
        if not args.no_linear_trend:
            additional_methods.append("Linear Trend")
        
        if additional_methods:
            print(f"📈 Additional Methods: {', '.join(additional_methods)}")
        else:
            print(f"📈 Additional Methods: DISABLED")
        
        if args.fast:
            print("⚡ FAST MODE: Using fast individual models")
        
        print()
        
        # Initialize ensemble predictor
        predictor = EnsembleTweetPredictor(
            data_path=args.data_path,
            save_plots=not args.no_plots,
            use_fast_models=args.fast,
            neural_prophet_weight=args.neural_prophet_weight,
            facebook_prophet_weight=args.facebook_prophet_weight,
            timesfm_weight=args.timesfm_weight,
            include_moving_average=not args.no_moving_average,
            include_linear_trend=not args.no_linear_trend
        )
        
        # Prepare models
        predictor.prepare_models(fast_mode=args.fast)
        
        # Generate predictions
        prediction_summary = predictor.generate_predictions(current_time)
        
        # Print results
        predictor.print_prediction_summary(prediction_summary)
        
        # Generate plots
        if not args.no_plots:
            predictor.plot_predictions(prediction_summary)
        
    except KeyboardInterrupt:
        print("\n🛑 Prediction interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 