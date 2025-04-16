#!/bin/bash

# Run Polymarket Data Analyzer
# This script activates the virtual environment and runs the analyzer

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run the analyzer with all arguments passed to this script
python -m src.polymarket.main "$@"

# Example usage:
# ./run_analyzer.sh --url "https://polymarket.com/event/elon-musk-of-tweets-april-11-18-628" --compare
# ./run_analyzer.sh --list-events 