from pathlib import Path
import os

def get_data_path(filename: str) -> Path:
    """
    Get the absolute path to a data file, handling both development and production environments.
    """
    # Get the project root directory (where the src folder is located)
    project_root = Path(__file__).parent.parent.parent
    
    # Define possible data directory paths
    data_dirs = [
        project_root / 'data',         # /path/to/project/data
        project_root / 'src' / 'data'  # /path/to/project/src/data
    ]
    
    # Check each possible location
    for data_dir in data_dirs:
        file_path = data_dir / filename
        if file_path.exists():
            return file_path
    
    # If the file doesn't exist in any location, default to the project root data directory
    # Create data directory if it doesn't exist
    default_data_dir = data_dirs[0]
    default_data_dir.mkdir(exist_ok=True)
    
    # Return the full path to the requested file
    return default_data_dir / filename 