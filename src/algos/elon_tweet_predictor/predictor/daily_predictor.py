from datetime import datetime, timedelta
from collections import defaultdict
import logging
from src.algos.elon_tweet_predictor.predictor.utils import (
    calculate_trend_factor, 
    validate_hours,
    get_weekday_name
)

def predict_daily(predictor, target_date_str=None, days=None, use_trend=True, hours=None):
    """
    Predict how many tweets Elon will post until a specific date.
    
    Parameters:
    predictor: TweetPredictor instance
    target_date_str (str): Target date in format YYYY-MM-DD
    days (int): Number of days to predict for (alternative to target_date)
    use_trend (bool): Whether to apply recent trend adjustment to predictions
    hours (list): List of specific hours (0-23) to include in the prediction
    
    Returns:
    dict: Prediction results
    """
    analyzer = predictor.analyzer
    logger = predictor.logger
    
    if analyzer is None or analyzer.hourly_rates is None:
        logger.error("Please set analyzer with analyzed patterns first")
        return
    
    # Validate hours input if provided
    hours = validate_hours(hours)
    if hours:
        logger.info(f"Using specific hours for prediction: {sorted(hours)}")
    
    # Determine target date
    if target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    elif days:
        target_date = datetime.now().date() + timedelta(days=days)
    else:
        target_date = datetime.now().date()
        
    # Check if target date is in the past
    if target_date < analyzer.df['date'].max():
        logger.error(f"Target date {target_date} is before the last date in the dataset {analyzer.df['date'].max()}.")
        logger.error("Please choose a future date.")
        return
    
    current_datetime = datetime.combine(analyzer.df['date'].max(), analyzer.df['created_at'].max().time())
    target_datetime = datetime.combine(target_date, datetime.max.time())
    
    # Calculate trend factor
    trend_factor = calculate_trend_factor(analyzer, use_trend)
    
    if use_trend:
        logger.info(f"\nTrend adjustment factor: {trend_factor:.2f}")
    else:
        logger.info("\nUsing historical averages without trend adjustment")
    
    # If target date is the same as last date, we predict for remaining hours
    if target_date == current_datetime.date():
        logger.info(f"\nPredicting tweets for remaining hours of {target_date}")
        remaining_prediction = predictor.predict_remaining_hours(
            current_datetime, 
            target_datetime, 
            trend_factor, 
            specific_hours=hours
        )
        
        # Display results even for same day
        logger.info(f"\nPrediction results:")
        logger.info(f"From {current_datetime.strftime('%Y-%m-%d %H:%M:%S')} to {target_date}")
        logger.info(f"Expected tweets for remaining hours: {remaining_prediction['expected_tweets']:.1f}")
        logger.info(f"Remaining hours: {remaining_prediction['remaining_hours']:.2f}")
        
        return {
            'from_date': current_datetime.date(),
            'to_date': target_date,
            'days': 0,
            'total_expected_tweets': remaining_prediction['expected_tweets'],
            'daily_breakdown': {str(current_datetime.date()): remaining_prediction['expected_tweets']},
            'prediction_details': [remaining_prediction]
        }
    
    # For future days
    logger.info(f"\nPredicting tweets from {current_datetime.date()} to {target_date}")
    
    # Get counts for remaining hours of the current day
    current_day_prediction = predictor.predict_remaining_hours(
        current_datetime, 
        datetime.combine(current_datetime.date(), datetime.max.time()),
        trend_factor,
        specific_hours=hours
    )
    
    remaining_days = (target_date - current_datetime.date()).days
    logger.info(f"Days to predict: {remaining_days} full days + remaining hours today")
    
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
                    hour_rate = analyzer.hour_of_day_averages.get((weekday, hour), 0)
                    expected += hour_rate * trend_factor
                except:
                    # Fallback to overall hourly rate
                    hour_rate = analyzer.hourly_rates.get(hour, 0)
                    expected += hour_rate / 24 * trend_factor
        else:
            # Get average tweets for this weekday
            expected = analyzer.weekday_averages.get(weekday, analyzer.daily_counts['count'].mean())
            expected *= trend_factor
        
        day_by_day[str(predict_date)] = expected
        total_expected += expected
        
        # Add to prediction details
        prediction_details.append({
            'date': predict_date,
            'weekday': get_weekday_name(weekday),
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
    logger.info(f"\nPrediction results:")
    if hours is not None:
        hour_str = ", ".join([f"{h}:00" for h in sorted(hours)])
        logger.info(f"Predicting for specific hours: {hour_str}")
        
    logger.info(f"From {current_datetime.date()} to {target_date}")
    logger.info(f"Expected tweets: {total_expected:.1f}")
    logger.info("\nDay-by-day breakdown:")
    
    for detail in prediction_details:
        if 'weekday' in detail:
            hour_info = f" (specific hours only)" if hours is not None else ""
            logger.info(f"- {detail['date']} ({detail['weekday']}){hour_info}: {detail['expected_tweets']:.1f} tweets")
        else:
            logger.info(f"- {current_datetime.date()} (remaining hours): {detail['expected_tweets']:.1f} tweets")
    
    return prediction_results 