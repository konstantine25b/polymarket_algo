#!/bin/bash
# Script to run the tweet scheduler as a background service

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the parent directory (src)
SRC_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
# Get the root directory of the project
ROOT_DIR="$( cd "$SRC_DIR/.." && pwd )"

# Change to the root directory
cd "$ROOT_DIR"

# Check if virtual environment exists
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Please create it first."
    echo "Run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if the logs directory exists, create if not
if [ ! -d "$SRC_DIR/logs" ]; then
    mkdir -p "$SRC_DIR/logs"
fi

# Parse command line arguments
INTERVAL=20
MAX_TWEETS=40
QUIET=""
TWEETS_ONLY=""
PREDICTIONS_ONLY=""
RUN_ONCE=""
NO_DEBUG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --max-tweets)
            MAX_TWEETS="$2"
            shift 2
            ;;
        --quiet)
            QUIET="--quiet"
            shift
            ;;
        --tweets-only)
            TWEETS_ONLY="--tweets-only"
            shift
            ;;
        --predictions-only)
            PREDICTIONS_ONLY="--predictions-only"
            shift
            ;;
        --run-once)
            RUN_ONCE="--run-once"
            shift
            ;;
        --no-debug)
            NO_DEBUG="--no-debug"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build the command
CMD="python -m src.scheduler --interval $INTERVAL --max-tweets $MAX_TWEETS $QUIET $TWEETS_ONLY $PREDICTIONS_ONLY $RUN_ONCE $NO_DEBUG"

# Run the scheduler in the background
echo "Starting tweet scheduler with command: $CMD"
nohup $CMD > "$SRC_DIR/logs/scheduler_output.log" 2>&1 &

# Get the process ID
PID=$!
echo "Scheduler started with PID: $PID"
echo $PID > "$SRC_DIR/logs/scheduler.pid"

echo "To stop the scheduler, run: kill $PID"
echo "Or use: kill \$(cat $SRC_DIR/logs/scheduler.pid)"
echo "Logs are available at $SRC_DIR/logs/scheduler.log" 