from ..polymarket_predictor.tweet_predictor import predict_tweet_frame_probabilities
from datetime import datetime, timedelta
import pytz
import pandas as pd

def show_tweet_predictions():
    # Set up the prediction window for the current Polymarket event
    # April 25, 2024, 12:00 ET to May 2, 2024, 12:00 ET
    eastern = pytz.timezone('US/Eastern')
    start = eastern.localize(datetime(2024, 4, 25, 12, 0, 0))
    end = eastern.localize(datetime(2024, 5, 2, 12, 0, 0))

    print(f"Predicting tweet count probabilities for: {start.strftime('%b %d, %Y %H:%M')} to {end.strftime('%b %d, %Y %H:%M')} (ET)")
    
    # Get predicted probabilities for tweet count frames
    probs = predict_tweet_frame_probabilities(start, end)
    
    # Sort and display the probabilities
    sorted_probs = sorted(probs.items(), key=lambda x: -x[1])
    print("\nPredicted probabilities for each tweet count range:")
    for frame, prob in sorted_probs:
        print(f"  {frame:>10}: {prob*100:.2f}%")

    # Load the data and print the first 5 rows
    data_path = 'data/elonmusk_reformatted.csv'
    df = pd.read_csv(data_path)
    print(df.head())  # Shows the first 5 rows

if __name__ == "__main__":
    show_tweet_predictions() 