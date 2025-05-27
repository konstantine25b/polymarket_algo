# Terminal Logger

A simple utility to capture and log terminal output to files when running commands. This tool preserves the exact terminal output formatting while saving it to a log file.

## Features

- Logs terminal output to timestamped files with exact terminal formatting preserved
- Works with any command, including those with emojis and ANSI color codes
- Supports custom log filenames
- Multiple ways to use: Python module, CLI tool, or bash wrapper

## Usage

There are multiple ways to use the Terminal Logger:

### 1. As a command-line wrapper

```bash
# Run any command with logging
python -m src.terminal_logger.logger "your command here"

# Example with Polymarket scheduler
python -m src.terminal_logger.logger "python -m src.scheduler.scheduler --buy-threshold 1.5 --sell-threshold 0.5 --sell-below 2.0 --min-prediction 7.0 --weighted-selection --tweet-interval 110 --buy-interval 60 --sell-interval 10 --use-csv-getter --get-tweet-count-first --show-positions --show-active-positions --dry-run"
```

### 2. Using the bash wrapper script

```bash
# Make sure the script is executable
chmod +x src/terminal_logger/run_with_log.sh

# Run with the bash wrapper
./src/terminal_logger/run_with_log.sh python -m src.scheduler.scheduler --dry-run
```

### 3. Using the dedicated CLI script

```bash
# Run with the logit module
python -m src.terminal_logger.logit your command here

# Example with custom log filename
python -m src.terminal_logger.logit --logfile my_custom_log.log python -m src.scheduler.scheduler --dry-run
```

### 4. From Python code

```python
from src.terminal_logger import run_with_logging

# Run a command and log its output
run_with_logging("python -m src.scheduler.scheduler --dry-run")

# Use a custom log filename
run_with_logging("python -m src.scheduler.scheduler --dry-run", "scheduler_run.log")
```

### 5. Using the wrapper example (for the scheduler)

For common scheduler commands, you can use the wrapper example that handles the parameters:

```bash
# Run the scheduler with default parameters and logging
python -m src.terminal_logger.wrapper_example --dry-run

# With custom parameters
python -m src.terminal_logger.wrapper_example --buy-threshold 2.0 --min-prediction 10.0 --dry-run
```

## Log File Location

Log files are stored in the `src/terminal_logger/logs/` directory with timestamped filenames by default. Each log file includes:

- Timestamp of execution
- The command that was run
- Complete terminal output with exact formatting
- Return code of the command

## How it Works

The terminal logger uses a simple but effective approach with the Unix `tee` command to capture output exactly as it appears in the terminal. This preserves all formatting, including ANSI color codes, emojis, and other special characters.

## Example

```bash
# Run the scheduler with logging
python -m src.terminal_logger.logger "python -m src.scheduler.scheduler --dry-run"
```

Output will be identical to running the command directly, but will also be saved to a log file.
