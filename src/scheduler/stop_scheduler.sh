#!/bin/bash
# Script to stop the tweet scheduler background service

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the parent directory (src)
SRC_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# PID file path
PID_FILE="$SRC_DIR/logs/scheduler.pid"

# Check if the PID file exists
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    
    # Check if the process is running
    if ps -p $PID > /dev/null; then
        echo "Stopping tweet scheduler with PID: $PID"
        kill $PID
        
        # Wait for the process to stop
        for i in {1..5}; do
            if ! ps -p $PID > /dev/null; then
                echo "Tweet scheduler stopped successfully."
                rm "$PID_FILE"
                exit 0
            fi
            echo "Waiting for process to stop... ($i/5)"
            sleep 1
        done
        
        # If process is still running, try kill -9
        if ps -p $PID > /dev/null; then
            echo "Forcefully terminating the process..."
            kill -9 $PID
            sleep 1
            if ! ps -p $PID > /dev/null; then
                echo "Tweet scheduler forcefully terminated."
                rm "$PID_FILE"
                exit 0
            else
                echo "Failed to terminate the process. Please check manually."
                exit 1
            fi
        fi
    else
        echo "No running scheduler found with PID: $PID. The process might have already stopped."
        rm "$PID_FILE"
    fi
else
    # Try to find the process by name
    SCHEDULER_PID=$(ps aux | grep "[p]ython -m src.scheduler" | awk '{print $2}')
    
    if [ -n "$SCHEDULER_PID" ]; then
        echo "Found running scheduler with PID: $SCHEDULER_PID"
        echo "Stopping tweet scheduler..."
        kill $SCHEDULER_PID
        
        # Wait for the process to stop
        for i in {1..5}; do
            if ! ps -p $SCHEDULER_PID > /dev/null; then
                echo "Tweet scheduler stopped successfully."
                exit 0
            fi
            echo "Waiting for process to stop... ($i/5)"
            sleep 1
        done
        
        # If process is still running, try kill -9
        if ps -p $SCHEDULER_PID > /dev/null; then
            echo "Forcefully terminating the process..."
            kill -9 $SCHEDULER_PID
            if ! ps -p $SCHEDULER_PID > /dev/null; then
                echo "Tweet scheduler forcefully terminated."
                exit 0
            else
                echo "Failed to terminate the process. Please check manually."
                exit 1
            fi
        fi
    else
        echo "No running scheduler found."
    fi
fi 