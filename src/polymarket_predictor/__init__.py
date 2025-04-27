"""
Polymarket Predictor module for tweet prediction.

This module provides tools to predict tweet counts for Polymarket events.
"""

from src.polymarket_predictor.main import (
    predict_tweet_frame_probabilities, 
    main
)

__all__ = [
    'predict_tweet_frame_probabilities',
    'main'
] 