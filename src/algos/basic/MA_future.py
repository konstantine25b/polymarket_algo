from datetime import datetime, timedelta
import csv
import os
import argparse
from collections import deque

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
filename = os.path.join(src_dir, 'data', 'elonmusk_daily_counts.csv')

def predict_future_tweet_counts(file_path, window_size=7, forecast_days=1):
    """
    Predicts tweet counts for the next 'forecast_days' using a moving average
    of the last 'window_size' days.

    Args:
        file_path (str): The path to the CSV file containing the data.
                           The file should have two columns: Date (YYYY:MM:DD) and Tweet Count.
        window_size (int): The number of previous days to consider for the moving average.
        forecast_days (int): The number of future days to predict.

    Returns:
        dict or None: A dictionary where keys are predicted dates (datetime.date)
                       and values are the predicted tweet counts (integer), or None if an error occurs.
    """
    dates = []
    counts = []
    predictions = {}

    print(f"\n{'='*50}")
    print(f"Log: Starting prediction process")
    print(f"Log: Input file: {file_path}")
    print(f"Log: Selected moving average window size: {window_size}")
    print(f"Log: Forecasting for {forecast_days} days")
    print(f"{'='*50}\n")

    try:
        # Validate window size and forecast days
        if window_size < 1:
            raise ValueError("Window size must be at least 1")
        if forecast_days < 1:
            raise ValueError("Number of forecast days must be at least 1")

        with open(file_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)  # Skip the header row if it exists

            for row_num, row in enumerate(reader, start=1):
                if len(row) == 2:
                    date_str, count_str = row
                    try:
                        year, month, day = map(int, date_str.split(':'))
                        date_obj = datetime(year, month, day)
                        count = int(count_str)
                        dates.append(date_obj)
                        counts.append(count)
                        print(f"Log: Processed row {row_num:3d} | Date: {date_str} | Count: {count:3d}")
                    except ValueError:
                        print(f"Log: Warning - Skipping row {row_num} (invalid format): {row}")
                else:
                    print(f"Log: Warning - Skipping row {row_num} (incorrect columns): {row}")

        if not dates:
            print("Log: Error - No valid data found in the CSV file.")
            return None

        # Sort data by date
        sorted_indices = sorted(range(len(dates)), key=lambda k: dates[k])
        sorted_dates = [dates[i] for i in sorted_indices]
        sorted_counts = [counts[i] for i in sorted_indices]

        last_date = sorted_dates[-1]
        total_days = len(sorted_dates)
        print(f"\n{'='*50}")
        print(f"Log: Data Summary")
        print(f"Log: First date: {sorted_dates[0].strftime('%Y:%m:%d')}")
        print(f"Log: Last date:  {last_date.strftime('%Y:%m:%d')}")
        print(f"Log: Total days available: {total_days}")
        print(f"{'='*50}\n")

        current_dates = deque(sorted_dates, maxlen=total_days + forecast_days)
        current_counts = deque(sorted_counts, maxlen=total_days + forecast_days)

        print(f"\n{'='*50}")
        print(f"Log: Starting Future Predictions")
        print(f"{'='*50}\n")

        for i in range(forecast_days):
            next_predict_date = current_dates[-1] + timedelta(days=1)

            if len(current_counts) >= window_size:
                recent_counts = list(current_counts)[-window_size:]
                moving_avg = sum(recent_counts) / window_size
                predicted_count = round(moving_avg)

                print(f"Log: Predicting for {next_predict_date.strftime('%Y:%m:%d')}")
                print(f"Log: Calculation Details (Moving Average)")
                print(f"Log: Using last {window_size} days: {recent_counts}")
                print(f"Log: Sum: {sum(recent_counts):3d} / {window_size} = {moving_avg:.2f}")
                print(f"Log: Rounded prediction: {predicted_count}")
            else:
                predicted_count = current_counts[-1] if current_counts else 0
                print(f"Log: Warning - Not enough data for {window_size}-day moving average for {next_predict_date.strftime('%Y:%m:%d')}")
                print(f"Log: Falling back to naive forecast (last observed count): {predicted_count}")

            predictions[next_predict_date.date()] = predicted_count
            current_dates.append(next_predict_date)
            current_counts.append(predicted_count)

        print(f"\n{'='*50}")
        print(f"Log: Future Prediction Summary")
        for date, count in predictions.items():
            print(f"Log: Predicted date:  {date.strftime('%Y:%m:%d')}, Predicted count: {count}")
        print(f"{'='*50}")

        return predictions

    except FileNotFoundError:
        print(f"Log: Error - File not found: '{file_path}'")
        return None
    except ValueError as ve:
        print(f"Log: Error - {str(ve)}")
        return None
    except Exception as e:
        print(f"Log: Error - An unexpected error occurred: {str(e)}")
        return None

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Predict future tweet counts using moving average')
    parser.add_argument('--window', type=int, default=7,
                       help='Number of days to use for moving average (default: 7)')
    parser.add_argument('--file', type=str, default=filename,
                       help='Path to CSV file with tweet counts (default: data/elonmusk_daily_counts.csv)')
    parser.add_argument('--days', type=int, default=1,
                       help='Number of future days to predict (default: 1)')

    args = parser.parse_args()

    # Validate window size
    if args.window < 1:
        print("Error: Window size must be at least 1")
        exit(1)

    prediction_results = predict_future_tweet_counts(args.file, args.window, args.days)

    if prediction_results:
        print(f"\n{'*'*50}")
        print("Future Tweet Count Predictions:")
        for date, count in prediction_results.items():
            print(f"- {date.strftime('%Y:%m:%d')}: {count} tweets")
        print(f"Calculation Method: {args.window}-day moving average")
        print(f"{'*'*50}")