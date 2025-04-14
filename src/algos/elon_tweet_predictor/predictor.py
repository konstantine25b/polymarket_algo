"""
This file provides backward compatibility for existing imports.
The actual implementation has been refactored into the predictor/ module.
"""

from src.algos.elon_tweet_predictor.predictor import TweetPredictor

# For backward compatibility
__all__ = ['TweetPredictor'] 