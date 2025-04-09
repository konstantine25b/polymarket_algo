import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os
import argparse
from collections import defaultdict
from pandas import Timestamp

class ElonTweetCountPredictor:
    def __init__(self):
        self.df = None
        self.hourly_rates = None
        self.daily_counts = None
        self.weekday_averages = None
        self.hour_of_day_averages = None
        self.last_date = None
        self.last_time = None
        
    def load_data(self, file_path):
        """Load the tweet data from the reformatted CSV"""
        print(f"\n{'='*50}")
        print(f"Loading data from: {file_path}")
        
        try:
            # Load the data
            self.df = pd.read_csv(file_path)
            
            # Parse the timestamp (format is year:month:day:hour:minute:second)
            self.df['created_at'] = pd.to_datetime(
                self.df['created_at'], 
                format='%Y:%m:%d:%H:%M:%S',
                errors='coerce'
            )
            
            # Drop rows with invalid timestamps
            self.df = self.df.dropna(subset=['created_at'])
            
            # Sort by time
            self.df = self.df.sort_values('created_at')
            
            # Extract date and time components
            self.df['date'] = self.df['created_at'].dt.date
            self.df['hour'] = self.df['created_at'].dt.hour
            self.df['weekday'] = self.df['created_at'].dt.weekday
            
            # Get the last available date and time
            self.last_date = self.df['created_at'].max().date()
            self.last_time = self.df['created_at'].max().time()
            
            print(f"Loaded {len(self.df)} tweets")
            print(f"Date range: {self.df['date'].min()} to {self.df['date'].max()}")
            print(f"Last tweet time: {self.last_time}")
            
            return True
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return False
    
    def analyze_patterns(self):
        """Analyze tweeting patterns to extract features for prediction"""
        if self.df is None:
            print("Please load data first")
            return
            
        print("\nAnalyzing tweeting patterns...")
        
        # Calculate daily counts
        self.daily_counts = self.df.groupby('date').size().reset_index(name='count')
        self.daily_counts['date'] = pd.to_datetime(self.daily_counts['date'])
        
        # Extract date components
        self.daily_counts['weekday'] = self.daily_counts['date'].dt.weekday
        
        # Calculate average tweets by weekday
        self.weekday_averages = self.daily_counts.groupby('weekday')['count'].mean()
        print("\nAverage tweets by weekday:")
        for day, avg in self.weekday_averages.items():
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
            print(f"{day_name}: {avg:.2f} tweets per day")
        
        # Calculate hourly distribution
        hour_counts = self.df.groupby('hour').size()
        total_days = (self.df['date'].max() - self.df['date'].min()).days + 1
        self.hourly_rates = hour_counts / total_days
        
        print("\nAverage hourly tweets (top 5):")
        for hour, rate in self.hourly_rates.nlargest(5).items():
            hour_ampm = f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"
            print(f"{hour_ampm}: {rate:.3f} tweets per day")
        
        # Display all hourly rates
        print("\nFull hourly tweet distribution:")
        for hour in range(24):
            rate = self.hourly_rates.get(hour, 0)
            hour_ampm = f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"
            print(f"{hour_ampm}: {rate:.3f} tweets per day")
        
        # Calculate average tweets per day
        avg_daily = self.daily_counts['count'].mean()
        print(f"\nOverall average: {avg_daily:.2f} tweets per day")
        
        # Calculate recent average (last 7 days)
        recent_avg = self.daily_counts.iloc[-7:]['count'].mean() if len(self.daily_counts) >= 7 else avg_daily
        print(f"Recent average (last 7 days): {recent_avg:.2f} tweets per day")
        
        # Calculate hour of day + weekday averages
        self.df['hour_weekday'] = self.df['weekday'] * 24 + self.df['hour']
        hour_weekday_counts = self.df.groupby(['weekday', 'hour']).size().reset_index(name='count')
        
        # Calculate averages by dividing by the number of that weekday in the dataset
        weekday_counts = self.daily_counts.groupby('weekday').size()
        hour_weekday_counts['rate'] = hour_weekday_counts.apply(
            lambda x: x['count'] / weekday_counts[x['weekday']], axis=1
        )
        
        self.hour_of_day_averages = hour_weekday_counts.set_index(['weekday', 'hour'])['rate']
    
    def display_hourly_averages(self):
        """Display average tweet counts for all 24 hours"""
        if self.hourly_rates is None:
            print("Please analyze patterns first")
            return
            
        print("\nAverage tweet counts for all 24 hours:")
        hours = []
        for hour in range(24):
            rate = self.hourly_rates.get(hour, 0)
            hour_ampm = f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"
            hours.append((hour, hour_ampm, rate))
        
        # Sort by rate in descending order
        hours.sort(key=lambda x: x[2], reverse=True)
        
        for _, hour_ampm, rate in hours:
            print(f"{hour_ampm}: {rate:.3f} tweets per day")
        
        return self.hourly_rates
    
    def predict_count(self, target_date_str=None, days=None, use_trend=True):
        """
        Predict how many tweets Elon will post until a specific date.
        
        Parameters:
        target_date_str (str): Target date in format YYYY-MM-DD
        days (int): Number of days to predict for (alternative to target_date)
        use_trend (bool): Whether to apply recent trend adjustment to predictions
        
        Returns:
        dict: Prediction results
        """
        if self.df is None or self.hourly_rates is None:
            print("Please load data and analyze patterns first")
            return
        
        # Determine target date
        if target_date_str:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        elif days:
            target_date = datetime.now().date() + timedelta(days=days)
        else:
            target_date = datetime.now().date()
            
        # Check if target date is in the past
        if target_date < self.last_date:
            print(f"Target date {target_date} is before the last date in the dataset {self.last_date}.")
            print("Please choose a future date.")
            return
        
        current_datetime = datetime.combine(self.last_date, self.last_time)
        target_datetime = datetime.combine(target_date, datetime.max.time())
        
        # Calculate trend factor
        recent_avg = self.daily_counts.iloc[-7:]['count'].mean() if len(self.daily_counts) >= 7 else self.daily_counts['count'].mean()
        overall_avg = self.daily_counts['count'].mean()
        trend_factor = recent_avg / overall_avg if overall_avg > 0 and use_trend else 1.0
        
        print(f"\nTrend adjustment factor: {trend_factor:.2f}" if use_trend else "\nUsing historical averages without trend adjustment")
        
        # If target date is the same as last date, we predict for remaining hours
        if target_date == self.last_date:
            print(f"\nPredicting tweets for remaining hours of {target_date}")
            remaining_prediction = self._predict_remaining_hours(current_datetime, target_datetime, trend_factor)
            
            # Display results even for same day
            print(f"\nPrediction results:")
            print(f"From {current_datetime.strftime('%Y-%m-%d %H:%M:%S')} to {target_date}")
            print(f"Expected tweets for remaining hours: {remaining_prediction['expected_tweets']:.1f}")
            print(f"Remaining hours: {remaining_prediction['remaining_hours']:.2f}")
            
            return {
                'from_date': self.last_date,
                'to_date': target_date,
                'days': 0,
                'total_expected_tweets': remaining_prediction['expected_tweets'],
                'daily_breakdown': {str(self.last_date): remaining_prediction['expected_tweets']},
                'prediction_details': [remaining_prediction]
            }
        
        # For future days
        print(f"\nPredicting tweets from {self.last_date} to {target_date}")
        
        # Get counts for remaining hours of the current day
        current_day_prediction = self._predict_remaining_hours(
            current_datetime, 
            datetime.combine(self.last_date, datetime.max.time()),
            trend_factor
        )
        
        remaining_days = (target_date - self.last_date).days
        print(f"Days to predict: {remaining_days} full days + remaining hours today")
        
        # Initialize results
        day_by_day = defaultdict(float)
        day_by_day[str(self.last_date)] = current_day_prediction['expected_tweets']
        
        total_expected = current_day_prediction['expected_tweets']
        prediction_details = [current_day_prediction]
        
        # Predict for each full day between last date and target date
        for i in range(1, remaining_days + 1):
            predict_date = self.last_date + timedelta(days=i)
            weekday = predict_date.weekday()
            
            # Get average tweets for this weekday
            day_avg = self.weekday_averages.get(weekday, self.daily_counts['count'].mean())
            
            # Apply trend factor if enabled
            expected = day_avg * (trend_factor if use_trend else 1.0)
            
            day_by_day[str(predict_date)] = expected
            total_expected += expected
            
            # Add to prediction details
            prediction_details.append({
                'date': predict_date,
                'weekday': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][weekday],
                'expected_tweets': expected
            })
        
        # Wrap up prediction results
        prediction_results = {
            'from_date': self.last_date,
            'to_date': target_date,
            'days': remaining_days + (0 if current_day_prediction['expected_tweets'] == 0 else 1),
            'total_expected_tweets': total_expected,
            'daily_breakdown': day_by_day,
            'prediction_details': prediction_details
        }
        
        # Display results
        print(f"\nPrediction results:")
        print(f"From {self.last_date} to {target_date}")
        print(f"Expected tweets: {total_expected:.1f}")
        print("\nDay-by-day breakdown:")
        
        for detail in prediction_details:
            if 'weekday' in detail:
                print(f"- {detail['date']} ({detail['weekday']}): {detail['expected_tweets']:.1f} tweets")
            else:
                print(f"- {self.last_date} (remaining hours): {detail['expected_tweets']:.1f} tweets")
        
        return prediction_results
    
    def _predict_remaining_hours(self, current_datetime, target_datetime, trend_factor=1.0):
        """Predict tweets for remaining hours of a day"""
        # Calculate remaining hours
        remaining_seconds = (target_datetime - current_datetime).total_seconds()
        remaining_hours = remaining_seconds / 3600
        
        if remaining_hours <= 0:
            return {
                'date': current_datetime.date(),
                'expected_tweets': 0,
                'remaining_hours': 0
            }
        
        current_hour = current_datetime.hour
        current_weekday = current_datetime.weekday()
        
        # For the exact hours, calculate expected tweets based on hourly rates
        expected_tweets = 0
        
        # Remaining portion of current hour
        current_minute = current_datetime.minute
        current_second = current_datetime.second
        remaining_portion = (60 - current_minute) / 60 - current_second / 3600
        
        # Get rate for current hour and weekday
        try:
            current_hour_rate = self.hour_of_day_averages.get((current_weekday, current_hour), 0)
            expected_tweets += current_hour_rate * remaining_portion * trend_factor
        except:
            # Fallback to overall hourly rate
            current_hour_rate = self.hourly_rates.get(current_hour, 0)
            expected_tweets += current_hour_rate * remaining_portion / 24 * trend_factor
        
        # Full hours after current hour
        for hour in range(current_hour + 1, 24):
            try:
                hour_rate = self.hour_of_day_averages.get((current_weekday, hour), 0)
                expected_tweets += hour_rate * trend_factor
            except:
                # Fallback to overall hourly rate
                hour_rate = self.hourly_rates.get(hour, 0)
                expected_tweets += hour_rate / 24 * trend_factor
        
        return {
            'date': current_datetime.date(),
            'expected_tweets': expected_tweets,
            'remaining_hours': remaining_hours
        }
    
    def evaluate_precision(self, days_back=14):
        """Calculate precision by comparing predictions for past days with actual counts"""
        if self.df is None or self.daily_counts is None:
            print("Please load data and analyze patterns first")
            return
            
        print(f"\nEvaluating prediction precision over the past {days_back} days...")
        
        # Get the actual daily counts for comparison
        end_date = self.last_date
        start_date = end_date - timedelta(days=days_back)
        
        # Actual counts
        actual_counts = self.daily_counts[
            (self.daily_counts['date'].dt.date >= start_date) & 
            (self.daily_counts['date'].dt.date <= end_date)
        ].set_index('date')['count'].to_dict()
        print("kosa", actual_counts)
        
        errors = []
        predictions = {}
        
        # For each day we want to evaluate
        for days in range(1, days_back):
            # Create a cutoff date for this prediction
            prediction_date = start_date + timedelta(days=days - 1)
            target_date = start_date + timedelta(days=days)
            
            # Create a temporary predictor using data before the target date
            temp_df = self.df[self.df['date'] < target_date].copy()
            
            if len(temp_df) < 100:  # Require minimum data for meaningful analysis
                continue
                
            temp_predictor = ElonTweetCountPredictor()
            temp_predictor.df = temp_df
            
            # Recalculate the last date and time from this subset
            temp_predictor.last_date = prediction_date
            temp_predictor.last_time = datetime.max.time()  # End of day
            
            # Analyze patterns on this subset
            temp_predictor.analyze_patterns()
            
            # Make one-day prediction from prediction_date to target_date
            pred_result = temp_predictor.predict_count(target_date_str=target_date.strftime('%Y-%m-%d'))
            
            if pred_result and 'total_expected_tweets' in pred_result:
                predicted = pred_result['total_expected_tweets']
                
                fixedDate = Timestamp(str(target_date)+' 00:00:00')
                actual = actual_counts.get(fixedDate , 0)
               
                error = abs(predicted - actual)
                errors.append(error)
                
                # Store prediction details
                predictions[target_date.strftime('%Y-%m-%d')] = {
                    'predicted': predicted,
                    'actual': actual,
                    'error': error,
                    'percent_error': (error / actual * 100) if actual > 0 else float('inf')
                }
        
        # Calculate precision metrics
        if errors:
            mae = sum(errors) / len(errors)
            rmse = (sum(e**2 for e in errors) / len(errors))**0.5
            
            # Fix for division by zero
            avg_actual = sum(p['actual'] for p in predictions.values()) / len(predictions) if predictions else 0
            
            print(f"\nPrediction Metrics:")
            print(f"Mean Absolute Error (MAE): {mae:.2f} tweets")
            print(f"Root Mean Squared Error (RMSE): {rmse:.2f} tweets")
            
            # Safe division to handle zero actual tweets
            if avg_actual > 0:
                print(f"Average Error Percentage: {(mae / avg_actual) * 100:.1f}%")
            else:
                print("Average Error Percentage: Cannot calculate (no actual tweets)")
            
            # Display prediction vs actual for each day
            print("\nDay-by-day comparison:")
            for date, data in sorted(predictions.items()):
                error_percent = data['percent_error'] if data['actual'] > 0 else "N/A"
                error_percent_display = f"({error_percent:.1f}%)" if isinstance(error_percent, (int, float)) else f"({error_percent})"
                
                print(f"- {date}: Predicted {data['predicted']:.1f}, Actual {data['actual']}, " +
                      f"Error {data['error']:.1f} {error_percent_display}")
            
            return {
                'mae': mae,
                'rmse': rmse,
                'avg_error_percent': (mae / avg_actual) * 100 if avg_actual > 0 else None,
                'predictions': predictions
            }
        
        print("No valid prediction days found for evaluation")
        return None
    
    def plot_activity(self):
        """Plot tweet activity over time"""
        if self.daily_counts is None:
            print("Please analyze patterns first")
            return
            
        plt.figure(figsize=(12, 8))
        
        # Plot daily tweet counts
        plt.subplot(2, 1, 1)
        plt.plot(self.daily_counts['date'], self.daily_counts['count'])
        plt.title('Elon Musk Daily Tweet Activity')
        plt.ylabel('Tweets per Day')
        plt.grid(True, alpha=0.3)
        
        # Plot 7-day moving average
        self.daily_counts['7d_avg'] = self.daily_counts['count'].rolling(7).mean()
        plt.plot(self.daily_counts['date'], self.daily_counts['7d_avg'], 'r--', label='7-day Avg')
        plt.legend()
        
        # Plot weekly distribution
        plt.subplot(2, 2, 3)
        weekday_avg = self.daily_counts.groupby('weekday')['count'].mean()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        plt.bar(days, [weekday_avg.get(i, 0) for i in range(7)])
        plt.title('Average Tweets by Day of Week')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.grid(True, axis='y', alpha=0.3)
        
        # Plot hourly distribution
        plt.subplot(2, 2, 4)
        hours = [f"{h}" for h in range(24)]
        plt.bar(hours, [self.hourly_rates.get(i, 0) for i in range(24)])
        plt.title('Hourly Tweet Distribution')
        plt.xticks(rotation=90)
        plt.xlabel('Hour of Day (24h)')
        plt.ylabel('Avg Tweets per Hour')
        plt.tight_layout()
        plt.grid(True, axis='y', alpha=0.3)
        
        plt.savefig('elon_tweet_activity.png')
        print("\nActivity plot saved as 'elon_tweet_activity.png'")
        
    def plot_precision_results(self, precision_results):
        """Plot precision evaluation results"""
        if not precision_results or 'predictions' not in precision_results:
            print("No precision results to plot")
            return
            
        predictions = precision_results['predictions']
        dates = sorted(predictions.keys())
        
        predicted_values = [predictions[d]['predicted'] for d in dates]
        actual_values = [predictions[d]['actual'] for d in dates]
        
        plt.figure(figsize=(12, 6))
        plt.plot(dates, predicted_values, 'b-', label='Predicted')
        plt.plot(dates, actual_values, 'r-', label='Actual')
        plt.title('Prediction Accuracy Evaluation')
        plt.xlabel('Date')
        plt.ylabel('Number of Tweets')
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        plt.savefig('elon_tweet_prediction_accuracy.png')
        print("\nPrecision plot saved as 'elon_tweet_prediction_accuracy.png'")

def main():
    parser = argparse.ArgumentParser(description='Elon Musk Tweet Count Predictor')
    parser.add_argument('--file', type=str, required=False,
                      help='Path to reformatted CSV file')
    parser.add_argument('--date', type=str, 
                      help='Target date to predict (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=7,
                      help='Number of days to predict (default: 7)')
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
    
    # Determine file path
    file_path = args.file
    if not file_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(script_dir)
        file_path = os.path.join(src_dir, 'data', 'elonmusk_reformatted.csv')

    try:
        predictor = ElonTweetCountPredictor()
        if predictor.load_data(file_path):
            predictor.analyze_patterns()
            
            if args.all_hours:
                predictor.display_hourly_averages()
                
            if args.precision:
                precision_results = predictor.evaluate_precision(days_back=args.days_back)
                if precision_results and args.plot:
                    predictor.plot_precision_results(precision_results)
            
            if args.date:
                predictor.predict_count(target_date_str=args.date, use_trend=not args.no_trend)
            else:
                predictor.predict_count(days=args.days, use_trend=not args.no_trend)
            if args.plot:
                predictor.plot_activity()
        else:
            print("Failed to load data. Please check your input file.")
    except Exception as e:
        import traceback
        print(f"\nError: {str(e)}")
        print(traceback.format_exc())
        print("Please check your input data and parameters")

if __name__ == "__main__":
    main()