"""
TimesFM (Time Series Foundation Model) based predictor for Elon Musk tweet counts.
"""

from .data_processor import TweetDataProcessor
from .predictor import TimesFMTweetPredictor
from .enhanced_predictor import EnhancedTimesFMTweetPredictor

# Create a FastTimesFMTweetPredictor alias for the optimized single model
class FastTimesFMTweetPredictor(TimesFMTweetPredictor):
    """Ultra-fast single TimesFM predictor optimized for speed."""
    
    def prepare_model(self, **kwargs):
        """Prepare super fast TimesFM model."""
        # Override with ultra-fast settings
        fast_settings = {
            'context_len': 32,      # REDUCED context length
            'horizon_len': 7,       # Standard horizon
            'num_samples': 10,      # REDUCED sampling
            'quantiles': [0.1, 0.9]
        }
        fast_settings.update(kwargs)  # Allow overrides
        
        return super().prepare_model(**fast_settings)

__all__ = ['TweetDataProcessor', 'TimesFMTweetPredictor', 'EnhancedTimesFMTweetPredictor', 'FastTimesFMTweetPredictor'] 