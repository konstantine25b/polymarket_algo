import os
import argparse
import pandas as pd
from src.algos.elon_tweet_predictor.data_loader import TweetDataLoader
from src.algos.elon_tweet_predictor.pattern_analyzer import TweetPatternAnalyzer
from src.algos.elon_tweet_predictor.predictor import TweetPredictor
from src.algos.elon_tweet_predictor.evaluator import PredictionEvaluator
from src.algos.elon_tweet_predictor.visualizer import TweetVisualizer
from src.utils.file_utils import get_data_path

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

    args = parser.parse_args()
    
    # Parse hours if provided
    specific_hours = None
    if args.hours:
        try:
            specific_hours = [int(h.strip()) for h in args.hours.split(',')]
        except ValueError:
            print("Warning: Invalid hours format. Please use comma-separated integers (e.g., 9,12,18)")
    
    # Determine file path
    file_path = args.file
    if not file_path:
        data_path = get_data_path('elonmusk_reformatted.csv')
        print(f"\nLoading data from: {data_path}")
    else:
        data_path = file_path

    try:
        # Initialize components
        data_loader = TweetDataLoader()
        
        if data_loader.load_data(data_path):
            # Create analyzer with loaded data
            analyzer = TweetPatternAnalyzer(data_loader.df)
            analyzer.analyze_patterns()
            
            # Create predictor with analyzer
            predictor = TweetPredictor(analyzer)
            
            # Create evaluator and visualizer
            evaluator = PredictionEvaluator(predictor, analyzer)
            visualizer = TweetVisualizer(analyzer)
            
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
            print("Failed to load data. Please check your input file.")
    except FileNotFoundError:
        print(f"Error loading data: File not found at {data_path}")
        print("Please ensure the data file exists in the data directory.")
    except Exception as e:
        import traceback
        print(f"\nError: {str(e)}")
        print(traceback.format_exc())
        print("Please check your input data and parameters")

if __name__ == "__main__":
    main() 