"""
Simulation Bidding Decision Strategy 1

This package provides simulation-based bidding and selling strategies that replicate
the real-world auto bidding functionality but operate on simulated JSON data.
"""

from .simulation_bidder import SimulationBidder
from .simulation_seller import SimulationSeller

__all__ = ['SimulationBidder', 'SimulationSeller'] 