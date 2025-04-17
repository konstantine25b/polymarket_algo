#!/usr/bin/env python3
"""
Main entry point for the Polymarket Tweet Predictor
This allows running the script with: python -m src
"""

import sys
import os

# Add the project root to the path to ensure all imports work correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import and run the tweet predictor
from src.polymarket_predictor.tweet_predictor import main

if __name__ == "__main__":
    main() 