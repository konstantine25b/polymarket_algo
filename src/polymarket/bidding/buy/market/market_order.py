"""
Market Buy Order implementation for Polymarket.
"""

from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

class MarketBuyOrder:
    """
    Class for creating and executing market buy orders on Polymarket.
    """
    
    def __init__(self, client):
        """
        Initialize the market buy order with a Polymarket client.
        
        Args:
            client: An initialized PolymarketClient instance
        """
        self.client = client
    
    def create_order(self, token_id, amount):
        """
        Create a market buy order.
        
        Args:
            token_id (str): The token ID to buy
            amount (float): The amount to buy
            
        Returns:
            dict: The signed order object
        """
        order_args = MarketOrderArgs(
            token_id=token_id,
            amount=amount,
            side=BUY,
        )
        
        return self.client.client.create_market_order(order_args)
    
    def execute_order(self, token_id, amount):
        """
        Create and execute a market buy order in one step.
        
        Args:
            token_id (str): The token ID to buy
            amount (float): The amount to buy
            
        Returns:
            dict: The response from the order execution
        """
        # Add human-like delay before creating order
        self.client._human_like_delay()
        
        signed_order = self.create_order(token_id, amount)
        
        # Add another small delay before posting order
        self.client._human_like_delay()
        
        response = self.client.client.post_order(signed_order, orderType=OrderType.FOK)
        return response 