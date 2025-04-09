from datetime import datetime, timedelta
import csv
import os
import argparse
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
filename = os.path.join(src_dir, 'data', 'elonmusk_daily_counts.csv')

class TweetPredictor:
    def __init__(self):
        self.df = None
        self.model = None
        self.fitted_model = None
        self.weekly_factors = None
        self.monthly_factors = None
        
    def load_data(self, file_path):
        """Load and validate tweet count data"""
        print(f"\n{'='*50}")
        print(f"Loading data from: {file_path}")

        try:
            # Use pandas to load data more efficiently
            self.df = pd.read_csv(file_path, header=0, names=['date', 'count'])
            
            # Convert dates and validate
            self.df['date'] = pd.to_datetime(self.df['date'], format='%Y:%m:%d', errors='coerce')
            self.df = self.df.dropna()
            
            # Ensure counts are integers
            self.df['count'] = self.df['count'].astype(int)
            
            # Sort chronologically
            self.df = self.df.sort_values('date')
            
            # Extract features
            self.df['weekday'] = self.df['date'].dt.weekday.astype(int)  # Ensure integer type
            self.df['month'] = self.df['date'].dt.month.astype(int)
            self.df['year'] = self.df['date'].dt.year.astype(int)
            self.df['day'] = self.df['date'].dt.day.astype(int)
            
            # Set date as index for time series analysis
            self.df = self.df.set_index('date')
            
            print(f"Loaded {len(self.df)} days of data")
            print(f"Date range: {self.df.index.min().date()} to {self.df.index.max().date()}")

            # Fill gaps in time series with NaN
            date_range = pd.date_range(start=self.df.index.min(), end=self.df.index.max(), freq='D')
            self.df = self.df.reindex(date_range)
            
            # Interpolate missing values (weekends, holidays, etc.)
            if self.df['count'].isna().sum() > 0:
                print(f"Interpolating {self.df['count'].isna().sum()} missing values")
                self.df['count'] = self.df['count'].interpolate(method='time')
                
                # Recalculate features for interpolated dates
                self.df['weekday'] = self.df.index.weekday.astype(int)
                self.df['month'] = self.df.index.month.astype(int)
                self.df['year'] = self.df.index.year.astype(int)
                self.df['day'] = self.df.index.day.astype(int)

        except Exception as e:
            print(f"Error loading data: {str(e)}")
            raise

    def calculate_seasonality(self):
        """Calculate seasonality patterns"""
        # Weekly seasonality
        weekly_pattern = self.df.groupby('weekday')['count'].mean()
        overall_mean = self.df['count'].mean()
        self.weekly_factors = (weekly_pattern / overall_mean).to_dict()
        
        # Monthly seasonality
        monthly_pattern = self.df.groupby('month')['count'].mean()
        self.monthly_factors = (monthly_pattern / overall_mean).to_dict()
        
        print("\nWeekly seasonality factors:")
        for day, factor in sorted(self.weekly_factors.items()):
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
            print(f"{day_name}: {factor:.3f}x baseline")
            
        print("\nMonthly seasonality factors:")
        for month, factor in sorted(self.monthly_factors.items()):
            month_name = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month-1]
            print(f"{month_name}: {factor:.3f}x baseline")
            
        # Add seasonality features
        self.df['weekly_factor'] = self.df['weekday'].map(self.weekly_factors)
        self.df['monthly_factor'] = self.df['month'].map(self.monthly_factors)

    def calculate_trend_features(self):
        """Calculate trend-based features"""
        # Rolling statistics
        self.df['rolling_7d_mean'] = self.df['count'].rolling(window=7, min_periods=1).mean()
        self.df['rolling_30d_mean'] = self.df['count'].rolling(window=30, min_periods=1).mean()
        
        # Momentum indicators
        self.df['momentum_7d'] = self.df['count'] / self.df['rolling_7d_mean']
        
        # Lag features
        for lag in [1, 7, 14]:
            self.df[f'lag_{lag}d'] = self.df['count'].shift(lag)
            
        # Rate of change
        self.df['roc_3d'] = self.df['count'].pct_change(periods=3)
        self.df['roc_7d'] = self.df['count'].pct_change(periods=7)
        
        # EWMA
        self.df['ewma_7d'] = self.df['count'].ewm(span=7).mean()
        
        # Fill NaN values that result from lagged features
        self.df = self.df.bfill().ffill()  # Fixed the deprecated warning

    def train_sarima_model(self, train_data=None, order=(1, 1, 1), seasonal_order=(1, 1, 1, 7)):
        """Train a SARIMA model on the data"""
        if train_data is None:
            train_data = self.df['count']
        
        print(f"\nTraining SARIMA({order}, {seasonal_order}) model...")
        
        try:
            # Train the SARIMA model
            self.model = SARIMAX(
                train_data,
                order=order,
                seasonal_order=seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            
            self.fitted_model = self.model.fit(disp=False)
            print(f"Model AIC: {self.fitted_model.aic:.2f}")
            
            return self.fitted_model
        except Exception as e:
            print(f"Error training SARIMA model: {str(e)}")
            # Fallback to simpler model if complex one fails
            print("Falling back to simpler model...")
            self.model = SARIMAX(
                train_data,
                order=(1, 1, 0),
                seasonal_order=(1, 0, 0, 7),
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            self.fitted_model = self.model.fit(disp=False)
            print(f"Fallback model AIC: {self.fitted_model.aic:.2f}")
            return self.fitted_model
    
    def optimize_sarima_parameters(self, p_values=(0, 1), d_values=(0, 1), q_values=(0, 1),
                                  P_values=(0, 1), D_values=(0, 1), Q_values=(0, 1), s_values=(7,)):
        """Find optimal SARIMA parameters through grid search"""
        best_aic = float('inf')
        best_params = None
        
        print("\nOptimizing SARIMA parameters (this may take a while)...")
        
        for p in p_values:
            for d in d_values:
                for q in q_values:
                    for P in P_values:
                        for D in D_values:
                            for Q in Q_values:
                                for s in s_values:
                                    try:
                                        model = SARIMAX(
                                            self.df['count'],
                                            order=(p, d, q),
                                            seasonal_order=(P, D, Q, s),
                                            enforce_stationarity=False,
                                            enforce_invertibility=False
                                        )
                                        results = model.fit(disp=False)
                                        
                                        if results.aic < best_aic:
                                            best_aic = results.aic
                                            best_params = ((p, d, q), (P, D, Q, s))
                                            print(f"New best parameters: SARIMA{best_params} (AIC: {best_aic:.2f})")
                                    except:
                                        continue
        
        print(f"\nOptimal parameters: SARIMA{best_params}")
        return best_params
    
    def evaluate_model(self, test_size=30):
        """Evaluate model performance using walk-forward validation"""
        if len(self.df) <= test_size:
            print("Not enough data for evaluation")
            return
            
        train_data = self.df[:-test_size]
        test_data = self.df[-test_size:]
        
        # Train on training data
        model = self.train_sarima_model(train_data['count'])
        
        # Make predictions
        predictions = model.forecast(steps=test_size)
        
        # Calculate metrics
        mae = mean_absolute_error(test_data['count'], predictions)
        rmse = np.sqrt(mean_squared_error(test_data['count'], predictions))
        mape = np.mean(np.abs((test_data['count'] - predictions) / np.maximum(1, test_data['count']))) * 100
        
        print("\nModel Evaluation:")
        print(f"MAE: {mae:.2f}")
        print(f"RMSE: {rmse:.2f}")
        print(f"MAPE: {mape:.2f}%")
        
        # Hybrid adjustment with seasonality
        hybrid_predictions = predictions.copy()
        for i, date in enumerate(test_data.index):
            weekday = date.weekday()
            month = date.month
            weekly_factor = self.weekly_factors.get(weekday, 1.0)
            monthly_factor = self.monthly_factors.get(month, 1.0)
            
            # Blend SARIMA with seasonality factors
            hybrid_predictions[i] = predictions[i] * 0.7 + (predictions[i] * weekly_factor * monthly_factor) * 0.3
        
        # Calculate hybrid metrics
        hybrid_mae = mean_absolute_error(test_data['count'], hybrid_predictions)
        hybrid_rmse = np.sqrt(mean_squared_error(test_data['count'], hybrid_predictions))
        hybrid_mape = np.mean(np.abs((test_data['count'] - hybrid_predictions) / np.maximum(1, test_data['count']))) * 100
        
        print("\nHybrid Model Evaluation:")
        print(f"MAE: {hybrid_mae:.2f}")
        print(f"RMSE: {hybrid_rmse:.2f}")
        print(f"MAPE: {hybrid_mape:.2f}%")
        
        return mae, rmse, mape, hybrid_mae, hybrid_rmse, hybrid_mape
    
    def predict_future_days(self, days=7, use_hybrid=True):
        """Predict tweet counts for future days"""
        if self.fitted_model is None:
            self.train_sarima_model()
            
        # Get prediction base
        print(f"\n{'*'*50}")
        print(f"Predicting the next {days} days...")
        
        # Get SARIMA forecasts
        sarima_forecasts = self.fitted_model.forecast(steps=days)
        
        # Create result dataframe
        last_date = self.df.index[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(days)]
        future_df = pd.DataFrame(index=future_dates)
        
        # Add weekday and month columns as integers
        future_df['weekday'] = [date.weekday() for date in future_dates]
        future_df['month'] = [date.month for date in future_dates]
        future_df['sarima_prediction'] = sarima_forecasts.values
        
        # Apply seasonality adjustment if using hybrid model
        if use_hybrid:
            future_df['weekly_factor'] = future_df['weekday'].apply(lambda x: self.weekly_factors.get(x, 1.0))
            future_df['monthly_factor'] = future_df['month'].apply(lambda x: self.monthly_factors.get(x, 1.0))
            
            # Blend SARIMA with seasonality factors
            future_df['prediction'] = future_df['sarima_prediction'] * 0.7 + \
                                      (future_df['sarima_prediction'] * 
                                       future_df['weekly_factor'] * 
                                       future_df['monthly_factor']) * 0.3
        else:
            future_df['prediction'] = future_df['sarima_prediction']
        
        # Round predictions to integers
        future_df['prediction'] = future_df['prediction'].round().astype(int)
        future_df['prediction'] = future_df['prediction'].clip(lower=0)  # Ensure non-negative
        
        # Get weekday names for display
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Display predictions
        print("\nFuture Predictions:")
        for date, row in future_df.iterrows():
            weekday = int(row['weekday'])  # Ensure integer for indexing
            weekday_name = weekday_names[weekday]
            print(f"- {date.date()} ({weekday_name}): {row['prediction']} tweets")
        
        print(f"\nMethod: {'Hybrid SARIMA + Seasonality' if use_hybrid else 'SARIMA only'}")
        print(f"{'*'*50}")
        
        return future_df
        
    def plot_predictions(self, future_df):
        """Plot historical data with future predictions"""
        try:
            plt.figure(figsize=(12, 6))
            
            # Plot historical data
            plt.plot(self.df.index[-90:], self.df['count'][-90:], label='Historical Data (90 days)', color='blue')
            
            # Plot future predictions
            plt.plot(future_df.index, future_df['prediction'], label='Predictions', color='red', linestyle='--')
            
            # Add confidence intervals (simplified)
            std_dev = self.df['count'].std()
            plt.fill_between(
                future_df.index,
                (future_df['prediction'] - 1.96 * std_dev).clip(lower=0),
                future_df['prediction'] + 1.96 * std_dev,
                color='red', alpha=0.2, label='95% Confidence Interval'
            )
            
            plt.title('Tweet Count Forecast')
            plt.xlabel('Date')
            plt.ylabel('Tweet Count')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Save the plot
            plt.tight_layout()
            plt.savefig('tweet_forecast.png')
            plt.close()
            
            print("\nForecast plot saved as 'tweet_forecast.png'")
        except Exception as e:
            print(f"Error creating plot: {str(e)}")

    def ensemble_predict(self, days=7):
        """Use multiple models for more robust predictions"""
        # Train multiple models with different parameters
        models = [
            ((1, 1, 1), (1, 1, 1, 7)),  # Standard SARIMA
            ((2, 1, 2), (1, 1, 1, 7)),  # More complex ARIMA part
            ((1, 1, 1), (2, 1, 0, 7)),  # More complex seasonal part
            ((1, 0, 1), (0, 1, 1, 7))   # Different differencing
        ]
        
        print("\nTraining ensemble of models...")
        forecasts = []
        
        for i, (order, seasonal_order) in enumerate(models):
            try:
                model = SARIMAX(
                    self.df['count'],
                    order=order,
                    seasonal_order=seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False
                )
                fitted_model = model.fit(disp=False)
                forecast = fitted_model.forecast(steps=days)
                forecasts.append(forecast)
                print(f"Model {i+1} trained: SARIMA{order}{seasonal_order}, AIC: {fitted_model.aic:.2f}")
            except:
                print(f"Model {i+1} failed to train, skipping...")
        
        if not forecasts:
            print("All ensemble models failed. Falling back to basic prediction.")
            return self.predict_future_days(days)
            
        # Average the forecasts
        ensemble_forecast = sum(forecasts) / len(forecasts)
        
        # Create result dataframe
        last_date = self.df.index[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(days)]
        future_df = pd.DataFrame(index=future_dates)
        
        future_df['weekday'] = [date.weekday() for date in future_dates]
        future_df['month'] = [date.month for date in future_dates]
        future_df['ensemble_prediction'] = ensemble_forecast.values
        
        # Apply seasonality adjustment
        future_df['weekly_factor'] = future_df['weekday'].apply(lambda x: self.weekly_factors.get(x, 1.0))
        future_df['monthly_factor'] = future_df['month'].apply(lambda x: self.monthly_factors.get(x, 1.0))
        
        # Blend ensemble with seasonality factors
        future_df['prediction'] = future_df['ensemble_prediction'] * 0.7 + \
                                  (future_df['ensemble_prediction'] * 
                                   future_df['weekly_factor'] * 
                                   future_df['monthly_factor']) * 0.3
        
        # Round predictions to integers
        future_df['prediction'] = future_df['prediction'].round().astype(int)
        future_df['prediction'] = future_df['prediction'].clip(lower=0)  # Ensure non-negative
        
        # Get weekday names for display
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Display predictions
        print(f"\n{'*'*50}")
        print(f"Ensemble predictions for the next {days} days:")
        print("\nFuture Predictions:")
        
        for date, row in future_df.iterrows():
            weekday = int(row['weekday'])
            weekday_name = weekday_names[weekday]
            print(f"- {date.date()} ({weekday_name}): {row['prediction']} tweets")
        
        print(f"\nMethod: Ensemble of {len(forecasts)} SARIMA models + Seasonality")
        print(f"{'*'*50}")
        
        return future_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Advanced tweet count predictor')
    parser.add_argument('--file', type=str, default=filename,
                       help='Path to CSV file')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of future days to predict (default: 7)')
    parser.add_argument('--evaluate', action='store_true',
                       help='Evaluate model on historical data')
    parser.add_argument('--optimize', action='store_true',
                       help='Optimize model parameters (time-consuming)')
    parser.add_argument('--plot', action='store_true',
                       help='Generate a forecast plot')
    parser.add_argument('--ensemble', action='store_true',
                       help='Use ensemble of models for prediction')

    args = parser.parse_args()

    try:
        predictor = TweetPredictor()
        predictor.load_data(args.file)
        predictor.calculate_seasonality()
        predictor.calculate_trend_features()
        
        if args.optimize:
            optimal_params = predictor.optimize_sarima_parameters()
            order, seasonal_order = optimal_params
        else:
            # Default parameters that work well for daily time series
            order = (1, 1, 1)
            seasonal_order = (1, 1, 1, 7)
        
        if args.evaluate:
            predictor.evaluate_model()
        
        if args.ensemble:
            future_df = predictor.ensemble_predict(days=args.days)
        else:    
            predictor.train_sarima_model(order=order, seasonal_order=seasonal_order)
            future_df = predictor.predict_future_days(days=args.days)
        
        if args.plot:
            predictor.plot_predictions(future_df)

    except Exception as e:
        import traceback
        print(f"\nError: {str(e)}")
        print(traceback.format_exc())
        print("Please check your input data and parameters")