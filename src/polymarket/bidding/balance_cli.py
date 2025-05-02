#!/usr/bin/env python
"""
Command-line utility to check wallet balances on Polygon network.
"""

import argparse
import sys
import json
from .wallet import check_wallet_balance

def main():
    """Main entry point for the balance checking CLI."""
    parser = argparse.ArgumentParser(description='Check wallet balance on Polygon network')
    parser.add_argument(
        '--wallet', '-w',
        type=str,
        help='Wallet address to check (defaults to address in .env file)'
    )
    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output in JSON format'
    )
    
    args = parser.parse_args()
    
    try:
        balance_info = check_wallet_balance(args.wallet)
        
        if args.json:
            # JSON output
            print(json.dumps(balance_info, indent=2))
        else:
            # Human-readable output
            print(f"\n{'=' * 50}")
            print(f"WALLET BALANCE: {balance_info['wallet']}")
            print(f"{'=' * 50}")
            print(f"MATIC Balance: {balance_info['matic_balance']:.4f} MATIC")
            print(f"USDC Balance:  {balance_info['usdc_balance']:.2f} USDC")
            
            if not balance_info['success']:
                print(f"\nWARNING: Some balance information may be incomplete or unavailable.")
                if balance_info['error']:
                    print(f"Error: {balance_info['error']}")
            print(f"{'=' * 50}\n")
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 