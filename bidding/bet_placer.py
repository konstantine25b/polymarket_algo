"""
Bet Placement Tool - Places bets on Polymarket using the bidding algorithm
with direct CLOB API interaction
"""

import argparse
import sys
import os
from typing import Dict, List, Any, Tuple, Optional
from pprint import pprint
from dotenv import load_dotenv
import time

from src.bidding.bidding_algorithm import BiddingAlgorithm
from src.constants import POLYMARKET_ELON_TWEETS_URL, CLOB_API_HOST

# Import Polymarket's py-clob-client
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, BookParams
from py_clob_client.order_builder.constants import BUY, SELL

# Load environment variables
load_dotenv()

class BetPlacer:
    """Tool for placing bets on Polymarket based on the bidding algorithm."""
    
    def __init__(self):
        self.algorithm = BiddingAlgorithm(edge_threshold=0.05, kelly_fraction=0.3)
        self.clob_client = self._connect_to_polymarket()
        
    def _connect_to_polymarket(self) -> Optional[ClobClient]:
        """
        Initialize connection to Polymarket's CLOB API.
        
        Returns:
            ClobClient instance or None if connection fails
        """
        try:
            private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
            if not private_key:
                print("Error: POLYMARKET_PRIVATE_KEY not found in environment variables")
                return None

            # Initialize client
            client = ClobClient(
                host=CLOB_API_HOST,
                key=private_key,
                chain_id=137,  # Polygon network
                signature_type=1  # EIP-712
            )
            
            # Create or derive API credentials (Level 2 authentication)
            try:
                creds = client.create_or_derive_api_creds()
                client.set_api_creds(creds)
                print("Successfully authenticated with Polymarket CLOB API")
            except Exception as e:
                # Continue even if API credential creation fails (read-only might still work)
                print(f"Warning: Could not create API credentials: {e}")
                print("Continuing in limited mode. Order placement may not work.")
                
            return client
        except Exception as e:
            print(f"Error connecting to Polymarket: {e}")
            return None
            
    def get_market_data(self, event_url: str) -> Dict[str, Any]:
        """
        Get market data for a specific event including token IDs and midpoint prices.
        
        Args:
            event_url: URL of the Polymarket event
            
        Returns:
            Dictionary with market data including token IDs and prices
        """
        # First, use the existing algorithm to get market details
        market_details, event_title = self.algorithm.polymarket_client.get_event_data(event_url)
        
        # Extract token_ids and fetch midpoint prices
        if not market_details:
            print("Could not fetch market details")
            return {}
            
        market_data = {}
        for market in market_details:
            question = market.get('question', '')
            token_id = market.get('token_id')
            
            if not token_id:
                continue
                
            # Extract the frame from the question (e.g., "100-124")
            frame = None
            if "less than" in question.lower():
                frame = "less than 100"
            elif "or more" in question.lower():
                frame = "400 or more"
            else:
                # Extract range like "100-124"
                import re
                match = re.search(r'(\d+)[-–](\d+)', question)
                if match:
                    frame = f"{match.group(1)}–{match.group(2)}"
            
            if not frame:
                continue
                
            # Get current midpoint price from CLOB API
            midpoint = None
            try:
                if self.clob_client:
                    # Create BookParams for the token
                    params = [BookParams(token_id=token_id)]
                    
                    # Get midpoint from CLOB API
                    midpoints_response = self.clob_client.get_midpoints(params=params)
                    midpoint_str = midpoints_response.get(token_id)
                    if midpoint_str:
                        midpoint = float(midpoint_str)
            except Exception as e:
                print(f"Error fetching midpoint for {frame}: {e}")
            
            # Fall back to algorithm's price if API call failed
            if midpoint is None:
                for algo_market in market_details:
                    if frame in algo_market.get('question', ''):
                        # Calculate from price if available
                        if "price" in algo_market:
                            midpoint = algo_market["price"]
                        # Or use percentage directly
                        elif "percentage" in algo_market:
                            midpoint = algo_market["percentage"] / 100.0
                
            if midpoint is not None:
                market_data[frame] = {
                    "token_id": token_id,
                    "question": question,
                    "midpoint": midpoint,
                    "probability": midpoint * 100.0  # Convert to percentage
                }
                
        return market_data
        
    def place_bet_via_clob(self, token_id: str, amount: float, price: float, side: str = "buy") -> Dict[str, Any]:
        """
        Place a bet directly via the CLOB API.
        
        Args:
            token_id: The token ID to bet on
            amount: Amount to bet (in USD)
            price: Price to bet at (0-1)
            side: "buy" or "sell"
            
        Returns:
            Dictionary with order details or empty if failed
        """
        if not self.clob_client:
            print("CLOB client not initialized")
            return {}
            
        try:
            # Create OrderArgs
            side_const = BUY if side.lower() == "buy" else SELL
            order_args = OrderArgs(
                token_id=token_id,
                price=str(price),
                size=str(amount),
                side=side_const
            )
            
            # Place the order
            response = self.clob_client.create_order(order_args)
            
            if response and "order_id" in response:
                print(f"Successfully placed {side} order for ${amount:.2f} at {price*100:.2f}%")
                return response
            else:
                print(f"Failed to place order: {response}")
                return {}
                
        except Exception as e:
            print(f"Error placing bet: {e}")
            return {}
        
    def run(self, event_url: str, bankroll: float, max_bet_pct: float = 0.1, 
            dry_run: bool = True, min_edge: float = 5.0):
        """
        Run the bet placer.
        
        Args:
            event_url: URL of the Polymarket event
            bankroll: Amount to allocate for betting (USD)
            max_bet_pct: Maximum percentage of bankroll to bet on a single outcome (0-1)
            dry_run: If True, don't place actual bets (just simulate)
            min_edge: Minimum edge required to place a bet (percentage)
        """
        # First, analyze the market to show opportunities
        print(f"\n{'='*50}")
        print(f" BETTING STRATEGY: ELON MUSK TWEET COUNT ")
        print(f"{'='*50}")
        print(f"Event URL: {event_url}")
        print(f"Bankroll: ${bankroll:.2f}")
        print(f"Max bet per opportunity: {max_bet_pct*100:.1f}% of bankroll (${bankroll * max_bet_pct:.2f})")
        print(f"Minimum edge required: {min_edge:.1f}%")
        print(f"Mode: {'DRY RUN (simulation only)' if dry_run else 'LIVE BETTING'}")
        print(f"{'='*50}\n")
        
        # Display analysis
        self.algorithm.display_analysis(event_url, bankroll)
        
        # Find value bets
        value_bets = self.algorithm.find_value_bets(event_url, bankroll)
        
        if not value_bets:
            print("No value betting opportunities found.")
            return []
        
        # Filter by minimum edge if specified
        if min_edge > 0:
            original_count = len(value_bets)
            value_bets = [bet for bet in value_bets if bet['edge'] >= min_edge]
            if original_count > len(value_bets):
                print(f"\nFiltered out {original_count - len(value_bets)} bets below minimum edge of {min_edge:.1f}%")
        
        if not value_bets:
            print(f"\nNo value bets with edge >= {min_edge:.1f}% found.")
            return []
            
        # Calculate total exposure
        total_bet_amount = sum(bet['recommended_bet'] for bet in value_bets)
        max_total_exposure = min(bankroll, total_bet_amount)
        
        print(f"\n{'='*50}")
        print(f" BETTING PLAN SUMMARY ")
        print(f"{'='*50}")
        print(f"Found {len(value_bets)} value betting opportunities.")
        print(f"Total recommended exposure: ${total_bet_amount:.2f}")
        print(f"Maximum exposure: ${max_total_exposure:.2f}")
        
        # Get market data including token IDs from CLOB API
        market_data = self.get_market_data(event_url)
        
        # Display bet details
        print("\nPlanned bets:")
        for i, bet in enumerate(value_bets, 1):
            frame = bet['frame']
            market_info = market_data.get(frame, {})
            token_id = market_info.get('token_id', 'Unknown')
            
            print(f"\n{i}. {frame}")
            print(f"   Token ID: {token_id}")
            print(f"   Our probability: {bet['our_probability']:.2f}%")
            print(f"   Market probability: {bet['market_probability']:.2f}%")
            print(f"   Edge: +{bet['edge']:.2f}%")
            print(f"   Recommended bet: ${bet['recommended_bet']:.2f}")
        
        if dry_run:
            print("\n[DRY RUN] Simulation complete. No bets were placed.")
            return value_bets
            
        # Confirm with user before placing real bets
        confirmation = input("\nDo you want to place these bets for real? (yes/no): ").strip().lower()
        if confirmation != 'yes':
            print("Bet placement cancelled.")
            return []
            
        # Place actual bets using CLOB API directly
        print("\nPlacing bets...")
        placed_bets = []
        
        for bet in value_bets:
            frame = bet['frame']
            our_prob = bet['our_probability']
            market_prob = bet['market_probability']
            recommended_bet = bet['recommended_bet']
            
            # Get market info
            market_info = market_data.get(frame, {})
            token_id = market_info.get('token_id')
            
            if not token_id:
                print(f"Could not find token ID for frame: {frame}")
                continue
                
            # Calculate actual bet size (capped at max_bet_percentage of bankroll)
            max_bet = bankroll * max_bet_pct
            actual_bet = min(recommended_bet, max_bet, bankroll)
            
            if actual_bet <= 0:
                print(f"Skipping {frame} - bet size too small")
                continue
                
            # Place the bet using CLOB API
            print(f"\nPlacing bet on {frame}:")
            print(f"  Our probability: {our_prob:.2f}%")
            print(f"  Market probability: {market_prob:.2f}%")
            print(f"  Edge: {our_prob - market_prob:+.2f}%")
            print(f"  Bet size: ${actual_bet:.2f}")
            print(f"  Token ID: {token_id}")
            
            # Calculate price (use market probability as price)
            price = market_prob / 100.0
            
            # Place bet using CLOB client
            order = self.place_bet_via_clob(
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
                
                # Update bankroll
                bankroll -= actual_bet
                
                if bankroll <= 0:
                    print("Insufficient bankroll to place more bets.")
                    break
                    
        print(f"\nPlaced {len(placed_bets)} bets successfully.")
        
        if placed_bets:
            print("\nBet details:")
            for i, bet in enumerate(placed_bets, 1):
                print(f"\n{i}. {bet['frame']}")
                print(f"   Amount: ${bet['bet_size']:.2f}")
                print(f"   Price: {bet['price']*100:.2f}%")
                print(f"   Order ID: {bet.get('order_id', 'N/A')}")
        else:
            print("\nNo bets were placed. Check the logs for errors.")
            
        return placed_bets


def main():
    """Main function to run the bet placer."""
    parser = argparse.ArgumentParser(description="Place bets on Polymarket based on algorithmic value betting")
    parser.add_argument("--url", default=POLYMARKET_ELON_TWEETS_URL, help="Polymarket event URL")
    parser.add_argument("--bankroll", type=float, default=100.0, help="Bankroll to allocate (USD)")
    parser.add_argument("--max-bet", type=float, default=0.1, help="Max bet per opportunity (as fraction of bankroll)")
    parser.add_argument("--min-edge", type=float, default=5.0, help="Minimum edge required (percentage)")
    parser.add_argument("--live", action="store_true", help="Place real bets (default is dry run)")
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.bankroll <= 0:
        print("Error: Bankroll must be positive")
        return 1
        
    if args.max_bet <= 0 or args.max_bet > 1:
        print("Error: Max bet must be between 0 and 1")
        return 1
        
    if args.min_edge < 0:
        print("Error: Minimum edge cannot be negative")
        return 1
    
    # Check if we have required environment variables
    if args.live and not os.getenv('POLYMARKET_PRIVATE_KEY'):
        print("Error: POLYMARKET_PRIVATE_KEY must be set in .env file for live betting")
        return 1
    
    # Create and run bet placer
    bet_placer = BetPlacer()
    bet_placer.run(
        event_url=args.url,
        bankroll=args.bankroll,
        max_bet_pct=args.max_bet,
        dry_run=not args.live,
        min_edge=args.min_edge
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 