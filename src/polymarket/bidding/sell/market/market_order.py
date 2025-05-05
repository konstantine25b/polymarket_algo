"""
Market Sell Order implementation for Polymarket.
"""

from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import SELL

class MarketSellOrder:
    """
    Class for creating and executing market sell orders on Polymarket.
    """
    
    def __init__(self, client):
        """
        Initialize the market sell order with a Polymarket client.
        
        Args:
            client: An initialized PolymarketClient instance
        """
        self.client = client
    
    def create_order(self, token_id, amount):
        """
        Create a market sell order.
        
        Args:
            token_id (str): The token ID to sell
            amount (float): The amount to sell
            
        Returns:
            dict: The signed order object
        """
        order_args = MarketOrderArgs(
            token_id=token_id,
            amount=amount,
            side=SELL,
        )
        
        return self.client.client.create_market_order(order_args)
    
    def execute_order(self, token_id, amount):
        """
        Create and execute a market sell order in one step.
        
        Args:
            token_id (str): The token ID to sell
            amount (float): The amount to sell
            
        Returns:
            dict: The response from the order execution
        """
        signed_order = self.create_order(token_id, amount)
        response = self.client.client.post_order(signed_order, orderType=OrderType.FOK)
        return response 