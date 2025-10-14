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
POLYMARKET_ELON_TWEETS_URL = "https://polymarket.com/event/elon-musk-of-tweets-october-10-october-17?tid=1760465035035"

# Data Paths
DATA_DIR = Path("src/polymarket/data")
PLOTS_DIR = Path("src/polymarket/plots")
PREDICTOR_PLOTS_DIR = Path("src/polymarket_predictor/plots")

# Tweet Predictor Constants
ET_TIMEZONE = pytz.timezone('US/Eastern')
MARKET_ID = "0x3b34b5dbc1f7baf76b9984d9661f70e1c4ef39d60f911205741450086ecceb00"  # NOTE: update when new market_id is known
MARKET_HASH = "elon-musk-of-tweets-october-10-october-17"
EVENT_HASH = "elon-musk-of-tweets-october-10-october-17"
FULL_EVENT_HASH = "elon-musk-of-tweets-october-10-october-17"

# Default data path for tweet analysis
DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    "data", 
    "elonmusk_reformatted.csv"
)

# Polymarket event timeframe (Eastern Time)
POLYMARKET_START_TIME = "2025-10-10 12:00:00"
POLYMARKET_END_TIME = "2025-10-17 12:00:00"
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
    {"name": "<20", "min": 0, "max": 19},
    {"name": "20–39", "min": 20, "max": 39},
    {"name": "40–59", "min": 40, "max": 59},
    {"name": "60–79", "min": 60, "max": 79},
    {"name": "80–99", "min": 80, "max": 99},
    {"name": "100–119", "min": 100, "max": 119},
    {"name": "120–139", "min": 120, "max": 139},
    {"name": "140–159", "min": 140, "max": 159},
    {"name": "160–179", "min": 160, "max": 179},
    {"name": "180–199", "min": 180, "max": 199},
    {"name": "200–219", "min": 200, "max": 219},
    {"name": "220–239", "min": 220, "max": 239},
    {"name": "240–259", "min": 240, "max": 259},
    {"name": "260–279", "min": 260, "max": 279},
    {"name": "280–299", "min": 280, "max": 299},
    {"name": "300–319", "min": 300, "max": 319},
    {"name": "320–339", "min": 320, "max": 339},
    {"name": "340–359", "min": 340, "max": 359},
    {"name": "360–379", "min": 360, "max": 379},
    {"name": "380–399", "min": 380, "max": 399},
    {"name": "400–419", "min": 400, "max": 419},
    {"name": "420–439", "min": 420, "max": 439},
    {"name": "440–459", "min": 440, "max": 459},
    {"name": "460–479", "min": 460, "max": 479},
    {"name": "480–499", "min": 480, "max": 499},
    {"name": "500+", "min": 500, "max": float('inf')}
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