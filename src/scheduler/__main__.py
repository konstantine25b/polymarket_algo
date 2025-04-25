#!/usr/bin/env python3
"""
Entry point for running the scheduler as a module.
Allows running with: python -m src.scheduler
"""

import sys
from .scheduler import main

if __name__ == "__main__":
    sys.exit(main()) 