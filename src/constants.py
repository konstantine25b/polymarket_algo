"""
Global constants for the Polymarket Algo project.
Contains configuration values, API endpoints, and default values.
"""

import os
import pytz
from datetime import datetime
from pathlib import Path

# Polymarket API Endpoints
GAMMA_API_HOST = "https://gamma-api.polymarket.com"
CLOB_API_HOST = "https://clob.polymarket.com"
POLYMARKET_API_HOST = "https://polymarket.com/api"
POLYMARKET_ORDER_BOOK_API = "https://polymarket.com/api/order-books"

# Polymarket Event URLs
# Current Elon Musk tweets event
POLYMARKET_ELON_TWEETS_URL = "https://polymarket.com/event/elon-musk-of-tweets-august-29-september-5?tid=1756647472325"

# Data Paths
DATA_DIR = Path("src/polymarket/data")
PLOTS_DIR = Path("src/polymarket/plots")
PREDICTOR_PLOTS_DIR = Path("src/polymarket_predictor/plots")

# Tweet Predictor Constants
ET_TIMEZONE = pytz.timezone('US/Eastern')
MARKET_ID = "0x3b34b5dbc1f7baf76b9984d9661f70e1c4ef39d60f911205741450086ecceb00"
MARKET_HASH = "will-elon-musk-tweet-over-100-times-august-29-september-05"
EVENT_HASH = "elon-musk-of-tweets-august-29-september-05"
FULL_EVENT_HASH = "elon-musk-of-tweets-august-29-september-05"

# Default data path for tweet analysis
DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    "data", 
    "elonmusk_reformatted.csv"
)

# Polymarket event timeframe (Eastern Time)
POLYMARKET_START_TIME = "2025-08-29 12:00:00"
POLYMARKET_END_TIME = "2025-09-05 12:00:00"
POLYMARKET_TIMEZONE = ET_TIMEZONE

# Define standard tweet count frames used by Polymarket
# TWEET_COUNT_FRAMES = [
#     {"name": "less than 100", "min": 0, "max": 99},
#     {"name": "100–124", "min": 100, "max": 124},
#     {"name": "125–149", "min": 125, "max": 149},
#     {"name": "150–174", "min": 150, "max": 174},
#     {"name": "175–199", "min": 175, "max": 199},
#     {"name": "200–224", "min": 200, "max": 224},
#     {"name": "225–249", "min": 225, "max": 249},
#     {"name": "250–274", "min": 250, "max": 274},
#     {"name": "275–299", "min": 275, "max": 299},
#     {"name": "300–324", "min": 300, "max": 324},
#     {"name": "325–349", "min": 325, "max": 349},
#     {"name": "350–374", "min": 350, "max": 374},
#     {"name": "375–399", "min": 375, "max": 399},
#     {"name": "400 or more", "min": 400, "max": float('inf')}
# ]

TWEET_COUNT_FRAMES = [
    {"name": "<100", "min": 0, "max": 99},
    {"name": "100–114", "min": 100, "max": 114},
    {"name": "115–129", "min": 115, "max": 129},
    {"name": "130–144", "min": 130, "max": 144},
    {"name": "145–159", "min": 145, "max": 159},
    {"name": "160–174", "min": 160, "max": 174},
    {"name": "175–189", "min": 175, "max": 189},
    {"name": "190–204", "min": 190, "max": 204},
    {"name": "205–219", "min": 205, "max": 219},
    {"name": "220–234", "min": 220, "max": 234},
    {"name": "235–249", "min": 235, "max": 249},
    {"name": "250–264", "min": 250, "max": 264},
    {"name": "265–279", "min": 265, "max": 279},
    {"name": "280–294", "min": 280, "max": 294},
    {"name": "295–309", "min": 295, "max": 309},
    {"name": "310–324", "min": 310, "max": 324},
    {"name": "325–339", "min": 325, "max": 339},
    {"name": "340–354", "min": 340, "max": 354},
    {"name": "355–369", "min": 355, "max": 369},
    {"name": "370–384", "min": 370, "max": 384},
    {"name": "385–399", "min": 385, "max": 399},
    {"name": "400+", "min": 400, "max": float('inf')}
]

# Apify Constants
APIFY_TOKEN = "apify_api_e6Vimb3keKr5cNn5Ac6WolYLDJdSYb0DKdym"
APIFY_TWITTER_ACTOR_TASK_ID = "nfp1fpt5gUlBwPcor"  # Using the known working actor directly 

# Tweet Getter Constants
DEFAULT_TWITTER_HANDLE = "elonmusk"
DEFAULT_MAX_TWEETS = 100
DEFAULT_CLI_MAX_TWEETS = 20  # Lower default for command line interface
DEFAULT_TWEETS_CSV_FILE = "src/data/elonmusk_reformatted.csv"
DEFAULT_OUTPUT_DIR = "src/data"
DEFAULT_FORMAT_STYLE = "georgia"  # Options: "georgia" for YYYY:MM:DD:HH:MM:SS, "edt" for EDT with AM/PM

# API Request Parameters
MAX_REQUEST_RETRIES = 5
MAX_EXHAUSTIVE_ATTEMPTS = 3
DEFAULT_TWEET_REQUEST_MULTIPLIER = 3  # For tweetsDesired, resultsLimit, etc.

# Format Templates
GEORGIA_TIMESTAMP_FORMAT = "%Y:%m:%d:%H:%M:%S"
EDT_TIMESTAMP_FORMAT = "%Y-%m-%d %I:%M:%S %p EDT"

# Tweet Fetching Cost Information
TWEET_FETCHING_COST = {
    "40_tweets": 3.2,  # Cost in cents for fetching up to 40 tweets
    "100_tweets": 5.0,  # Cost in cents for fetching up to 100 tweets
    "1000_tweets": 30.0  # Cost in cents for fetching up to 1000 tweets
}

# CSV Header Mapping 
CSV_HEADER_MAP = {
    "id_str": "id",
    "tweet_id": "id",
    "tweet_text": "text",
    "tweet_created_at": "created_at"
} 