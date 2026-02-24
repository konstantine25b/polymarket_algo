"""
Simple script to place a small test bet on Polymarket.
This is useful for testing if the betting algorithm and API connection work correctly.
"""

import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from dotenv import load_dotenv
from src.bidding.bet_placer import BetPlacer
from src.constants import POLYMARKET_ELON_TWEETS_URL

# Token IDs for the Elon Musk tweet count market
TOKEN_IDS = {
    "100-124": "62127882564573659696078211379206514569863900554253147022969635995443789126179",
    # Add more token IDs as needed
}

def place_test_bet(token_id: str, price: float):
    """
    Place a small test bet (0.1 USD) on a specific token.
    
    Args:
        token_id: The token ID to bet on
        price: The price to bet at (0-1)
    """
    # Load environment variables
    load_dotenv()
    
    # Check if we have the required private key
    if not os.getenv('POLYMARKET_PRIVATE_KEY'):
        print("Error: POLYMARKET_PRIVATE_KEY must be set in .env file")
        return
        
    # Initialize bet placer
    bet_placer = BetPlacer()
    
    # Place a small test bet
    print(f"\nPlacing test bet:")
    print(f"Token ID: {token_id}")
    print(f"Price: {price*100:.2f}%")
    print(f"Amount: $0.10")
    
    # Place the bet - convert price to string for API
    order = bet_placer.place_bet_via_clob(
        token_id=token_id,
        amount=0.1,  # $0.10 test bet
        price=str(price),  # Convert price to string
        side="buy"
    )
    
    if order:
        print("\nBet placed successfully!")
        print(f"Order ID: {order.get('order_id')}")
    else:
        print("\nFailed to place bet. Check the error messages above.")

if __name__ == "__main__":
    # Example usage
    print("Available frames:")
    for frame in TOKEN_IDS:
        print(f"- {frame}")
    
    frame = input("\nEnter the frame to bet on (e.g., '100-124'): ").strip()
    token_id = TOKEN_IDS.get(frame)
    
    if not token_id:
        print(f"Error: Unknown frame '{frame}'")
        sys.exit(1)
        
    price = float(input("Enter the price (0-1): ").strip())
    
    place_test_bet(token_id, price) 