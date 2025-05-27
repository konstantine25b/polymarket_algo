#!/usr/bin/env python
import os
import sys
import datetime
import subprocess
import tempfile

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

def get_log_filename():
    """Generate a timestamped log filename"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return "terminal_log_{0}.log".format(timestamp)

def log_terminal_output(command, log_filename=None):
    """
    Execute a terminal command and log its output to a file in real-time.
    Uses the script command which gives the exact terminal output.
    
    Args:
        command (str): The command to execute
        log_filename (str, optional): Custom log filename. If None, a timestamped name is used.
        
    Returns:
        int: Return code of the command
    """
    if log_filename is None:
        log_filename = get_log_filename()
    
    log_path = os.path.join(logs_dir, log_filename)
    
    # Create the log file with header
    with open(log_path, 'w') as log_file:
        log_file.write("=== Command executed at {0} ===\n".format(datetime.datetime.now()))
        log_file.write("Command: {0}\n".format(command))
        log_file.write("="*50 + "\n\n")
    
    # Print information about logging
    print("📝 Logging terminal output to: {0}".format(log_path))
    
    # We use a simple bash script to:
    # 1. Run the actual command
    # 2. Capture all output to the log file
    # 3. Display the same output to the terminal
    bash_script = """
    # Run the command while capturing output
    {0} 2>&1 | tee -a "{1}"
    # Store the exit code from the command
    exit_code=${{PIPESTATUS[0]}}
    exit $exit_code
    """.format(command, log_path)
    
    # Run the bash script
    return_code = subprocess.call(['bash', '-c', bash_script])
    
    # Write the footer with return code
    with open(log_path, 'a') as log_file:
        log_file.write("\n" + "="*50 + "\n")
        log_file.write("Command completed with return code: {0}\n".format(return_code))
    
    return return_code

def run_with_logging(command, log_filename=None):
    """
    Simple wrapper function to run a command with logging
    """
    return log_terminal_output(command, log_filename)

if __name__ == "__main__":
    # If script is run directly, use the first argument as the command to execute
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        log_terminal_output(command)
    else:
        print("Usage: python -m src.terminal_logger.logger 'your command here'")
        sys.exit(1) 