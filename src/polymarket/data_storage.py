# src/polymarket/data_storage.py

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional

class DataStorage:
    """Handles storage and retrieval of market data."""
    
    def __init__(self, base_dir: str = "data"):
        """
        Initialize the data storage.
        
        Args:
            base_dir: Base directory for storing data files.
        """
        self.base_dir = base_dir
        # Create the base directory and subdirectories if they don't exist
        os.makedirs(os.path.join(self.base_dir, "json"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "csv"), exist_ok=True)
    
    def _generate_filename(self, event_slug: str, file_format: str) -> str:
        """
        Generate a filename for the data file.
        
        Args:
            event_slug: The event slug from the URL.
            file_format: The file format extension (e.g., 'json', 'csv').
            
        Returns:
            The generated filename.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{event_slug}_{timestamp}.{file_format}"
    
    def save_json(self, event_slug: str, market_data: List[Dict[str, Any]], event_title: str) -> str:
        """
        Save market data as JSON.
        
        Args:
            event_slug: The event slug from the URL.
            market_data: The market data to save.
            event_title: The title of the event.
            
        Returns:
            The path to the saved file.
        """
        if not market_data:
            print("No data to save.")
            return ""
        
        # Create data object
        data_to_save = {
            "event_slug": event_slug,
            "event_title": event_title,
            "timestamp": datetime.now().isoformat(),
            "market_data": market_data
        }
        
        # Generate the filename
        filename = self._generate_filename(event_slug, "json")
        filepath = os.path.join(self.base_dir, "json", filename)
        
        # Save the data
        with open(filepath, 'w') as f:
            json.dump(data_to_save, f, indent=2)
        
        print(f"Data saved to {filepath}")
        return filepath
    
    def save_csv(self, event_slug: str, market_data: List[Dict[str, Any]], event_title: str) -> str:
        """
        Save market data as CSV.
        
        Args:
            event_slug: The event slug from the URL.
            market_data: The market data to save.
            event_title: The title of the event.
            
        Returns:
            The path to the saved file.
        """
        if not market_data:
            print("No data to save.")
            return ""
        
        # Generate the filename
        filename = self._generate_filename(event_slug, "csv")
        filepath = os.path.join(self.base_dir, "csv", filename)
        
        # Extract data for CSV
        csv_data = []
        for item in market_data:
            row = {
                "question": item.get("question", "Unknown"),
                "outcome": item.get("outcome", "Unknown"),
                "token_id": item.get("token_id", ""),
                "price": item.get("price", ""),
                "percentage": item.get("percentage", "")
            }
            csv_data.append(row)
        
        # Save the data
        with open(filepath, 'w', newline='') as f:
            if csv_data:
                fieldnames = csv_data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)
        
        print(f"Data saved to {filepath}")
        return filepath
    
    def load_json(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Load market data from a JSON file.
        
        Args:
            filepath: The path to the JSON file.
            
        Returns:
            The loaded data or None if loading fails.
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading JSON data: {e}")
            return None
    
    def get_latest_data_file(self, event_slug: str, file_format: str = "json") -> Optional[str]:
        """
        Get the path to the latest data file for an event.
        
        Args:
            event_slug: The event slug.
            file_format: The file format to search for.
            
        Returns:
            The path to the latest file or None if no file is found.
        """
        directory = os.path.join(self.base_dir, file_format)
        if not os.path.exists(directory):
            return None
        
        files = [f for f in os.listdir(directory) if f.startswith(event_slug) and f.endswith(f".{file_format}")]
        if not files:
            return None
        
        # Sort by modification time
        files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)
        return os.path.join(directory, files[0])
    
    def list_stored_events(self) -> List[str]:
        """
        List all stored events.
        
        Returns:
            A list of event slugs for which data is stored.
        """
        directory = os.path.join(self.base_dir, "json")
        if not os.path.exists(directory):
            return []
        
        # Extract unique event slugs from filenames
        files = os.listdir(directory)
        event_slugs = set()
        
        for f in files:
            if f.endswith(".json"):
                # Extract the event slug (everything before the first underscore)
                parts = f.split('_')
                if len(parts) > 1:
                    event_slugs.add(parts[0])
        
        return list(event_slugs) 