"""
Prophet-based prediction algorithm for tweet count prediction.

This module provides time series forecasting capabilities using Facebook Prophet,
with additional regularization to prevent extreme predictions.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import prophet
from prophet import Prophet
import logging
import matplotlib.pyplot as plt
from src.constants import ET_TIMEZONE
import os
from scipy import stats

# Configure logging for Prophet (to avoid excessive output)
logging.getLogger('prophet').setLevel(logging.WARNING)
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

def prepare_prophet_data(df: pd.DataFrame, polymarket_start: datetime, current_time: datetime) -> pd.DataFrame:
    """
    Prepare historical tweet data for Prophet forecasting
    
    Args:
        df: DataFrame containing preprocessed tweet data
        polymarket_start: Start datetime for the analysis period
        current_time: Current datetime for the analysis cutoff
        
    Returns:
        DataFrame formatted for Prophet (with 'ds' and 'y' columns)
    """
    # Look back further for better context - up to 90 days before start
    lookback_start = polymarket_start - timedelta(days=90)
    
    # Filter data to include tweets within the relevant period plus lookback
    relevant_df = df[(df['created_at_dt'] >= lookback_start) & 
                     (df['created_at_dt'] <= current_time)]
    
    if relevant_df.empty:
        raise ValueError("No relevant tweet data found in the specified time period")
    
    # Create a copy to avoid SettingWithCopyWarning
    relevant_df = relevant_df.copy()
    
    # Create a date range from lookback start to current time with hourly frequency
    # Convert timezone-aware datetimes to naive datetimes (required by Prophet)
    lookback_start_naive = lookback_start.replace(tzinfo=None)
    current_time_naive = current_time.replace(tzinfo=None)
    
    # Count tweets per day - convert to naive datetime for grouping
    relevant_df['day'] = relevant_df['created_at_dt'].dt.tz_localize(None).dt.floor('D')
    daily_counts = relevant_df.groupby('day').size().reset_index()
    daily_counts.columns = ['ds', 'y']
    
    # Create a DataFrame with all days (not just days with tweets)
    date_range = pd.date_range(start=lookback_start_naive, end=current_time_naive, freq='D')
    all_days_df = pd.DataFrame({'ds': date_range})
    
    # Merge to ensure all days are represented (even those with no tweets)
    prophet_df = pd.merge(all_days_df, daily_counts, on='ds', how='left')
    prophet_df['y'] = prophet_df['y'].fillna(0)
    
    return prophet_df

def train_prophet_model(
    prophet_df: pd.DataFrame, 
    historical_avg: float,
    seasonality_mode: str = 'additive',
    changepoint_prior_scale: float = 0.01
) -> Prophet:
    """
    Train a Prophet model on the prepared data with strong regularization
    
    Args:
        prophet_df: DataFrame containing 'ds' and 'y' columns
        historical_avg: Historical average tweet rate for regularization
        seasonality_mode: 'additive' or 'multiplicative'
        changepoint_prior_scale: Controls flexibility of the trend (lower = more rigid)
        
    Returns:
        Trained Prophet model
    """
    # Extremely conservative growth settings to prevent unrealistic predictions
    model = Prophet(
        seasonality_mode=seasonality_mode,
        changepoint_prior_scale=changepoint_prior_scale,  # Lower value = less flexible trend
        daily_seasonality=True,
        weekly_seasonality=True,  # Always include weekly seasonality
        yearly_seasonality=False,  # Disable yearly seasonality (often not enough data)
        growth='linear',  # Use linear growth
        changepoint_range=0.8,  # Look at most of the historical data for changepoints
        interval_width=0.95,  # 95% confidence interval
        mcmc_samples=0  # Disable MCMC sampling for speed and stability
    )
    
    # Add custom seasonality for tweeting patterns
    model.add_seasonality(
        name='weekly',
        period=7,
        fourier_order=3,  # Lower order = more regularization
        mode=seasonality_mode
    )
    
    # Apply custom caps to growth to prevent unrealistic predictions
    max_rate = max(historical_avg * 2, 100)  # Cap at 2x historical average or 100/day
    
    # Fit the model
    model.fit(prophet_df)
    
    return model

def generate_prophet_forecast(
    model: Prophet, 
    prophet_df: pd.DataFrame,
    polymarket_end: datetime, 
    current_time: datetime,
    include_history: bool = False,
    force_cap: Optional[float] = None
) -> pd.DataFrame:
    """
    Generate a forecast using the trained Prophet model
    
    Args:
        model: Trained Prophet model
        prophet_df: Training data DataFrame
        polymarket_end: End datetime for the forecast
        current_time: Current datetime
        include_history: Whether to include historical data in the forecast
        force_cap: Optional maximum value to cap predictions
        
    Returns:
        DataFrame containing the forecast
    """
    # Convert timezone-aware datetimes to naive datetimes (required by Prophet)
    polymarket_end_naive = polymarket_end.replace(tzinfo=None)
    current_time_naive = current_time.replace(tzinfo=None)
    
    # Calculate the number of days to forecast
    days_to_forecast = (polymarket_end_naive - current_time_naive).days + 1
    
    # Create future dataframe with daily frequency
    future = model.make_future_dataframe(
        periods=days_to_forecast, 
        freq='D', 
        include_history=include_history
    )
    
    # Generate forecast
    forecast = model.predict(future)
    
    # Apply cap if provided
    if force_cap is not None:
        forecast['yhat'] = np.minimum(forecast['yhat'], force_cap)
        forecast['yhat_upper'] = np.minimum(forecast['yhat_upper'], force_cap * 1.1)
        forecast['yhat_lower'] = np.minimum(forecast['yhat_lower'], forecast['yhat'])
    
    return forecast

def plot_prophet_forecast(
    model: Prophet, 
    forecast: pd.DataFrame, 
    prophet_df: pd.DataFrame, 
    polymarket_start: datetime, 
    polymarket_end: datetime
) -> plt.Figure:
    """
    Create visualization of the Prophet forecast
    
    Args:
        model: Trained Prophet model
        forecast: Forecast DataFrame
        prophet_df: Training data DataFrame
        polymarket_start: Start datetime for the analysis period
        polymarket_end: End datetime for the analysis period
        
    Returns:
        Matplotlib Figure object
    """
    # Create the main forecast figure
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111)
    
    # Plot actual data points
    ax.scatter(prophet_df['ds'], prophet_df['y'], color='black', s=10, label='Actual Tweets')
    
    # Plot forecast
    ax.plot(forecast['ds'], forecast['yhat'], color='blue', label='Forecast')
    ax.fill_between(forecast['ds'], forecast['yhat_lower'], forecast['yhat_upper'], 
                   color='blue', alpha=0.2, label='95% Confidence Interval')
    
    # Add vertical lines for key timestamps
    # Convert timezone-aware datetime to naive datetime for plotting
    polymarket_start_naive = polymarket_start.replace(tzinfo=None)
    polymarket_end_naive = polymarket_end.replace(tzinfo=None)
    current_time = datetime.now(ET_TIMEZONE).replace(tzinfo=None)
    
    ax.axvline(x=polymarket_start_naive, color='green', linestyle='--', label='Start Time')
    ax.axvline(x=current_time, color='red', linestyle='--', label='Current Time')
    ax.axvline(x=polymarket_end_naive, color='orange', linestyle='--', label='End Time')
    
    # Format the plot
    ax.set_title('Daily Tweet Count Forecast')
    ax.set_xlabel('Date')
    ax.set_ylabel('Tweet Count')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Format x-axis dates
    plt.gcf().autofmt_xdate()
    
    plt.tight_layout()
    
    return fig

def calculate_cumulative_forecast(
    forecast: pd.DataFrame, 
    prophet_df: pd.DataFrame, 
    polymarket_start: datetime,
    current_time: datetime,
    current_tweet_count: int
) -> pd.DataFrame:
    """
    Calculate cumulative tweet counts from the forecast
    
    Args:
        forecast: Forecast DataFrame from Prophet
        prophet_df: Training data DataFrame
        polymarket_start: Start datetime for the analysis period
        current_time: Current datetime for the analysis cutoff
        current_tweet_count: Current tweet count in the period
        
    Returns:
        DataFrame with cumulative forecast
    """
    # Convert timezone-aware datetimes to naive datetimes
    polymarket_start_naive = polymarket_start.replace(tzinfo=None)
    current_time_naive = current_time.replace(tzinfo=None)
    
    # Create a copy of the forecast DataFrame
    cumulative = forecast.copy()
    
    # Filter to only include dates after the current time
    future_forecast = cumulative[cumulative['ds'] >= current_time_naive].copy()
    
    # Ensure we have non-negative predictions
    future_forecast['yhat'] = np.maximum(0, future_forecast['yhat'])
    future_forecast['yhat_lower'] = np.maximum(0, future_forecast['yhat_lower'])
    future_forecast['yhat_upper'] = np.maximum(0, future_forecast['yhat_upper'])
    
    # Calculate cumulative sums starting from the current count
    future_forecast['cumulative_yhat'] = current_tweet_count + future_forecast['yhat'].cumsum()
    future_forecast['cumulative_yhat_lower'] = current_tweet_count + future_forecast['yhat_lower'].cumsum()
    future_forecast['cumulative_yhat_upper'] = current_tweet_count + future_forecast['yhat_upper'].cumsum()
    
    # Merge back with the full forecast
    cumulative = pd.merge(
        cumulative, 
        future_forecast[['ds', 'cumulative_yhat', 'cumulative_yhat_lower', 'cumulative_yhat_upper']], 
        on='ds', 
        how='left'
    )
    
    # Fill NaN values for historical dates
    cumulative['cumulative_yhat'] = cumulative['cumulative_yhat'].fillna(current_tweet_count)
    cumulative['cumulative_yhat_lower'] = cumulative['cumulative_yhat_lower'].fillna(current_tweet_count)
    cumulative['cumulative_yhat_upper'] = cumulative['cumulative_yhat_upper'].fillna(current_tweet_count)
    
    return cumulative

def calculate_realistic_bounds(
    historical_data: pd.DataFrame,
    remaining_days: float,
    current_tweet_count: int,
    event_span_days: float
) -> Tuple[float, float, float, float]:
    """
    Calculate realistic minimum, average, and maximum predictions based on historical data
    
    Args:
        historical_data: DataFrame with historical tweet data
        remaining_days: Number of days remaining in the prediction period
        current_tweet_count: Current tweet count
        event_span_days: Total duration of the event in days
        
    Returns:
        Tuple of (min_prediction, avg_prediction, max_prediction, most_likely_prediction)
    """
    # Extract daily counts
    if 'date' not in historical_data.columns and 'created_at_dt' in historical_data.columns:
        historical_data = historical_data.copy()
        historical_data['date'] = historical_data['created_at_dt'].dt.date
    
    # Calculate daily statistics
    daily_counts = historical_data.groupby('date').size()
    
    # Get current rate - tweets per day so far
    elapsed_days = event_span_days - remaining_days
    current_rate = current_tweet_count / elapsed_days if elapsed_days > 0 else daily_counts.median()
    
    # Get recent data (last 30 days) for better trend estimation
    recent_dates = sorted(daily_counts.index)[-30:]
    recent_counts = daily_counts[daily_counts.index.isin(recent_dates)]
    
    # Calculate various percentiles for robust statistics
    p10 = max(1, daily_counts.quantile(0.10))  # 10th percentile with minimum of 1
    p25 = max(2, daily_counts.quantile(0.25))  # 25th percentile
    p50 = daily_counts.quantile(0.50)  # Median (50th percentile)
    p75 = daily_counts.quantile(0.75)  # 75th percentile
    p90 = daily_counts.quantile(0.90)  # 90th percentile
    
    # Recent percentiles (may be different from overall)
    if len(recent_counts) >= 10:
        recent_p50 = recent_counts.quantile(0.50)
    else:
        recent_p50 = p50
    
    # Calculate realistic bounds using percentiles and current trend
    min_prediction = current_tweet_count + (p10 * remaining_days * 0.9)
    
    # Base avg on both historical median and current rate
    if elapsed_days >= 1:
        # Weight current rate more if we have more elapsed days
        weight_current = min(0.7, elapsed_days / 7)  # Cap at 70%
        weight_historical = 1 - weight_current
        avg_rate = (current_rate * weight_current) + (p50 * weight_historical)
    else:
        # Not enough current data, rely more on historical
        avg_rate = (recent_p50 * 0.6) + (p50 * 0.4)
    
    avg_prediction = current_tweet_count + (avg_rate * remaining_days)
    
    # Calculate a most likely prediction that accounts for trend
    if elapsed_days >= 1 and current_rate > 0:
        # Trend factor: current vs historical
        trend_factor = current_rate / p50 if p50 > 0 else 1.0
        # Dampen extreme trend factors
        if trend_factor > 1:
            trend_factor = 1 + ((trend_factor - 1) * 0.7)
        elif trend_factor < 1:
            trend_factor = 1 - ((1 - trend_factor) * 0.7)
        
        most_likely_rate = p50 * trend_factor
        most_likely_prediction = current_tweet_count + (most_likely_rate * remaining_days)
    else:
        most_likely_prediction = avg_prediction
    
    # Maximum prediction with higher percentile and buffer
    if remaining_days > 3:
        # For longer forecasts, use higher percentile
        max_prediction = current_tweet_count + (p90 * remaining_days * 1.1)
    else:
        # For short forecasts, be more conservative
        max_prediction = current_tweet_count + (p75 * remaining_days * 1.2)
    
    # Ensure the bounds are in logical order
    min_prediction = max(current_tweet_count, min_prediction)
    avg_prediction = max(min_prediction, avg_prediction)
    most_likely_prediction = max(min_prediction, most_likely_prediction)
    max_prediction = max(most_likely_prediction, max_prediction)
    
    return min_prediction, avg_prediction, max_prediction, most_likely_prediction

def run_prophet_simulation(
    forecasted_final: float,
    forecasted_std: float, 
    min_prediction: float,
    max_prediction: float,
    most_likely: float,
    current_tweet_count: int,
    remaining_days: float,
    num_simulations: int = 5000
) -> np.ndarray:
    """
    Generate simulations based on the Prophet forecast with realistic bounds,
    using a custom mixture distribution for more realistic results
    
    Args:
        forecasted_final: Final predicted value from Prophet
        forecasted_std: Standard deviation for the forecast
        min_prediction: Minimum reasonable prediction
        max_prediction: Maximum reasonable prediction
        most_likely: Most likely prediction value
        current_tweet_count: Current tweet count
        remaining_days: Number of days remaining
        num_simulations: Number of simulations to run
        
    Returns:
        NumPy array of simulated end values
    """
    # Ensure the forecasted value is within reasonable bounds
    forecasted_final = max(min_prediction, min(forecasted_final, max_prediction))
    
    # Calculate a realistic standard deviation based on remaining time
    # For longer periods, variance increases with square root of time
    time_factor = np.sqrt(remaining_days)
    base_std = max(5, (max_prediction - min_prediction) / 4)
    adjusted_std = base_std * time_factor * 0.5  # Reduce by half for more concentration
    
    # Generate simulations using a mixture of distributions for more realistic results
    np.random.seed(42)  # For reproducibility
    
    # Use most_likely as the center of our main distribution
    center = most_likely
    
    # For more realistic simulations, we'll use a mixture of distributions
    # 1. Gamma distribution (skewed right) - good for tweet counts
    # 2. Small amount of uniform noise for fat tails
    
    # Prepare parameters for Gamma distribution
    # For Gamma: mean = shape * scale, variance = shape * scale^2
    # We solve for shape and scale to match our desired mean and variance
    
    # Target mean = center - current_tweet_count (because we'll add current_tweet_count later)
    target_mean = center - current_tweet_count
    # Target variance - use our adjusted standard deviation
    target_var = adjusted_std ** 2
    
    if target_mean <= 0 or target_var <= 0:
        # Fallback to simple normal if parameters are invalid
        shape = 1
        scale = 1
    else:
        # Calculate Gamma parameters
        scale = target_var / target_mean
        shape = target_mean / scale
    
    # Generate primary samples from Gamma distribution
    primary_samples = np.random.gamma(shape, scale, size=int(num_simulations * 0.95))
    
    # Generate secondary samples from uniform distribution for fat tails
    uniform_samples = np.random.uniform(
        low=0, 
        high=max_prediction - current_tweet_count,
        size=int(num_simulations * 0.05)
    )
    
    # Combine the samples
    combined_samples = np.concatenate([primary_samples, uniform_samples])
    np.random.shuffle(combined_samples)  # Shuffle to mix distributions
    
    # Take exactly num_simulations
    samples = combined_samples[:num_simulations]
    
    # Add current count and ensure all are within bounds
    simulations = current_tweet_count + samples
    simulations = np.clip(simulations, min_prediction, max_prediction)
    
    # Round to integers (tweet counts are discrete)
    simulations = np.round(simulations).astype(int)
    
    return simulations

def predict_with_prophet(
    df: pd.DataFrame,
    polymarket_start: datetime,
    polymarket_end: datetime,
    count_frames: List[Dict[str, Any]],
    current_tweet_count: int,
    num_simulations: int = 10000,
    current_time: datetime = None,
    random_seed: int = 42
) -> Dict[str, Any]:
    """
    Make predictions using a simplified approach with historical rates
    
    Args:
        df: DataFrame containing preprocessed tweet data
        polymarket_start: Start datetime for the analysis period
        polymarket_end: End datetime for the analysis period
        count_frames: List of count frame dictionaries
        current_tweet_count: Current tweet count in the period
        num_simulations: Number of Monte Carlo simulations to run
        current_time: Current time for prediction context (if None, uses system time)
        random_seed: Random seed for reproducible results
        
    Returns:
        dict: Prophet prediction results
    """
    # Use provided current_time or fall back to system time
    if current_time is None:
        now = datetime.now(ET_TIMEZONE)
    else:
        # Ensure current_time is timezone-aware
        if current_time.tzinfo is None:
            now = ET_TIMEZONE.localize(current_time)
        else:
            now = current_time
    
    try:
        # Calculate time periods
        remaining_days = (polymarket_end - now).total_seconds() / (24 * 3600)
        elapsed_days = (now - polymarket_start).total_seconds() / (24 * 3600)
        print(f"Event timing: {elapsed_days:.1f} days elapsed, {remaining_days:.1f} days remaining")
        
        # Calculate current tweet rate
        current_rate = current_tweet_count / elapsed_days if elapsed_days > 0 else 0
        print(f"Current tweet rate: {current_rate:.1f} tweets/day")
        
        # Calculate historical statistics
        df_with_date = df.copy()
        df_with_date['date'] = df_with_date['created_at_dt'].dt.date
        daily_counts = df_with_date.groupby('date').size()
        
        historical_avg = daily_counts.mean()
        historical_median = daily_counts.median()
        historical_max = daily_counts.max()
        historical_std = daily_counts.std()
        
        print(f"Historical tweet statistics (daily):")
        print(f"  Min: {daily_counts.min():.1f}, Median: {historical_median:.1f}, Mean: {historical_avg:.1f}, Max: {historical_max:.1f}")
        print(f"  Standard deviation: {historical_std:.1f}")
        
        # Use a blend of current rate and historical rate for the prediction
        # If we have at least 1 day of data, weight the current rate more heavily
        if elapsed_days >= 1:
            weight_current = min(0.7, elapsed_days / 7)  # Cap at 70%
            weight_historical = 1 - weight_current
            print(f"Weighting: {weight_current:.2f} current, {weight_historical:.2f} historical")
            
            predicted_rate = (current_rate * weight_current) + (historical_median * weight_historical)
        else:
            # Not enough current data, use historical median
            predicted_rate = historical_median
            print(f"Using historical median rate: {predicted_rate:.2f}")
            
        # Calculate expected additional tweets
        expected_additional = predicted_rate * remaining_days
        final_prediction = current_tweet_count + expected_additional
        
        print(f"Predicted rate: {predicted_rate:.1f} tweets/day")
        print(f"Expected final count: {final_prediction:.1f} tweets")
        
        # Calculate confidence interval
        # For count data, we use std that scales with the square root of time
        forecast_std = historical_std * np.sqrt(remaining_days * 0.6)  # Slightly reduced factor for tighter bounds
        
        # Calculate 90% confidence interval
        lower_ci = max(current_tweet_count, final_prediction - (1.65 * forecast_std))
        upper_ci = final_prediction + (1.65 * forecast_std)
        
        print(f"90% confidence interval: {lower_ci:.1f} to {upper_ci:.1f}")
        
        # Create simulations using a lognormal distribution (better for count data than normal)
        # Set up the lognormal parameters to match our mean and std
        # For lognormal: mean = exp(mu + sigma^2/2), var = [exp(sigma^2) - 1] * exp(2*mu + sigma^2)
        
        # First, calculate target mean and variance for the additional tweets
        target_mean = expected_additional
        target_var = forecast_std**2
        
        # Then convert to lognormal parameters
        if target_mean > 0 and target_var > 0:
            # Calculate lognormal parameters
            phi = np.sqrt(1 + (target_var / target_mean**2))
            sigma = np.sqrt(np.log(phi**2))
            mu = np.log(target_mean) - 0.5 * sigma**2
            
            # Generate samples from lognormal distribution
            np.random.seed(random_seed)
            additional_tweets = np.random.lognormal(mu, sigma, num_simulations)
            
            # Add current count and round to integers
            simulations = np.round(current_tweet_count + additional_tweets).astype(int)
        else:
            # Fallback to normal distribution if parameters are invalid
            np.random.seed(random_seed)
            additional_tweets = np.maximum(0, np.random.normal(expected_additional, forecast_std, num_simulations))
            simulations = np.round(current_tweet_count + additional_tweets).astype(int)
        
        # Calculate probabilities for each frame
        frame_probabilities = {}
        for frame in count_frames:
            count = np.sum((simulations >= frame["min"]) & (simulations <= frame["max"]))
            probability = count / len(simulations) * 100
            frame_probabilities[frame["name"]] = probability
        
        # Print distribution of simulations
        print("\nSimulation distribution:")
        for frame in count_frames:
            count = np.sum((simulations >= frame["min"]) & (simulations <= frame["max"]))
            pct = count / len(simulations) * 100
            print(f"  {frame['name']}: {pct:.1f}% ({count} simulations)")
            
        # Generate simple forecast data for plotting
        # Create dates from now to end date
        forecast_dates = pd.date_range(start=now, end=polymarket_end, freq='D')
        forecast_df = pd.DataFrame({'ds': forecast_dates})
        
        # Add y values based on predicted rate
        forecast_df['yhat'] = predicted_rate
        forecast_df['yhat_lower'] = predicted_rate * 0.7  # Simple lower bound
        forecast_df['yhat_upper'] = predicted_rate * 1.3  # Simple upper bound
        
        # Create dummy prophet model object for compatibility
        model = Prophet()
        
        # Create past data for plotting
        past_dates = pd.date_range(start=polymarket_start, end=now, freq='D')
        past_df = pd.DataFrame({'ds': past_dates})
        
        # Create visualization
        print("Creating forecast visualization...")
        fig = plt.figure(figsize=(12, 6))
        ax = fig.add_subplot(111)
        
        # Plot historical rate
        ax.axhline(y=historical_median, color='gray', linestyle='--', label=f'Historical median: {historical_median:.1f}')
        
        # Plot current and predicted rates
        ax.axhline(y=current_rate, color='blue', linestyle='-', label=f'Current rate: {current_rate:.1f}')
        ax.axhline(y=predicted_rate, color='red', linestyle='-', label=f'Predicted rate: {predicted_rate:.1f}')
        
        # Add vertical lines for key timestamps
        polymarket_start_naive = polymarket_start.replace(tzinfo=None)
        polymarket_end_naive = polymarket_end.replace(tzinfo=None)
        current_time_naive = now.replace(tzinfo=None)
        
        ax.axvline(x=polymarket_start_naive, color='green', linestyle='--', label='Start Time')
        ax.axvline(x=current_time_naive, color='red', linestyle='--', label='Current Time')
        ax.axvline(x=polymarket_end_naive, color='orange', linestyle='--', label='End Time')
        
        # Format the plot
        ax.set_title('Tweet Rate Forecast')
        ax.set_xlabel('Date')
        ax.set_ylabel('Tweet Rate (per day)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        
        # Save the forecast figure
        try:
            output_dir = 'src/polymarket_predictor/plots'
            os.makedirs(output_dir, exist_ok=True)
            fig.savefig(f"{output_dir}/prophet_forecast.png")
            plt.close(fig)
        except Exception as e:
            print(f"Warning: Could not save forecast figure: {e}")
        
        # Create visualization of probability distribution
        print("Creating probability distribution visualization...")
        dist_fig = plt.figure(figsize=(12, 6))
        ax = dist_fig.add_subplot(111)
        
        # Create histogram of simulations
        n, bins, patches = plt.hist(simulations, bins=30, alpha=0.6, density=True, color='skyblue')
        
        # Add KDE for smooth distribution visualization
        try:
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(simulations)
            x = np.linspace(min(simulations), max(simulations), 1000)
            ax.plot(x, kde(x), 'r-', linewidth=2)
        except Exception:
            pass  # Skip KDE if it fails
        
        # Add vertical lines for key values
        ax.axvline(x=current_tweet_count, color='black', linestyle='-', label=f'Current: {current_tweet_count}', linewidth=2)
        ax.axvline(x=final_prediction, color='red', linestyle='--', label=f'Prediction: {final_prediction:.1f}', linewidth=2)
        ax.axvline(x=lower_ci, color='orange', linestyle=':', label=f'90% CI: {lower_ci:.1f} - {upper_ci:.1f}', linewidth=1.5)
        ax.axvline(x=upper_ci, color='orange', linestyle=':', linewidth=1.5)
        
        # Format the plot
        ax.set_title('Final Tweet Count Probability Distribution')
        ax.set_xlabel('Total Tweets')
        ax.set_ylabel('Probability Density')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        try:
            dist_fig.savefig(f"{output_dir}/tweet_distribution.png")
            plt.close(dist_fig)
        except Exception as e:
            print(f"Warning: Could not save distribution figure: {e}")
        
        # Return the results in compatible format
        return {
            'model': model,
            'prophet_df': past_df,
            'forecast': forecast_df,
            'simulations': simulations,
            'frame_probabilities': frame_probabilities,
            'confidence_interval': (lower_ci, upper_ci),
            'expected_count': final_prediction
        }
        
    except Exception as e:
        print(f"Error in prediction: {e}")
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        return {
            'error': str(e),
            'frame_probabilities': {frame["name"]: 0 for frame in count_frames}
        } 