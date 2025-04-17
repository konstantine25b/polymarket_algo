# src/polymarket/order_handler.py

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

class OrderHandler:
    """Class for processing and analyzing Polymarket order book data."""
    
    def __init__(self):
        """Initialize the order handler."""
        pass
    
    def process_order_book(self, order_frames: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process order book data into a more structured format.
        
        Args:
            order_frames: Raw order book data from EventHandler
            
        Returns:
            Processed order book data with calculated metrics
        """
        processed_data = {
            'event_title': order_frames.get('event_title', ''),
            'event_id': order_frames.get('event_id', ''),
            'timestamp': order_frames.get('timestamp', datetime.now().isoformat()),
            'markets': []
        }
        
        # Process each market's order book
        for market_question, market_data in order_frames.get('order_frames', {}).items():
            processed_market = {
                'question': market_question,
                'market_id': market_data.get('market_id', ''),
                'buy_orders': self._process_orders(market_data.get('buy_orders', [])),
                'sell_orders': self._process_orders(market_data.get('sell_orders', [])),
                'metrics': {}
            }
            
            # Calculate metrics for this market
            metrics = self._calculate_order_book_metrics(
                processed_market['buy_orders'],
                processed_market['sell_orders']
            )
            processed_market['metrics'] = metrics
            
            processed_data['markets'].append(processed_market)
        
        return processed_data
    
    def _process_orders(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process and normalize orders.
        
        Args:
            orders: List of raw order data
            
        Returns:
            Processed orders with consistent format
        """
        processed_orders = []
        
        for order in orders:
            processed_order = {
                'price': float(order.get('price', 0)),
                'size': float(order.get('size', 0)),
                'total': float(order.get('price', 0)) * float(order.get('size', 0))
            }
            processed_orders.append(processed_order)
        
        # Sort by price (descending for buy orders, ascending for sell orders)
        processed_orders.sort(key=lambda x: x['price'], reverse=True)
        
        return processed_orders
    
    def _calculate_order_book_metrics(
        self, 
        buy_orders: List[Dict[str, Any]], 
        sell_orders: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate various metrics from order book data.
        
        Args:
            buy_orders: Processed buy orders
            sell_orders: Processed sell orders
            
        Returns:
            Dictionary of calculated metrics
        """
        metrics = {}
        
        # Calculate total volume
        buy_volume = sum(order['size'] for order in buy_orders)
        sell_volume = sum(order['size'] for order in sell_orders)
        metrics['total_volume'] = buy_volume + sell_volume
        
        # Calculate weighted average prices
        if buy_volume > 0:
            metrics['weighted_buy_price'] = sum(order['total'] for order in buy_orders) / buy_volume
        else:
            metrics['weighted_buy_price'] = 0
            
        if sell_volume > 0:
            metrics['weighted_sell_price'] = sum(order['total'] for order in sell_orders) / sell_volume
        else:
            metrics['weighted_sell_price'] = 0
        
        # Calculate market depth (how much money needed to move price by 10%)
        metrics['buy_depth'] = self._calculate_market_depth(buy_orders, 0.1)
        metrics['sell_depth'] = self._calculate_market_depth(sell_orders, 0.1)
        
        # Calculate bid-ask spread
        if buy_orders and sell_orders:
            best_bid = max(order['price'] for order in buy_orders) if buy_orders else 0
            best_ask = min(order['price'] for order in sell_orders) if sell_orders else 1
            metrics['bid_ask_spread'] = best_ask - best_bid
            metrics['bid_ask_spread_percentage'] = (metrics['bid_ask_spread'] / best_ask) * 100 if best_ask > 0 else 0
        else:
            metrics['bid_ask_spread'] = 0
            metrics['bid_ask_spread_percentage'] = 0
        
        # Calculate order book imbalance (buy volume / total volume)
        total_volume = buy_volume + sell_volume
        if total_volume > 0:
            metrics['order_imbalance'] = buy_volume / total_volume
        else:
            metrics['order_imbalance'] = 0.5  # Default to balanced
        
        return metrics
    
    def _calculate_market_depth(self, orders: List[Dict[str, Any]], price_change: float) -> float:
        """
        Calculate market depth (amount needed to move price by given percentage).
        
        Args:
            orders: List of processed orders
            price_change: The price change to measure depth for (e.g., 0.1 for 10%)
            
        Returns:
            The market depth value
        """
        if not orders:
            return 0
            
        # For buy orders, we want the highest price
        # For sell orders, we want the lowest price
        is_buy_orders = orders[0]['price'] >= orders[-1]['price'] if len(orders) > 1 else True
        
        reference_price = orders[0]['price'] if is_buy_orders else orders[-1]['price']
        target_price = reference_price * (1 - price_change) if is_buy_orders else reference_price * (1 + price_change)
        
        cumulative_size = 0
        for order in orders:
            if (is_buy_orders and order['price'] >= target_price) or (not is_buy_orders and order['price'] <= target_price):
                cumulative_size += order['size']
            else:
                break
                
        return cumulative_size
    
    def analyze_probability_changes(
        self, 
        current_data: Dict[str, Any], 
        previous_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze changes in market probabilities between two snapshots.
        
        Args:
            current_data: Current market data
            previous_data: Previous market data for comparison
            
        Returns:
            Analysis of probability changes
        """
        analysis = {
            'event_title': current_data.get('event_title', ''),
            'event_id': current_data.get('event_id', ''),
            'current_timestamp': current_data.get('timestamp', ''),
            'previous_timestamp': previous_data.get('timestamp', '') if previous_data else None,
            'markets': []
        }
        
        # Process current market data
        current_markets = {m.get('question', ''): m for m in current_data.get('markets', [])}
        
        # If we have previous data, prepare it for comparison
        previous_markets = {}
        if previous_data:
            previous_markets = {m.get('question', ''): m for m in previous_data.get('markets', [])}
        
        # Analyze each market
        for question, market in current_markets.items():
            market_analysis = {
                'question': question,
                'market_id': market.get('market_id', ''),
                'current_metrics': market.get('metrics', {}),
                'changes': {}
            }
            
            # If we have previous data for this market, calculate changes
            if question in previous_markets:
                prev_market = previous_markets[question]
                
                # Calculate changes in key metrics
                for metric_key in market.get('metrics', {}):
                    current_value = market['metrics'].get(metric_key, 0)
                    prev_value = prev_market['metrics'].get(metric_key, 0)
                    
                    market_analysis['changes'][metric_key] = {
                        'previous': prev_value,
                        'current': current_value,
                        'absolute_change': current_value - prev_value,
                        'percentage_change': ((current_value - prev_value) / prev_value * 100) if prev_value != 0 else 0
                    }
            
            analysis['markets'].append(market_analysis)
        
        return analysis
    
    def detect_anomalies(self, market_data: Dict[str, Any], threshold: float = 2.0) -> List[Dict[str, Any]]:
        """
        Detect anomalies in market data based on statistical measures.
        
        Args:
            market_data: Processed market data
            threshold: Z-score threshold for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        for market in market_data.get('markets', []):
            market_question = market.get('question', '')
            metrics = market.get('metrics', {})
            
            # Check for anomalies in bid-ask spread
            if 'bid_ask_spread_percentage' in metrics and metrics['bid_ask_spread_percentage'] > 5:  # 5% spread
                anomalies.append({
                    'market': market_question,
                    'type': 'high_spread',
                    'metric': 'bid_ask_spread_percentage',
                    'value': metrics['bid_ask_spread_percentage'],
                    'threshold': 5
                })
            
            # Check for order imbalance
            if 'order_imbalance' in metrics:
                imbalance = metrics['order_imbalance']
                if imbalance > 0.7 or imbalance < 0.3:  # Highly imbalanced
                    anomalies.append({
                        'market': market_question,
                        'type': 'order_imbalance',
                        'metric': 'order_imbalance',
                        'value': imbalance,
                        'threshold': '0.3-0.7 range'
                    })
            
            # Check for unusual market depth
            if 'buy_depth' in metrics and 'sell_depth' in metrics:
                depth_ratio = metrics['buy_depth'] / metrics['sell_depth'] if metrics['sell_depth'] > 0 else float('inf')
                if depth_ratio > 3 or depth_ratio < 0.33:  # Highly imbalanced depth
                    anomalies.append({
                        'market': market_question,
                        'type': 'depth_imbalance',
                        'metric': 'depth_ratio',
                        'value': depth_ratio,
                        'threshold': '0.33-3.0 range'
                    })
        
        return anomalies
    
    def calculate_liquidity_score(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate a liquidity score for each market based on order book metrics.
        
        Args:
            market_data: Processed market data
            
        Returns:
            Dictionary mapping market questions to liquidity scores
        """
        liquidity_scores = {}
        
        for market in market_data.get('markets', []):
            market_question = market.get('question', '')
            metrics = market.get('metrics', {})
            
            # Base score starts at 50
            score = 50
            
            # Add points for higher volume (up to 20 points)
            volume = metrics.get('total_volume', 0)
            volume_score = min(20, volume / 1000)  # 1 point per $1000 up to 20
            score += volume_score
            
            # Subtract points for high spread (up to 20 points)
            spread_pct = metrics.get('bid_ask_spread_percentage', 0)
            spread_penalty = min(20, spread_pct * 4)  # 4 points per 1% spread
            score -= spread_penalty
            
            # Add points for market depth (up to 20 points)
            depth = metrics.get('buy_depth', 0) + metrics.get('sell_depth', 0)
            depth_score = min(20, depth / 500)  # 1 point per $500 up to 20
            score += depth_score
            
            # Add points for balance (up to 10 points)
            imbalance = metrics.get('order_imbalance', 0.5)
            balance_score = 10 - (abs(imbalance - 0.5) * 20)  # 10 points at perfect balance (0.5)
            score += max(0, balance_score)
            
            # Normalize score to 0-100 range
            score = max(0, min(100, score))
            
            liquidity_scores[market_question] = score
        
        return liquidity_scores 