import os
import argparse
import pandas as pd
from src.algos.elon_tweet_predictor.data_loader import TweetDataLoader
from src.algos.elon_tweet_predictor.pattern_analyzer import TweetPatternAnalyzer
from src.algos.elon_tweet_predictor.predictor import TweetPredictor
from src.algos.elon_tweet_predictor.evaluator import PredictionEvaluator
from src.algos.elon_tweet_predictor.visualizer import TweetVisualizer
from src.algos.elon_tweet_predictor.predictor.logging_utils import setup_logger, LOG_LEVELS
from src.utils.file_utils import get_data_path

"""
Elon Musk Tweet Count Predictor

This script is the main entry point for the tweet prediction system. It orchestrates the
workflow of loading tweet data, analyzing patterns, making predictions, and optionally
visualizing the results or evaluating prediction accuracy.

The script supports multiple prediction modes:
- Predicting for a specific target date
- Predicting for N days ahead 
- Predicting for the next N hours
- Predicting for specific hours of the day

Command line options:
--file            Path to a reformatted CSV file containing tweet data
--date            Target date to predict (YYYY-MM-DD)
--days            Number of days to predict (default: 7)
--hours           Comma-separated list of specific hours (0-23) to predict (e.g., 9,12,18)
--next-hours      Predict for the next N hours instead of full days
--plot            Generate activity visualization plots
--precision       Evaluate prediction precision against historical data
--days-back       Number of days back for precision evaluation (default: 14)
--all-hours       Display tweet counts for all 24 hours
--no-trend        Disable trend adjustment (use historical averages only)
--verbose, -v     Verbosity level (SILENT, ERROR, WARNING, INFO, DEBUG, VERBOSE)
--log-file        Log to file instead of console
--detailed-logs   Show detailed log format with timestamps and module names (default is clean format)

Examples:
- Predict for the next 7 days: 
  python -m src.algos.elon_tweet_predictor.main

- Predict for a specific date with detailed logs:
  python -m src.algos.elon_tweet_predictor.main --date 2023-12-31 --detailed-logs

- Predict for the next 12 hours with debug information:
  python -m src.algos.elon_tweet_predictor.main --next-hours 12 --verbose DEBUG
"""

def main():
    parser = argparse.ArgumentParser(description='Elon Musk Tweet Count Predictor')
    parser.add_argument('--file', type=str, required=False,
                      help='Path to reformatted CSV file')
    parser.add_argument('--date', type=str, 
                      help='Target date to predict (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=7,
                      help='Number of days to predict (default: 7)')
    parser.add_argument('--hours', type=str,
                      help='Comma-separated list of specific hours (0-23) to include in prediction (e.g., 9,12,18)')
    parser.add_argument('--next-hours', type=int,
                      help='Predict for the next N hours instead of full days (e.g., 4)')
    parser.add_argument('--plot', action='store_true',
                      help='Generate activity plots')
    parser.add_argument('--precision', action='store_true',
                      help='Evaluate prediction precision')
    parser.add_argument('--days-back', type=int, default=14,
                      help='Number of days back for precision evaluation (default: 14)')
    parser.add_argument('--all-hours', action='store_true',
                      help='Display tweet counts for all 24 hours')
    parser.add_argument('--no-trend', action='store_true',
                      help='Disable trend adjustment (use historical averages only)')
    parser.add_argument('--verbose', '-v', type=str, choices=list(LOG_LEVELS.keys()), default='INFO',
                      help='Verbosity level (SILENT, ERROR, WARNING, INFO, DEBUG, VERBOSE)')
    parser.add_argument('--log-file', type=str,
                      help='Log to file instead of console')
    parser.add_argument('--detailed-logs', action='store_true',
                      help='Show detailed log format with timestamps and module names')

    args = parser.parse_args()
    
    # Set up logging with clean format by default
    logger = setup_logger(level=args.verbose, log_file=args.log_file, clean_format=not args.detailed_logs)
    
    # Parse hours if provided
    specific_hours = None
    if args.hours:
        try:
            specific_hours = [int(h.strip()) for h in args.hours.split(',')]
        except ValueError:
            logger.warning("Invalid hours format. Please use comma-separated integers (e.g., 9,12,18)")
    
    # Determine file path
    file_path = args.file
    if not file_path:
        data_path = get_data_path('elonmusk_reformatted.csv')
        logger.info(f"Loading data from: {data_path}")
    else:
        data_path = file_path

    try:
        # Initialize components
        data_loader = TweetDataLoader(logger=logger)
        
        if data_loader.load_data(data_path):
            # Create analyzer with loaded data
            analyzer = TweetPatternAnalyzer(data_loader.df, logger=logger)
            analyzer.analyze_patterns()
            
            # Create predictor with analyzer
            predictor = TweetPredictor(analyzer, logger=logger)
            
            # Create evaluator and visualizer
            evaluator = PredictionEvaluator(predictor, analyzer, logger=logger)
            visualizer = TweetVisualizer(analyzer, logger=logger)
            
            if args.all_hours:
                analyzer.display_hourly_averages()
                
            if args.precision:
                precision_results = evaluator.evaluate_precision(days_back=args.days_back)
                if precision_results and args.plot:
                    visualizer.plot_precision_results(precision_results)
            
            # If next-hours is specified, use that prediction method
            if args.next_hours:
                predictor.predict_next_hours(hours_ahead=args.next_hours, use_trend=not args.no_trend)
            # Otherwise use the standard date/days prediction
            elif args.date:
                predictor.predict_count(target_date_str=args.date, use_trend=not args.no_trend, hours=specific_hours)
            else:
                predictor.predict_count(days=args.days, use_trend=not args.no_trend, hours=specific_hours)
                
            if args.plot:
                visualizer.plot_activity()
        else:
            logger.error("Failed to load data. Please check your input file.")
    except FileNotFoundError:
        logger.error(f"Error loading data: File not found at {data_path}")
        logger.error("Please ensure the data file exists in the data directory.")
    except Exception as e:
        import traceback
        logger.error(f"Error: {str(e)}")
        logger.debug(traceback.format_exc())
        logger.error("Please check your input data and parameters")

if __name__ == "__main__":
    main() 