"""
Main CLI interface for the ensemble tweet prediction model.
"""

import argparse
import sys
import numpy as np
import random
import os
from pathlib import Path
from datetime import datetime
from pytz import timezone

# Set deterministic behavior for PyTorch/Lightning (before importing Neural Prophet)
try:
    import torch
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(42)
        torch.cuda.manual_seed_all(42)
    # PyTorch Lightning specific settings
    import pytorch_lightning as pl
    pl.seed_everything(42, workers=True)
except ImportError:
    pass

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from prediction_algos.ensemble import EnsembleTweetPredictor
from constants import TWEET_COUNT_FRAMES

# Define the timezone
ET_TIMEZONE = timezone('US/Eastern')

def main():
    parser = argparse.ArgumentParser(description='Ensemble Tweet Prediction using multiple models')
    parser.add_argument('--data-path', type=str, 
                        help='Path to tweet data CSV file')
    parser.add_argument('--current-time', type=str,
                        help='Current time for prediction (YYYY-MM-DD HH:MM:SS format)')
    parser.add_argument('--fast', action='store_true',
                        help='Use fast model variants for quicker predictions')
    parser.add_argument('--no-plots', action='store_true', default=True,
                        help='Disable plot generation (default: True)')
    parser.add_argument('--plots', action='store_true',
                        help='Enable plot generation')
    parser.add_argument('--ensemble-method', type=str, default='weighted_average',
                        choices=['weighted_average', 'median', 'best_performer'],
                        help='Ensemble combination method')
    parser.add_argument('--random-seed', type=int, default=42,
                        help='Random seed for reproducible results (default: 42)')
    
    parser.add_argument('--show-eachalgo-distribution',
                        action='store_true',
                        help='Show probability distribution for each individual algorithm in the ensemble')
    
    # Model weight arguments with new defaults
    parser.add_argument('--neural-prophet-weight', type=float, default=0.17,
                        help='Weight for Neural Prophet model (default: 0.17)')
    parser.add_argument('--facebook-prophet-weight', type=float, default=0.25,
                        help='Weight for Facebook Prophet model (default: 0.25)')
    parser.add_argument('--timesfm-weight', type=float, default=0.30,
                        help='Weight for TimesFM model (default: 0.30)')
    parser.add_argument('--basic-prophet-weight', type=float, default=0.25,
                        help='Weight for Basic Prophet model (default: 0.25)')
    parser.add_argument('--moving-average-weight', type=float, default=0.015,
                        help='Weight for moving average method (default: 0.015)')
    parser.add_argument('--linear-trend-weight', type=float, default=0.015,
                        help='Weight for linear trend method (default: 0.015)')
    
    args = parser.parse_args()
    
    # Set random seeds for reproducible results
    seed = args.random_seed
    np.random.seed(seed)
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    
    # Set PyTorch seeds again with the actual seed from args
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
        # PyTorch Lightning specific settings with actual seed
        import pytorch_lightning as pl
        pl.seed_everything(seed, workers=True)
    except ImportError:
        pass
    
    # Parse current time if provided
    current_time = None
    if args.current_time:
        try:
            current_time = ET_TIMEZONE.localize(
                datetime.strptime(args.current_time, "%Y-%m-%d %H:%M:%S")
            )
        except ValueError:
            print("Error: Invalid time format. Use YYYY-MM-DD HH:MM:SS")
            return
    
    # Initialize ensemble predictor with custom weights
    try:
        # Determine if plots should be enabled
        enable_plots = args.plots and not args.no_plots
        
        predictor = EnsembleTweetPredictor(
            data_path=args.data_path,
            save_plots=enable_plots,
            use_fast_models=args.fast,
            neural_prophet_weight=args.neural_prophet_weight,
            facebook_prophet_weight=args.facebook_prophet_weight,
            timesfm_weight=args.timesfm_weight,
            basic_prophet_weight=args.basic_prophet_weight,
            moving_average_weight=args.moving_average_weight,
            linear_trend_weight=args.linear_trend_weight,
            random_seed=args.random_seed
        )
        
        # Generate predictions
        prediction_summary = predictor.generate_predictions(current_time)
        
        # Show individual algorithm distributions if requested
        if args.show_eachalgo_distribution:
            predictor.print_individual_algorithm_distributions(prediction_summary)
        
        # Print results
        predictor.print_prediction_summary(prediction_summary)
        
        # Create plots if enabled
        if enable_plots:
            predictor.plot_predictions(prediction_summary)
        
        # Print time frame probabilities  
        print("\nPredicted probabilities for tweet count frames:")
        print("-" * 50)
        
        # Show ALL frames in order (from TWEET_COUNT_FRAMES), not just non-zero ones
        for frame in TWEET_COUNT_FRAMES:
            frame_name = frame['name']
            frame_data = prediction_summary['predictions_by_frame'][frame_name]
            prob = frame_data['probability']
            range_str = frame_data['range']
            print(f"{frame_name:20s}: {prob:7.4f} ({prob*100:6.2f}%) [{range_str}]")
        
        print("-" * 50)
        total_prob = sum(data['probability'] for data in prediction_summary['predictions_by_frame'].values())
        print(f"{'TOTAL':20s}: {total_prob:7.4f} (100.00%)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 