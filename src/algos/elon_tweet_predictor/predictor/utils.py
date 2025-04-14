from datetime import datetime, timedelta

def calculate_trend_factor(analyzer, use_trend=True):
    """
    Calculate the trend adjustment factor based on recent vs overall tweet activity
    
    Parameters:
    analyzer: TweetPatternAnalyzer instance
    use_trend: Whether to apply trend adjustment
    
    Returns:
    float: Trend adjustment factor (1.0 if no adjustment)
    """
    if not use_trend:
        return 1.0
        
    # Calculate trend factor
    recent_avg = analyzer.daily_counts.iloc[-7:]['count'].mean() if len(analyzer.daily_counts) >= 7 else analyzer.daily_counts['count'].mean()
    overall_avg = analyzer.daily_counts['count'].mean()
    
    if overall_avg <= 0:
        return 1.0
        
    return recent_avg / overall_avg

def validate_hours(hours):
    """
    Validate and filter provided hours to ensure they're in valid range
    
    Parameters:
    hours: List of hour integers to validate
    
    Returns:
    list or None: Filtered list of valid hours or None if no valid hours
    """
    if hours is None:
        return None
        
    valid_hours = []
    for hour in hours:
        if isinstance(hour, int) and 0 <= hour < 24:
            valid_hours.append(hour)
        else:
            print(f"Ignoring invalid hour: {hour}. Hours must be integers between 0-23.")
    
    if not valid_hours and hours:
        print("No valid hours provided. Using all hours for prediction.")
        return None
        
    return valid_hours

def get_weekday_name(weekday_index):
    """
    Get the weekday name from the weekday index (0-6)
    
    Parameters:
    weekday_index: Integer from 0 (Monday) to 6 (Sunday)
    
    Returns:
    str: Weekday name
    """
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return weekday_names[weekday_index]

def format_hour_ampm(hour):
    """
    Format hour as AM/PM string
    
    Parameters:
    hour: Hour (0-23)
    
    Returns:
    str: Formatted hour string (e.g., "12 PM")
    """
    return f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}" 