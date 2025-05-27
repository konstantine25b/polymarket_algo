#!/usr/bin/env python
"""
Simple command-line utility to run a command with terminal logging
"""
import sys
import os
import argparse
from .logger import log_terminal_output, get_log_filename, logs_dir

def main():
    parser = argparse.ArgumentParser(description="Run a command and log its output")
    parser.add_argument('command', nargs='+', help='Command to execute and log')
    parser.add_argument('--logfile', '-o', help='Custom log filename (optional)')
    
    args = parser.parse_args()
    
    # Join command parts back into a string
    command = ' '.join(args.command)
    
    # Print logging information
    log_filename = args.logfile if args.logfile else get_log_filename()
    print("📝 Logging terminal output to: {0}".format(os.path.join(logs_dir, log_filename)))
    
    # Run the command with logging
    return_code = log_terminal_output(command, args.logfile)
    
    # Exit with the same return code as the command
    sys.exit(return_code)

if __name__ == "__main__":
    main() 