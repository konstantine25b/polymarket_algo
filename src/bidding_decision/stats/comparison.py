"""
Comparison tool for Polymarket predictions and order book data.
"""

import os
import json
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import logging
import datetime
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import re
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_prediction_data_from_module(algorithm: str = "prophet", **kwargs) -> Dict[str, Any]:
    """
    Get prediction data from various prediction algorithm modules.
    
    Args:
        algorithm: Algorithm to use ("prophet", "facebook_prophet", "neural_prophet", "timesfm", "ensemble")
        **kwargs: Additional arguments for the specific algorithm
        
    Returns:
        Dict containing prediction data with frame_probabilities and summary
    """
    try:
        # Import the predictor class based on algorithm
        if algorithm == "prophet":
            # Use the original polymarket_predictor
            return get_prediction_data_legacy(prophet=True)
        elif algorithm == "facebook_prophet":
            from src.prediction_algos.facebook_prophet import TweetPredictor
            predictor = TweetPredictor(save_plots=False)
        elif algorithm == "enhanced_facebook_prophet":
            from src.prediction_algos.facebook_prophet import EnhancedTweetPredictor
            predictor = EnhancedTweetPredictor(
                save_plots=False,
                random_seed=kwargs.get('random_seed', 42)
            )
        elif algorithm == "neural_prophet":
            from src.prediction_algos.neural_prophet.predictor import NeuralTweetPredictor
            predictor = NeuralTweetPredictor(save_plots=False)
        elif algorithm == "enhanced_neural_prophet":
            from src.prediction_algos.neural_prophet.enhanced_predictor import EnhancedNeuralTweetPredictor
            predictor = EnhancedNeuralTweetPredictor(
                save_plots=False,
                random_seed=kwargs.get('random_seed', 42)
            )
        elif algorithm == "timesfm":
            from src.prediction_algos.timesfm.predictor import TimesFMTweetPredictor
            predictor = TimesFMTweetPredictor(save_plots=False)
        elif algorithm == "enhanced_timesfm":
            from src.prediction_algos.timesfm import EnhancedTimesFMTweetPredictor
            predictor = EnhancedTimesFMTweetPredictor(
                save_plots=False,
                random_seed=kwargs.get('random_seed', 42)
            )
        elif algorithm == "ensemble":
            from src.prediction_algos.ensemble.predictor import EnsembleTweetPredictor
            predictor = EnsembleTweetPredictor(
                save_plots=False,
                random_seed=kwargs.get('random_seed', 42)
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        # Set random seed for reproducible results (except enhanced_timesfm which gets it in constructor)
        if algorithm != "enhanced_timesfm" and hasattr(predictor, 'set_random_seed'):
            predictor.set_random_seed(kwargs.get('random_seed', 42))
        
        # Prepare the model with any provided parameters
        if algorithm == "facebook_prophet":
            predictor.prepare_model(
                changepoint_prior_scale=kwargs.get('changepoint_prior', 0.05),
                seasonality_prior_scale=kwargs.get('seasonality_prior', 10.0)
            )
        elif algorithm == "enhanced_facebook_prophet":
            # Enhanced Facebook Prophet uses prepare_models (plural) method
            predictor.prepare_models()
        elif algorithm == "neural_prophet":
            predictor.prepare_model(
                epochs=kwargs.get('epochs', 50),
                learning_rate=kwargs.get('learning_rate', 0.15)
            )
        elif algorithm == "enhanced_neural_prophet":
            # Enhanced Neural Prophet uses prepare_models (plural) method
            predictor.prepare_models()
        elif algorithm == "timesfm":
            predictor.prepare_model()
        elif algorithm == "enhanced_timesfm":
            # Enhanced TimesFM uses prepare_models (plural) method
            predictor.prepare_models()
        elif algorithm == "ensemble":
            # Ensemble uses prepare_models (plural) method instead
            predictor.prepare_models(fast_mode=kwargs.get('fast_mode', False))
        
        # Generate predictions
        current_time = kwargs.get('current_time', None)
        if algorithm in ["enhanced_facebook_prophet", "enhanced_neural_prophet"]:
            # Enhanced models use generate_enhanced_predictions
            predictions = predictor.generate_enhanced_predictions(current_time=current_time)
        else:
            # Standard models use generate_predictions
            predictions = predictor.generate_predictions(current_time=current_time)
        
        # Handle show_eachalgo_distribution for ensemble algorithm
        if algorithm == "ensemble" and kwargs.get('show_eachalgo_distribution', False):
            # Calculate and display individual algorithm distributions
            individual_probs = predictor.calculate_individual_algorithm_probabilities(predictions)
            predictor.print_individual_algorithm_distributions(predictions)
        
        # Convert predictions to the expected format
        prediction_data = {
            'frame_probabilities': {},
            'summary': {
                'expected_value': 0
            },
            'algorithm': algorithm,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Extract frame probabilities and calculate expected value
        total_prob = 0
        expected_value = 0
        
        # Handle different prediction formats
        if 'predictions_by_frame' in predictions:
            # Special handling for ensemble algorithm to use corrected probabilities
            if algorithm == "ensemble":
                # Use the corrected ensemble probabilities instead of the flawed ones
                individual_probs = predictor.calculate_individual_algorithm_probabilities(predictions)
                
                if individual_probs:
                    # Calculate corrected ensemble probabilities using renormalized weights
                    displayed_total_weight = sum(data['weight'] for data in individual_probs.values())
                    corrected_ensemble_probs = {}
                    
                    # Get all frame names
                    from constants import TWEET_COUNT_FRAMES
                    all_frame_names = [frame['name'] for frame in TWEET_COUNT_FRAMES]
                    
                    for frame_name in all_frame_names:
                        weighted_sum = 0.0
                        
                        for algo_name, data in individual_probs.items():
                            original_weight = data['weight']
                            # Renormalize weight so displayed algorithms sum to 1.0
                            renormalized_weight = original_weight / displayed_total_weight if displayed_total_weight > 0 else 0.0
                            prob = data['probabilities'].get(frame_name, 0.0)
                            weighted_sum += prob * renormalized_weight
                        
                        corrected_ensemble_probs[frame_name] = weighted_sum
                    
                    # Final normalization to ensure probabilities sum to 1
                    total_corrected_prob = sum(corrected_ensemble_probs.values())
                    if total_corrected_prob > 0:
                        corrected_ensemble_probs = {frame: prob / total_corrected_prob for frame, prob in corrected_ensemble_probs.items()}
                    
                    # Use corrected probabilities
                    for frame_name, probability in corrected_ensemble_probs.items():
                        prediction_data['frame_probabilities'][frame_name] = probability * 100  # Convert to percentage
                        total_prob += probability
                        
                        # Calculate midpoint for expected value
                        try:
                            if "less than" in frame_name.lower():
                                parts = frame_name.lower().split("less than")
                                upper = float(parts[1].strip().split()[0])
                                midpoint = upper / 2
                            elif "or more" in frame_name.lower():
                                parts = frame_name.lower().split("or more")
                                lower = float(parts[0].strip().split()[-1])
                                midpoint = lower * 1.2
                            else:
                                # Standard range like "150–174"
                                range_clean = frame_name.replace('–', '-').strip()
                                if '-' in range_clean:
                                    parts = range_clean.split('-')
                                    if len(parts) == 2:
                                        lower = float(parts[0].strip())
                                        upper = float(parts[1].strip())
                                        midpoint = (lower + upper) / 2
                                    else:
                                        midpoint = 150  # Default
                                else:
                                    midpoint = 150  # Default
                            
                            expected_value += probability * midpoint
                        except (ValueError, IndexError):
                            # Default midpoint if parsing fails
                            midpoint = 150
                            expected_value += probability * midpoint
                else:
                    # Fallback to original method if individual_probs calculation fails
                    for frame_name, frame_data in predictions['predictions_by_frame'].items():
                        probability = frame_data['probability']
                        min_tweets = frame_data.get('min', 0)
                        max_tweets = frame_data.get('max', float('inf'))
                        
                        # Calculate midpoint for expected value
                        if max_tweets == float('inf'):
                            midpoint = min_tweets * 1.2  # Estimate for "X or more" cases
                        else:
                            midpoint = (min_tweets + max_tweets) / 2
                        
                        prediction_data['frame_probabilities'][frame_name] = probability * 100  # Convert to percentage
                        total_prob += probability
                        expected_value += probability * midpoint
            else:
                # Standard handling for non-ensemble algorithms
                for frame_name, frame_data in predictions['predictions_by_frame'].items():
                    probability = frame_data['probability']
                    min_tweets = frame_data.get('min', 0)
                    max_tweets = frame_data.get('max', float('inf'))
                    
                    # Calculate midpoint for expected value
                    if max_tweets == float('inf'):
                        midpoint = min_tweets * 1.2  # Estimate for "X or more" cases
                    else:
                        midpoint = (min_tweets + max_tweets) / 2
                    
                    prediction_data['frame_probabilities'][frame_name] = probability * 100  # Convert to percentage
                    total_prob += probability
                    expected_value += probability * midpoint
        
        elif 'ensemble_results' in predictions and 'probabilities' in predictions['ensemble_results']:
            # Format used by enhanced algorithms (enhanced_timesfm, enhanced_neural_prophet, enhanced_facebook_prophet)
            probabilities_dict = predictions['ensemble_results']['probabilities']
            for frame_name, probability in probabilities_dict.items():
                # Try to get midpoint from frame name
                try:
                    if "less than" in frame_name.lower():
                        parts = frame_name.lower().split("less than")
                        upper = float(parts[1].strip().split()[0])
                        midpoint = upper / 2
                    elif "or more" in frame_name.lower():
                        parts = frame_name.lower().split("or more")
                        lower = float(parts[0].strip().split()[-1])
                        midpoint = lower * 1.2
                    else:
                        # Standard range like "150–174"
                        range_clean = frame_name.replace('–', '-').strip()
                        if '-' in range_clean:
                            parts = range_clean.split('-')
                            if len(parts) == 2:
                                lower = float(parts[0].strip())
                                upper = float(parts[1].strip())
                                midpoint = (lower + upper) / 2
                            else:
                                midpoint = 150  # Default
                        else:
                            midpoint = 150  # Default
                    
                    prediction_data['frame_probabilities'][frame_name] = probability * 100  # Convert to percentage
                    total_prob += probability
                    expected_value += probability * midpoint
                except (ValueError, IndexError):
                    # Default midpoint if parsing fails
                    midpoint = 150
                    prediction_data['frame_probabilities'][frame_name] = probability * 100
                    total_prob += probability
                    expected_value += probability * midpoint
                    
        elif 'frame_probabilities' in predictions:
            # Format used by legacy prophet (already in percentage)
            for frame_name, probability in predictions['frame_probabilities'].items():
                prediction_data['frame_probabilities'][frame_name] = probability
                
                # Try to get midpoint from frame name
                try:
                    if "less than" in frame_name.lower():
                        parts = frame_name.lower().split("less than")
                        upper = float(parts[1].strip().split()[0])
                        midpoint = upper / 2
                    elif "or more" in frame_name.lower():
                        parts = frame_name.lower().split("or more")
                        lower = float(parts[0].strip().split()[-1])
                        midpoint = lower * 1.2
                    else:
                        # Standard range like "150–174"
                        range_clean = frame_name.replace('–', '-').strip()
                        if '-' in range_clean:
                            parts = range_clean.split('-')
                            if len(parts) == 2:
                                lower = float(parts[0].strip())
                                upper = float(parts[1].strip())
                                midpoint = (lower + upper) / 2
                            else:
                                midpoint = 150  # Default
                        else:
                            midpoint = 150  # Default
                    
                    total_prob += probability / 100  # Convert percentage to probability
                    expected_value += (probability / 100) * midpoint
                except (ValueError, IndexError):
                    # Default midpoint if parsing fails
                    midpoint = 150
                    total_prob += probability / 100
                    expected_value += (probability / 100) * midpoint
        
        # Use total_predicted if available in the summary
        if 'total_predicted' in predictions:
            prediction_data['summary']['expected_value'] = predictions['total_predicted']
        elif 'ensemble_results' in predictions and 'total_predicted' in predictions['ensemble_results']:
            # Enhanced algorithms store total_predicted in ensemble_results
            prediction_data['summary']['expected_value'] = predictions['ensemble_results']['total_predicted']
        else:
            prediction_data['summary']['expected_value'] = expected_value
        
        logger.info(f"Generated predictions using {algorithm} algorithm")
        logger.info(f"Total probability: {total_prob:.4f}, Expected value: {prediction_data['summary']['expected_value']:.2f}")
        
        return prediction_data
        
    except ImportError as e:
        logger.error(f"Failed to import {algorithm} predictor: {e}")
        logger.error("Falling back to legacy prophet predictor")
        return get_prediction_data_legacy(prophet=True)
    except Exception as e:
        logger.error(f"Error generating predictions with {algorithm}: {e}")
        logger.error("Falling back to legacy prophet predictor")
        return get_prediction_data_legacy(prophet=True)

def get_prediction_data_legacy(prophet: bool = True) -> Dict[str, Any]:
    """
    Get prediction data from the legacy polymarket_predictor module.
    
    Args:
        prophet: Whether to use the Prophet algorithm
        
    Returns:
        Dict containing prediction data
    """
    try:
        # Build the command to run
        cmd = ["python", "-m", "src.polymarket_predictor", "--json"]
        if prophet:
            cmd.append("--prophet")
        
        # Try with --brief flag first
        try:
            # Add brief flag and run the command
            brief_cmd = cmd + ["--brief"]
            result = subprocess.run(brief_cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            # If --brief fails, try without it
            logger.warning("Brief flag not recognized, trying without --brief")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Find the JSON data in the output (it might have other text before/after)
        json_start = result.stdout.find('{')
        json_end = result.stdout.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = result.stdout[json_start:json_end]
            # Parse the JSON output
            prediction_data = json.loads(json_str)
            return prediction_data
        else:
            logger.error("Could not find valid JSON in output")
            return {}
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running prediction command: {e}")
        logger.error(f"Command output: {e.stderr}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing prediction JSON: {e}")
        logger.error(f"Output: {result.stdout}")
        return {}

# Alias for backward compatibility
def get_prediction_data(prophet: bool = True) -> Dict[str, Any]:
    """
    Get prediction data from the polymarket_predictor module.
    
    Args:
        prophet: Whether to use the Prophet algorithm
        
    Returns:
        Dict containing prediction data
    """
    return get_prediction_data_legacy(prophet=prophet)

def get_market_data(refresh: bool = True) -> Dict[str, Any]:
    """
    Get order book data from the Polymarket order book module.
    
    Args:
        refresh: Whether to fetch fresh data
        
    Returns:
        Dict containing market data
    """
    try:
        # Build the command to run
        cmd = ["python", "-m", "src.polymarket.order_book.show_market_status", "--json"]
        if refresh:
            cmd.append("--refresh")
        
        # Run the command and capture the output
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the JSON output
        market_data = json.loads(result.stdout)
        return market_data
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running market command: {e}")
        logger.error(f"Command output: {e.stderr}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing market JSON: {e}")
        return {}

def normalize_range_name(range_name: str) -> str:
    """
    Normalize range names to ensure consistency between prediction and market data sources.
    
    Args:
        range_name: The range name to normalize
        
    Returns:
        str: Normalized range name
    """
    # Convert to lowercase for case-insensitive comparison
    name = range_name.lower().strip()
    
    # Remove any date suffixes first (e.g., "June 6–13?", "April 25–May 2")
    # Look for patterns like "june 6–13?" or "april 25–may 2"
    # Remove date patterns at the end
    name = re.sub(r'\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d+[–-]\d+\??.*$', '', name)
    name = re.sub(r'\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d+[–-]\d+\??.*$', '', name)
    # Also handle cases like "June 6–13?" 
    name = re.sub(r'\s+\w+\s+\d+[–-]\d+\??.*$', '', name)
    name = name.strip()
    
    # Handle "less than X" format - extract the actual number
    if "less than" in name:
        # Try to extract the number after "less than"
        try:
            match = re.search(r'less than (\d+)', name)
            if match:
                num = int(match.group(1))
                return f"less than {num}"
            else:
                # Fallback to the current frames from constants
                from src.constants import TWEET_COUNT_FRAMES
                for frame in TWEET_COUNT_FRAMES:
                    if frame["name"].lower().startswith("less than"):
                        return frame["name"]
                return "less than 150"  # Default fallback
        except (ValueError, ImportError):
            return "less than 150"  # Default fallback
    
    # Handle "X or more" format
    if "or more" in name:
        # Extract the number before "or more"
        try:
            match = re.search(r'(\d+)\s*or more', name)
            if match:
                num = int(match.group(1))
                return f"{num} or more"
            else:
                # Fallback to extracting any number
                num = int(''.join(filter(str.isdigit, name.split("or more")[0])))
                return f"{num} or more"
        except (ValueError, ImportError):
            # If we can't extract a number, return the original format
            return "500 or more"  # Default case for new frames
    
    # Strip any "Will Elon tweet" prefix 
    if "will elon tweet" in name:
        name = name.replace("will elon tweet", "").strip()
    
    # Remove " times" suffix if present
    name = name.replace(" times", "").strip()
    
    # Extract just the numeric range part
    if "–" in name or "-" in name:
        # Split by any dash character
        separator = "–" if "–" in name else "-"
        parts = name.split(separator)
        
        if len(parts) == 2:
            start, end = parts
            # Try to convert to numbers to ensure it's a valid range
            try:
                start_num = int(start.strip())
                end_num = int(end.strip())
                # Return in standard format with en dash
                return f"{start_num}–{end_num}"
            except ValueError:
                pass
    
    # If all else fails, return the original name, but clean it up
    return name.strip()

def generate_comparison_table(
    prediction_data: Optional[Dict[str, Any]] = None, 
    market_data: Optional[Dict[str, Any]] = None,
    refresh: bool = True,
    use_prophet: bool = True,
    algorithm: str = "prophet",
    output_path: Optional[str] = None,
    threshold: float = 0.0,
    silent: bool = False,
    **prediction_kwargs
) -> pd.DataFrame:
    """
    Generate a comparison table between prediction and market data.
    
    Args:
        prediction_data: Prediction data (fetched if None)
        market_data: Market data (fetched if None)
        refresh: Whether to refresh market data
        use_prophet: Whether to use Prophet for predictions (legacy compatibility)
        algorithm: Algorithm to use ("prophet", "facebook_prophet", "neural_prophet", "timesfm", "ensemble")
        output_path: Path to save the comparison table CSV
        threshold: Minimum opportunity percentage to include in results
        silent: Whether to suppress printing of the table to console
        **prediction_kwargs: Additional arguments for the prediction algorithm
        
    Returns:
        DataFrame with comparison data
    """
    # Fetch data if not provided
    if prediction_data is None:
        if algorithm == "prophet" and use_prophet:
            # Legacy compatibility
            prediction_data = get_prediction_data(prophet=use_prophet)
        else:
            # Use new algorithm-based approach
            prediction_data = get_prediction_data_from_module(algorithm=algorithm, **prediction_kwargs)
    
    if market_data is None:
        market_data = get_market_data(refresh=refresh)
    
    # Check if we have valid data
    if not prediction_data or not market_data:
        logger.error("Failed to get valid data for comparison")
        return pd.DataFrame()
    
    # Log which algorithm was used
    used_algorithm = prediction_data.get('algorithm', 'unknown')
    logger.info(f"Using prediction algorithm: {used_algorithm}")
    
    # Get frame probabilities from prediction
    pred_probs = prediction_data.get('frame_probabilities', {})
    
    # Get market probabilities, asks, and bids from order book
    market_probs = {}
    market_asks = {}
    market_bids = {}
    market_token_ids = {}  # Store token IDs
    market_market_ids = {}  # Store market IDs
    market_ranges = []  # Keep the original order
    
    for range_name, details in market_data.get('markets', {}).items():
        # Normalize the range name to match between data sources
        norm_name = normalize_range_name(range_name)
        market_probs[norm_name] = details.get('probability', 0)
        market_asks[norm_name] = details.get('ask', 0)
        market_bids[norm_name] = details.get('bid', 0)
        market_token_ids[norm_name] = details.get('token_id', 'N/A')  # Get token ID
        market_market_ids[norm_name] = details.get('market_id', 'N/A')  # Get market ID
        if norm_name not in market_ranges:
            market_ranges.append(norm_name)
    
    # Determine which ranges need to be combined based on what's in the market data
    combined_ranges = {}
    for market_range in market_ranges:
        if market_range == "350 or more":
            # Check if we need to combine "350-374", "375-399" and others above 350
            combined_ranges[market_range] = [
                r for r in pred_probs.keys() 
                if (r.startswith("350") or r.startswith("375") or 
                    r.startswith("400") or "or more" in r)
            ]
    
    # Normalize prediction range names as well and combine values for ranges
    # that map to the same Polymarket range
    normalized_pred_probs = {}
    processed_ranges = set()
    
    # First handle the special combined ranges
    for target_range, source_ranges in combined_ranges.items():
        combined_prob = 0
        for range_name in source_ranges:
            if range_name in pred_probs:
                combined_prob += pred_probs[range_name]
                processed_ranges.add(range_name)
        normalized_pred_probs[target_range] = combined_prob
    
    # Then process the remaining ranges
    for range_name, prob in pred_probs.items():
        if range_name in processed_ranges:
            continue  # Skip already processed ranges
            
        norm_name = normalize_range_name(range_name)
        
        # Only include ranges that map to actual market ranges
        if norm_name in market_ranges:
            # Sum probabilities for ranges that map to the same normalized name
            if norm_name in normalized_pred_probs:
                normalized_pred_probs[norm_name] += prob
            else:
                normalized_pred_probs[norm_name] = prob
    
    # Create comparison table
    comparison_data = []
    
    # Only use ranges that exist in the Polymarket data
    for range_name in market_ranges:
        pred_prob = normalized_pred_probs.get(range_name, 0)
        market_prob = market_probs.get(range_name, 0)
        market_ask = market_asks.get(range_name, 0)
        market_bid = market_bids.get(range_name, 0)
        token_id = market_token_ids.get(range_name, 'N/A')
        market_id = market_market_ids.get(range_name, 'N/A')
        
        # Calculate spread (gap between ask and bid)
        spread = market_ask - market_bid if market_ask > 0 and market_bid > 0 else 0
        
        # Calculate differences using ask price instead of market price
        diff = pred_prob - market_ask
        opportunity = abs(diff)
        
        # Calculate spread-adjusted opportunity
        spread_adj_opportunity = max(0, opportunity - spread)
        
        # Calculate sell-only opportunity (only when prediction < bid)
        sell_only_opportunity = max(0, opportunity - spread - threshold) if diff < 0 else 0
        
        # Calculate adjusted opportunities
        fully_adj_opportunity_with_threshold = max(0, opportunity - spread - threshold) if opportunity >= threshold or range_name == 'EXPECTED VALUE' else 0
        buy_only_opportunity_with_threshold = max(0, fully_adj_opportunity_with_threshold) if diff > 0 else 0
        sell_only_opportunity_with_threshold = max(0, fully_adj_opportunity_with_threshold) if diff < 0 else 0
        
        comparison_data.append({
            'Range': range_name,
            'Pred (%)': pred_prob,
            'Mkt (%)': market_prob,
            'Bid (%)': market_bid,
            'Ask (%)': market_ask,
            'Spread (%)': spread,
            'Diff (%)': diff,
            'Opp (%)': opportunity,
            'Adj-Sp (%)': spread_adj_opportunity,
            f'Adj-Full ({threshold}%)': fully_adj_opportunity_with_threshold,
            f'Buy-Only ({threshold}%)': buy_only_opportunity_with_threshold,
            f'Sell-Only ({threshold}%)': sell_only_opportunity_with_threshold,
            'Token ID': token_id,
            'Market ID': market_id
        })
    
    # Create DataFrame
    df = pd.DataFrame(comparison_data)
    
    # Calculate expected values
    pred_ev = prediction_data.get('summary', {}).get('expected_value', 0)
    market_ev = market_data.get('summary', {}).get('expected_value', 0)
    ev_diff = pred_ev - market_ev
    
    # Create the summary row with same dtype as existing columns
    # Create a copy of the data with one row to match dtypes
    if len(df) > 0:
        summary_data = {
            'Range': 'EXPECTED VALUE',
            'Pred (%)': pred_ev,
            'Mkt (%)': market_ev,
            'Bid (%)': np.nan,  # Use np.nan instead of None
            'Ask (%)': np.nan,
            'Spread (%)': np.nan,
            'Diff (%)': ev_diff,
            'Opp (%)': abs(ev_diff),
            'Adj-Sp (%)': abs(ev_diff),  # No spread for expected value
            f'Adj-Full ({threshold}%)': max(0, abs(ev_diff) - threshold),
            f'Buy-Only ({threshold}%)': max(0, ev_diff - threshold) if ev_diff > 0 else 0,
            f'Sell-Only ({threshold}%)': max(0, abs(ev_diff) - threshold) if ev_diff < 0 else 0,
            'Token ID': None,  # No token ID for expected value
            'Market ID': None   # No market ID for expected value
        }
        
        # Ensure all columns in summary_data exist in the DataFrame
        for col in df.columns:
            if col not in summary_data:
                summary_data[col] = np.nan
                
        # Convert None values to np.nan for numeric columns
        for col in ['Bid (%)', 'Ask (%)', 'Spread (%)']:
            if col in summary_data:
                summary_data[col] = np.nan
        
        # Append to DataFrame using loc to maintain dtypes
        df.loc[len(df)] = summary_data
    else:
        # If the DataFrame is empty, create it from scratch with the summary row
        df = pd.DataFrame([{
            'Range': 'EXPECTED VALUE',
            'Pred (%)': pred_ev,
            'Mkt (%)': market_ev,
            'Bid (%)': np.nan,
            'Ask (%)': np.nan,
            'Spread (%)': np.nan,
            'Diff (%)': ev_diff,
            'Opp (%)': abs(ev_diff),
            'Adj-Sp (%)': abs(ev_diff),
            f'Adj-Full ({threshold}%)': max(0, abs(ev_diff) - threshold),
            f'Buy-Only ({threshold}%)': max(0, ev_diff - threshold) if ev_diff > 0 else 0,
            f'Sell-Only ({threshold}%)': max(0, abs(ev_diff) - threshold) if ev_diff < 0 else 0,
            'Token ID': None,
            'Market ID': None
        }])
    
    # Save to file if requested
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Comparison table saved to {output_path}")
    
    return df

def visualize_comparison(
    comparison_df: Optional[pd.DataFrame] = None,
    prediction_data: Optional[Dict[str, Any]] = None, 
    market_data: Optional[Dict[str, Any]] = None,
    refresh: bool = True,
    use_prophet: bool = True,
    threshold: float = 0.0,
    output_path: Optional[str] = None
) -> None:
    """
    Visualize the comparison between prediction and market data.
    
    Args:
        comparison_df: Comparison DataFrame (generated if None)
        prediction_data: Prediction data (fetched if comparison_df is None)
        market_data: Market data (fetched if comparison_df is None)
        refresh: Whether to refresh market data
        use_prophet: Whether to use Prophet for predictions
        threshold: Minimum opportunity percentage to include in results
        output_path: Path to save visualization
    """
    # Generate comparison table if not provided
    if comparison_df is None:
        comparison_df = generate_comparison_table(
            prediction_data, market_data, 
            refresh=refresh, 
            use_prophet=use_prophet,
            threshold=threshold
        )
    
    if comparison_df.empty:
        logger.error("No data to visualize")
        return
    
    # Filter out the expected value row for plotting
    plot_df = comparison_df[comparison_df['Range'] != 'EXPECTED VALUE'].copy()
    
    if plot_df.empty:
        logger.error("No data points to visualize after filtering")
        return
    
    # Create figure with subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 18))
    
    # Plot the comparison
    ranges = plot_df['Range']
    x = np.arange(len(ranges))
    width = 0.2  # Narrower bars to fit all series
    
    # First subplot: Prediction vs Market vs Bid vs Ask
    bars1 = ax1.bar(x - 1.5*width, plot_df['Pred (%)'], width, label='Prediction')
    bars2 = ax1.bar(x - 0.5*width, plot_df['Mkt (%)'], width, label='Market')
    bars3 = ax1.bar(x + 0.5*width, plot_df['Bid (%)'], width, label='Bid Price')
    bars4 = ax1.bar(x + 1.5*width, plot_df['Ask (%)'], width, label='Ask Price')
    
    ax1.set_xlabel('Range')
    ax1.set_ylabel('Probability (%)')
    ax1.set_title('Prediction vs Market, Bid, Ask Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(ranges, rotation=45, ha='right')
    ax1.legend()
    
    # Second subplot: Spread visualization
    bars_spread = ax2.bar(x, plot_df['Spread (%)'], width, label='Bid-Ask Spread')
    
    # Color the spread bars based on size
    for i, bar in enumerate(bars_spread):
        intensity = min(1.0, plot_df['Spread (%)'].iloc[i] / plot_df['Spread (%)'].max() if plot_df['Spread (%)'].max() > 0 else 0)
        bar.set_color(plt.cm.Oranges(0.5 + intensity/2))
    
    ax2.set_xlabel('Range')
    ax2.set_ylabel('Spread (%)')
    ax2.set_title('Bid-Ask Spread by Range')
    ax2.set_xticks(x)
    ax2.set_xticklabels(ranges, rotation=45, ha='right')
    ax2.legend()
    
    # Third subplot: Opportunities and Adjusted Opportunities
    full_adj_opp_col = f'Adj-Full ({threshold}%)'
    
    # Create grouped bar chart for opportunities
    bars_opp = ax3.bar(x - width, plot_df['Opp (%)'], width, label='Raw Opportunity')
    bars_spread_adj = ax3.bar(x, plot_df['Adj-Sp (%)'], width, label='After Spread')
    bars_full_adj = ax3.bar(x + width, plot_df[full_adj_opp_col], width, label=f'After Spread + {threshold}%')
    
    # Color the bars based on opportunity size
    for i in range(len(plot_df)):
        # Raw opportunity bars in blue
        intensity_opp = min(1.0, plot_df['Opp (%)'].iloc[i] / plot_df['Opp (%)'].max() if plot_df['Opp (%)'].max() > 0 else 0)
        bars_opp[i].set_color(plt.cm.Blues(0.5 + intensity_opp/2))
        
        # Spread-adjusted opportunity bars in green
        intensity_spread_adj = min(1.0, plot_df['Adj-Sp (%)'].iloc[i] / plot_df['Adj-Sp (%)'].max() if plot_df['Adj-Sp (%)'].max() > 0 else 0)
        bars_spread_adj[i].set_color(plt.cm.Greens(0.5 + intensity_spread_adj/2))
        
        # Fully-adjusted opportunity bars in red
        intensity_full_adj = min(1.0, plot_df[full_adj_opp_col].iloc[i] / plot_df[full_adj_opp_col].max() if plot_df[full_adj_opp_col].max() > 0 else 0)
        bars_full_adj[i].set_color(plt.cm.Reds(0.5 + intensity_full_adj/2))
    
    ax3.set_xlabel('Range')
    ax3.set_ylabel('Opportunity (%)')
    ax3.set_title(f'Trading Opportunities (Raw, Spread-Adjusted, and Fully-Adjusted)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(ranges, rotation=45, ha='right')
    ax3.legend()
    
    # Add a 'buy' or 'sell' annotation to the top 3 fully adjusted opportunities
    adj_opps = plot_df[full_adj_opp_col]
    if adj_opps.max() > 0:  # Only if there are opportunities above threshold
        top_opps = adj_opps.nlargest(3)
        for opp in top_opps:
            if opp > 0:  # Only annotate non-zero opportunities
                idx = adj_opps[adj_opps == opp].index[0]
                row = plot_df.iloc[idx]
                diff = row['Diff (%)']
                
                position = (idx, opp + 0.5)
                action = "BUY" if diff > 0 else "SELL"
                price = row['Ask (%)'] if diff > 0 else row['Bid (%)']
                spread = row['Spread (%)']
                
                ax3.annotate(
                    f"{action} at {price:.2f}% (Spread: {spread:.2f}%, Edge: {opp:.2f}%)",
                    position, 
                    xytext=(0, 5),
                    textcoords='offset points',
                    ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5)
                )
    
    # Add expected values as text
    ev_row = comparison_df[comparison_df['Range'] == 'EXPECTED VALUE'].iloc[0]
    fig.text(
        0.5, 0.02,
        f"Expected Values: Prediction = {ev_row['Pred (%)']:.2f}, " + 
        f"Market = {ev_row['Mkt (%)']:.2f}, " + 
        f"Difference = {ev_row['Diff (%)']:.2f}",
        ha='center', fontsize=12, bbox=dict(facecolor='yellow', alpha=0.2)
    )
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path)
        logger.info(f"Visualization saved to {output_path}")
    else:
        plt.show()

def enhanced_visualization(
    comparison_df: pd.DataFrame,
    threshold: float = 0.0,
    output_path: Optional[str] = None
) -> None:
    """
    Create an enhanced visualization with multiple informative charts.
    
    Args:
        comparison_df: Comparison DataFrame
        threshold: Minimum opportunity percentage to highlight
        output_path: Path to save visualization
    """
    if comparison_df.empty:
        logger.error("No data to visualize")
        return
    
    # Filter out the expected value row for plotting
    plot_df = comparison_df[comparison_df['Range'] != 'EXPECTED VALUE'].copy()
    
    if plot_df.empty:
        logger.error("No data points to visualize after filtering")
        return
    
    # Create a larger figure with multiple subplots
    fig = plt.figure(figsize=(20, 15))
    fig.suptitle(f'Market vs Prediction Analysis (Threshold: {threshold}%)', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    # Define grid layout
    gs = plt.GridSpec(3, 2, figure=fig, height_ratios=[1, 1, 1.2], wspace=0.25, hspace=0.35)
    
    # 1. Probability Comparison - Upper Left
    ax1 = fig.add_subplot(gs[0, 0])
    _plot_probability_comparison(ax1, plot_df)
    
    # 2. Bid-Ask Spread - Upper Right
    ax2 = fig.add_subplot(gs[0, 1])
    _plot_bid_ask_spread(ax2, plot_df)
    
    # 3. Trading Opportunities - Middle Left
    ax3 = fig.add_subplot(gs[1, 0])
    full_adj_opp_col = f'Adj-Full ({threshold}%)'
    _plot_trading_opportunities(ax3, plot_df, full_adj_opp_col, threshold)
    
    # 4. Expected Value - Middle Right
    ax4 = fig.add_subplot(gs[1, 1])
    ev_row = comparison_df[comparison_df['Range'] == 'EXPECTED VALUE'].iloc[0]
    _plot_expected_value(ax4, ev_row, threshold)
    
    # 5. Detailed Recommendations - Bottom Full Width
    ax5 = fig.add_subplot(gs[2, :])
    _plot_detailed_recommendations(ax5, plot_df, full_adj_opp_col, threshold)
    
    # Add timestamp and information
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plt.figtext(0.01, 0.01, f"Generated: {timestamp}", fontsize=8)
    plt.figtext(0.99, 0.01, "Source: Polymarket Order Book & Prophet Predictions", 
                fontsize=8, ha='right')
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"Enhanced visualization saved to {output_path}")
    else:
        plt.show()

def _plot_probability_comparison(ax, df):
    """Plot probability comparison chart"""
    ranges = df['Range']
    x = np.arange(len(ranges))
    width = 0.25
    
    bars1 = ax.bar(x - width, df['Pred (%)'], width, label='Prediction', color='#4285F4')
    bars2 = ax.bar(x, df['Mkt (%)'], width, label='Market', color='#34A853')
    
    # Add value labels on the bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 1:  # Only show labels for bars with height > 1%
                ax.text(
                    bar.get_x() + bar.get_width()/2.,
                    height + 1,
                    f'{height:.1f}%',
                    ha='center', va='bottom',
                    fontsize=8, rotation=0
                )
    
    ax.set_xlabel('Range')
    ax.set_ylabel('Probability (%)')
    ax.set_title('Prediction vs Market Probabilities')
    ax.set_xticks(x - width/2)
    ax.set_xticklabels(ranges, rotation=45, ha='right')
    ax.legend(loc='upper right')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Highlight top predicted range
    max_pred_idx = df['Pred (%)'].argmax()
    ax.get_xticklabels()[max_pred_idx].set_color('red')
    ax.get_xticklabels()[max_pred_idx].set_fontweight('bold')

def _plot_bid_ask_spread(ax, df):
    """Plot bid-ask spread chart"""
    ranges = df['Range']
    x = np.arange(len(ranges))
    width = 0.25
    
    bars1 = ax.bar(x - width, df['Bid (%)'], width, label='Bid', color='#FBBC05')
    bars2 = ax.bar(x, df['Ask (%)'], width, label='Ask', color='#EA4335')
    
    # Calculate and plot spread as a line
    spreads = df['Ask (%)'] - df['Bid (%)']
    ax2 = ax.twinx()
    ax2.plot(x, spreads, 'k--', label='Spread', linewidth=1.5, alpha=0.6)
    ax2.set_ylabel('Spread (%)')
    
    ax.set_xlabel('Range')
    ax.set_ylabel('Price (%)')
    ax.set_title('Bid-Ask Prices and Spreads')
    ax.set_xticks(x - width/2)
    ax.set_xticklabels(ranges, rotation=45, ha='right')
    
    # Combine legends
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc='upper right')
    
    ax.grid(axis='y', linestyle='--', alpha=0.3)

def _plot_trading_opportunities(ax, df, full_adj_opp_col, threshold):
    """Plot trading opportunities chart"""
    # Sort by adjusted opportunity
    sorted_df = df.sort_values(by=full_adj_opp_col, ascending=False).copy()
    
    # Get the buy-only opportunity column name
    buy_only_col = f'Buy-Only ({threshold}%)'
    
    # Get the sell-only opportunity column name
    sell_only_col = f'Sell-Only ({threshold}%)'
    
    # Only show rows with meaningful opportunities
    display_df = sorted_df[sorted_df[full_adj_opp_col] > 0]
    if display_df.empty:
        display_df = sorted_df.head(3)  # Show at least top 3 if none above threshold
    
    ranges = display_df['Range']
    x = np.arange(len(ranges))
    width = 0.2  # Make bars narrower to fit four columns
    
    # Create grouped bar chart for opportunities
    bars_raw = ax.bar(x - 1.5*width, display_df['Opp (%)'], width, 
                      label='Raw Opp', color='#4285F4', alpha=0.7)
    bars_full_adj = ax.bar(x - 0.5*width, display_df[full_adj_opp_col], width, 
                      label=f'Adj ({threshold}%)', color='#34A853')
    bars_buy_only = ax.bar(x + 0.5*width, display_df[buy_only_col], width, 
                      label=f'Buy-Only', color='#FBBC05')
    bars_sell_only = ax.bar(x + 1.5*width, display_df[sell_only_col], width, 
                      label=f'Sell-Only', color='#EA4335')
    
    # Add value labels
    for bars in [bars_raw, bars_full_adj, bars_buy_only, bars_sell_only]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width()/2.,
                    height + 0.5,
                    f'{height:.1f}%',
                    ha='center', va='bottom',
                    fontsize=9
                )
    
    # Add buy/sell annotations
    for i, (_, row) in enumerate(display_df.iterrows()):
        if row[full_adj_opp_col] > 0:
            action = "BUY" if row['Diff (%)'] > 0 else "SELL"
            ax.annotate(
                f"{action}",
                (i, 0),
                xytext=(0, -20),
                textcoords='offset points',
                ha='center', va='center',
                fontsize=12, fontweight='bold',
                color='white', bbox=dict(boxstyle="round,pad=0.3", 
                                         fc='#EA4335' if action == 'SELL' else '#34A853', 
                                         ec="none")
            )
    
    ax.set_xlabel('Range')
    ax.set_ylabel('Opportunity (%)')
    ax.set_title('Top Trading Opportunities')
    ax.set_xticks(x)
    ax.set_xticklabels(ranges, rotation=0)
    ax.legend(loc='upper right')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Set y-axis to start at 0
    ax.set_ylim(bottom=0)

def _plot_expected_value(ax, ev_row, threshold):
    """Plot expected value comparison"""
    labels = ['Prediction', 'Market']
    values = [ev_row['Pred (%)'], ev_row['Mkt (%)']]
    diff = ev_row['Diff (%)']
    abs_diff = abs(diff)
    adj_diff = max(0, abs_diff - threshold)
    
    # Create the bar chart
    bars = ax.bar(labels, values, color=['#4285F4', '#34A853'])
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2.,
            height + 1,
            f'{height:.2f}',
            ha='center', va='bottom',
            fontsize=10
        )
    
    # Add difference annotation
    direction = '↑' if diff > 0 else '↓'
    color = '#34A853' if diff > 0 else '#EA4335'
    
    ax.annotate(
        f"Diff: {diff:.2f} {direction}",
        xy=(0.5, max(values) * 0.6),
        xytext=(0.5, max(values) * 0.6),
        textcoords='axes fraction',
        ha='center',
        fontsize=12,
        fontweight='bold',
        color=color
    )
    
    # Add adjusted opportunity if significant
    if adj_diff > 0:
        ax.annotate(
            f"Adj Opp: {adj_diff:.2f}%",
            xy=(0.5, max(values) * 0.5),
            xytext=(0.5, max(values) * 0.5),
            textcoords='axes fraction',
            ha='center',
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc='#FBBC05', ec="none", alpha=0.3)
        )
    
    ax.set_title('Expected Value Comparison')
    ax.set_ylabel('Expected Tweet Count')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Add a recommendation if there's a significant difference
    if abs_diff > threshold:
        action = "HIGHER" if diff > 0 else "LOWER"
        ax.text(
            0.5, 0.05,
            f"Prediction is {action} than market",
            transform=ax.transAxes,
            ha='center',
            fontsize=11,
            bbox=dict(boxstyle="round,pad=0.3", fc='#FBBC05', ec="none", alpha=0.3)
        )

def _plot_detailed_recommendations(ax, df, full_adj_opp_col, threshold):
    """Plot detailed recommendations chart"""
    # Find top opportunities
    df_filtered = df[df[full_adj_opp_col] > 0].copy()
    
    # Get the buy-only opportunity column name
    buy_only_col = f'Buy-Only ({threshold}%)'
    
    # Get the sell-only opportunity column name
    sell_only_col = f'Sell-Only ({threshold}%)'
    
    if df_filtered.empty:
        ax.text(
            0.5, 0.5,
            "No significant trading opportunities found above threshold",
            ha='center', va='center',
            fontsize=14, fontweight='bold',
            transform=ax.transAxes
        )
        ax.set_title("Trading Recommendations")
        ax.axis('off')
        return
    
    # Sort by adjusted opportunity
    df_sorted = df_filtered.sort_values(by=full_adj_opp_col, ascending=False)
    
    # Take top 5 or all if less
    top_opps = df_sorted.head(5)
    
    # Create table data
    table_data = []
    for _, row in top_opps.iterrows():
        action = "BUY" if row['Diff (%)'] > 0 else "SELL"
        price = row['Ask (%)'] if action == "BUY" else row['Bid (%)']
        spread = row['Spread (%)']
        edge = row[full_adj_opp_col]
        pred = row['Pred (%)']
        market = row['Mkt (%)']
        spread_adj = row['Adj-Sp (%)']
        buy_only = row[buy_only_col]
        sell_only = row[sell_only_col]
        token_id = row.get('Token ID', 'N/A')
        
        # Truncate token ID if it's too long
        if token_id and isinstance(token_id, str) and len(token_id) > 10:
            token_id = token_id[:7] + "..."
        
        table_data.append([
            row['Range'],
            action,
            f"{price:.2f}%",
            f"{spread:.2f}%",
            f"{pred:.2f}%",
            f"{market:.2f}%",
            f"{row['Diff (%)']}%",
            f"{edge:.2f}%",
            f"{buy_only:.2f}%",
            f"{sell_only:.2f}%",
            token_id
        ])
    
    # Create the table
    columns = ['Range', 'Action', 'Price', 'Spread', 'Pred', 'Mkt', 'Diff', f'Adj ({threshold}%)', 'Buy-Only', 'Sell-Only', 'Token ID']
    colors = []
    
    for row in table_data:
        if row[1] == "BUY":
            colors.append(['w', 'w', '#C8E6C9', '#FFF9C4', 'w', 'w', 'w', 'w', '#E8F5E9', '#F5F5F5', '#E8F5E9'])  # Green for BUY
        else:
            colors.append(['w', 'w', '#FFCDD2', '#FFF9C4', 'w', 'w', 'w', 'w', '#F5F5F5', '#FFEBEE', '#FFEBEE'])  # Red for SELL
    
    table = ax.table(
        cellText=table_data,
        colLabels=columns,
        loc='center',
        cellLoc='center',
        colColours=['#F5F5F5'] * len(columns),
        cellColours=colors
    )
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    
    # Add a title
    ax.set_title("Detailed Trading Recommendations", fontsize=14, fontweight='bold', pad=20)
    
    # Add a summary text
    top_action = table_data[0][1]
    top_range = table_data[0][0]
    top_price = table_data[0][2]
    top_spread = table_data[0][3]
    top_edge = table_data[0][7]
    top_token = table_data[0][10]
    
    summary_text = (
        f"Best Opportunity: {top_action} {top_range} at {top_price}\n"
        f"with {top_edge} edge (after {top_spread} spread and {threshold}% threshold)\n"
        f"Token ID: {top_token}"
    )
    
    ax.text(
        0.5, 0.9,
        summary_text,
        ha='center', va='center',
        fontsize=14, fontweight='bold',
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.5", fc='#FFF9C4', ec="none")
    )
    
    ax.axis('off')

def visualize_simple_table(
    comparison_df: pd.DataFrame,
    output_path: Optional[str] = None,
    threshold: float = 0.0
) -> None:
    """
    Create a simple, readable visualization of the comparison table.
    
    Args:
        comparison_df: Comparison DataFrame
        output_path: Path to save visualization
        threshold: Threshold value used for adjusted opportunities
    """
    if comparison_df.empty:
        logger.error("No data to visualize")
        return
    
    # Create a copy to avoid modifying the original
    df = comparison_df.copy()
    
    # Format the DataFrame for display
    # Remove token ID and market ID for visualization clarity
    display_df = df.drop(['Token ID', 'Market ID'], axis=1, errors='ignore')
    
    # Define the figure size based on the table dimensions
    rows, cols = display_df.shape
    fig_width = max(12, cols * 1.2)  # At least 12 inches wide, or wider for many columns
    fig_height = max(8, rows * 0.5)  # At least 8 inches tall, or taller for many rows
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('off')
    
    # Create the table
    table = ax.table(
        cellText=display_df.round(2).values,
        colLabels=display_df.columns,
        loc='center',
        cellLoc='center'
    )
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    
    # Color the header row
    for j in range(len(display_df.columns)):
        table[(0, j)].set_facecolor('#E0E0E0')
        table[(0, j)].set_text_props(weight='bold')
    
    # Color the cells based on values (for opportunity columns)
    opportunity_cols = ['Opp (%)', 'Adj-Sp (%)', f'Adj-Full ({threshold}%)', 
                         f'Buy-Only ({threshold}%)', f'Sell-Only ({threshold}%)']
    opportunity_col_indices = [list(display_df.columns).index(col) for col in opportunity_cols if col in display_df.columns]
    
    # Define a color normalizer for the opportunity values
    norm = mcolors.Normalize(vmin=0, vmax=display_df[opportunity_cols].values.max())
    cmap_buy = cm.Greens
    cmap_sell = cm.Reds
    
    # Get indices of the 'Diff (%)' column for determining buy/sell coloring
    diff_col_idx = list(display_df.columns).index('Diff (%)')
    
    # Color cells based on values
    for i in range(len(display_df)):
        row_dict = display_df.iloc[i].to_dict()
        
        # Highlight the EXPECTED VALUE row differently
        if display_df.iloc[i]['Range'] == 'EXPECTED VALUE':
            for j in range(len(display_df.columns)):
                table[(i+1, j)].set_facecolor('#FFF9C4')  # Light yellow for expected value row
            continue
        
        # Highlight opportunity columns based on value
        for j in opportunity_col_indices:
            value = display_df.iloc[i].iloc[j]
            if value > 0:
                diff_value = display_df.iloc[i].iloc[diff_col_idx]
                # Use green for buy opportunities (positive diff) and red for sell (negative diff)
                if 'Buy-Only' in display_df.columns[j]:
                    # Buy-only column only has buy opportunities
                    color = cmap_buy(norm(value))
                elif 'Sell-Only' in display_df.columns[j]:
                    # Sell-only column only has sell opportunities
                    color = cmap_sell(norm(value))
                else:
                    # Other opportunity columns use green/red based on diff value
                    color = cmap_buy(norm(value)) if diff_value > 0 else cmap_sell(norm(value))
                
                table[(i+1, j)].set_facecolor(color)
    
    # Add a title and timestamp
    plt.title(f"Market vs Prediction Comparison Table (Threshold: {threshold}%)", 
             fontsize=14, fontweight='bold', pad=20)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plt.figtext(0.01, 0.01, f"Generated: {timestamp}", fontsize=8)
    
    # Adjust layout
    plt.tight_layout()
    
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"Simple table visualization saved to {output_path}")
    else:
        plt.show()

def initialize_directories():
    """Create necessary directories for output files."""
    # Create output directory for CSV files
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create subdirectory for visualizations
    viz_dir = os.path.join(output_dir, 'viz')
    os.makedirs(viz_dir, exist_ok=True)
    
    return output_dir, viz_dir

def main():
    """Command line entry point"""
    import argparse
    
    # Set pandas display options to show all columns
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.float_format', '{:.2f}'.format)
    pd.set_option('display.precision', 2)
    
    # Initialize directories
    output_dir, viz_dir = initialize_directories()
    
    parser = argparse.ArgumentParser(
        description='Compare prediction and market data',
        epilog="""
Examples:
  # Use Facebook Prophet with custom parameters
  python -m src.bidding_decision.stats.comparison --algorithm facebook_prophet --changepoint-prior 0.1 --seasonality-prior 15.0

  # Use Enhanced Facebook Prophet (automatic parameter optimization)
  python -m src.bidding_decision.stats.comparison --algorithm enhanced_facebook_prophet

  # Use Neural Prophet with custom training
  python -m src.bidding_decision.stats.comparison --algorithm neural_prophet --epochs 100 --learning-rate 0.05

  # Use Enhanced Neural Prophet (multiple models with ensemble)
  python -m src.bidding_decision.stats.comparison --algorithm enhanced_neural_prophet

  # Use TimesFM algorithm
  python -m src.bidding_decision.stats.comparison --algorithm timesfm

  # Use Enhanced TimesFM (multiple model variants)
  python -m src.bidding_decision.stats.comparison --algorithm enhanced_timesfm

  # Use Ensemble method (combines all models)
  python -m src.bidding_decision.stats.comparison --algorithm ensemble --fast-mode

  # Generate visualization with enhanced charts
  python -m src.bidding_decision.stats.comparison --algorithm enhanced_neural_prophet --visualize --enhanced-viz

  # Set minimum threshold for opportunities
  python -m src.bidding_decision.stats.comparison --algorithm enhanced_facebook_prophet --threshold 2.0
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--output', type=str, help='Path to save the comparison table CSV')
    parser.add_argument('--no-refresh', action='store_true', help='Do not refresh market data')
    parser.add_argument('--no-prophet', action='store_true', help='Do not use Prophet for predictions')
    parser.add_argument('--visualize', action='store_true', help='Generate visualization')
    parser.add_argument('--viz-output', type=str, help='Path to save visualization')
    parser.add_argument('--threshold', type=float, default=0.0, help='Minimum opportunity percentage (0-100) to include in results')
    parser.add_argument('--enhanced-viz', action='store_true', help='Generate enhanced visualization with more details')
    parser.add_argument('--simple-table', action='store_true', help='Generate simple table visualization')
    parser.add_argument('--show-tokens', action='store_true', help='Show token IDs in console output')
    parser.add_argument('--silent', action='store_true', help='Suppress console output of the comparison table')
    
    # New algorithm selection arguments
    parser.add_argument('--algorithm', type=str, default='prophet', 
                        choices=['prophet', 'facebook_prophet', 'neural_prophet', 'timesfm', 'ensemble', 
                                'enhanced_facebook_prophet', 'enhanced_neural_prophet', 'enhanced_timesfm'],
                        help='Prediction algorithm to use (default: prophet)')
    
    # Facebook Prophet specific parameters
    parser.add_argument('--changepoint-prior', type=float, default=0.05,
                        help='Facebook Prophet changepoint prior scale (default: 0.05)')
    parser.add_argument('--seasonality-prior', type=float, default=10.0,
                        help='Facebook Prophet seasonality prior scale (default: 10.0)')
    
    # Neural Prophet specific parameters
    parser.add_argument('--epochs', type=int, default=50,
                        help='Neural Prophet training epochs (default: 50)')
    parser.add_argument('--learning-rate', type=float, default=0.15,
                        help='Neural Prophet learning rate (default: 0.15)')
    
    # General parameters
    parser.add_argument('--current-time', type=str,
                        help='Current time for prediction context (format: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--fast-mode', action='store_true',
                        help='Use fast mode for ensemble predictions (default: False)')
    parser.add_argument('--random-seed', type=int, default=42,
                        help='Random seed for reproducible results (default: 42)')

    args = parser.parse_args()
    
    # Set default output paths if not specified
    if args.output is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        algorithm_suffix = args.algorithm if args.algorithm != 'prophet' else 'prophet'
        args.output = os.path.join(output_dir, f'comparison_{algorithm_suffix}_{timestamp}.csv')
    
    if args.visualize and args.viz_output is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        algorithm_suffix = args.algorithm if args.algorithm != 'prophet' else 'prophet'
        args.viz_output = os.path.join(viz_dir, f'comparison_{algorithm_suffix}_{timestamp}.png')
    
    # Path for simple table visualization
    simple_table_output = None
    if args.simple_table:
        if args.viz_output:
            # Modify the viz_output path to indicate it's a simple table
            simple_table_output = args.viz_output.replace('.png', '_table.png')
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            algorithm_suffix = args.algorithm if args.algorithm != 'prophet' else 'prophet'
            simple_table_output = os.path.join(viz_dir, f'table_{algorithm_suffix}_{timestamp}.png')
    
    # Parse current time if provided
    current_time = None
    if args.current_time:
        try:
            current_time = datetime.datetime.strptime(args.current_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print(f"Error: Invalid time format. Use YYYY-MM-DD HH:MM:SS")
            sys.exit(1)
    
    # Prepare prediction algorithm kwargs
    prediction_kwargs = {}
    if current_time:
        prediction_kwargs['current_time'] = current_time
    
    # Add algorithm-specific parameters
    if args.algorithm == 'facebook_prophet':
        prediction_kwargs['changepoint_prior'] = args.changepoint_prior
        prediction_kwargs['seasonality_prior'] = args.seasonality_prior
    elif args.algorithm == 'neural_prophet':
        prediction_kwargs['epochs'] = args.epochs
        prediction_kwargs['learning_rate'] = args.learning_rate
    elif args.algorithm == 'ensemble':
        prediction_kwargs['fast_mode'] = args.fast_mode
    
    # Add common parameters
    prediction_kwargs['random_seed'] = args.random_seed
    
    try:
        # Generate comparison table
        df = generate_comparison_table(
            refresh=not args.no_refresh,
            use_prophet=not args.no_prophet,
            algorithm=args.algorithm,
            output_path=args.output,
            threshold=args.threshold,
            silent=args.silent,
            **prediction_kwargs
        )
        
        # Print algorithm information
        if not args.silent:
            print(f"\nUsing prediction algorithm: {args.algorithm}")
            if args.algorithm == 'facebook_prophet':
                print(f"  - Changepoint prior: {args.changepoint_prior}")
                print(f"  - Seasonality prior: {args.seasonality_prior}")
            elif args.algorithm == 'neural_prophet':
                print(f"  - Epochs: {args.epochs}")
                print(f"  - Learning rate: {args.learning_rate}")
            if current_time:
                print(f"  - Current time: {current_time}")
        
        # Print the table if not in silent mode
        if not df.empty and not args.silent:
            # Determine which columns to show 
            display_cols = [col for col in df.columns if col not in ['Token ID', 'Market ID']]
            print("\nComparison Table:")
            print(df[display_cols].to_string(index=False))
            
            # Show token IDs in a cleaner format if requested
            if args.show_tokens:
                print("\nToken IDs:")
                data_rows = df[df['Range'] != 'EXPECTED VALUE']
                for _, row in data_rows.iterrows():
                    if 'Token ID' in row and row['Token ID']:
                        print(f"{row['Range']}: {row['Token ID']}")
            
            # Find the largest adjusted opportunity
            data_rows = df[df['Range'] != 'EXPECTED VALUE']
            full_adj_opp_col = f'Adj-Full ({args.threshold}%)'
            buy_only_col = f'Buy-Only ({args.threshold}%)'
            sell_only_col = f'Sell-Only ({args.threshold}%)'
            
            if not data_rows.empty:
                # Find the index of the max adjusted opportunity
                max_adj_idx = data_rows[full_adj_opp_col].idxmax()
                max_opp_row = data_rows.loc[max_adj_idx]
                
                # Only show if there's a meaningful opportunity
                if max_opp_row[full_adj_opp_col] > 0:
                    print("\nBest Trading Opportunity:")
                    print(f"Range: {max_opp_row['Range']}")
                    print(f"Prediction: {max_opp_row['Pred (%)']}%")
                    print(f"Market: {max_opp_row['Mkt (%)']}%")
                    print(f"Bid: {max_opp_row['Bid (%)']}%")
                    print(f"Ask: {max_opp_row['Ask (%)']}%")
                    print(f"Spread: {max_opp_row['Spread (%)']}%")
                    print(f"Difference: {max_opp_row['Diff (%)']}%")
                    print(f"Opportunity: {max_opp_row['Opp (%)']}%")
                    print(f"Spread-Adjusted Opportunity: {max_opp_row['Adj-Sp (%)']}%")
                    print(f"Fully-Adjusted Opportunity: {max_opp_row[full_adj_opp_col]}%")
                    print(f"Buy-Only Opportunity: {max_opp_row[buy_only_col]}%")
                    print(f"Sell-Only Opportunity: {max_opp_row[sell_only_col]}%")
                    
                    # Show token ID for best opportunity
                    if 'Token ID' in max_opp_row and max_opp_row['Token ID']:
                        print(f"Token ID: {max_opp_row['Token ID']}")
                    
                    # Trading recommendation with specific price
                    if max_opp_row['Diff (%)'] > 0:
                        print(f"Recommendation: BUY {max_opp_row['Range']} at {max_opp_row['Ask (%)']}% (prediction: {max_opp_row['Pred (%)']}%)")
                        print(f"Edge: {max_opp_row[full_adj_opp_col]}% after spread and {args.threshold}% threshold")
                    else:
                        print(f"Recommendation: SELL {max_opp_row['Range']} at {max_opp_row['Bid (%)']}% (prediction: {max_opp_row['Pred (%)']}%)")
                        print(f"Edge: {max_opp_row[full_adj_opp_col]}% after spread and {args.threshold}% threshold")
                else:
                    print("\nNo significant trading opportunities found above the threshold.")
                    print(f"Try lowering the threshold (currently set to {args.threshold}%)")
            else:
                print("No data available for comparison. Please check the logs for errors.")
        else:
            if df.empty:
                print("No data available for comparison. Please check the logs for errors.")
        
        # Generate simple table visualization if requested
        if args.simple_table and not df.empty:
            visualize_simple_table(
                comparison_df=df,
                output_path=simple_table_output,
                threshold=args.threshold
            )
            print(f"\nSimple table visualization saved to: {simple_table_output}")
        
        # Generate visualization if requested
        if args.visualize and not df.empty:
            if args.enhanced_viz:
                enhanced_visualization(
                    comparison_df=df,
                    output_path=args.viz_output,
                    threshold=args.threshold
                )
            else:
                visualize_comparison(
                    comparison_df=df,
                    output_path=args.viz_output,
                    threshold=args.threshold
                )
            print(f"\nVisualization saved to: {args.viz_output}")
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        print(f"Error: {str(e)}")
        print("Please check the logs for more details.")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 