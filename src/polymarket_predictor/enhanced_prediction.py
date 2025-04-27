"""
Enhanced prediction algorithm for tweet count prediction.

This module provides more sophisticated prediction algorithms that improve upon
the basic Monte Carlo simulation in the original implementation.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from scipy import stats

# Import local modules
from src.constants import ET_TIMEZONE

def analyze_hourly_pattern(df: pd.DataFrame, last_n_days: int = 30) -> Dict[int, float]:
    """
    Analyze hourly tweet patterns to create a distribution of tweet probability by hour
    
    Args:
        df: DataFrame containing preprocessed tweet data
        last_n_days: Number of recent days to analyze for the pattern
        
    Returns:
        dict: Mapping of hour (0-23) to tweet probability
    """
    # Get the recent data only
    now = datetime.now(ET_TIMEZONE)
    start_date = now - timedelta(days=last_n_days)
    
    # Filter for recent tweets
    recent_df = df[df['created_at_dt'] >= start_date]
    if recent_df.empty:
        # If no recent data, use all data
        recent_df = df
    
    # Extract hour from datetime
    recent_df['hour'] = recent_df['created_at_dt'].dt.hour
    
    # Calculate the distribution
    hourly_counts = recent_df.groupby('hour').size()
    total_tweets = hourly_counts.sum()
    
    # Create a probability distribution (normalize to sum to 1.0)
    hourly_probs = {}
    for hour in range(24):
        count = hourly_counts.get(hour, 0)
        hourly_probs[hour] = count / total_tweets if total_tweets > 0 else 1/24
    
    return hourly_probs

def analyze_daily_pattern(df: pd.DataFrame, last_n_days: int = 90) -> Dict[int, float]:
    """
    Analyze daily tweet patterns to create a distribution of tweet probability by day of week
    
    Args:
        df: DataFrame containing preprocessed tweet data
        last_n_days: Number of recent days to analyze for the pattern
        
    Returns:
        dict: Mapping of day (0-6, Monday=0) to tweet probability
    """
    # Get the recent data only
    now = datetime.now(ET_TIMEZONE)
    start_date = now - timedelta(days=last_n_days)
    
    # Filter for recent tweets
    recent_df = df[df['created_at_dt'] >= start_date]
    if recent_df.empty:
        # If no recent data, use all data
        recent_df = df
    
    # Extract day of week from datetime
    recent_df['day_of_week'] = recent_df['created_at_dt'].dt.weekday
    
    # Count occurrences of each day
    daily_counts = recent_df.groupby('day_of_week').size()
    
    # Calculate the number of each weekday in the period
    day_occurrences = {}
    current_date = start_date.date()
    end_date = now.date()
    
    while current_date <= end_date:
        day_of_week = current_date.weekday()
        day_occurrences[day_of_week] = day_occurrences.get(day_of_week, 0) + 1
        current_date += timedelta(days=1)
    
    # Calculate average tweets per day of week
    daily_avg = {}
    for day in range(7):
        count = daily_counts.get(day, 0)
        occurrences = day_occurrences.get(day, 1)  # Avoid division by zero
        daily_avg[day] = count / occurrences
    
    # Normalize to get relative weights (probability distribution)
    total_avg = sum(daily_avg.values())
    daily_probs = {day: avg / total_avg for day, avg in daily_avg.items()}
    
    return daily_probs

def calculate_rate_with_trend(df: pd.DataFrame, 
                             polymarket_start: datetime, 
                             polymarket_end: datetime, 
                             current_tweet_count: int) -> Dict[str, float]:
    """
    Calculate tweet rate with advanced trend analysis
    
    Args:
        df: DataFrame containing preprocessed tweet data
        polymarket_start: Start datetime for the analysis period
        polymarket_end: End datetime for the analysis period
        current_tweet_count: Current tweet count in the period
        
    Returns:
        dict: Enhanced analysis results
    """
    now = datetime.now(ET_TIMEZONE)
    
    # Calculate time periods
    elapsed_days = (now - polymarket_start).total_seconds() / (24 * 3600)
    remaining_days = (polymarket_end - now).total_seconds() / (24 * 3600)
    
    # Current rate calculation
    current_rate = current_tweet_count / elapsed_days if elapsed_days > 0 else 0
    
    # Calculate historical rates for different periods
    day_ranges = [7, 14, 30, 60, 90]
    rates = {}
    weights = {}
    
    # Assign decreasing weights to older periods
    total_weight = 0
    for i, days in enumerate(day_ranges):
        # Weight decreases as we go further back in time
        weight = 1.0 / (i + 1)
        total_weight += weight
        weights[days] = weight
    
    # Normalize weights to sum to 1.0
    for days in weights:
        weights[days] /= total_weight
    
    # Calculate rates for different time periods
    for days in day_ranges:
        period_start = now - timedelta(days=days)
        period_tweets = df[(df['created_at_dt'] >= period_start) & (df['created_at_dt'] <= now)]
        
        # Handle the case where the period is longer than our data
        if now > period_start:
            actual_days = min(days, (now - period_start).total_seconds() / (24 * 3600))
            rates[days] = len(period_tweets) / actual_days
        else:
            rates[days] = current_rate
    
    # Calculate trend-adjusted rate using weighted average
    weighted_rate = sum(rates[days] * weights[days] for days in day_ranges)
    
    # Calculate acceleration (rate of change of rate)
    if len(day_ranges) >= 2:
        short_term = rates[day_ranges[0]]  # e.g., 7-day rate
        long_term = rates[day_ranges[-1]]  # e.g., 90-day rate
        acceleration = (short_term - long_term) / long_term if long_term > 0 else 0
    else:
        acceleration = 0
    
    # Apply acceleration factor to future rate prediction
    # If acceleration is positive, future rate might be higher than current
    acceleration_factor = 1.0 + (acceleration * 0.5)  # Dampen the acceleration effect
    
    # Calculate projected rate
    projected_rate = weighted_rate * acceleration_factor
    
    # Ensure rate is positive
    projected_rate = max(0.1, projected_rate)
    
    # Calculate daily tweet std deviation for volatility estimation
    df['date'] = df['created_at_dt'].dt.date
    daily_counts = df.groupby('date').size()
    
    # Use robust estimator for volatility (exclude outliers)
    if len(daily_counts) > 10:
        # Filter out extreme outliers (beyond 3 std devs)
        mean_count = daily_counts.mean()
        std_count = daily_counts.std()
        filtered_counts = daily_counts[(daily_counts > mean_count - 3*std_count) & 
                                      (daily_counts < mean_count + 3*std_count)]
        daily_std = filtered_counts.std()
    else:
        daily_std = daily_counts.std() if len(daily_counts) > 1 else projected_rate * 0.2
    
    return {
        'tweet_count': current_tweet_count,
        'elapsed_days': elapsed_days,
        'remaining_days': remaining_days,
        'current_rate': current_rate,
        'projected_rate': projected_rate,
        'acceleration': acceleration,
        'acceleration_factor': acceleration_factor,
        'rates': rates,
        'daily_std': daily_std,
        'weights': weights
    }

def run_enhanced_monte_carlo(
    df: pd.DataFrame,
    analysis: Dict[str, float],
    count_frames: List[Dict[str, Any]],
    num_simulations: int = 10000,
    confidence_level: float = 0.95
) -> Tuple[np.ndarray, Dict[str, float], Tuple[float, float]]:
    """
    Run enhanced Monte Carlo simulation using more sophisticated modeling
    
    Args:
        df: DataFrame containing preprocessed tweet data
        analysis: Dictionary with time period analysis results
        count_frames: List of count frame dictionaries
        num_simulations: Number of Monte Carlo simulations to run
        confidence_level: Confidence level for interval calculation (0.0-1.0)
        
    Returns:
        tuple: (simulations, frame_probabilities, confidence_interval)
    """
    # Extract values from analysis
    tweet_count = analysis['tweet_count']
    remaining_days = analysis['remaining_days']
    projected_rate = analysis['projected_rate']
    daily_std = analysis['daily_std']
    
    # Get daily and hourly patterns
    daily_probs = analyze_daily_pattern(df)
    hourly_probs = analyze_hourly_pattern(df)
    
    # Determine which days are in the remaining period
    now = datetime.now(ET_TIMEZONE)
    current_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = now + timedelta(days=remaining_days)
    
    # Calculate remaining days with their weekday weights
    remaining_day_weights = []
    while current_day < end_time:
        weekday = current_day.weekday()
        day_weight = daily_probs.get(weekday, 1/7)  # Default to uniform if missing
        remaining_day_weights.append(day_weight)
        current_day += timedelta(days=1)
    
    # Normalize day weights to sum to remaining_days
    if remaining_day_weights:
        total_weight = sum(remaining_day_weights)
        normalized_weights = [w * remaining_days / total_weight for w in remaining_day_weights]
    else:
        normalized_weights = []
    
    # Base expected tweets for remaining period
    expected_tweets = projected_rate * remaining_days
    
    # Run Monte Carlo simulation with enhanced model
    np.random.seed(42)  # For reproducibility
    print(f"Running enhanced Monte Carlo simulation with {num_simulations} iterations...")
    
    # Generate simulations using Negative Binomial distribution which is more appropriate for count data
    # It models the number of successes before a specified number of failures
    
    # Parameters for Negative Binomial: r (failures), p (probability)
    # Convert from mean (μ) and variance (σ²) to r and p:
    # p = μ/σ²
    # r = μ²/(σ²-μ)
    
    # Use expected tweets as mean and calculate variance from daily_std
    mean = expected_tweets
    variance = (daily_std ** 2) * remaining_days
    
    # Ensure mean and variance are positive and variance > mean (overdispersion)
    mean = max(0.1, mean)
    variance = max(mean * 1.1, variance)  # Ensure overdispersion
    
    # Calculate Negative Binomial parameters
    p = mean / variance if variance > 0 else 0.5
    r = mean ** 2 / (variance - mean) if variance > mean else 1
    
    # Bound p between 0 and 1
    p = max(0.001, min(0.999, p))
    
    # Generate simulations from Negative Binomial
    # Add tweet_count to the generated values since we're predicting additional tweets
    raw_sims = np.random.negative_binomial(n=r, p=p, size=num_simulations)
    simulations = raw_sims + tweet_count
    
    # Calculate probabilities for each frame
    frame_probabilities = {}
    for frame in count_frames:
        count = np.sum((simulations >= frame["min"]) & (simulations <= frame["max"]))
        probability = count / len(simulations) * 100
        frame_probabilities[frame["name"]] = probability
    
    # Calculate confidence interval
    alpha = 1 - confidence_level
    lower_percentile = alpha / 2 * 100
    upper_percentile = (1 - alpha / 2) * 100
    ci_lower = max(tweet_count, np.percentile(simulations, lower_percentile))
    ci_upper = np.percentile(simulations, upper_percentile)
    confidence_interval = (ci_lower, ci_upper)
    
    return simulations, frame_probabilities, confidence_interval

def detect_anomalies(df: pd.DataFrame, lookback_days: int = 30) -> Dict[str, Any]:
    """
    Detect anomalies in recent tweet patterns that might affect predictions
    
    Args:
        df: DataFrame containing preprocessed tweet data
        lookback_days: Number of recent days to analyze for anomalies
        
    Returns:
        dict: Dictionary containing anomaly detection results
    """
    now = datetime.now(ET_TIMEZONE)
    start_date = now - timedelta(days=lookback_days)
    
    # Filter for recent tweets
    recent_df = df[df['created_at_dt'] >= start_date]
    if recent_df.empty:
        return {'anomalies_detected': False}
    
    # Aggregate by day
    recent_df['date'] = recent_df['created_at_dt'].dt.date
    daily_counts = recent_df.groupby('date').size()
    
    # Calculate basic statistics
    mean_count = daily_counts.mean()
    std_count = daily_counts.std()
    
    # Check for outlier days (>2 standard deviations from mean)
    outliers = daily_counts[abs(daily_counts - mean_count) > 2 * std_count]
    
    # Check for sustained trend changes
    if len(daily_counts) >= 14:
        # Split into two halves
        sorted_counts = daily_counts.sort_index()
        half_point = len(sorted_counts) // 2
        first_half = sorted_counts.iloc[:half_point]
        second_half = sorted_counts.iloc[half_point:]
        
        # Compare means of the two halves
        first_mean = first_half.mean()
        second_mean = second_half.mean()
        percent_change = (second_mean - first_mean) / first_mean * 100 if first_mean > 0 else 0
        
        significant_trend_change = abs(percent_change) > 30  # 30% change threshold
    else:
        significant_trend_change = False
        percent_change = 0
    
    # Check for recent zeros (unusually low activity)
    recent_3days = daily_counts.sort_index().tail(3)
    unusual_inactivity = (recent_3days < 0.3 * mean_count).any() if not recent_3days.empty else False
    
    # Check for sudden spike followed by decline (could be one-off event)
    spike_followed_by_decline = False
    if len(daily_counts) >= 5:
        sorted_counts = daily_counts.sort_index()
        for i in range(len(sorted_counts) - 3):
            current = sorted_counts.iloc[i]
            next_day = sorted_counts.iloc[i+1]
            two_days_later = sorted_counts.iloc[i+2]
            
            if (next_day > current * 2) and (two_days_later < next_day * 0.7):
                spike_followed_by_decline = True
                break
    
    # Create anomaly report
    anomalies = {
        'anomalies_detected': bool(len(outliers) > 0 or significant_trend_change or unusual_inactivity or spike_followed_by_decline),
        'outlier_days': len(outliers),
        'outlier_dates': list(outliers.index) if len(outliers) > 0 else [],
        'significant_trend_change': significant_trend_change,
        'percent_change': percent_change,
        'unusual_inactivity': unusual_inactivity,
        'spike_followed_by_decline': spike_followed_by_decline
    }
    
    return anomalies

def predict_with_enhanced_algorithm(
    df: pd.DataFrame,
    polymarket_start: datetime,
    polymarket_end: datetime,
    count_frames: List[Dict[str, Any]],
    current_tweet_count: int,
    num_simulations: int = 10000
) -> Dict[str, Any]:
    """
    Make predictions using the enhanced algorithm
    
    Args:
        df: DataFrame containing preprocessed tweet data
        polymarket_start: Start datetime for the analysis period
        polymarket_end: End datetime for the analysis period
        count_frames: List of count frame dictionaries
        current_tweet_count: Current tweet count in the period
        num_simulations: Number of Monte Carlo simulations to run
        
    Returns:
        dict: Enhanced prediction results
    """
    # Run enhanced rate analysis
    analysis = calculate_rate_with_trend(df, polymarket_start, polymarket_end, current_tweet_count)
    
    # Check for anomalies
    anomalies = detect_anomalies(df)
    
    # Apply anomaly corrections if needed
    if anomalies['anomalies_detected']:
        print("\n--- Anomaly Detection Results ---")
        if anomalies['outlier_days'] > 0:
            print(f"Detected {anomalies['outlier_days']} outlier days in recent history")
            if anomalies['outlier_dates']:
                print(f"Outlier dates: {', '.join(str(d) for d in anomalies['outlier_dates'])}")
        
        if anomalies['significant_trend_change']:
            print(f"Significant trend change detected: {anomalies['percent_change']:.1f}% change in recent activity")
            
            # Adjust the projected rate based on the trend change
            adjustment = 1 + (anomalies['percent_change'] / 100) * 0.7  # Dampen the effect by 30%
            analysis['projected_rate'] *= adjustment
            print(f"Adjusted projected rate by factor of {adjustment:.2f}")
        
        if anomalies['unusual_inactivity']:
            print("Warning: Unusual inactivity detected in recent days")
            
        if anomalies['spike_followed_by_decline']:
            print("Warning: Recent spike followed by decline detected (possible one-off event)")
    
    # Run enhanced Monte Carlo simulation
    simulations, frame_probabilities, confidence_interval = run_enhanced_monte_carlo(
        df, analysis, count_frames, num_simulations)
    
    # Calculate expected tweet count
    expected_count = analysis['tweet_count'] + (analysis['projected_rate'] * analysis['remaining_days'])
    
    # Return the results
    return {
        'analysis': analysis,
        'anomalies': anomalies,
        'simulations': simulations,
        'frame_probabilities': frame_probabilities,
        'confidence_interval': confidence_interval,
        'expected_count': expected_count
    } 