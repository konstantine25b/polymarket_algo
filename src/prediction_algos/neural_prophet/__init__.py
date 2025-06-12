"""
Neural Prophet-based predictor for Elon Musk tweet counts.
"""

from .data_processor import TweetDataProcessor
from .predictor import NeuralTweetPredictor
from .enhanced_predictor import EnhancedNeuralTweetPredictor

# Create a FastNeuralTweetPredictor alias for the optimized single model
class FastNeuralTweetPredictor(NeuralTweetPredictor):
    """Ultra-fast single Neural Prophet predictor optimized for speed."""
    
    def prepare_model(self, **kwargs):
        """Prepare super fast Neural Prophet model."""
        # Override with ultra-fast settings
        fast_settings = {
            'epochs': 20,           # VERY LOW epochs
            'learning_rate': 0.3,   # HIGH learning rate
            'yearly_seasonality': True,
            'weekly_seasonality': True,
            'daily_seasonality': False,  # DISABLED
            'n_forecasts': 1
        }
        fast_settings.update(kwargs)  # Allow overrides
        
        return super().prepare_model(**fast_settings)

__all__ = ['TweetDataProcessor', 'NeuralTweetPredictor', 'EnhancedNeuralTweetPredictor', 'FastNeuralTweetPredictor'] 