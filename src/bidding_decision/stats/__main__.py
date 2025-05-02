#!/usr/bin/env python3
"""
Command line interface for the stats module.
"""

import os
import sys
from .comparison import main, initialize_directories

if __name__ == "__main__":
    # Ensure directories exist
    initialize_directories()
    
    # Run the main function
    sys.exit(main()) 