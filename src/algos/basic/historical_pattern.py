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
    
    def predict_count(self, target_date_str=None, days=None, use_trend=True, hours=None):
        """
        Predict how many tweets Elon will post until a specific date and time.
        
        Parameters:
        target_date_str (str): Target date in format YYYY-MM-DD
        days (int): Number of days to predict for (alternative to target_date)
        use_trend (bool): Whether to apply recent trend adjustment to predictions
        hours (list): List of specific hours (0-23) to include in the prediction
        
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
        
        # Validate hours input if provided
        if hours is not None:
            valid_hours = []
            for hour in hours:
                if isinstance(hour, int) and 0 <= hour < 24:
                    valid_hours.append(hour)
                else:
                    print(f"Ignoring invalid hour: {hour}. Hours must be integers between 0-23.")
            
            if not valid_hours and hours:
                print("No valid hours provided. Using all hours for prediction.")
                hours = None
            else:
                hours = valid_hours
                print(f"Using specific hours for prediction: {sorted(hours)}")
        
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
            remaining_prediction = self._predict_remaining_hours(current_datetime, target_datetime, trend_factor, specific_hours=hours)
            
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
            trend_factor,
            specific_hours=hours
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
            
            # If using specific hours, calculate based on those hours only
            if hours is not None:
                expected = 0
                for hour in hours:
                    try:
                        hour_rate = self.hour_of_day_averages.get((weekday, hour), 0)
                        expected += hour_rate * (trend_factor if use_trend else 1.0)
                    except:
                        # Fallback to overall hourly rate
                        hour_rate = self.hourly_rates.get(hour, 0)
                        expected += hour_rate / 24 * (trend_factor if use_trend else 1.0)
            else:
                # Get average tweets for this weekday
                expected = self.weekday_averages.get(weekday, self.daily_counts['count'].mean())
                expected *= (trend_factor if use_trend else 1.0)
            
            day_by_day[str(predict_date)] = expected
            total_expected += expected
            
            # Add to prediction details
            prediction_details.append({
                'date': predict_date,
                'weekday': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][weekday],
                'expected_tweets': expected,
                'hours_included': hours
            })
        
        # Wrap up prediction results
        prediction_results = {
            'from_date': self.last_date,
            'to_date': target_date,
            'days': remaining_days + (0 if current_day_prediction['expected_tweets'] == 0 else 1),
            'total_expected_tweets': total_expected,
            'daily_breakdown': day_by_day,
            'prediction_details': prediction_details,
            'specific_hours': hours
        }
        
        # Display results
        print(f"\nPrediction results:")
        if hours is not None:
            hour_str = ", ".join([f"{h}:00" for h in sorted(hours)])
            print(f"Predicting for specific hours: {hour_str}")
            
        print(f"From {self.last_date} to {target_date}")
        print(f"Expected tweets: {total_expected:.1f}")
        print("\nDay-by-day breakdown:")
        
        for detail in prediction_details:
            if 'weekday' in detail:
                hour_info = f" (specific hours only)" if hours is not None else ""
                print(f"- {detail['date']} ({detail['weekday']}){hour_info}: {detail['expected_tweets']:.1f} tweets")
            else:
                print(f"- {self.last_date} (remaining hours): {detail['expected_tweets']:.1f} tweets")
        
        return prediction_results
    def predict_next_hours(self, hours_ahead=4, use_trend=True):
        """
        Predict how many tweets Elon will post in the next N hours.
        
        Parameters:
        hours_ahead (int): Number of hours to predict for
        use_trend (bool): Whether to apply recent trend adjustment to predictions
        
        Returns:
        dict: Prediction results
        """
        if self.df is None or self.hourly_rates is None:
            print("Please load data and analyze patterns first")
            return
        
        # Get current datetime from last available data point
        current_datetime = datetime.combine(self.last_date, self.last_time)
        target_datetime = current_datetime + timedelta(hours=hours_ahead)
        
        print(f"\nPredicting tweets for the next {hours_ahead} hours")
        print(f"From: {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"To: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calculate trend factor
        recent_avg = self.daily_counts.iloc[-7:]['count'].mean() if len(self.daily_counts) >= 7 else self.daily_counts['count'].mean()
        overall_avg = self.daily_counts['count'].mean()
        trend_factor = recent_avg / overall_avg if overall_avg > 0 and use_trend else 1.0
        
        print(f"Trend adjustment factor: {trend_factor:.2f}" if use_trend else "Using historical averages without trend adjustment")
        
        # Initialize prediction
        expected_tweets = 0
        hour_by_hour = []
        
        # Current hour
        current_hour = current_datetime.hour
        current_weekday = current_datetime.weekday()
        
        # Remaining portion of current hour
        current_minute = current_datetime.minute
        current_second = current_datetime.second
        remaining_portion = (60 - current_minute) / 60 - current_second / 3600
        
        # Track how many hours we've predicted
        hours_counted = 0
        
        # First handle partial remaining hour
        try:
            current_hour_rate = self.hour_of_day_averages.get((current_weekday, current_hour), 0)
            hour_expected = current_hour_rate * remaining_portion * trend_factor
        except:
            # Fallback to overall hourly rate
            current_hour_rate = self.hourly_rates.get(current_hour, 0)
            hour_expected = current_hour_rate * remaining_portion / 24 * trend_factor
        
        expected_tweets += hour_expected
        
        # Add current hour to hour-by-hour breakdown
        hour_by_hour.append({
            'datetime': current_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'hour': current_hour,
            'weekday': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][current_weekday],
            'expected_tweets': hour_expected,
            'partial': True,
            'portion': remaining_portion
        })
        
        hours_counted += remaining_portion
        
        # Now predict for full hours
        while hours_counted < hours_ahead:
            # Calculate the next hour
            next_datetime = current_datetime + timedelta(hours=int(hours_counted) + 1)
            next_hour = next_datetime.hour
            next_weekday = next_datetime.weekday()
            
            # If we've reached the last hour boundary
            if hours_counted + 1 > hours_ahead:
                # Calculate portion of the last hour
                portion = hours_ahead - hours_counted
            else:
                portion = 1.0  # Full hour
            
            try:
                hour_rate = self.hour_of_day_averages.get((next_weekday, next_hour), 0)
                hour_expected = hour_rate * portion * trend_factor
            except:
                # Fallback to overall hourly rate
                hour_rate = self.hourly_rates.get(next_hour, 0)
                hour_expected = hour_rate * portion / 24 * trend_factor
            
            expected_tweets += hour_expected
            
            # Add to hour-by-hour breakdown
            hour_by_hour.append({
                'datetime': next_datetime.strftime('%Y-%m-%d %H:%M'),
                'hour': next_hour,
                'weekday': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][next_weekday],
                'expected_tweets': hour_expected,
                'partial': portion < 1.0,
                'portion': portion
            })
            
            hours_counted += portion
            
            # Stop if we've counted enough hours
            if hours_counted >= hours_ahead:
                break
        
        # Prepare results
        prediction_results = {
            'from_datetime': current_datetime,
            'to_datetime': target_datetime,
            'hours': hours_ahead,
            'total_expected_tweets': expected_tweets,
            'hour_by_hour': hour_by_hour
        }
        
        # Display results
        print(f"\nPrediction results:")
        print(f"Expected tweets in the next {hours_ahead} hours: {expected_tweets:.2f}")
        print("\nHour-by-hour breakdown:")
        
        for detail in hour_by_hour:
            hour_ampm = f"{detail['hour'] % 12 or 12} {'AM' if detail['hour'] < 12 else 'PM'}"
            if detail['partial']:
                print(f"- {detail['datetime']} ({hour_ampm}, {detail['portion']*60:.0f} min): {detail['expected_tweets']:.2f} tweets")
            else:
                print(f"- {detail['datetime']} ({hour_ampm}): {detail['expected_tweets']:.2f} tweets")
        
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
    def _predict_remaining_hours(self, current_datetime, target_datetime, trend_factor=1.0, specific_hours=None):
        """
        Predict tweets for remaining hours of a day
        
        Parameters:
        current_datetime: Current datetime
        target_datetime: Target datetime
        trend_factor: Trend adjustment factor
        specific_hours: List of specific hours (0-23) to include in the prediction
        """
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
        
        # Check if we should include the current hour
        include_current_hour = specific_hours is None or current_hour in specific_hours
        
        if include_current_hour:
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
            # Skip hours not in specific_hours if provided
            if specific_hours is not None and hour not in specific_hours:
                continue
                
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
            'remaining_hours': remaining_hours,
            'hours_included': specific_hours
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
            
            # If next-hours is specified, use that prediction method
            if args.next_hours:
                predictor.predict_next_hours(hours_ahead=args.next_hours, use_trend=not args.no_trend)
            # Otherwise use the standard date/days prediction
            elif args.date:
                predictor.predict_count(target_date_str=args.date, use_trend=not args.no_trend, hours=specific_hours)
            else:
                predictor.predict_count(days=args.days, use_trend=not args.no_trend, hours=specific_hours)
                
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