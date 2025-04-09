from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import warnings
warnings.filterwarnings('ignore')

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
default_filename = os.path.join(src_dir, 'data', 'elonmusk_reformatted.csv')

class ElonTweetPredictor:
    def __init__(self):
        self.df = None
        self.daily_counts = None
        self.daily_features = None
        self.model = None
        self.weekday_probs = None
        self.hourly_probs = None
        self.last_date = None
        
    def load_data(self, file_path):
        """Load the tweet data from the reformatted CSV"""
        print(f"\n{'='*50}")
        print(f"Loading data from: {file_path}")
        
        try:
            # Load the data
            self.df = pd.read_csv(file_path)
            
            # Parse the timestamp
            self.df['created_at'] = pd.to_datetime(
                self.df['created_at'], 
                format='%Y:%m:%d:%H:%M:%S',
                errors='coerce'
            )
            
            # Drop rows with invalid timestamps
            self.df = self.df.dropna(subset=['created_at'])
            
            # Sort by time
            self.df = self.df.sort_values('created_at')
            
            # Extract date and time components
            self.df['date'] = self.df['created_at'].dt.date
            self.df['hour'] = self.df['created_at'].dt.hour
            self.df['weekday'] = self.df['created_at'].dt.weekday
            self.df['month'] = self.df['created_at'].dt.month
            
            # Get the last available date
            self.last_date = self.df['date'].max()
            
            print(f"Loaded {len(self.df)} tweets")
            print(f"Date range: {self.df['date'].min()} to {self.df['date'].max()}")
            
            return True
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return False
            
    def analyze_patterns(self):
        """Analyze tweeting patterns to extract features for prediction"""
        if self.df is None:
            print("Please load data first")
            return
            
        print("\nAnalyzing tweeting patterns...")
        
        # Calculate daily counts
        self.daily_counts = self.df.groupby('date').size().reset_index(name='count')
        self.daily_counts['date'] = pd.to_datetime(self.daily_counts['date'])
        
        # Create a continuous date range to include days with no tweets
        date_range = pd.date_range(start=self.daily_counts['date'].min(), end=self.daily_counts['date'].max())
        date_df = pd.DataFrame({'date': date_range})
        self.daily_counts = date_df.merge(self.daily_counts, on='date', how='left').fillna(0)
        
        # Extract date components for the continuous range
        self.daily_counts['weekday'] = self.daily_counts['date'].dt.weekday
        self.daily_counts['month'] = self.daily_counts['date'].dt.month
        self.daily_counts['day_of_month'] = self.daily_counts['date'].dt.day
        self.daily_counts['year'] = self.daily_counts['date'].dt.year
        
        # Calculate tweeting probability by weekday
        self.weekday_probs = self.df.groupby('weekday').size() / self.daily_counts.groupby('weekday').size()
        print("\nTweeting probability by weekday:")
        for day, prob in self.weekday_probs.items():
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
            print(f"{day_name}: {prob:.2%}")
            
        # Calculate hourly distribution
        self.hourly_probs = self.df.groupby('hour').size() / self.df.groupby('hour').size().sum()
        
        # Find most active hours
        top_hours = self.hourly_probs.nlargest(3)
        print("\nMost active hours:")
        for hour, prob in top_hours.items():
            hour_ampm = f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"
            print(f"{hour_ampm}: {prob:.2%} of tweets")
            
        # Create features for the model
        self.create_features()
        
    def create_features(self):
        """Create features for the prediction model"""
        # Create a dataframe with one row per day
        self.daily_features = self.daily_counts.copy()
        
        # Add binary indicator for whether he tweeted that day
        self.daily_features['tweeted'] = (self.daily_features['count'] > 0).astype(int)
        
        # Add lag features (did he tweet in the past N days?)
        for lag in range(1, 8):
            self.daily_features[f'tweeted_lag_{lag}'] = self.daily_features['tweeted'].shift(lag).fillna(0)
            
        # Add moving average features
        for window in [3, 7, 14]:
            self.daily_features[f'avg_tweets_{window}d'] = self.daily_features['count'].rolling(window).mean().fillna(0)
            
        # Add day-of-week features (using sine and cosine for cyclical nature)
        self.daily_features['weekday_sin'] = np.sin(2 * np.pi * self.daily_features['weekday'] / 7)
        self.daily_features['weekday_cos'] = np.cos(2 * np.pi * self.daily_features['weekday'] / 7)
        
        # Add month features (using sine and cosine for cyclical nature)
        self.daily_features['month_sin'] = np.sin(2 * np.pi * self.daily_features['month'] / 12)
        self.daily_features['month_cos'] = np.cos(2 * np.pi * self.daily_features['month'] / 12)
        
        # Add streak features
        self.daily_features['streak'] = 0
        streak = 0
        
        for i in range(len(self.daily_features)):
            if self.daily_features.iloc[i]['tweeted'] == 1:
                streak += 1
            else:
                streak = 0
            self.daily_features.iloc[i, self.daily_features.columns.get_loc('streak')] = streak
            
        # Add absence streak features
        self.daily_features['absence_streak'] = 0
        absence_streak = 0
        
        for i in range(len(self.daily_features)):
            if self.daily_features.iloc[i]['tweeted'] == 0:
                absence_streak += 1
            else:
                absence_streak = 0
            self.daily_features.iloc[i, self.daily_features.columns.get_loc('absence_streak')] = absence_streak
        
        # Drop rows with NaN values from lag features
        self.daily_features = self.daily_features.dropna()
        
    def train_model(self):
        """Train the tweet prediction model"""
        if self.daily_features is None:
            print("Please analyze patterns first")
            return
            
        print("\nTraining prediction model...")
        
        # Prepare features for model
        feature_cols = [col for col in self.daily_features.columns if col not in ['date', 'count', 'tweeted']]
        X = self.daily_features[feature_cols]
        y = self.daily_features['tweeted']
        
        # Split into training and testing sets chronologically
        train_size = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
        y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]
        
        # Train a random forest classifier
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Evaluate the model
        y_pred = self.model.predict(X_test)
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        print(f"Model performance:")
        print(f"Accuracy: {accuracy:.2%}")
        print(f"Precision: {precision:.2%}")
        print(f"Recall: {recall:.2%}")
        print(f"F1 score: {f1:.2%}")
        
        # Feature importance
        importances = self.model.feature_importances_
        feature_importance = pd.DataFrame({
            'Feature': feature_cols,
            'Importance': importances
        }).sort_values('Importance', ascending=False)
        
        print("\nTop 5 most important features:")
        for idx, row in feature_importance.head(5).iterrows():
            print(f"- {row['Feature']}: {row['Importance']:.4f}")
            
    def predict_future(self, days=7, count_model=True):
        """Predict if Elon will tweet in the next N days"""
        if self.model is None:
            print("Please train the model first")
            return
            
        print(f"\n{'*'*50}")
        print(f"Predicting tweets for the next {days} days...")
        
        # Get the last date in the data
        last_date = self.daily_features['date'].max()
        
        # Create a dataframe for future dates
        future_dates = [last_date + timedelta(days=i+1) for i in range(days)]
        future_df = pd.DataFrame({'date': future_dates})
        
        # Extract features for future dates
        future_df['weekday'] = future_df['date'].dt.weekday
        future_df['month'] = future_df['date'].dt.month
        future_df['day_of_month'] = future_df['date'].dt.day
        future_df['year'] = future_df['date'].dt.year
        
        # Add cyclical features
        future_df['weekday_sin'] = np.sin(2 * np.pi * future_df['weekday'] / 7)
        future_df['weekday_cos'] = np.cos(2 * np.pi * future_df['weekday'] / 7)
        future_df['month_sin'] = np.sin(2 * np.pi * future_df['month'] / 12)
        future_df['month_cos'] = np.cos(2 * np.pi * future_df['month'] / 12)
        
        # Add lag features using the last known values
        last_days = self.daily_features.iloc[-7:]['tweeted'].values
        
        for lag in range(1, 8):
            if lag <= len(last_days):
                future_df[f'tweeted_lag_{lag}'] = [last_days[-lag]] + [0] * (days - 1)
            else:
                future_df[f'tweeted_lag_{lag}'] = 0
                
        # Add moving average features
        last_counts = self.daily_features.iloc[-14:]['count'].values
        
        for window in [3, 7, 14]:
            if window <= len(last_counts):
                avg = np.mean(last_counts[-window:])
                future_df[f'avg_tweets_{window}d'] = avg
            else:
                future_df[f'avg_tweets_{window}d'] = np.mean(last_counts)
                
        # Add streak features
        last_streak = self.daily_features.iloc[-1]['streak']
        future_df['streak'] = last_streak
        
        # Add absence streak features
        last_absence_streak = self.daily_features.iloc[-1]['absence_streak']
        future_df['absence_streak'] = last_absence_streak
        
        # Get the feature columns used in training
        feature_cols = [col for col in self.daily_features.columns if col not in ['date', 'count', 'tweeted']]
        
        # Make binary predictions
        # Ensure X_future has the same columns in the same order as training data
        X_future = future_df[feature_cols].copy()
        
        # For each day, update features based on previous predictions
        predictions = []
        
        # Check if model is binary or single-class
        # Try to get classes from the model
        n_classes = len(self.model.classes_)
        
        for i in range(days):
            # Get features for the current day
            X_day = X_future.iloc[[i]]
            
            # Make prediction
            will_tweet = self.model.predict(X_day)[0]
            
            # Handle probability prediction based on number of classes
            if n_classes > 1:
                # Normal binary case
                proba = self.model.predict_proba(X_day)[0][1]
            else:
                # Single class case - set probability based on the class
                proba = 1.0 if will_tweet == 1 else 0.0
            
            # Store prediction
            day_prediction = {
                'date': future_df.iloc[i]['date'].date(),
                'weekday': future_df.iloc[i]['weekday'],
                'will_tweet': bool(will_tweet),
                'probability': proba,
                'expected_tweets': 0
            }
            predictions.append(day_prediction)
            
            # Update lag features for the next day if there is one
            if i < days - 1:
                for lag in range(7, 1, -1):
                    if f'tweeted_lag_{lag-1}' in X_future.columns and f'tweeted_lag_{lag}' in X_future.columns:
                        X_future.iloc[i+1, X_future.columns.get_loc(f'tweeted_lag_{lag}')] = X_future.iloc[i, X_future.columns.get_loc(f'tweeted_lag_{lag-1}')]
                
                if 'tweeted_lag_1' in X_future.columns:
                    X_future.iloc[i+1, X_future.columns.get_loc('tweeted_lag_1')] = int(will_tweet)
                
                # Update streak features
                if will_tweet:
                    streak = X_future.iloc[i, X_future.columns.get_loc('streak')] + 1
                    absence_streak = 0
                else:
                    streak = 0
                    absence_streak = X_future.iloc[i, X_future.columns.get_loc('absence_streak')] + 1
                    
                X_future.iloc[i+1, X_future.columns.get_loc('streak')] = streak
                X_future.iloc[i+1, X_future.columns.get_loc('absence_streak')] = absence_streak
                
                # Update moving averages
                for window in [3, 7, 14]:
                    col_name = f'avg_tweets_{window}d'
                    if col_name in X_future.columns:
                        # This is a simplification; real updates would need to track actual counts
                        avg = X_future.iloc[i, X_future.columns.get_loc(col_name)]
                        X_future.iloc[i+1, X_future.columns.get_loc(col_name)] = avg
        
        # If we should predict counts too
        if count_model:
            self.predict_tweet_counts(predictions)
            
        # Display predictions
        today = datetime.now().date()
        print("\nTweet Predictions:")
        
        for pred in predictions:
            date = pred['date']
            weekday_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][pred['weekday']]
            today_str = " (TODAY)" if date == today else ""
            
            if pred['will_tweet']:
                print(f"- {date} ({weekday_name}){today_str}: WILL tweet with {pred['probability']:.1%} probability. Expected: {pred['expected_tweets']} tweets")
            else:
                print(f"- {date} ({weekday_name}){today_str}: WON'T tweet with {1-pred['probability']:.1%} probability")
                
        print(f"\nMethod: Random Forest with Tweet History and Temporal Patterns")
        print(f"{'*'*50}")
        
        return predictions
    def predict_tweet_counts(self, predictions):
        """Predict the number of tweets for days predicted to have activity"""
        # Create a simple model for tweet counts based on weekday averages
        weekday_avgs = self.daily_counts.groupby('weekday')['count'].mean()
        
        for pred in predictions:
            if pred['will_tweet']:
                # Get average count for this weekday
                avg_count = weekday_avgs.get(pred['weekday'], 0)
                
                # Adjust based on recent trend
                recent_avg = self.daily_counts.iloc[-7:]['count'].mean()
                overall_avg = self.daily_counts['count'].mean()
                
                # Trend factor (how recent activity compares to overall)
                trend_factor = recent_avg / overall_avg if overall_avg > 0 else 1.0
                
                # Apply trend factor to weekday average
                expected_count = max(1, round(avg_count * trend_factor))
                pred['expected_tweets'] = expected_count
                
    def plot_activity(self):
        """Plot tweet activity over time"""
        if self.daily_counts is None:
            print("Please analyze patterns first")
            return
            
        plt.figure(figsize=(12, 6))
        
        # Plot tweet counts
        plt.subplot(2, 1, 1)
        plt.plot(self.daily_counts['date'], self.daily_counts['count'])
        plt.title('Elon Musk Tweet Activity')
        plt.ylabel('Tweets per Day')
        plt.grid(True, alpha=0.3)
        
        # Plot 7-day moving average
        self.daily_counts['7d_avg'] = self.daily_counts['count'].rolling(7).mean()
        plt.plot(self.daily_counts['date'], self.daily_counts['7d_avg'], 'r--', label='7-day Avg')
        plt.legend()
        
        # Plot weekly distribution
        plt.subplot(2, 1, 2)
        weekday_avg = self.daily_counts.groupby('weekday')['count'].mean()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        plt.bar(days, [weekday_avg.get(i, 0) for i in range(7)])
        plt.title('Average Tweets by Day of Week')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.grid(True, axis='y', alpha=0.3)
        
        plt.savefig('elon_tweet_activity.png')
        print("\nActivity plot saved as 'elon_tweet_activity.png'")
        
    def export_predictions(self, predictions, filename='elon_predictions.csv'):
        """Export predictions to CSV"""
        if not predictions:
            print("No predictions to export")
            return
            
        pred_df = pd.DataFrame(predictions)
        pred_df.to_csv(filename, index=False)
        print(f"\nPredictions exported to {filename}")
        
    def analyze_content(self, top_n=10):
        """Analyze tweet content for patterns and topics"""
        if self.df is None or 'text' not in self.df.columns:
            print("Text data not available")
            return
            
        print("\nAnalyzing tweet content...")
        
        # Calculate tweet length statistics
        self.df['length'] = self.df['text'].str.len()
        avg_length = self.df['length'].mean()
        print(f"Average tweet length: {avg_length:.1f} characters")
        
        # Find common words and hashtags (basic implementation)
        try:
            import re
            from collections import Counter
            
            # Combine all tweet text
            all_text = ' '.join(self.df['text'].values)
            
            # Extract hashtags
            hashtags = re.findall(r'#\w+', all_text.lower())
            hashtag_counts = Counter(hashtags)
            
            if hashtag_counts:
                print("\nTop hashtags:")
                for tag, count in hashtag_counts.most_common(5):
                    print(f"- {tag}: {count} occurrences")
            
            # Look for URLs
            url_count = len(re.findall(r'https?://\S+', all_text))
            print(f"\nTweets with URLs: {url_count} ({url_count/len(self.df):.1%})")
            
            # Look for media (simplified check)
            media_indicators = ['https://t.co', 'pic.twitter', '.jpg', '.png', '.gif']
            media_count = sum(1 for text in self.df['text'] if any(ind in text for ind in media_indicators))
            print(f"Estimated tweets with media: {media_count} ({media_count/len(self.df):.1%})")
            
        except Exception as e:
            print(f"Content analysis error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Elon Musk Tweet Predictor')
    parser.add_argument('--file', type=str, default=default_filename,
                      help='Path to reformatted CSV file')
    parser.add_argument('--days', type=int, default=7,
                      help='Number of future days to predict (default: 7)')
    parser.add_argument('--plot', action='store_true',
                      help='Generate activity plots')
    parser.add_argument('--export', action='store_true',
                      help='Export predictions to CSV')
    parser.add_argument('--analyze', action='store_true',
                      help='Analyze tweet content')

    args = parser.parse_args()

    try:
        predictor = ElonTweetPredictor()
        if predictor.load_data(args.file):
            predictor.analyze_patterns()
            predictor.train_model()
            predictions = predictor.predict_future(days=args.days)
            
            if args.plot:
                predictor.plot_activity()
                
            if args.export:
                predictor.export_predictions(predictions)
                
            if args.analyze:
                predictor.analyze_content()
        else:
            print("Failed to load data. Please check your input file.")
    except Exception as e:
        import traceback
        print(f"\nError: {str(e)}")
        print(traceback.format_exc())
        print("Please check your input data and parameters")

if __name__ == "__main__":
    main()