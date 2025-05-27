"""
Terminal Logger - A simple utility for logging terminal outputs to files
"""

from .logger import log_terminal_output, run_with_logging, get_log_filename
from .logger import logs_dir

__all__ = ['log_terminal_output', 'run_with_logging', 'get_log_filename', 'logs_dir'] 