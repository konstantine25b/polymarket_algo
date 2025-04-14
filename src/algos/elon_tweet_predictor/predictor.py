from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

class TweetPredictor:
    def __init__(self, analyzer=None):
        self.analyzer = analyzer
        
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
        if self.analyzer is None or self.analyzer.hourly_rates is None:
            print("Please set analyzer with analyzed patterns first")
            return
        
        # Determine target date
        if target_date_str:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        elif days:
            target_date = datetime.now().date() + timedelta(days=days)
        else:
            target_date = datetime.now().date()
            
        # Check if target date is in the past
        if target_date < self.analyzer.df['date'].max():
            print(f"Target date {target_date} is before the last date in the dataset {self.analyzer.df['date'].max()}.")
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
        
        current_datetime = datetime.combine(self.analyzer.df['date'].max(), self.analyzer.df['created_at'].max().time())
        target_datetime = datetime.combine(target_date, datetime.max.time())
        
        # Calculate trend factor
        recent_avg = self.analyzer.daily_counts.iloc[-7:]['count'].mean() if len(self.analyzer.daily_counts) >= 7 else self.analyzer.daily_counts['count'].mean()
        overall_avg = self.analyzer.daily_counts['count'].mean()
        trend_factor = recent_avg / overall_avg if overall_avg > 0 and use_trend else 1.0
        
        print(f"\nTrend adjustment factor: {trend_factor:.2f}" if use_trend else "\nUsing historical averages without trend adjustment")
        
        # If target date is the same as last date, we predict for remaining hours
        if target_date == current_datetime.date():
            print(f"\nPredicting tweets for remaining hours of {target_date}")
            remaining_prediction = self._predict_remaining_hours(current_datetime, target_datetime, trend_factor, specific_hours=hours)
            
            # Display results even for same day
            print(f"\nPrediction results:")
            print(f"From {current_datetime.strftime('%Y-%m-%d %H:%M:%S')} to {target_date}")
            print(f"Expected tweets for remaining hours: {remaining_prediction['expected_tweets']:.1f}")
            print(f"Remaining hours: {remaining_prediction['remaining_hours']:.2f}")
            
            return {
                'from_date': current_datetime.date(),
                'to_date': target_date,
                'days': 0,
                'total_expected_tweets': remaining_prediction['expected_tweets'],
                'daily_breakdown': {str(current_datetime.date()): remaining_prediction['expected_tweets']},
                'prediction_details': [remaining_prediction]
            }
        
        # For future days
        print(f"\nPredicting tweets from {current_datetime.date()} to {target_date}")
        
        # Get counts for remaining hours of the current day
        current_day_prediction = self._predict_remaining_hours(
            current_datetime, 
            datetime.combine(current_datetime.date(), datetime.max.time()),
            trend_factor,
            specific_hours=hours
        )
        
        remaining_days = (target_date - current_datetime.date()).days
        print(f"Days to predict: {remaining_days} full days + remaining hours today")
        
        # Initialize results
        day_by_day = defaultdict(float)
        day_by_day[str(current_datetime.date())] = current_day_prediction['expected_tweets']
        
        total_expected = current_day_prediction['expected_tweets']
        prediction_details = [current_day_prediction]
        
        # Predict for each full day between last date and target date
        for i in range(1, remaining_days + 1):
            predict_date = current_datetime.date() + timedelta(days=i)
            weekday = predict_date.weekday()
            
            # If using specific hours, calculate based on those hours only
            if hours is not None:
                expected = 0
                for hour in hours:
                    try:
                        hour_rate = self.analyzer.hour_of_day_averages.get((weekday, hour), 0)
                        expected += hour_rate * (trend_factor if use_trend else 1.0)
                    except:
                        # Fallback to overall hourly rate
                        hour_rate = self.analyzer.hourly_rates.get(hour, 0)
                        expected += hour_rate / 24 * (trend_factor if use_trend else 1.0)
            else:
                # Get average tweets for this weekday
                expected = self.analyzer.weekday_averages.get(weekday, self.analyzer.daily_counts['count'].mean())
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
            'from_date': current_datetime.date(),
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
            
        print(f"From {current_datetime.date()} to {target_date}")
        print(f"Expected tweets: {total_expected:.1f}")
        print("\nDay-by-day breakdown:")
        
        for detail in prediction_details:
            if 'weekday' in detail:
                hour_info = f" (specific hours only)" if hours is not None else ""
                print(f"- {detail['date']} ({detail['weekday']}){hour_info}: {detail['expected_tweets']:.1f} tweets")
            else:
                print(f"- {current_datetime.date()} (remaining hours): {detail['expected_tweets']:.1f} tweets")
        
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
        if self.analyzer is None or self.analyzer.hourly_rates is None:
            print("Please set analyzer with analyzed patterns first")
            return
        
        # Get current datetime from last available data point
        current_datetime = datetime.combine(
            self.analyzer.df['date'].max(), 
            self.analyzer.df['created_at'].max().time()
        )
        target_datetime = current_datetime + timedelta(hours=hours_ahead)
        
        print(f"\nPredicting tweets for the next {hours_ahead} hours")
        print(f"From: {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"To: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calculate trend factor
        recent_avg = self.analyzer.daily_counts.iloc[-7:]['count'].mean() if len(self.analyzer.daily_counts) >= 7 else self.analyzer.daily_counts['count'].mean()
        overall_avg = self.analyzer.daily_counts['count'].mean()
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
            current_hour_rate = self.analyzer.hour_of_day_averages.get((current_weekday, current_hour), 0)
            hour_expected = current_hour_rate * remaining_portion * trend_factor
        except:
            # Fallback to overall hourly rate
            current_hour_rate = self.analyzer.hourly_rates.get(current_hour, 0)
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
                hour_rate = self.analyzer.hour_of_day_averages.get((next_weekday, next_hour), 0)
                hour_expected = hour_rate * portion * trend_factor
            except:
                # Fallback to overall hourly rate
                hour_rate = self.analyzer.hourly_rates.get(next_hour, 0)
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
                current_hour_rate = self.analyzer.hour_of_day_averages.get((current_weekday, current_hour), 0)
                expected_tweets += current_hour_rate * remaining_portion * trend_factor
            except:
                # Fallback to overall hourly rate
                current_hour_rate = self.analyzer.hourly_rates.get(current_hour, 0)
                expected_tweets += current_hour_rate * remaining_portion / 24 * trend_factor
        
        # Full hours after current hour
        for hour in range(current_hour + 1, 24):
            # Skip hours not in specific_hours if provided
            if specific_hours is not None and hour not in specific_hours:
                continue
                
            try:
                hour_rate = self.analyzer.hour_of_day_averages.get((current_weekday, hour), 0)
                expected_tweets += hour_rate * trend_factor
            except:
                # Fallback to overall hourly rate
                hour_rate = self.analyzer.hourly_rates.get(hour, 0)
                expected_tweets += hour_rate / 24 * trend_factor
        
        return {
            'date': current_datetime.date(),
            'expected_tweets': expected_tweets,
            'remaining_hours': remaining_hours,
            'hours_included': specific_hours
        } 