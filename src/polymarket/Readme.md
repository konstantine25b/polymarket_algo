# Polymarket Data Analyzer

A comprehensive toolkit for fetching, analyzing, and visualizing prediction market data from Polymarket events.

## Overview

This module allows you to:

1. Fetch current market probabilities from any Polymarket event
2. Store the data in structured JSON and CSV formats
3. Generate visualizations of the market probabilities
4. Track and compare changes in market sentiment over time

## File Structure

The analyzer consists of the following components:

- `api_client.py`: Handles communication with Polymarket's APIs (Gamma and CLOB)
- `data_storage.py`: Manages data persistence in JSON and CSV formats
- `visualization.py`: Creates data visualizations using matplotlib
- `main.py`: Orchestrates the workflow and provides a command-line interface
- `__init__.py`: Makes the directory a proper Python package

## How to Run

You can run the Polymarket analyzer in several ways:

### 1. Using the run_analyzer.sh script

The simplest method is to use the provided shell script, which handles environment activation:

```bash
# Make the script executable (one-time setup)
chmod +x run_analyzer.sh

# Run with a specific Polymarket event URL
./run_analyzer.sh --url "https://polymarket.com/event/your-event-slug"

# Compare with previous data for the same event
./run_analyzer.sh --url "https://polymarket.com/event/your-event-slug" --compare

# List all previously stored events
./run_analyzer.sh --list-events
```

### 2. Using Python directly

If you prefer to run Python directly:

```bash
# Activate virtual environment
source venv/bin/activate

# Run with specific Polymarket event URL
python -m src.polymarket.main --url "https://polymarket.com/event/your-event-slug"

# Additional options
python -m src.polymarket.main --url "https://polymarket.com/event/your-event-slug" --no-plot  # Skip plot generation
python -m src.polymarket.main --url "https://polymarket.com/event/your-event-slug" --compare  # Compare with previous data
python -m src.polymarket.main --list-events  # List stored events
python -m src.polymarket.main --output-dir "custom_directory"  # Use custom output directory
```

## Module Details

### API Client (`api_client.py`)

The API client module communicates with Polymarket's APIs:

- **Gamma API**: Fetches event details, market questions, and available outcomes
- **CLOB API**: Fetches current market prices for each outcome

Key functions:

- `extract_slug_from_url()`: Extracts the event identifier from a Polymarket URL
- `get_market_details_from_gamma()`: Retrieves market structure data
- `get_market_prices_from_clob()`: Retrieves current prices for market outcomes
- `get_event_data()`: Combines the above to provide complete market data

### Data Storage (`data_storage.py`)

The data storage module handles persistence of market data:

- Stores data in both JSON and CSV formats
- Creates timestamped files for historical tracking
- Provides methods to retrieve and load historical data

Key functions:

- `save_json()`: Stores complete market data in JSON format
- `save_csv()`: Stores market data in CSV format for easy import into spreadsheets
- `load_json()`: Loads previously saved JSON data
- `get_latest_data_file()`: Finds the most recent data file for an event
- `list_stored_events()`: Lists all events for which data is stored

### Visualization (`visualization.py`)

The visualization module creates graphical representations of market data:

- Generates bar charts of market probabilities
- Creates comparison charts to track changes over time
- Automatically extracts and formats market ranges from questions

Key functions:

- `extract_range_value()`: Parses numeric ranges from market questions
- `sort_by_range()`: Sorts markets by their numeric ranges
- `plot_market_probabilities()`: Creates probability bar charts
- `plot_market_comparison()`: Creates charts comparing current vs. previous data

### Main Script (`main.py`)

The main script provides the command-line interface and workflow orchestration:

- Parses command-line arguments
- Coordinates the workflow between components
- Handles output directory management

Key functions:

- `parse_arguments()`: Processes command-line arguments
- `setup_directories()`: Creates necessary directory structure
- `list_stored_events()`: Lists previously stored events
- `process_event()`: Orchestrates the data fetching, storage, and visualization process

## Output

The analyzer produces the following outputs in the specified output directory (default: "results"):

- **JSON Data**: `{output_dir}/data/json/{event_slug}_{timestamp}.json`
- **CSV Data**: `{output_dir}/data/csv/{event_slug}_{timestamp}.csv`
- **Probability Plot**: `{output_dir}/plots/{event_slug}_probabilities.png`
- **Comparison Plot**: `{output_dir}/plots/{event_slug}_comparison.png` (when using --compare)

## Understanding the Visualization

The visualization shows the probability for each market outcome (only "Yes" outcomes to avoid duplication):

- **X-axis**: The market ranges (e.g., "100-124", "125-149", etc.)
- **Y-axis**: The probability percentage (from 0% to 100%)
- **Labels**: Each bar is labeled with its exact percentage value

For comparison plots:

- **Gray bars**: Previous probabilities
- **Blue bars**: Current probabilities
- **Labels**: Show current percentage and change (e.g., "44.0% (+2.5%)")
- **Color-coding**: Changes are color-coded (black for small changes, green for increases, red for decreases)

## Example Usage

Here's a complete example workflow:

```bash
# First run: Fetch data for an event
./run_analyzer.sh --url "https://polymarket.com/event/elon-musk-of-tweets-april-11-18-628"

# Wait some time for market conditions to change...

# Second run: Fetch updated data and compare with previous
./run_analyzer.sh --url "https://polymarket.com/event/elon-musk-of-tweets-april-11-18-628" --compare

# List all events for which we have data
./run_analyzer.sh --list-events
```

## Troubleshooting

If you encounter issues:

1. Ensure you have the required dependencies installed:

   ```bash
   pip install requests matplotlib py-clob-client>=0.20.0
   ```

2. Verify that the Polymarket URL is correct and accessible

3. Check that you have an active internet connection

4. Ensure the output directory is writable

## Advanced Usage

For programmatic use of the components:

```python
from src.polymarket.api_client import PolymarketAPIClient
from src.polymarket.data_storage import DataStorage
from src.polymarket.visualization import MarketVisualizer

# Fetch data
client = PolymarketAPIClient()
market_data, event_title = client.get_event_data("https://polymarket.com/event/your-event")

# Store data
storage = DataStorage("custom_data_dir")
json_file = storage.save_json("event_slug", market_data, event_title)

# Visualize data
visualizer = MarketVisualizer("custom_plots_dir")
plot_file = visualizer.plot_market_probabilities(market_data, event_title, "event_slug")
```
