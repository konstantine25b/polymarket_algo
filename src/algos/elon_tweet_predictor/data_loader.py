import pandas as pd
from datetime import datetime

class TweetDataLoader:
    def __init__(self):
        self.df = None
        self.last_date = None
        self.last_time = None
        
    def load_data(self, file_path):
        """Load the tweet data from the reformatted CSV"""
        print(f"\n{'='*50}")
        print(f"Loading data from: {file_path}")
        
        try:
            # Load the data
            self.df = pd.read_csv(file_path)
            
            # Parse the timestamp (format is year:month:day:hour:minute:second)
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
            
            # Get the last available date and time
            self.last_date = self.df['created_at'].max().date()
            self.last_time = self.df['created_at'].max().time()
            
            print(f"Loaded {len(self.df)} tweets")
            print(f"Date range: {self.df['date'].min()} to {self.df['date'].max()}")
            print(f"Last tweet time: {self.last_time}")
            
            return True
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return False 