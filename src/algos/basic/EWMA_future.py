from datetime import datetime, timedelta
import csv
import os
import argparse
import numpy as np
from collections import defaultdict
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
filename = os.path.join(src_dir, 'data', 'elonmusk_daily_counts.csv')

class TweetPredictor:
    def __init__(self):
        self.dates = []
        self.counts = []
        self.weekday_pattern = defaultdict(list)

    def load_data(self, file_path):
        """Load and validate tweet count data"""
        print(f"\n{'='*50}")
        print(f"Loading data from: {file_path}")

        try:
            with open(file_path, 'r') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader, None)  # Skip header
                if header:
                    print(f"Log: Header row found: {', '.join(header)}")

                for row_num, row in enumerate(reader, start=1):
                    if len(row) == 2:
                        date_str, count_str = row
                        try:
                            date_obj = datetime.strptime(date_str, '%Y:%m:%d')
                            count = int(count_str)
                            self.dates.append(date_obj)
                            self.counts.append(count)
                            # Store counts by weekday (0=Monday)
                            self.weekday_pattern[date_obj.weekday()].append(count)
                        except ValueError:
                            print(f"Warning: Skipping invalid row {row_num}: {row}")
                    else:
                        print(f"Warning: Skipping malformed row {row_num}: {row}")

            if not self.dates:
                raise ValueError("No valid data found in CSV file")

            # Sort data chronologically
            sorted_indices = sorted(range(len(self.dates)), key=lambda k: self.dates[k])
            self.dates = [self.dates[i] for i in sorted_indices]
            self.counts = [self.counts[i] for i in sorted_indices]

            print(f"Log: Loaded {len(self.dates)} days of data")
            print(f"Log: Date range: {self.dates[0].date()} to {self.dates[-1].date()}")

            # Basic check for chronological order (already enforced by sorting)
            for i in range(len(self.dates) - 1):
                if self.dates[i] >= self.dates[i+1]:
                    print("Warning: Dates in the input file might not be strictly chronological (though they have been sorted).")
                    break

        except FileNotFoundError:
            print(f"Error: File not found at '{file_path}'")
            raise
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            raise

    def calculate_seasonality(self):
        """Calculate weekly patterns"""
        self.weekly_factors = {}
        mean_count = np.mean(self.counts) if self.counts else 0
        if mean_count == 0:
            print("Warning: Cannot calculate seasonality as the mean count is zero.")
            return

        print("\nLog: Calculating weekly seasonality factors:")
        for weekday, counts in self.weekday_pattern.items():
            if counts:
                factor = np.mean(counts) / mean_count
                self.weekly_factors[weekday] = factor
                print(f"Log: Day {weekday}: Factor = Mean({counts}) / Mean(All) = {np.mean(counts):.2f} / {mean_count:.2f} = {factor:.3f}")
            else:
                self.weekly_factors[weekday] = 1.0 # Default to 1 if no data for that weekday

        print("\nWeekly Seasonality Factors:")
        for day, factor in sorted(self.weekly_factors.items()):
            day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][day]
            print(f"Log: {day_name} ({day}): {factor:.3f}x baseline")

    def predict_next_day(self, current_dates, current_counts, ewma_span=7, rate_window=3):
        """Make prediction combining EWMA trend and rate change for the immediate next day"""
        if len(current_counts) < max(ewma_span, rate_window):
            raise ValueError("Insufficient data for selected parameters")

        # Calculate EWMA baseline
        ewma = self.calculate_ewma(current_counts, span=ewma_span)
        baseline = ewma[-1]
        print(f"Log: EWMA Baseline ({ewma_span} days): {baseline:.2f}")

        # Calculate recent rate of change
        recent_rate = self.calculate_rate(current_counts, window=rate_window)
        print(f"Log: Recent Rate of Change (last {rate_window} days): {recent_rate:.3f}")

        # Get next day's weekday factor
        next_date = current_dates[-1] + timedelta(days=1)
        next_weekday = next_date.weekday()
        seasonality = self.weekly_factors.get(next_weekday, 1.0)
        print(f"Log: Day {next_weekday} Seasonality Factor: {seasonality:.3f}")

        # Combine factors
        prediction = baseline * seasonality * (1 + recent_rate)
        prediction = max(0, round(prediction))
        print(f"Log: Raw Adjusted Prediction: {baseline * seasonality * (1 + recent_rate):.2f}")

        return next_date, prediction

    def calculate_ewma(self, counts, span=7):
        """Exponentially Weighted Moving Average"""
        return list(pd.Series(counts).ewm(span=span).mean())

    def calculate_rate(self, counts, window=3):
        """Calculate recent growth rate"""
        recent = counts[-window:]
        if recent[0] == 0:
            return 0  # Avoid division by zero
        return (recent[-1] - recent[0]) / recent[0]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Advanced tweet count predictor')
    parser.add_argument('--ewma', type=int, default=7,
                       help='EWMA span for baseline trend (default: 7)')
    parser.add_argument('--rate', type=int, default=3,
                       help='Window for rate calculation (default: 3)')
    parser.add_argument('--file', type=str, default=filename,
                       help='Path to CSV file')
    parser.add_argument('--days', type=int, default=1,
                       help='Number of future days to predict (default: 1)')

    args = parser.parse_args()

    try:
        predictor = TweetPredictor()
        predictor.load_data(args.file)
        predictor.calculate_seasonality()

        predictions = {}
        current_dates = list(predictor.dates)
        current_counts = list(predictor.counts)

        print(f"\n{'='*50}")
        print("Starting Predictions:")

        for i in range(args.days):
            print(f"\n{'='*30}")
            print(f"Predicting day {i+1}...")
            next_date, prediction = predictor.predict_next_day(
                current_dates,
                current_counts,
                ewma_span=args.ewma,
                rate_window=args.rate
            )
            predictions[next_date.date()] = prediction
            current_dates.append(next_date)
            current_counts.append(prediction) # Use the prediction for the next day's prediction
            print(f"Log: Prediction for {next_date.date()}: {prediction} tweets")

        print(f"\n{'*'*50}")
        print("Future Predictions:")
        for date, count in predictions.items():
            print(f"- {date}: {count} tweets")
        print(f"\nMethod: EWMA({args.ewma}) + Rate({args.rate}) + Weekly Seasonality")
        print(f"{'*'*50}")

    except Exception as e:
        print(f"\nError: {str(e)}")
        print("Please check your input data and parameters")