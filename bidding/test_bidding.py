from src.bidding.bidding_algorithm import BiddingAlgorithm
import json
from typing import Dict, Any

def create_sample_market_data() -> Dict[str, Any]:
    """
    Create sample market data to demonstrate probability calculation.
    This simulates a real Polymarket order book.
    """
    return {
        'markets': [
            {
                'market_id': 'elon_tweets_100-124',
                'question': 'Will Elon tweet 100-124 times this week?',
                'outcome': 'Yes',
                'token_id': 'token123',
                'buy_orders': [
                    {'price': 75, 'size': 100},  # Someone willing to buy at 75 cents
                    {'price': 74, 'size': 50},
                    {'price': 73, 'size': 200}
                ],
                'sell_orders': [
                    {'price': 76, 'size': 150},  # Someone willing to sell at 76 cents
                    {'price': 77, 'size': 100},
                    {'price': 78, 'size': 50}
                ],
                'probability': 0.75  # Market's current probability
            }
        ]
    }

def create_sample_our_probabilities() -> Dict[str, float]:
    """
    Create sample probabilities from our algorithm.
    These are the probabilities we think are correct.
    """
    return {
        'elon_tweets_100-124': 0.80  # We think it's 80% likely
    }

def print_market_details(market: Dict[str, Any], polymarket_prob: float, our_prob: float) -> None:
    """Print details about a market and its probabilities in a clear way."""
    print("\n" + "="*50)
    print(f"MARKET: {market['question']}")
    print("="*50)
    
    print("\nCURRENT ORDERS ON POLYMARKET:")
    print("-"*30)
    print("People wanting to BUY 'Yes':")
    for order in sorted(market['buy_orders'], key=lambda x: x['price'], reverse=True):
        print(f"  • Willing to pay {order['price']}¢ per share for {order['size']} shares")
    
    print("\nPeople wanting to SELL 'Yes':")
    for order in sorted(market['sell_orders'], key=lambda x: x['price']):
        print(f"  • Willing to sell at {order['price']}¢ per share for {order['size']} shares")
    
    print("\nPROBABILITIES:")
    print("-"*30)
    print(f"Polymarket's current probability: {polymarket_prob:.1%}")
    print(f"Our algorithm's probability:     {our_prob:.1%}")
    
    if our_prob > polymarket_prob:
        print(f"\n💡 VALUE BET OPPORTUNITY!")
        print(f"We think it's {our_prob - polymarket_prob:.1%} more likely than the market does!")
    else:
        print("\n❌ No value bet - market probability is higher than ours")

def main():
    # Create sample data for one market
    market_data = create_sample_market_data()
    our_probabilities = create_sample_our_probabilities()
    
    # Initialize the bidding algorithm with $1000 bankroll
    algorithm = BiddingAlgorithm(bankroll=1000)
    
    # Analyze markets
    opportunities = algorithm.analyze_markets(market_data, our_probabilities)
    
    # Print results for the market
    market = market_data['markets'][0]
    market_id = market['market_id']
    polymarket_prob = algorithm._calculate_implied_probability(market)
    our_prob = our_probabilities.get(market_id, 0.0)
    print_market_details(market, polymarket_prob, our_prob)
    
    # Print betting recommendation
    if opportunities:
        print("\nBETTING RECOMMENDATION:")
        print("-"*30)
        opp = opportunities[0]
        print(f"Bet Amount: ${algorithm.bankroll * opp.stake_percentage:.2f}")
        print(f"Percentage of Bankroll: {opp.stake_percentage:.1%}")
        print(f"Expected Value: {opp.value:.1%}")

if __name__ == "__main__":
    main() 