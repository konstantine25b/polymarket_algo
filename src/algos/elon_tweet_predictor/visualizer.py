import matplotlib.pyplot as plt
import logging

class TweetVisualizer:
    def __init__(self, analyzer=None, logger=None):
        self.analyzer = analyzer
        self.logger = logger or logging.getLogger(__name__)
        
    def plot_activity(self):
        """Plot tweet activity over time"""
        if self.analyzer is None or self.analyzer.daily_counts is None:
            self.logger.error("Please set analyzer with analyzed patterns first")
            return
            
        plt.figure(figsize=(12, 8))
        
        # Plot daily tweet counts
        plt.subplot(2, 1, 1)
        plt.plot(self.analyzer.daily_counts['date'], self.analyzer.daily_counts['count'])
        plt.title('Elon Musk Daily Tweet Activity')
        plt.ylabel('Tweets per Day')
        plt.grid(True, alpha=0.3)
        
        # Plot 7-day moving average
        self.analyzer.daily_counts['7d_avg'] = self.analyzer.daily_counts['count'].rolling(7).mean()
        plt.plot(self.analyzer.daily_counts['date'], self.analyzer.daily_counts['7d_avg'], 'r--', label='7-day Avg')
        plt.legend()
        
        # Plot weekly distribution
        plt.subplot(2, 2, 3)
        weekday_avg = self.analyzer.daily_counts.groupby('weekday')['count'].mean()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        plt.bar(days, [weekday_avg.get(i, 0) for i in range(7)])
        plt.title('Average Tweets by Day of Week')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.grid(True, axis='y', alpha=0.3)
        
        # Plot hourly distribution
        plt.subplot(2, 2, 4)
        hours = [f"{h}" for h in range(24)]
        plt.bar(hours, [self.analyzer.hourly_rates.get(i, 0) for i in range(24)])
        plt.title('Hourly Tweet Distribution')
        plt.xticks(rotation=90)
        plt.xlabel('Hour of Day (24h)')
        plt.ylabel('Avg Tweets per Hour')
        plt.tight_layout()
        plt.grid(True, axis='y', alpha=0.3)
        
        plt.savefig('elon_tweet_activity.png')
        self.logger.info("\nActivity plot saved as 'elon_tweet_activity.png'")
        
    def plot_precision_results(self, precision_results):
        """Plot precision evaluation results"""
        if not precision_results or 'predictions' not in precision_results:
            self.logger.warning("No precision results to plot")
            return
            
        predictions = precision_results['predictions']
        dates = sorted(predictions.keys())
        
        predicted_values = [predictions[d]['predicted'] for d in dates]
        actual_values = [predictions[d]['actual'] for d in dates]
        
        plt.figure(figsize=(12, 8))
        
        # Plot 1: Predicted vs Actual
        plt.subplot(2, 1, 1)
        plt.plot(dates, predicted_values, 'b-', marker='o', label='Predicted')
        plt.plot(dates, actual_values, 'r-', marker='x', label='Actual')
        plt.title('Prediction Accuracy Evaluation')
        plt.ylabel('Number of Tweets')
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Plot 2: Error percentages
        plt.subplot(2, 1, 2)
        error_percentages = [predictions[d]['percent_error'] for d in dates if predictions[d]['actual'] > 0]
        error_dates = [d for d in dates if predictions[d]['actual'] > 0]
        
        if error_percentages:
            plt.bar(error_dates, error_percentages)
            plt.axhline(y=sum(error_percentages)/len(error_percentages), color='r', linestyle='--', 
                      label=f'Avg: {sum(error_percentages)/len(error_percentages):.1f}%')
            plt.title('Error Percentages by Day')
            plt.xlabel('Date')
            plt.ylabel('Error Percentage (%)')
            plt.xticks(rotation=45)
            plt.legend()
            plt.grid(True, axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('elon_tweet_prediction_accuracy.png')
        self.logger.info("\nPrecision plot saved as 'elon_tweet_prediction_accuracy.png'") 