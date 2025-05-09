#!/usr/bin/env python3
"""
Script to get token IDs for your Polymarket positions.
This extracts token IDs for "Yes" outcomes of markets you hold positions in.
"""

import argparse
import logging
import sys
import os
import json
import requests
from datetime import datetime

from src.polymarket.my_positions.position_tracker import PolymarketPositionTracker
from src.constants import POLYMARKET_API_HOST

def setup_logging(verbose=False):
    """Configure logging"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('TokenIDFetcher')

def get_token_ids_for_positions(verbose=False):
    """Get token IDs for all positions"""
    logger = setup_logging(verbose)
    
    # Initialize position tracker
    logger.info("Initializing position tracker...")
    tracker = PolymarketPositionTracker(log_level=logger.level)
    
    # Get your positions
    logger.info("Fetching your positions...")
    positions = tracker.get_simple_positions()
    
    if not positions:
        logger.warning("No positions found")
        return
    
    logger.info(f"Found {len(positions)} markets with positions")
    
    # For each market, get the token IDs
    results = []
    
    for market_id, outcomes in positions.items():
        market_name = tracker.get_market_name(market_id)
        logger.info(f"Getting token IDs for market: {market_name}")
        
        # Get market details from Polymarket API
        try:
            # Create a requests session for better connection reuse
            session = requests.Session()
            
            # Try multiple API endpoints to get market details
            api_endpoints = [
                f"https://clob.polymarket.com/markets/{market_id}",
                f"{POLYMARKET_API_HOST}/markets/{market_id}",
                f"{POLYMARKET_API_HOST}/v2/markets/{market_id}",
                f"https://gamma-api.polymarket.com/markets/{market_id}"
            ]
            
            market_data = None
            for endpoint in api_endpoints:
                try:
                    logger.debug(f"Trying endpoint: {endpoint}")
                    response = session.get(endpoint)
                    if response.status_code == 200:
                        market_data = response.json()
                        logger.debug(f"Success with endpoint: {endpoint}")
                        break
                except Exception as e:
                    logger.debug(f"Failed with endpoint {endpoint}: {e}")
            
            if not market_data:
                logger.warning(f"Could not fetch market data for {market_id}")
                continue
            
            # Extract token IDs from the "tokens" field which contains objects with token_id and outcome
            token_ids = {}
            
            if 'tokens' in market_data and isinstance(market_data['tokens'], list):
                tokens_array = market_data['tokens']
                for token_obj in tokens_array:
                    if 'token_id' in token_obj and 'outcome' in token_obj:
                        outcome = token_obj['outcome']
                        token_id = token_obj['token_id']
                        token_ids[outcome] = token_id
                        logger.debug(f"Found token ID for outcome {outcome}: {token_id}")
                
                if token_ids:
                    logger.info(f"Successfully extracted {len(token_ids)} token IDs from 'tokens' field")
                else:
                    logger.warning(f"No token IDs found in 'tokens' field")
            else:
                # Alternative extraction methods - try to find outcomes and token IDs in other fields
                logger.debug(f"No 'tokens' field found. Available fields: {', '.join(market_data.keys())}")
                
                # Try alternative field names for outcomes and token IDs
                for field in ['outcomes', 'clobTokenIds', 'tokenIds', 'token_ids']:
                    if field in market_data:
                        logger.debug(f"Found field {field} in market data")
            
            # Collect data
            market_result = {
                "market_id": market_id,
                "market_name": market_name,
                "positions": {},
                "token_ids": token_ids
            }
            
            # Add position details
            for outcome, quantity in outcomes.items():
                position_data = {
                    "quantity": quantity,
                    "token_id": token_ids.get(outcome)
                }
                market_result["positions"][outcome] = position_data
            
            results.append(market_result)
            
            # Output what we found for debugging
            if token_ids:
                logger.info(f"Found {len(token_ids)} token IDs for market {market_name}")
            else:
                logger.warning(f"No token IDs found for market {market_name}")
                if verbose:
                    # Don't dump the full market data anymore since we've identified where the token IDs are
                    if 'tokens' in market_data:
                        logger.debug(f"Tokens field: {json.dumps(market_data['tokens'], indent=2)}")
            
        except Exception as e:
            logger.error(f"Error fetching token IDs for market {market_id}: {str(e)}")
    
    return results

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Get token IDs for your Polymarket positions. These token IDs are required for programmatic trading using the CLOB API.'
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output with detailed API responses')
    parser.add_argument('--output', '-o', type=str, help='Save token IDs to a JSON file for use with trading scripts')
    args = parser.parse_args()
    
    logger = setup_logging(args.verbose)
    
    try:
        results = get_token_ids_for_positions(args.verbose)
        
        if not results:
            logger.warning("No token IDs found for your positions")
            return
        
        # Print results
        print("\nTOKEN IDs FOR YOUR POSITIONS:")
        for market in results:
            print(f"\n{market['market_name']} ({market['market_id']}):")
            for outcome, position in market['positions'].items():
                token_id = position.get('token_id', 'Unknown')
                quantity = position.get('quantity', 0)
                print(f"  {outcome}: {quantity:.6f} shares")
                print(f"    Token ID: {token_id}")
        
        # Save to file if requested
        if args.output:
            output_file = args.output
            try:
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Results saved to {output_file}")
            except Exception as e:
                logger.error(f"Error saving results to file: {e}")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 