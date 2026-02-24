import requests
from dotenv import load_dotenv
import os
from eth_account import Account
from src.bidding.wallet import PolymarketWallet

load_dotenv()

POLYMARKET_ADDRESS = "0x434a58D61B426941EE8fe53471828F94583D31e0"
SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/polymarket/polymarket-matic"

def get_positions_value(address: str) -> float:
    query = '''
    query($user: String!) {
      marketPositions(where: { user: $user }) {
        netValue
      }
    }
    '''
    variables = {"user": address.lower()}
    try:
        response = requests.post(SUBGRAPH_URL, json={"query": query, "variables": variables}, timeout=15)
        response.raise_for_status()
        data = response.json()
        positions = data.get("data", {}).get("marketPositions", [])
        total = sum(float(pos.get("netValue", 0)) for pos in positions)
        return total
    except Exception as e:
        print(f"Error fetching positions value: {e}")
        return 0.0

def main():
    print(f"Checking Polymarket portfolio for address: {POLYMARKET_ADDRESS}")
    positions_value = get_positions_value(POLYMARKET_ADDRESS)
    print(f"Total value of open positions: ${positions_value:.2f}")

    print("Getting USDC cash balance...")
    cash = PolymarketWallet.get_portfolio_cash_by_address(POLYMARKET_ADDRESS)
    print(f"USDC cash balance: ${cash:.2f}")

    portfolio_value = positions_value + cash
    print(f"\nPolymarket Portfolio Value (positions + cash): ${portfolio_value:.2f}")

if __name__ == "__main__":
    main()