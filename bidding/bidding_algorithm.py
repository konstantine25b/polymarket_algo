"""
Bidding Algorithm for Polymarket

This module implements the bidding algorithm that compares our tweet prediction model's
probabilities with Polymarket's current odds to identify value betting opportunities.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import pytz

# Import our prediction model
from ..polymarket_predictor.tweet_predictor import predict_tweet_frame_probabilities

# Import Polymarket API client for market data
from ..polymarket.api_client import PolymarketAPIClient

@dataclass
class BettingOpportunity:
    """Represents a potential betting opportunity."""
    market_id: str
    question: str
    outcome: str
    token_id: str
    polymarket_probability: float  # Current Polymarket implied probability
    our_probability: float         # Our algorithm's probability
    value: float                   # Difference between our probability and Polymarket's
    stake_percentage: float        # Percentage of bankroll to stake (our probability if value > 0)

class BiddingAlgorithm:
    """
    Core algorithm that compares our prediction model with Polymarket odds
    to find value bets and optimal bet sizes.
    """
    
    def __init__(self, edge_threshold: float = 0.05, kelly_fraction: float = 0.3):
        """
        Initialize the bidding algorithm.
        
        Args:
            edge_threshold: Minimum edge (our prob - market prob) to consider a bet (e.g., 0.05 = 5%)
            kelly_fraction: Fraction of Kelly criterion to use (e.g., 0.3 = 30% of full Kelly)
        """
        self.edge_threshold = edge_threshold
        self.kelly_fraction = kelly_fraction
        self.polymarket_client = PolymarketAPIClient._get_instance()
    
    @staticmethod
    def normalize_frame_name(frame: str) -> str:
        """
        Normalize frame names to ensure consistent matching (en dash, no extra spaces, lowercase).
        """
        if not isinstance(frame, str):
            return frame
        # Replace hyphens with en dashes, strip whitespace, lowercase
        frame = frame.replace("-", "–")
        frame = frame.replace("–", "–")  # Ensure en dash
        frame = frame.strip().lower()
        return frame

    def get_polymarket_probabilities(self, event_url: str) -> Dict[str, float]:
        """
        Fetch current probabilities from Polymarket.
        
        Args:
            event_url: URL of the Polymarket event (e.g., "https://polymarket.com/event/elon-musk-of-tweets-april-25-may-2")
            
        Returns:
            Dictionary mapping outcome frames to probabilities (as percentages)
        """
        print(f"Fetching Polymarket probabilities for {event_url}")
        
        # Extract slug and thread ID
        event_slug = self.polymarket_client.extract_slug_from_url(event_url)
        thread_id = self.polymarket_client.extract_tid_from_url(event_url)
        
        # Fetch market details
        market_details, event_title = self.polymarket_client.get_event_data(event_url)
        
        if not market_details:
            print("Failed to fetch market details from Polymarket")
            return {}
            
        print(f"Retrieved data for: {event_title}")
        
        # Extract probabilities for each outcome
        probabilities = {}
        for market in market_details:
            outcome = market.get("outcome", "")
            
            # Only process outcomes that are tweet count frames
            if "Will Elon tweet" not in market.get("question", ""):
                continue
                
            # Try to get percentage directly
            if "percentage" in market:
                probability = market["percentage"]  # Keep as percentage
            # Or calculate from price
            elif "price" in market:
                probability = market["price"] * 100  # Convert to percentage
            else:
                continue
                
            # Clean up the outcome text to match our frame format
            # e.g., "Yes" for "Will Elon tweet 100-124 times" -> "100-124"
            if outcome.upper() == "YES":
                question = market.get("question", "")
                if "less than" in question.lower():
                    frame = "less than 100"
                elif "or more" in question.lower():
                    frame = "400 or more"
                else:
                    # Extract the range, e.g., "100-124"
                    import re
                    match = re.search(r'(\d+)[-–](\d+)', question)
                    if match:
                        frame = f"{match.group(1)}–{match.group(2)}"
                    else:
                        continue
                    
                # Normalize frame name
                norm_frame = self.normalize_frame_name(frame)
                probabilities[norm_frame] = probability
        
        return probabilities
    
    def get_our_probabilities(self, start_date=None, end_date=None) -> Dict[str, float]:
        """
        Get probabilities from our prediction model.
        
        Args:
            start_date: Start date of the prediction window
            end_date: End date of the prediction window
            
        Returns:
            Dictionary mapping outcome frames to probabilities
        """
        print("Getting probabilities from our prediction model")
        
        # If no dates provided, use current Polymarket timeframe
        if not start_date or not end_date:
            eastern = pytz.timezone('US/Eastern')
            # Use the date range that matches the available tweet data (2025-04-25 to 2025-05-02)
            start_date = eastern.localize(datetime(2025, 4, 25, 12, 0, 0))
            end_date = eastern.localize(datetime(2025, 5, 2, 12, 0, 0))
        
        # Format dates as strings for the predictor
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Get probabilities from our model using keyword arguments
        our_probabilities = predict_tweet_frame_probabilities(
            start_date_str=start_date_str,
            end_date_str=end_date_str
        )
        
        # Normalize frame names in our probabilities
        if our_probabilities:
            norm_probs = {}
            for frame, prob in our_probabilities.items():
                norm_frame = self.normalize_frame_name(frame)
                norm_probs[norm_frame] = prob
            return norm_probs
        return our_probabilities
    
    def find_value_bets(self, event_url: str, bankroll: float = 1000.0) -> List[Dict[str, Any]]:
        """
        Find value betting opportunities by comparing our probabilities with Polymarket's.
        
        Args:
            event_url: URL of the Polymarket event
            bankroll: Available bankroll for betting (in USD)
            
        Returns:
            List of dictionaries with value betting opportunities
        """
        print(f"Finding value bets for {event_url}")
        
        # Get probabilities from both sources
        market_probs = self.get_polymarket_probabilities(event_url)
        our_probs = self.get_our_probabilities()
        
        if not market_probs or not our_probs:
            print("Could not get probabilities from one or both sources")
            return []
            
        # Find value bets (where our probability > market probability)
        value_bets = []
        for frame in our_probs:
            if frame in market_probs:
                our_prob = our_probs[frame]
                market_prob = market_probs[frame]
                edge = our_prob - market_prob
                
                # Only consider bets where we have a significant edge
                if edge > self.edge_threshold:
                    # Calculate Kelly bet size
                    kelly_bet = self._kelly_criterion(our_prob, market_prob, bankroll)
                    
                    value_bets.append({
                        "frame": frame,
                        "our_probability": our_prob,
                        "market_probability": market_prob,
                        "edge": edge,
                        "kelly_bet": kelly_bet,
                        "recommended_bet": kelly_bet * self.kelly_fraction  # Use fraction of Kelly
                    })
        
        # Sort by edge (highest first)
        value_bets.sort(key=lambda x: x["edge"], reverse=True)
        
        return value_bets
    
    def _kelly_criterion(self, our_prob: float, market_prob: float, bankroll: float) -> float:
        """
        Calculate optimal bet size using the Kelly Criterion.
        
        Args:
            our_prob: Our estimated probability (0-1)
            market_prob: Market probability / price (0-1)
            bankroll: Available bankroll
            
        Returns:
            Optimal bet size in USD
        """
        # Calculate b (the odds received, expressed as a decimal)
        # For a $1 bet, we get $(1/market_prob) if we win
        b = (1 / market_prob) - 1
        
        # Calculate f (fraction of bankroll to bet)
        # Kelly formula: f = (bp - q) / b where p is probability of winning, q is probability of losing
        p = our_prob
        q = 1 - p
        
        # Safeguard against negative or invalid results
        if b <= 0 or p <= 0:
            return 0
            
        f = (b * p - q) / b
        
        # Cap the Kelly bet at 50% of bankroll as a safety measure
        f = min(f, 0.5)
        
        # Don't bet if Kelly suggests a negative amount
        if f <= 0:
            return 0
            
        # Return dollar amount
        return f * bankroll
    
    def display_analysis(self, event_url: str, bankroll: float = 1000.0) -> None:
        """
        Display full betting analysis for a given event.
        
        Args:
            event_url: URL of the Polymarket event
            bankroll: Available bankroll for betting
        """
        print("\n========== BIDDING ALGORITHM ANALYSIS ==========\n")
        
        # Get probabilities from both sources
        market_probs = self.get_polymarket_probabilities(event_url)
        our_probs = self.get_our_probabilities()
        
        if not market_probs or not our_probs:
            print("Could not get complete data. Analysis aborted.")
            return
            
        print("\n----- PROBABILITY COMPARISON -----")
        print(f"{'Frame':<15} {'Our Prob':>10} {'Market Prob':>15} {'Edge':>10}")
        print("-" * 55)
        
        # Combine all frames from both sources
        all_frames = set(our_probs.keys()) | set(market_probs.keys())
        
        for frame in sorted(all_frames):
            our_prob = our_probs.get(frame, "N/A")
            market_prob = market_probs.get(frame, "N/A")
            
            # Format probabilities as percentages
            our_prob_str = f"{our_prob:.2f}%" if isinstance(our_prob, (int, float)) else "N/A"
            market_prob_str = f"{market_prob:.2f}%" if isinstance(market_prob, (int, float)) else "N/A"
            
            # Calculate edge if both probabilities are available
            edge_str = "N/A"
            if isinstance(our_prob, (int, float)) and isinstance(market_prob, (int, float)):
                edge = our_prob - market_prob
                edge_str = f"{edge:+.2f}%"
                
            # Print the normalized frame name in original format (capitalize for display)
            display_frame = frame.replace("–", "–").replace("less than", "less than").replace("or more", "or more").title()
            print(f"{display_frame:<15} {our_prob_str:>10} {market_prob_str:>15} {edge_str:>10}")
            
        # Find and display value bets
        value_bets = self.find_value_bets(event_url, bankroll)
        
        if value_bets:
            print("\n----- VALUE BETTING OPPORTUNITIES -----")
            for i, bet in enumerate(value_bets, 1):
                print(f"\nValue Bet #{i}: {bet['frame']}")
                print(f"  Our probability: {bet['our_probability']:.2f}%")
                print(f"  Market probability: {bet['market_probability']:.2f}%")
                print(f"  Edge: {bet['edge']:+.2f}%")
                print(f"  Recommended bet: ${bet['recommended_bet']:.2f}")
        else:
            print("\nNo value betting opportunities identified.")
            
        print("\n===============================================\n")

    def place_value_bets(self, event_url: str, bankroll: float = 1000.0, max_bet_percentage: float = 0.1) -> List[Dict[str, Any]]:
        """
        Place bets on value betting opportunities.
        
        Args:
            event_url: URL of the Polymarket event
            bankroll: Available bankroll for betting
            max_bet_percentage: Maximum percentage of bankroll to bet on a single outcome
            
        Returns:
            List of placed bets with their details
        """
        print("\n========== PLACING VALUE BETS ==========\n")
        
        # Get value betting opportunities
        value_bets = self.find_value_bets(event_url, bankroll)
        
        if not value_bets:
            print("No value betting opportunities found.")
            return []
            
        # Initialize wallet
        try:
            from .wallet import PolymarketWallet
            wallet = PolymarketWallet()
        except Exception as e:
            print(f"Error initializing wallet: {e}")
            return []
            
        # Check wallet balance
        balance = wallet.get_balance()
        print(f"Current wallet balance: ${balance:.2f} USDC")
        
        if balance <= 0:
            print("Insufficient balance to place bets.")
            return []
            
        # Place bets
        placed_bets = []
        for bet in value_bets:
            frame = bet['frame']
            our_prob = bet['our_probability']
            market_prob = bet['market_probability']
            recommended_bet = bet['recommended_bet']
            
            # Calculate actual bet size (capped at max_bet_percentage of bankroll)
            max_bet = bankroll * max_bet_percentage
            actual_bet = min(recommended_bet, max_bet, balance)
            
            if actual_bet <= 0:
                print(f"Skipping {frame} - bet size too small")
                continue
                
            # Get token ID for the frame
            market_details, _ = self.polymarket_client.get_event_data(event_url)
            token_id = None
            
            for market in market_details:
                if frame in market.get('question', ''):
                    token_id = market.get('token_id')
                    break
                    
            if not token_id:
                print(f"Could not find token ID for frame: {frame}")
                continue
                
            # Place the bet
            print(f"\nPlacing bet on {frame}:")
            print(f"  Our probability: {our_prob:.2f}%")
            print(f"  Market probability: {market_prob:.2f}%")
            print(f"  Edge: {our_prob - market_prob:+.2f}%")
            print(f"  Bet size: ${actual_bet:.2f}")
            
            # Calculate price (inverse of market probability)
            price = market_prob / 100.0
            
            # Place the bet
            order = wallet.place_bet(
                token_id=token_id,
                amount=actual_bet,
                price=price,
                side="buy"
            )
            
            if order:
                placed_bets.append({
                    "frame": frame,
                    "token_id": token_id,
                    "bet_size": actual_bet,
                    "price": price,
                    "order_id": order.get("order_id"),
                    "our_probability": our_prob,
                    "market_probability": market_prob
                })
                
                # Update balance
                balance -= actual_bet
                
                if balance <= 0:
                    print("Insufficient balance to place more bets.")
                    break
                    
        print(f"\nPlaced {len(placed_bets)} bets successfully.")
        return placed_bets


def main():
    """
    Main function to demonstrate the bidding algorithm.
    """
    # Create bidding algorithm instance
    bidding_algo = BiddingAlgorithm(edge_threshold=0.05, kelly_fraction=0.3)
    
    # Example Polymarket event URL
    event_url = "https://polymarket.com/event/elon-musk-of-tweets-april-25-may-2?tid=1745668299160"
    
    # Display full analysis
    bidding_algo.display_analysis(event_url, bankroll=1000.0)
    
    
if __name__ == "__main__":
    main() 