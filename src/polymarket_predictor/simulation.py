import numpy as np
from typing import Dict, List, Tuple, Optional

def run_monte_carlo_simulation(
    final_prediction: float,
    remaining_vol: float,
    tweet_count: int,
    count_frames: List[Dict[str, any]],
    num_simulations: int = 5000
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Run Monte Carlo simulation to predict tweet count probabilities
    
    Args:
        final_prediction: Predicted final tweet count
        remaining_vol: Volatility estimate for the remaining period
        tweet_count: Current tweet count (used as minimum value)
        count_frames: List of count frame dictionaries
        num_simulations: Number of Monte Carlo simulations to run
        
    Returns:
        tuple: (simulations, frame_probabilities) where simulations is array of simulation results
              and frame_probabilities is dictionary mapping frames to probabilities
    """
    # Run Monte Carlo simulation
    np.random.seed(42)  # For reproducibility
    print(f"Running Monte Carlo simulation with {num_simulations} iterations...")
    simulations = np.random.normal(final_prediction, remaining_vol, num_simulations)
    
    # Enforce the constraint that predictions cannot be less than current count
    simulations = np.maximum(simulations, tweet_count)
    
    # Calculate probabilities for each frame
    frame_probabilities = {}
    for frame in count_frames:
        count = np.sum((simulations >= frame["min"]) & (simulations <= frame["max"]))
        probability = count / len(simulations) * 100
        frame_probabilities[frame["name"]] = probability
    
    return simulations, frame_probabilities

def calculate_confidence_interval(
    final_prediction: float,
    std_dev: float
) -> Tuple[float, float]:
    """
    Calculate 95% confidence interval for the prediction
    
    Args:
        final_prediction: Predicted final tweet count
        std_dev: Standard deviation
        
    Returns:
        tuple: (lower_bound, upper_bound) 95% confidence interval
    """
    lower_bound = final_prediction - 2 * std_dev
    upper_bound = final_prediction + 2 * std_dev
    
    return (lower_bound, upper_bound)

def map_final_count_to_frame(
    final_count: int,
    count_frames: List[Dict[str, any]]
) -> Optional[str]:
    """
    Map a final tweet count to its corresponding frame
    
    Args:
        final_count: Final tweet count
        count_frames: List of count frame dictionaries
        
    Returns:
        str: Frame name containing the final count, or None if no match
    """
    for frame in count_frames:
        if frame["min"] <= final_count <= frame["max"]:
            return frame["name"]
    
    return None

def generate_event_outcome_probabilities(
    df,
    start_time,
    end_time,
    count_frames,
    use_trend=True,
    num_simulations=5000,
    current_tweet_count=None,
    override_auto_count=False
) -> Dict[str, float]:
    """
    Generate outcome probabilities for all frames
    
    This is a placeholder function - the implementation would integrate
    time_analysis, prediction calculation, and Monte Carlo simulation
    to produce the final probabilities for all frames.
    
    Args:
        df: DataFrame containing preprocessed tweet data
        start_time: Start datetime for the analysis period
        end_time: End datetime for the analysis period
        count_frames: List of count frame dictionaries
        use_trend: Whether to use trend adjustment in predictions
        num_simulations: Number of Monte Carlo simulations to run
        current_tweet_count: Manual override for current tweet count
        override_auto_count: Whether to use the provided current_tweet_count
        
    Returns:
        dict: Dictionary mapping frames to probabilities
    """
    # This would integrate functionality from other modules to calculate the probabilities
    # The actual implementation would be in the main predict_tweet_frame_probabilities function
    
    # For now, return a sample result
    frame_names = [frame["name"] for frame in count_frames]
    return {frame: 0.0 for frame in frame_names} 