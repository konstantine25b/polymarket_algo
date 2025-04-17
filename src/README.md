# LARK Polymarket Algorithmic Analysis

This directory contains algorithms and tools for analyzing Polymarket events, with a focus on predicting Elon Musk's tweeting patterns.

## Directory Structure

- `algos/`: Core prediction algorithms for tweet analysis
  - `basic/`: Basic prediction algorithms
  - `elon_tweet_predictor/`: Specialized prediction for Elon Musk's tweets
- `data/`: Data files used by the prediction algorithms
- `formating_tweet_data/`: Scripts for formatting and cleaning tweet data
- `polymarket/`: API clients and utilities for interacting with Polymarket
- `polymarket_predictor/`: High-level tweet count prediction for Polymarket markets
- `utils/`: Utility functions used across modules

## Key Modules

### Polymarket Tweet Predictor

The `polymarket_predictor` module provides a high-level interface for predicting Elon Musk's tweet counts for Polymarket events. It combines historical tweet pattern analysis, current tweet counts, and Monte Carlo simulation to generate probabilities for each possible bracket.

```bash
# Run with default settings
python -m src.polymarket_predictor.tweet_predictor

# Specify exact tweet count
python -m src.polymarket_predictor.tweet_predictor --exact-count 147

# Verify the current tweet count without running predictions
python -m src.polymarket_predictor.tweet_predictor --verify-count
```

See `src/polymarket_predictor/README.md` for detailed usage instructions.

### Polymarket API Client

The `polymarket` module provides tools for fetching and analyzing data from Polymarket events, including market probabilities, order books, and more.

```bash
# Get current Polymarket odds and timeframes
python -m src.polymarket.main

# Generate visualization plots
python -m src.polymarket.main --generate-plot

# Fetch and display order book data
python -m src.polymarket.main --order-frames
```

See `src/polymarket/Readme.md` for detailed usage instructions.

### Elon Tweet Predictor

The `algos/elon_tweet_predictor` module provides the underlying prediction algorithms used by the high-level Tweet Predictor. It offers more customization options for detailed analysis.

## Usage Examples

### Basic Tweet Prediction

```python
from src.polymarket_predictor import predict_tweet_frame_probabilities

# Get predictions with default settings
probabilities = predict_tweet_frame_probabilities()

# Print probabilities
for frame, probability in probabilities.items():
    print(f"{frame}: {probability:.1f}%")
```

### Fetching Polymarket Data

```python
from src.polymarket.api_client import PolymarketAPIClient

# Get the standard tweet count frames from Polymarket
frames = PolymarketAPIClient.get_tweet_count_frames()
print(frames)

# Get data for a specific Polymarket event
event_url = "https://polymarket.com/event/elon-musk-of-tweets-april-11-18"
market_data, event_title = PolymarketAPIClient.get_event_data(event_url)
```

### Combining Modules

```python
# Get current tweet count
from src.polymarket_predictor import verify_tweet_count
current_count = verify_tweet_count(
    start_date_str="2025-04-11 12:00:00",
    end_date_str="2025-04-17 23:59:59"
)

# Generate predictions based on current count
from src.polymarket_predictor import predict_tweet_frame_probabilities
probabilities = predict_tweet_frame_probabilities(
    current_tweet_count=current_count,
    override_auto_count=True
)

# Get current Polymarket odds for comparison
from src.polymarket.api_client import PolymarketAPIClient
event_url = "https://polymarket.com/event/elon-musk-of-tweets-april-11-18"
market_data, _ = PolymarketAPIClient.get_event_data(event_url)

# Print comparison of our predictions vs market odds
print("Predicted vs Market:")
for market in market_data:
    question = market["question"]
    market_prob = market.get("percentage", 0)
    # Extract the frame from the question
    import re
    frame_match = re.search(r"(\d+–\d+|less than \d+|\d+ or more)", question)
    if frame_match:
        frame = frame_match.group(1)
        our_prob = probabilities.get(frame, 0)
        print(f"{frame}: Our: {our_prob:.1f}% | Market: {market_prob:.1f}%")
```

## Integration with Main Project

This source directory is part of the larger LARK Polymarket Algo project. For full usage instructions and project overview, see the main README.md file in the project root.
