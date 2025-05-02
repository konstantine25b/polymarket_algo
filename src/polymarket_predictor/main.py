import os
import argparse
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import sys
import json
from typing import Dict, List, Tuple, Optional

# Import local modules
from src.polymarket_predictor.time_utils import parse_timestamp, get_current_et_time
from src.polymarket_predictor.data_processing import (
    load_and_validate_tweet_data,
    verify_tweet_count,
    count_tweets_in_timeframe
)
from src.polymarket_predictor.market_api import get_count_frames
from src.polymarket_predictor.analysis import (
    analyze_tweet_patterns,
    calculate_time_periods,
    calculate_predictions
)
from src.polymarket_predictor.simulation import (
    run_monte_carlo_simulation,
    calculate_confidence_interval,
    map_final_count_to_frame
)
from src.polymarket_predictor.visualization import (
    plot_monte_carlo_simulation,
    plot_historical_trends
)
# Import enhanced prediction module
from src.polymarket_predictor.enhanced_prediction import (
    predict_with_enhanced_algorithm
)
# Import Prophet prediction module
from src.polymarket_predictor.prophet_prediction import (
    predict_with_prophet
)

# Import constants
from src.constants import (
    ET_TIMEZONE,
    DEFAULT_DATA_PATH,
    POLYMARKET_START_TIME,
    POLYMARKET_END_TIME,
    TWEET_COUNT_FRAMES
)

def predict_tweet_frame_probabilities(
    data_path=DEFAULT_DATA_PATH, 
    start_date_str=None, 
    end_date_str=None, 
    data_file=None, 
    use_trend=True, 
    num_simulations=5000, 
    current_tweet_count=None,
    override_auto_count=False,
    use_enhanced_algorithm=True,  # New parameter to use enhanced algorithm
    use_prophet_algorithm=False   # New parameter to use Prophet algorithm
) -> Optional[Dict[str, float]]:
    """
    Predict probabilities for tweet count frames with robust timezone handling
    
    Args:
        data_path: Path to the tweet data CSV file (default path used if not provided)
        start_date_str: Start date/time string in format 'YYYY-MM-DD HH:MM:SS' (ET timezone)
        end_date_str: End date/time string in format 'YYYY-MM-DD HH:MM:SS' (ET timezone)
        data_file: Alternative path to tweet data (overrides data_path if provided)
        use_trend: Whether to use trend adjustment in predictions
        num_simulations: Number of Monte Carlo simulations to run
        current_tweet_count: Manual override for current tweet count
        override_auto_count: Whether to use the provided current_tweet_count instead of auto-counting
        use_enhanced_algorithm: Whether to use the enhanced prediction algorithm
        use_prophet_algorithm: Whether to use the Prophet-based prediction algorithm
        
    Returns:
        Dictionary mapping tweet count frames to probabilities
    """
    # Use data_file parameter if provided (for backward compatibility)
    if data_file is not None:
        data_path = data_file
        
    # Use provided date strings if available, otherwise use constants
    start_time = start_date_str if start_date_str is not None else POLYMARKET_START_TIME
    end_time = end_date_str if end_date_str is not None else POLYMARKET_END_TIME
    
    # Get count frames from API or constants
    count_frames = get_count_frames()
    
    # Load and preprocess tweet data
    df = load_and_validate_tweet_data(data_path)
    if df.empty:
        print("Error: Failed to load tweet data")
        return None
    
    # Parse start and end times with robust timezone handling
    try:
        polymarket_start = ET_TIMEZONE.localize(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S"), is_dst=None)
    except Exception as e:
        print(f"Warning: Error parsing start time {start_time}: {e}")
        print("Using default start time from constants")
        polymarket_start = ET_TIMEZONE.localize(datetime.strptime(POLYMARKET_START_TIME, "%Y-%m-%d %H:%M:%S"), is_dst=None)
        
    try:
        polymarket_end = ET_TIMEZONE.localize(datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S"), is_dst=None)
    except Exception as e:
        print(f"Warning: Error parsing end time {end_time}: {e}")
        print("Using default end time from constants")
        polymarket_end = ET_TIMEZONE.localize(datetime.strptime(POLYMARKET_END_TIME, "%Y-%m-%d %H:%M:%S"), is_dst=None)
    
    # Get current time
    now = get_current_et_time()
    
    print(f"Current time (ET): {now}")
    print(f"Analysis time range (ET): {polymarket_start} to {polymarket_end}")
    
    # Check if the event is still ongoing
    if now > polymarket_end:
        print("Event has ended. Calculating final results...")
        tweets_in_window = df[(df['created_at_dt'] >= polymarket_start) & (df['created_at_dt'] <= polymarket_end)]
        final_count = len(tweets_in_window)
        print(f"Final tweet count: {final_count}")
        
        # Map the final count to a frame
        winning_frame = map_final_count_to_frame(final_count, count_frames)
        if winning_frame:
            print(f"Final count falls in the '{winning_frame}' frame")
            
            # Return 100% probability for the winning frame
            frame_probabilities = {frame["name"]: 0.0 for frame in count_frames}
            frame_probabilities[winning_frame] = 100.0
            
            return frame_probabilities
        else:
            print(f"Error: Could not map final count {final_count} to any frame")
            return None
    
    # Event is still ongoing, calculate predictions
    print("Event is still ongoing. Calculating predictions...")
    
    # First determine the current tweet count (auto or manual)
    if override_auto_count and current_tweet_count is not None:
        # Use manual count
        tweet_count = current_tweet_count
        print(f"Using manually specified tweet count: {tweet_count}")
    else:
        # Auto-count tweets
        tweets_so_far = df[(df['created_at_dt'] >= polymarket_start) & (df['created_at_dt'] <= now)]
        tweet_count = len(tweets_so_far)
        print(f"Using current tweet count of {tweet_count} tweets")
    
    # Use Prophet algorithm if specified
    if use_prophet_algorithm:
        print("\nUsing Prophet-based prediction algorithm...")
        
        # Run Prophet prediction
        prophet_results = predict_with_prophet(
            df=df,
            polymarket_start=polymarket_start,
            polymarket_end=polymarket_end,
            count_frames=count_frames,
            current_tweet_count=tweet_count,
            num_simulations=num_simulations
        )
        
        # Check if there was an error
        if 'error' in prophet_results:
            print(f"Error in Prophet prediction: {prophet_results['error']}")
            # Fall back to enhanced algorithm
            print("Falling back to enhanced algorithm...")
            use_enhanced_algorithm = True
            use_prophet_algorithm = False
        else:
            # Print prediction information
            print("\n--- Prophet Prediction Results ---")
            print(f"Expected final count: {prophet_results['expected_count']:.1f} tweets")
            print(f"95% confidence interval: {prophet_results['confidence_interval'][0]:.1f} to {prophet_results['confidence_interval'][1]:.1f} tweets")
            
            # Print predicted probabilities
            frame_probabilities = prophet_results['frame_probabilities']
            print(f"\nPredicted probabilities for tweet count frames ({polymarket_start} to {polymarket_end}, ET timezone):")
            
            # Order frames by the predefined order
            ordered_frames = []
            for frame in count_frames:
                ordered_frames.append((frame["name"], frame_probabilities[frame["name"]]))
            
            for frame_name, probability in ordered_frames:
                print(f"{frame_name}: {probability:.1f}%")
            
            # Present top 3 most likely outcomes
            print("\nTop 3 most likely outcomes:")
            sorted_by_prob = sorted(frame_probabilities.items(), key=lambda x: x[1], reverse=True)
            for i, (frame_name, probability) in enumerate(sorted_by_prob[:3]):
                if probability > 0:
                    print(f"{i+1}. {frame_name}: {probability:.1f}%")
            
            # Generate visualizations
            plot_monte_carlo_simulation(
                prophet_results['simulations'], 
                tweet_count, 
                prophet_results['expected_count'], 
                prophet_results['confidence_interval'], 
                count_frames, 
                frame_probabilities
            )
            
            plot_historical_trends(
                df,
                polymarket_start,
                polymarket_end,
                tweet_count,
                prophet_results['expected_count']
            )
            
            return frame_probabilities
    
    # Use enhanced algorithm if specified
    if use_enhanced_algorithm:
        print("\nUsing enhanced prediction algorithm...")
        
        # Run enhanced prediction
        enhanced_results = predict_with_enhanced_algorithm(
            df=df,
            polymarket_start=polymarket_start,
            polymarket_end=polymarket_end,
            count_frames=count_frames,
            current_tweet_count=tweet_count,
            num_simulations=num_simulations
        )
        
        # Extract analysis results
        analysis = enhanced_results['analysis']
        
        # Print analysis information
        print("\n--- Advanced Prediction Analysis ---")
        print(f"Prediction window (ET): {polymarket_start} to {polymarket_end} "
              f"({(polymarket_end - polymarket_start).total_seconds() / (24 * 3600):.1f} days)")
        print(f"Current tweet count: {tweet_count} tweets "
              f"({analysis['elapsed_days']:.2f} days elapsed, {analysis['remaining_days']:.2f} days remaining)")
        
        # Print historical rates
        print("\n--- Historical Rates (tweets/day) ---")
        for days, rate in analysis['rates'].items():
            print(f"{days}-day rate: {rate:.1f} (weight: {analysis['weights'][days]:.2f})")
        
        # Print trend information
        print(f"\nAcceleration factor: {analysis['acceleration_factor']:.2f}")
        
        # Print prediction information
        print("\n--- Prediction Results ---")
        print(f"Current rate: {analysis['current_rate']:.2f} tweets/day")
        print(f"Projected rate: {analysis['projected_rate']:.2f} tweets/day")
        print(f"Expected final count: {enhanced_results['expected_count']:.1f} tweets")
        print(f"95% confidence interval: {enhanced_results['confidence_interval'][0]:.1f} to {enhanced_results['confidence_interval'][1]:.1f} tweets")
        
        # Print predicted probabilities
        frame_probabilities = enhanced_results['frame_probabilities']
        print(f"\nPredicted probabilities for tweet count frames ({polymarket_start} to {polymarket_end}, ET timezone):")
        
        # Order frames by the predefined order
        ordered_frames = []
        for frame in count_frames:
            ordered_frames.append((frame["name"], frame_probabilities[frame["name"]]))
        
        for frame_name, probability in ordered_frames:
            print(f"{frame_name}: {probability:.1f}%")
        
        # Present top 3 most likely outcomes
        print("\nTop 3 most likely outcomes:")
        sorted_by_prob = sorted(frame_probabilities.items(), key=lambda x: x[1], reverse=True)
        for i, (frame_name, probability) in enumerate(sorted_by_prob[:3]):
            if probability > 0:
                print(f"{i+1}. {frame_name}: {probability:.1f}%")
        
        # Generate visualizations
        plot_monte_carlo_simulation(
            enhanced_results['simulations'], 
            tweet_count, 
            enhanced_results['expected_count'], 
            enhanced_results['confidence_interval'], 
            count_frames, 
            frame_probabilities
        )
        
        plot_historical_trends(
            df,
            polymarket_start,
            polymarket_end,
            tweet_count,
            enhanced_results['expected_count']
        )
        
        return frame_probabilities
    
    else:
        # Use original algorithm
        print("\nUsing original prediction algorithm...")
        
        # Calculate time periods and tweet rates
        time_analysis = calculate_time_periods(df, polymarket_start, polymarket_end)
        
        # Update the tweet count in the analysis
        time_analysis['tweet_count'] = tweet_count
        
        # Print analysis information
        print("\n--- Advanced Prediction Analysis ---")
        print(f"Prediction window (ET): {polymarket_start} to {polymarket_end} "
              f"({(polymarket_end - polymarket_start).total_seconds() / (24 * 3600):.1f} days)")
        print(f"Current tweet count: {tweet_count} tweets "
              f"({time_analysis['elapsed_days']:.2f} days elapsed, {time_analysis['remaining_days']:.2f} days remaining)")
        print(f"Historical daily average: {time_analysis['historical_avg']:.1f} tweets per day")
        print(f"Recent rates: 7-day: {time_analysis['rate_7d']:.1f}, "
              f"14-day: {time_analysis['rate_14d']:.1f}, 30-day: {time_analysis['rate_30d']:.1f} tweets/day")
        print(f"Trend factors: 7-day: {time_analysis['trend_7d']:.2f}, "
              f"14-day: {time_analysis['trend_14d']:.2f}, 30-day: {time_analysis['trend_30d']:.2f}")
        
        # Calculate predictions
        predictions = calculate_predictions(time_analysis, use_trend)
        
        # Print prediction models
        print("\n--- Prediction Models ---")
        print(f"Current count (lower bound): {predictions['current_count']:.1f} tweets")
        print(f"Simple linear prediction: {predictions['base_prediction']:.1f} tweets")
        print(f"Trend-adjusted prediction: {predictions['trend_adjusted_prediction']:.1f} tweets")
        print(f"Weekday-adjusted prediction: {predictions['weekday_adjusted_prediction']:.1f} tweets")
        print(f"Ensemble prediction: {predictions['ensemble_prediction']:.1f} tweets")
        
        # Use ensemble prediction as the final prediction
        final_prediction = predictions['ensemble_prediction']
        
        # Calculate confidence interval
        std_dev = time_analysis['daily_std'] * (time_analysis['remaining_days']**0.5)
        confidence_interval = calculate_confidence_interval(final_prediction, std_dev)
        
        print(f"95% confidence interval: {confidence_interval[0]:.1f} to {confidence_interval[1]:.1f} tweets")
        
        # Run Monte Carlo simulation
        simulations, frame_probabilities = run_monte_carlo_simulation(
            final_prediction,
            std_dev,
            tweet_count,
            count_frames,
            num_simulations
        )
        
        # Print predicted probabilities
        print(f"\nPredicted probabilities for tweet count frames ({polymarket_start} to {polymarket_end}, ET timezone):")
        
        # Order frames by the predefined order
        ordered_frames = []
        for frame in count_frames:
            ordered_frames.append((frame["name"], frame_probabilities[frame["name"]]))
        
        for frame_name, probability in ordered_frames:
            print(f"{frame_name}: {probability:.1f}%")
        
        # Present top 3 most likely outcomes
        print("\nTop 3 most likely outcomes:")
        sorted_by_prob = sorted(frame_probabilities.items(), key=lambda x: x[1], reverse=True)
        for i, (frame_name, probability) in enumerate(sorted_by_prob[:3]):
            if probability > 0:
                print(f"{i+1}. {frame_name}: {probability:.1f}%")
        
        # Generate visualizations
        plot_monte_carlo_simulation(
            simulations, 
            tweet_count, 
            final_prediction, 
            confidence_interval, 
            count_frames, 
            frame_probabilities
        )
        
        plot_historical_trends(
            df,
            polymarket_start,
            polymarket_end,
            tweet_count,
            final_prediction
        )
        
        return frame_probabilities

def main():
    """Command line entry point"""
    parser = argparse.ArgumentParser(description='Predict Elon Musk tweet counts')
    parser.add_argument('--verify-count', action='store_true', help='Verify tweet count in a specific timeframe')
    parser.add_argument('--data-path', type=str, default=DEFAULT_DATA_PATH, help='Path to tweet data CSV')
    parser.add_argument('--start-time', type=str, help='Start time in format YYYY-MM-DD HH:MM:SS')
    parser.add_argument('--end-time', type=str, help='End time in format YYYY-MM-DD HH:MM:SS')
    parser.add_argument('--no-trend', action='store_true', help='Disable trend adjustment')
    parser.add_argument('--simulations', type=int, default=10000, help='Number of Monte Carlo simulations')
    parser.add_argument('--count', type=int, help='Override current tweet count')
    parser.add_argument('--classic', action='store_true', help='Use classic algorithm instead of enhanced')
    parser.add_argument('--prophet', action='store_true', help='Use Prophet-based algorithm for prediction')
    parser.add_argument('--json', action='store_true', help='Output prediction results in JSON format')
    parser.add_argument('--output', type=str, help='Save JSON output to the specified file')
    parser.add_argument('--brief', action='store_true', help='Output JSON data only without additional text or logging')
    
    args = parser.parse_args()
    
    # Set up brief mode if requested
    original_stdout = None
    if args.brief and args.json:
        # Suppress logging output
        logging.getLogger().setLevel(logging.ERROR)
        # Save original stdout and redirect to /dev/null
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
    
    if args.verify_count:
        # Use provided times or defaults
        start_time = args.start_time if args.start_time else POLYMARKET_START_TIME
        end_time = args.end_time if args.end_time else POLYMARKET_END_TIME
        verify_tweet_count(start_time, end_time, args.data_path)
    else:
        # Run prediction with specified parameters
        result = predict_tweet_frame_probabilities(
            data_path=args.data_path,
            start_date_str=args.start_time,
            end_date_str=args.end_time,
            use_trend=not args.no_trend,
            num_simulations=args.simulations,
            current_tweet_count=args.count,
            override_auto_count=args.count is not None,
            use_enhanced_algorithm=not args.classic and not args.prophet,
            use_prophet_algorithm=args.prophet
        )
        
        # Handle JSON output if requested
        if args.json and result:
            # Restore stdout if in brief mode
            if args.brief and original_stdout:
                sys.stdout = original_stdout
            
            # Create a structured JSON object
            now = datetime.now(ET_TIMEZONE)
            
            # Format frame probabilities
            frame_probs = {}
            for frame_name, probability in result.items():
                frame_probs[frame_name] = round(probability, 2)
            
            # Find most likely outcome
            most_likely = max(result.items(), key=lambda x: x[1])
            
            # Calculate expected value
            expected_value = 0
            total_prob = 0
            for frame_name, probability in result.items():
                # Extract numeric range from frame name
                try:
                    if "less than" in frame_name.lower():
                        # Handle "less than X" case
                        parts = frame_name.lower().split("less than")
                        upper = float(parts[1].strip().split()[0])
                        midpoint = upper / 2
                    elif "or more" in frame_name.lower():
                        # Handle "X or more" case
                        parts = frame_name.lower().split("or more")
                        lower = float(parts[0].strip().split()[-1])
                        midpoint = lower * 1.2  # Estimate
                    else:
                        # Standard range like "150-174"
                        range_clean = frame_name.replace('–', '-').strip()
                        if '-' in range_clean:
                            parts = range_clean.split('-')
                            if len(parts) == 2:
                                lower = float(parts[0].strip())
                                upper = float(parts[1].strip())
                                midpoint = (lower + upper) / 2
                            else:
                                continue
                        else:
                            continue
                    
                    # Add to expected value
                    expected_value += midpoint * (probability / 100)
                    total_prob += probability / 100
                except (ValueError, IndexError):
                    pass
            
            # Normalize expected value if needed
            if total_prob > 0:
                expected_value = expected_value / total_prob
            
            json_data = {
                "timestamp": now.isoformat(),
                "prediction_type": "prophet" if args.prophet else "enhanced" if not args.classic else "classic",
                "frame_probabilities": frame_probs,
                "summary": {
                    "most_likely": {
                        "frame": most_likely[0],
                        "probability": round(most_likely[1], 2)
                    },
                    "expected_value": round(expected_value, 2)
                }
            }
            
            # Output JSON
            if args.output:
                try:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
                    
                    # Write to file
                    with open(args.output, 'w') as f:
                        json.dump(json_data, f, indent=2)
                    if not args.brief:
                        print(f"Prediction results saved to {args.output}")
                except Exception as e:
                    if not args.brief:
                        print(f"Error saving to file: {e}")
                    # Fallback to printing
                    print(json.dumps(json_data, indent=2, ensure_ascii=False))
            else:
                # Print JSON data to console
                print(json.dumps(json_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main() 