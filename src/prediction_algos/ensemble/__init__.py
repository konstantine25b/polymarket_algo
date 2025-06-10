"""
Ensemble prediction algorithms combining multiple forecasting models.
"""

from .predictor import EnsembleTweetPredictor

class FastEnsembleTweetPredictor(EnsembleTweetPredictor):
    """Fast variant of ensemble predictor using optimized models."""
    
    def __init__(self, data_path=None, save_plots=True, 
                 neural_prophet_weight=0.17, facebook_prophet_weight=0.25, timesfm_weight=0.35,
                 basic_prophet_weight=0.20, moving_average_weight=0.015, linear_trend_weight=0.015):
        """
        Initialize fast ensemble predictor with optimized models.
        
        Args:
            data_path (str): Path to tweet data CSV file
            save_plots (bool): Whether to save prediction plots
            neural_prophet_weight (float): Weight for Neural Prophet model
            facebook_prophet_weight (float): Weight for Facebook Prophet model  
            timesfm_weight (float): Weight for TimesFM model
            basic_prophet_weight (float): Weight for Basic Prophet model
            moving_average_weight (float): Weight for moving average predictions
            linear_trend_weight (float): Weight for linear trend predictions
        """
        super().__init__(
            data_path=data_path,
            save_plots=save_plots,
            use_fast_models=True,  # Enable fast models by default
            neural_prophet_weight=neural_prophet_weight,
            facebook_prophet_weight=facebook_prophet_weight,
            timesfm_weight=timesfm_weight,
            basic_prophet_weight=basic_prophet_weight,
            moving_average_weight=moving_average_weight,
            linear_trend_weight=linear_trend_weight
        )

__all__ = ['EnsembleTweetPredictor', 'FastEnsembleTweetPredictor'] 