import os
import sys

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Import and run the scheduler
from src.tweet_collector.tweet_scheduler import TweetScheduler

if __name__ == "__main__":
    print("🚀 Starting Tweet Collection Service...")
    scheduler = TweetScheduler()
    scheduler.run() 