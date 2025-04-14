import pandas as pd
from datetime import datetime, timedelta
from pandas import Timestamp
import os
import logging
from pathlib import Path
from src.utils.file_utils import get_data_path

class PredictionEvaluator:
    def __init__(self, predictor=None, analyzer=None, logger=None):
        self.predictor = predictor
        self.analyzer = analyzer
        self.logger = logger or logging.getLogger(__name__)
        
    def evaluate_precision(self, days_back=14):
        """Calculate precision by comparing predictions for past days with actual counts"""
        if self.analyzer is None or self.analyzer.daily_counts is None:
            self.logger.error("Please set analyzer with analyzed patterns first")
            return
            
        self.logger.info(f"\nEvaluating prediction precision over the past {days_back} days...")
        
        # Get the actual daily counts for comparison
        end_date = self.analyzer.df['date'].max()
        start_date = end_date - timedelta(days=days_back)
        
        # Actual counts
        actual_counts = self.analyzer.daily_counts[
            (self.analyzer.daily_counts['date'].dt.date >= start_date) & 
            (self.analyzer.daily_counts['date'].dt.date <= end_date)
        ].set_index('date')['count'].to_dict()
        
        errors = []
        predictions = {}
        
        # For each day we want to evaluate
        for days in range(1, days_back):
            # Create a cutoff date for this prediction
            prediction_date = start_date + timedelta(days=days - 1)
            target_date = start_date + timedelta(days=days)
            
            # Create a temporary predictor using data before the target date
            temp_df = self.analyzer.df[self.analyzer.df['date'] < target_date].copy()
            
            if len(temp_df) < 100:  # Require minimum data for meaningful analysis
                continue
                
            # Create temporary analyzer and predictor
            from src.algos.elon_tweet_predictor.pattern_analyzer import TweetPatternAnalyzer
            from src.algos.elon_tweet_predictor.predictor import TweetPredictor
            
            temp_analyzer = TweetPatternAnalyzer(temp_df)
            temp_analyzer.analyze_patterns()
            
            temp_predictor = TweetPredictor(temp_analyzer)
            
            # Make one-day prediction from prediction_date to target_date
            pred_result = temp_predictor.predict_count(target_date_str=target_date.strftime('%Y-%m-%d'))
            
            if pred_result and 'total_expected_tweets' in pred_result:
                predicted = pred_result['total_expected_tweets']
                
                fixedDate = Timestamp(str(target_date)+' 00:00:00')
                actual = actual_counts.get(fixedDate, 0)
               
                error = abs(predicted - actual)
                errors.append(error)
                
                # Store prediction details
                predictions[target_date.strftime('%Y-%m-%d')] = {
                    'predicted': predicted,
                    'actual': actual,
                    'error': error,
                    'percent_error': (error / actual * 100) if actual > 0 else float('inf')
                }
        
        # Calculate precision metrics
        if errors:
            mae = sum(errors) / len(errors)
            rmse = (sum(e**2 for e in errors) / len(errors))**0.5
            
            # Fix for division by zero
            avg_actual = sum(p['actual'] for p in predictions.values()) / len(predictions) if predictions else 0
            
            self.logger.info(f"\nPrediction Metrics:")
            self.logger.info(f"Mean Absolute Error (MAE): {mae:.2f} tweets")
            self.logger.info(f"Root Mean Squared Error (RMSE): {rmse:.2f} tweets")
            
            # Safe division to handle zero actual tweets
            if avg_actual > 0:
                self.logger.info(f"Average Error Percentage: {(mae / avg_actual) * 100:.1f}%")
            else:
                self.logger.info("Average Error Percentage: Cannot calculate (no actual tweets)")
            
            # Display prediction vs actual for each day
            self.logger.info("\nDay-by-day comparison:")
            for date, data in sorted(predictions.items()):
                error_percent = data['percent_error'] if data['actual'] > 0 else "N/A"
                error_percent_display = f"({error_percent:.1f}%)" if isinstance(error_percent, (int, float)) else f"({error_percent})"
                
                self.logger.info(f"- {date}: Predicted {data['predicted']:.1f}, Actual {data['actual']}, " +
                      f"Error {data['error']:.1f} {error_percent_display}")
            
            return {
                'mae': mae,
                'rmse': rmse,
                'avg_error_percent': (mae / avg_actual) * 100 if avg_actual > 0 else None,
                'predictions': predictions
            }
        
        self.logger.warning("No valid prediction days found for evaluation")
        return None 