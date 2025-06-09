"""
Enhanced TimesFM predictor with multiple model configurations and ensemble methods.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path
import sys
from scipy import stats

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from constants import TWEET_COUNT_FRAMES, ET_TIMEZONE

from .predictor import TimesFMTweetPredictor


class EnhancedTimesFMTweetPredictor:
    """Enhanced TimesFM predictor with multiple model configurations."""
    
    def __init__(self, data_path=None, save_plots=True):
        """
        Initialize the enhanced TimesFM predictor.
        
        Args:
            data_path (str): Path to tweet data CSV file
            save_plots (bool): Whether to save prediction plots
        """
        self.data_path = data_path
        self.save_plots = save_plots
        self.models = {}
        self.predictions = {}
        self.plots_dir = Path("src/prediction_algos/timesfm/plots")
        
        # Create plots directory
        if self.save_plots:
            self.plots_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_models(self):
        """Prepare multiple TimesFM models with different configurations."""
        print("Preparing Enhanced TimesFM Ensemble...")
        
        # Model configurations
        model_configs = {
            'short_context': {
                'context_len': 32,
                'num_samples': 80,
                'model_name': 'timesfm-1.0-200m'
            },
            'medium_context': {
                'context_len': 64,
                'num_samples': 100,
                'model_name': 'timesfm-1.0-200m'
            },
            'long_context': {
                'context_len': 128,
                'num_samples': 100,
                'model_name': 'timesfm-1.0-200m'
            },
            'high_sampling': {
                'context_len': 64,
                'num_samples': 200,
                'model_name': 'timesfm-1.0-200m'
            }
        }
        
        # Initialize models
        for model_name, config in model_configs.items():
            print(f"\n--- Preparing {model_name} model ---")
            model = TimesFMTweetPredictor(
                data_path=self.data_path,
                save_plots=False  # Disable individual plots
            )
            
            model.prepare_model(
                context_len=config['context_len'],
                horizon_len=7,
                num_samples=config['num_samples'],
                quantiles=[0.1, 0.9],
                model_name=config['model_name']
            )
            
            self.models[model_name] = model
            print(f"{model_name} model ready!")
        
        print(f"\n✅ Enhanced TimesFM ensemble with {len(self.models)} models prepared!")
        return self.models
    
    def generate_predictions(self, current_time=None):
        """
        Generate predictions from all models and create ensemble.
        
        Args:
            current_time (datetime): Current time for prediction context
            
        Returns:
            dict: Complete ensemble prediction results
        """
        if not self.models:
            self.prepare_models()
        
        print("\n=== Enhanced TimesFM Ensemble Prediction ===")
        
        # Generate predictions from each model
        for model_name, model in self.models.items():
            print(f"\nGenerating predictions with {model_name} model...")
            prediction = model.predict_remaining_tweets(current_time)
            probabilities = model.calculate_probabilities(prediction)
            
            self.predictions[model_name] = {
                'prediction_results': prediction,
                'probabilities': probabilities
            }
        
        # Create ensemble predictions
        ensemble_results = self._create_ensemble_prediction()
        
        # Get week context
        week_data = list(self.models.values())[0].data_processor.get_current_week_data(current_time)
        
        return {
            'model_type': 'Enhanced TimesFM Ensemble',
            'ensemble_results': ensemble_results,
            'individual_predictions': self.predictions,
            'week_context': week_data,
            'num_models': len(self.models)
        }
    
    def _create_ensemble_prediction(self):
        """Create ensemble prediction from multiple models."""
        # Collect predictions
        total_predictions = []
        remaining_predictions = []
        lower_bounds = []
        upper_bounds = []
        
        # Collect all probabilities
        all_probabilities = {}
        for frame in TWEET_COUNT_FRAMES:
            all_probabilities[frame['name']] = []
        
        for model_name, pred_data in self.predictions.items():
            results = pred_data['prediction_results']
            probabilities = pred_data['probabilities']
            
            total_predictions.append(results['total_predicted'])
            remaining_predictions.append(results['remaining_tweets'])
            lower_bounds.append(results['confidence_interval']['lower'])
            upper_bounds.append(results['confidence_interval']['upper'])
            
            # Collect probabilities
            for frame_name, prob in probabilities.items():
                all_probabilities[frame_name].append(prob)
        
        # Calculate ensemble statistics
        ensemble_total = np.mean(total_predictions)
        ensemble_remaining = np.mean(remaining_predictions)
        ensemble_lower = np.mean(lower_bounds)
        ensemble_upper = np.mean(upper_bounds)
        
        # Calculate ensemble probabilities (average)
        ensemble_probabilities = {}
        for frame_name, probs in all_probabilities.items():
            ensemble_probabilities[frame_name] = np.mean(probs)
        
        # Normalize ensemble probabilities
        total_prob = sum(ensemble_probabilities.values())
        if total_prob > 0:
            ensemble_probabilities = {k: v / total_prob for k, v in ensemble_probabilities.items()}
        
        # Calculate ensemble uncertainty
        total_std = np.std(total_predictions)
        remaining_std = np.std(remaining_predictions)
        
        # Get current tweets from any model
        current_tweets = list(self.predictions.values())[0]['prediction_results']['current_tweets']
        days_remaining = list(self.predictions.values())[0]['prediction_results']['days_remaining']
        
        return {
            'total_predicted': ensemble_total,
            'remaining_tweets': ensemble_remaining,
            'current_tweets': current_tweets,
            'days_remaining': days_remaining,
            'confidence_interval': {
                'lower': ensemble_lower,
                'upper': ensemble_upper,
                'width': ensemble_upper - ensemble_lower
            },
            'ensemble_uncertainty': {
                'total_std': total_std,
                'remaining_std': remaining_std,
                'coefficient_of_variation': total_std / ensemble_total if ensemble_total > 0 else 0
            },
            'probabilities': ensemble_probabilities,
            'individual_totals': total_predictions,
            'model_agreement': {
                'min_prediction': min(total_predictions),
                'max_prediction': max(total_predictions),
                'range': max(total_predictions) - min(total_predictions),
                'agreement_score': 1 - (np.std(total_predictions) / np.mean(total_predictions)) if np.mean(total_predictions) > 0 else 0
            }
        }
    
    def print_prediction_summary(self, prediction_summary):
        """Print a formatted summary of ensemble predictions."""
        ensemble = prediction_summary['ensemble_results']
        individual = prediction_summary['individual_predictions']
        week_context = prediction_summary['week_context']
        
        print(f"\n=== ENHANCED TIMESFM ENSEMBLE SUMMARY ===")
        print(f"Number of models: {prediction_summary['num_models']}")
        print(f"Current time: {week_context['current_time']}")
        print(f"Week period: {week_context['week_start']} to {week_context['week_end']}")
        print(f"Tweets posted so far: {ensemble['current_tweets']}")
        print(f"Time remaining: {week_context['time_remaining']}")
        print(f"Days remaining: {ensemble['days_remaining']}")
        
        print(f"\n=== ENSEMBLE PREDICTIONS ===")
        print(f"Remaining tweets: {ensemble['remaining_tweets']:.1f}")
        print(f"Total predicted: {ensemble['total_predicted']:.1f}")
        print(f"80% Confidence interval: {ensemble['confidence_interval']['lower']:.1f} - {ensemble['confidence_interval']['upper']:.1f}")
        
        print(f"\n=== MODEL AGREEMENT ===")
        agreement = ensemble['model_agreement']
        print(f"Agreement score: {agreement['agreement_score']:.3f} (1.0 = perfect agreement)")
        print(f"Prediction range: {agreement['min_prediction']:.1f} - {agreement['max_prediction']:.1f}")
        print(f"Standard deviation: {ensemble['ensemble_uncertainty']['total_std']:.1f}")
        print(f"Coefficient of variation: {ensemble['ensemble_uncertainty']['coefficient_of_variation']:.3f}")
        
        print(f"\n=== INDIVIDUAL MODEL PREDICTIONS ===")
        for model_name, pred_data in individual.items():
            total_pred = pred_data['prediction_results']['total_predicted']
            print(f"{model_name:15s}: {total_pred:6.1f} tweets")
        
        print(f"\n=== ELON MUSK TWEET COUNT PREDICTIONS ===")
        print("=" * 70)
        print(f"Ensemble prediction: {ensemble['total_predicted']:.1f}")
        print(f"80% Confidence interval: {ensemble['confidence_interval']['lower']:.1f} - {ensemble['confidence_interval']['upper']:.1f}")
        
        print(f"\nPROBABILITIES BY TIME FRAME (Ensemble):")
        print("-" * 50)
        
        # Sort by probability (highest first)
        sorted_probs = sorted(ensemble['probabilities'].items(), key=lambda x: x[1], reverse=True)
        
        for frame_name, probability in sorted_probs:
            percentage = probability * 100
            print(f"{frame_name:20s}: {probability:8.3f} ({percentage:5.1f}%)")
    
    def plot_predictions(self, prediction_summary, save=None):
        """
        Create comprehensive visualization plots for ensemble predictions.
        
        Args:
            prediction_summary (dict): Prediction results
            save (str): Optional filename to save plot
        """
        if not self.save_plots:
            return
            
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        ensemble = prediction_summary['ensemble_results']
        individual = prediction_summary['individual_predictions']
        
        # Create subplots
        fig, axes = plt.subplots(2, 3, figsize=(20, 12))
        fig.suptitle('Enhanced TimesFM Ensemble Predictions', fontsize=16, fontweight='bold')
        
        # Plot 1: Individual model predictions comparison
        ax1 = axes[0, 0]
        model_names = list(individual.keys())
        total_preds = [individual[name]['prediction_results']['total_predicted'] for name in model_names]
        
        bars = ax1.bar(range(len(model_names)), total_preds, alpha=0.7, color='lightcoral')
        ax1.axhline(ensemble['total_predicted'], color='red', linestyle='--', linewidth=2, label='Ensemble')
        ax1.set_title('Individual Model Predictions')
        ax1.set_xlabel('Model')
        ax1.set_ylabel('Total Predicted Tweets')
        ax1.set_xticks(range(len(model_names)))
        ax1.set_xticklabels(model_names, rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=9)
        
        # Plot 2: Ensemble probability distribution
        ax2 = axes[0, 1]
        frames = list(ensemble['probabilities'].keys())
        probs = [ensemble['probabilities'][frame] * 100 for frame in frames]
        
        bars = ax2.bar(range(len(frames)), probs, alpha=0.7, color='lightblue', edgecolor='navy')
        ax2.set_title('Ensemble Probability Distribution')
        ax2.set_xlabel('Tweet Count Range')
        ax2.set_ylabel('Probability (%)')
        ax2.set_xticks(range(len(frames)))
        ax2.set_xticklabels(frames, rotation=45, ha='right')
        ax2.grid(True, alpha=0.3)
        
        # Add probability labels
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
        
        # Plot 3: Model agreement visualization
        ax3 = axes[0, 2]
        total_preds_array = np.array(total_preds)
        ax3.boxplot([total_preds_array], labels=['Models'])
        ax3.scatter([1] * len(total_preds), total_preds, alpha=0.7, color='red', s=50)
        ax3.axhline(ensemble['total_predicted'], color='blue', linestyle='--', linewidth=2, label='Ensemble Mean')
        ax3.set_title('Model Agreement')
        ax3.set_ylabel('Total Predicted Tweets')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Confidence intervals comparison
        ax4 = axes[1, 0]
        for i, (model_name, pred_data) in enumerate(individual.items()):
            ci = pred_data['prediction_results']['confidence_interval']
            total = pred_data['prediction_results']['total_predicted']
            ax4.errorbar([i], [total], 
                        yerr=[[total - ci['lower']], [ci['upper'] - total]], 
                        fmt='o', capsize=5, capthick=2, alpha=0.7, label=model_name)
        
        # Add ensemble CI
        ensemble_ci = ensemble['confidence_interval']
        ensemble_total = ensemble['total_predicted']
        ax4.errorbar([len(individual)], [ensemble_total], 
                    yerr=[[ensemble_total - ensemble_ci['lower']], [ensemble_ci['upper'] - ensemble_total]], 
                    fmt='s', capsize=8, capthick=3, color='red', markersize=8, label='Ensemble')
        
        ax4.set_title('Confidence Intervals Comparison')
        ax4.set_xlabel('Model')
        ax4.set_ylabel('Total Predicted Tweets')
        ax4.set_xticks(range(len(individual) + 1))
        ax4.set_xticklabels(list(individual.keys()) + ['Ensemble'], rotation=45, ha='right')
        ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax4.grid(True, alpha=0.3)
        
        # Plot 5: Probability distributions comparison (selected ranges)
        ax5 = axes[1, 1]
        selected_ranges = ['150–174', '175–199', '200–224']  # Most likely ranges
        
        x_pos = np.arange(len(selected_ranges))
        width = 0.15
        
        for i, (model_name, pred_data) in enumerate(individual.items()):
            probs = [pred_data['probabilities'].get(range_name, 0) * 100 for range_name in selected_ranges]
            ax5.bar(x_pos + i * width, probs, width, alpha=0.7, label=model_name)
        
        # Add ensemble
        ensemble_probs = [ensemble['probabilities'].get(range_name, 0) * 100 for range_name in selected_ranges]
        ax5.bar(x_pos + len(individual) * width, ensemble_probs, width, alpha=0.9, color='red', label='Ensemble')
        
        ax5.set_title('Probability Distributions (Key Ranges)')
        ax5.set_xlabel('Tweet Count Range')
        ax5.set_ylabel('Probability (%)')
        ax5.set_xticks(x_pos + width * len(individual) / 2)
        ax5.set_xticklabels(selected_ranges)
        ax5.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax5.grid(True, alpha=0.3)
        
        # Plot 6: Ensemble uncertainty metrics
        ax6 = axes[1, 2]
        uncertainty = ensemble['ensemble_uncertainty']
        agreement = ensemble['model_agreement']
        
        metrics = ['Std Dev', 'CV', 'Range', 'Agreement']
        values = [
            uncertainty['total_std'],
            uncertainty['coefficient_of_variation'] * 100,  # Convert to percentage
            agreement['range'],
            agreement['agreement_score'] * 100  # Convert to percentage
        ]
        colors = ['orange', 'green', 'purple', 'blue']
        
        bars = ax6.bar(metrics, values, color=colors, alpha=0.7)
        ax6.set_title('Ensemble Uncertainty Metrics')
        ax6.set_ylabel('Value')
        
        # Add value labels
        for bar, value in zip(bars, values):
            ax6.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
                    f'{value:.1f}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        # Save plot
        if save:
            plt.savefig(save, dpi=300, bbox_inches='tight')
        elif self.save_plots:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.plots_dir / f"enhanced_timesfm_ensemble_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {filename}")
        
        plt.show() 