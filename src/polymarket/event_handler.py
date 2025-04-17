import json
import csv
import os
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import time

class EventHandler:
    """Handler for Polymarket event data."""
    
    def __init__(self, data_dir: Union[str, Path] = "data"):
        """
        Initialize the event handler.
        
        Args:
            data_dir: Directory for storing event data
        """
        self.data_dir = Path(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
    
    def extract_event_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract the event ID from a Polymarket URL.
        
        Args:
            url: The Polymarket event URL
            
        Returns:
            The event ID or None if not found
        """
        # Extract event ID from the tid parameter
        tid_match = re.search(r'tid=(\d+)', url)
        if tid_match:
            return tid_match.group(1)
        
        # Try to extract from the path if there's no tid parameter
        path_match = re.search(r'/event/([^/\?]+)', url)
        if path_match:
            return path_match.group(1)
        
        return None
    
    def fetch_event_data(self, url: str) -> Dict[str, Any]:
        """
        Fetch event data from Polymarket API.
        
        Args:
            url: The Polymarket event URL
            
        Returns:
            The event data as a dictionary
        """
        event_id = self.extract_event_id_from_url(url)
        if not event_id:
            raise ValueError(f"Could not extract event ID from URL: {url}")
        
        # Construct API URL
        api_url = f"https://polymarket.com/api/events/{event_id}"
        
        # Make the API request
        response = requests.get(api_url)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to fetch event data: {response.status_code}")
        
        # Parse JSON response
        data = response.json()
        if 'data' not in data:
            raise ValueError(f"Unexpected API response structure: {data}")
        
        return data['data']
    
    def fetch_order_frames(self, url: str) -> Dict[str, Any]:
        """
        Fetch order frames (orderbook) data for a Polymarket event.
        
        Args:
            url: The Polymarket event URL
            
        Returns:
            Dictionary containing buy and sell orders
        """
        event_id = self.extract_event_id_from_url(url)
        if not event_id:
            raise ValueError(f"Could not extract event ID from URL: {url}")
        
        # First, get the event data to extract the market IDs
        event_data = self.fetch_event_data(url)
        
        order_frames = {}
        
        # Process each market in the event
        for market in event_data.get('markets', []):
            market_id = market.get('id')
            market_question = market.get('question')
            
            if not market_id:
                continue
                
            # Construct the order book API URL
            api_url = f"https://strapi-matic.poly.market/order-books?marketId={market_id}"
            
            # Make the API request with a retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.get(api_url)
                    if response.status_code == 200:
                        order_data = response.json()
                        
                        # Add this market's order data to the collection
                        order_frames[market_question] = {
                            'market_id': market_id,
                            'buy_orders': order_data.get('buyOrders', []),
                            'sell_orders': order_data.get('sellOrders', [])
                        }
                        break
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Wait before retrying
                    else:
                        print(f"Failed to fetch order book for market {market_id}: {e}")
        
        return {
            'event_title': event_data.get('title', ''),
            'event_id': event_id,
            'timestamp': datetime.now().isoformat(),
            'order_frames': order_frames
        }
    
    def process_event_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw event data into a more usable format.
        
        Args:
            data: The raw event data from the API
            
        Returns:
            Processed event data
        """
        processed_data = {
            'event_id': data.get('id', ''),
            'title': data.get('title', ''),
            'slug': data.get('slug', ''),
            'description': data.get('description', ''),
            'markets': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Process each market in the event
        for market in data.get('markets', []):
            market_data = {
                'id': market.get('id', ''),
                'question': market.get('question', ''),
                'outcomes': []
            }
            
            # Get probabilities for each outcome
            for outcome in market.get('outcomes', []):
                outcome_data = {
                    'id': outcome.get('id', ''),
                    'value': outcome.get('value', ''),
                    'probability': float(outcome.get('probability', 0))
                }
                market_data['outcomes'].append(outcome_data)
            
            processed_data['markets'].append(market_data)
        
        return processed_data
    
    def save_event_data(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Save event data to JSON and CSV files.
        
        Args:
            data: The processed event data
            filename: Optional filename to use (default: event_slug_timestamp)
            
        Returns:
            The path to the saved JSON file
        """
        # Generate filename if not provided
        if not filename:
            event_slug = data.get('slug', 'event')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{event_slug}_{timestamp}"
        
        # Create paths for JSON and CSV files
        json_path = self.data_dir / f"{filename}.json"
        csv_path = self.data_dir / f"{filename}.csv"
        
        # Save JSON file
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Create flattened data for CSV
        csv_data = []
        for market in data.get('markets', []):
            market_id = market.get('id', '')
            question = market.get('question', '')
            
            for outcome in market.get('outcomes', []):
                csv_data.append({
                    'event_id': data.get('event_id', ''),
                    'event_title': data.get('title', ''),
                    'market_id': market_id,
                    'question': question,
                    'outcome_id': outcome.get('id', ''),
                    'outcome_value': outcome.get('value', ''),
                    'probability': outcome.get('probability', 0),
                    'timestamp': data.get('timestamp', '')
                })
        
        # Save CSV file
        if csv_data:
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
                writer.writeheader()
                writer.writerows(csv_data)
        
        return str(json_path)
    
    def load_event_data(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        Load event data from a saved JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            The loaded event data
        """
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def find_latest_event_data(self, event_slug: str) -> Optional[str]:
        """
        Find the most recent data file for a given event slug.
        
        Args:
            event_slug: The event slug to search for
            
        Returns:
            Path to the most recent data file or None if not found
        """
        # Find all matching files
        pattern = f"{event_slug}_*.json"
        matching_files = list(self.data_dir.glob(pattern))
        
        if not matching_files:
            return None
        
        # Sort by modification time (most recent first)
        matching_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        return str(matching_files[0])
    
    def list_stored_events(self) -> List[Dict[str, Any]]:
        """
        List all events that have data stored.
        
        Returns:
            List of dictionaries with event info
        """
        events = []
        seen_events = set()
        
        # Find all JSON files in the data directory
        json_files = list(self.data_dir.glob("*.json"))
        
        for file_path in json_files:
            try:
                # Load the file to extract event information
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                event_id = data.get('event_id')
                if event_id and event_id not in seen_events:
                    seen_events.add(event_id)
                    
                    # Get file modification time
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    events.append({
                        'event_id': event_id,
                        'title': data.get('title', 'Unknown'),
                        'slug': data.get('slug', ''),
                        'file_count': 1,
                        'latest_file': str(file_path),
                        'last_updated': mod_time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                elif event_id:
                    # Increment file count for this event
                    for event in events:
                        if event['event_id'] == event_id:
                            event['file_count'] += 1
                            
                            # Update last_updated if this file is newer
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            event_time = datetime.strptime(event['last_updated'], '%Y-%m-%d %H:%M:%S')
                            
                            if file_time > event_time:
                                event['last_updated'] = file_time.strftime('%Y-%m-%d %H:%M:%S')
                                event['latest_file'] = str(file_path)
                            
                            break
                            
            except (json.JSONDecodeError, IOError) as e:
                # Skip invalid files
                print(f"Error processing {file_path}: {e}")
                continue
        
        # Sort by last_updated (most recent first)
        events.sort(key=lambda x: x['last_updated'], reverse=True)
        
        return events 