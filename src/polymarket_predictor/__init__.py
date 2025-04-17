"""
Polymarket Tweet Predictor - Tools for predicting and analyzing tweet counts for Polymarket events.
"""

from .tweet_predictor import predict_tweet_frame_probabilities, verify_tweet_count

__all__ = ['predict_tweet_frame_probabilities', 'verify_tweet_count'] 