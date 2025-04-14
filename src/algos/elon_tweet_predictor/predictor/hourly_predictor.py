from datetime import datetime, timedelta
from src.algos.elon_tweet_predictor.predictor.utils import (
    calculate_trend_factor,
    get_weekday_name,
    format_hour_ampm
)

def predict_next_hours(predictor, hours_ahead=4, use_trend=True):
    """
    Predict how many tweets Elon will post in the next N hours.
    
    Parameters:
    predictor: TweetPredictor instance
    hours_ahead (int): Number of hours to predict for
    use_trend (bool): Whether to apply recent trend adjustment to predictions
    
    Returns:
    dict: Prediction results
    """
    analyzer = predictor.analyzer
    
    if analyzer is None or analyzer.hourly_rates is None:
        print("Please set analyzer with analyzed patterns first")
        return
    
    # Get current datetime from last available data point
    current_datetime = datetime.combine(
        analyzer.df['date'].max(), 
        analyzer.df['created_at'].max().time()
    )
    target_datetime = current_datetime + timedelta(hours=hours_ahead)
    
    print(f"\nPredicting tweets for the next {hours_ahead} hours")
    print(f"From: {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"To: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Calculate trend factor
    trend_factor = calculate_trend_factor(analyzer, use_trend)
    
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
        current_hour_rate = analyzer.hour_of_day_averages.get((current_weekday, current_hour), 0)
        hour_expected = current_hour_rate * remaining_portion * trend_factor
    except:
        # Fallback to overall hourly rate
        current_hour_rate = analyzer.hourly_rates.get(current_hour, 0)
        hour_expected = current_hour_rate * remaining_portion / 24 * trend_factor
    
    expected_tweets += hour_expected
    
    # Add current hour to hour-by-hour breakdown
    hour_by_hour.append({
        'datetime': current_datetime.strftime('%Y-%m-%d %H:%M:%S'),
        'hour': current_hour,
        'weekday': get_weekday_name(current_weekday),
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
            hour_rate = analyzer.hour_of_day_averages.get((next_weekday, next_hour), 0)
            hour_expected = hour_rate * portion * trend_factor
        except:
            # Fallback to overall hourly rate
            hour_rate = analyzer.hourly_rates.get(next_hour, 0)
            hour_expected = hour_rate * portion / 24 * trend_factor
        
        expected_tweets += hour_expected
        
        # Add to hour-by-hour breakdown
        hour_by_hour.append({
            'datetime': next_datetime.strftime('%Y-%m-%d %H:%M'),
            'hour': next_hour,
            'weekday': get_weekday_name(next_weekday),
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
        hour_ampm = format_hour_ampm(detail['hour'])
        if detail['partial']:
            print(f"- {detail['datetime']} ({hour_ampm}, {detail['portion']*60:.0f} min): {detail['expected_tweets']:.2f} tweets")
        else:
            print(f"- {detail['datetime']} ({hour_ampm}): {detail['expected_tweets']:.2f} tweets")
    
    return prediction_results 