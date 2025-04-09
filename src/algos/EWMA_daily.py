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
                next(reader, None)  # Skip header
                
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
            
            print(f"Loaded {len(self.dates)} days of data")
            print(f"Date range: {self.dates[0].date()} to {self.dates[-1].date()}")
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            raise

    def calculate_seasonality(self):
        """Calculate weekly patterns"""
        self.weekly_factors = {}
        for weekday, counts in self.weekday_pattern.items():
            if counts:
                self.weekly_factors[weekday] = np.mean(counts) / np.mean(self.counts)
        print("\nWeekly seasonality factors:")
        for day, factor in sorted(self.weekly_factors.items()):
            print(f"Day {day}: {factor:.3f}x baseline")

    def predict_next_day(self, ewma_span=7, rate_window=3):
        """Make prediction combining EWMA trend and rate change"""
        if len(self.counts) < max(ewma_span, rate_window):
            raise ValueError("Insufficient data for selected parameters")
        
        # Calculate EWMA baseline
        ewma = self.calculate_ewma(span=ewma_span)
        baseline = ewma[-1]
        
        # Calculate recent rate of change
        recent_rate = self.calculate_rate(window=rate_window)
        
        # Get next day's weekday factor
        next_date = self.dates[-1] + timedelta(days=1)
        next_weekday = next_date.weekday()
        seasonality = self.weekly_factors.get(next_weekday, 1.0)
        
        # Combine factors
        prediction = baseline * seasonality * (1 + recent_rate)
        prediction = max(0, round(prediction))
        
        print("\nPrediction Components:")
        print(f"- Baseline EWMA ({ewma_span} days): {baseline:.1f}")
        print(f"- Recent rate ({rate_window} days): {recent_rate:.3f}")
        print(f"- Day {next_weekday} factor: {seasonality:.3f}")
        print(f"Raw adjusted prediction: {baseline * seasonality * (1 + recent_rate):.1f}")
        
        return next_date, prediction

    def calculate_ewma(self, span=7):
        """Exponentially Weighted Moving Average"""
        return list(pd.Series(self.counts).ewm(span=span).mean())

    def calculate_rate(self, window=3):
        """Calculate recent growth rate"""
        recent = self.counts[-window:]
        return (recent[-1] - recent[0]) / max(1, recent[0])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Advanced tweet count predictor')
    parser.add_argument('--ewma', type=int, default=7,
                       help='EWMA span for baseline trend (default: 7)')
    parser.add_argument('--rate', type=int, default=3,
                       help='Window for rate calculation (default: 3)')
    parser.add_argument('--file', type=str, default=filename,
                       help='Path to CSV file')
    
    args = parser.parse_args()
    
    try:
        predictor = TweetPredictor()
        predictor.load_data(args.file)
        predictor.calculate_seasonality()
        
        next_date, prediction = predictor.predict_next_day(
            ewma_span=args.ewma,
            rate_window=args.rate
        )
        
        print(f"\n{'*'*50}")
        print(f"Final Prediction for {next_date.date()}: {prediction} tweets")
        print(f"Method: EWMA({args.ewma}) + Rate({args.rate}) + Weekly Seasonality")
        print(f"{'*'*50}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("Please check your input data and parameters")