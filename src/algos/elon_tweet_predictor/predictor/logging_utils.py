import logging
import os
import sys

# Define log levels with descriptive names
LOG_LEVELS = {
    'SILENT': 100,    # Custom level to disable all output
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'VERBOSE': 5      # Custom level for very detailed output
}

# Global variable to track current verbosity
_current_verbosity = 'INFO'

def setup_logger(name='elon_tweet_predictor', level='INFO', log_file=None, clean_format=False):
    """
    Set up and configure logger
    
    Parameters:
    name (str): Logger name
    level (str): Log level - 'SILENT', 'ERROR', 'WARNING', 'INFO', 'DEBUG', or 'VERBOSE'
    log_file (str): Optional path to log file
    clean_format (bool): If True, use a cleaner output format without timestamps and logger names
    
    Returns:
    logger: Configured logger
    """
    global _current_verbosity
    
    # Validate log level
    if level.upper() not in LOG_LEVELS:
        print(f"Invalid log level: {level}. Using INFO.")
        level = 'INFO'
    
    _current_verbosity = level.upper()
    
    # Add custom log level for VERBOSE if it doesn't exist
    if not hasattr(logging, 'VERBOSE'):
        logging.addLevelName(LOG_LEVELS['VERBOSE'], 'VERBOSE')
        
    # Create logger
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Set level - use 100 for SILENT to effectively disable logging
    if level.upper() == 'SILENT':
        logger.setLevel(LOG_LEVELS['SILENT'])
    else:
        logger.setLevel(LOG_LEVELS[level.upper()])
    
    # Create formatter - standard or clean format
    if clean_format:
        formatter = logging.Formatter('%(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create console handler unless SILENT
    if level.upper() != 'SILENT':
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Create file handler if a log file is specified
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        # Always use detailed format for file logging
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_verbosity():
    """Get the current verbosity level"""
    global _current_verbosity
    return _current_verbosity

def set_verbosity(level):
    """Set the global verbosity level"""
    global _current_verbosity
    _current_verbosity = level.upper()

def verbose_print(message, min_level='INFO'):
    """
    Print message only if current verbosity is at or above min_level
    
    Parameters:
    message (str): Message to print
    min_level (str): Minimum verbosity level required to print
    """
    global _current_verbosity
    if LOG_LEVELS.get(_current_verbosity, 0) <= LOG_LEVELS.get(min_level.upper(), 0):
        return
    print(message) 