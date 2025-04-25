import time
from datetime import datetime, timezone, timedelta
import pytz

# Constants - using Eastern Time (ET) for all timezone operations
EDT_TZ = pytz.timezone('US/Eastern')
ET_TZ = pytz.timezone('US/Eastern')  # Main ET timezone reference
# Keep Georgia timezone constant as alias to ET for backward compatibility
GEORGIA_TZ = pytz.timezone('US/Eastern')  # Now also points to US/Eastern

def convert_to_unix_timestamp(timestamp):
    """
    Convert various timestamp formats to unix timestamp (seconds since epoch)
    
    Args:
        timestamp: Can be int, float, string, or datetime object
        
    Returns:
        int: Unix timestamp
    """
    if isinstance(timestamp, (int, float)):
        return int(timestamp)
    
    if isinstance(timestamp, str):
        # Try ISO format first
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except ValueError:
            pass
        
        # Try Twitter format
        try:
            dt = datetime.strptime(timestamp, '%a %b %d %H:%M:%S %z %Y')
            return int(dt.timestamp())
        except ValueError:
            pass
            
        # Try other common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y:%m:%d:%H:%M:%S',
            '%Y/%m/%d %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp, fmt)
                dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
            except ValueError:
                continue
                
        raise ValueError(f"Could not parse timestamp: {timestamp}")
    
    if isinstance(timestamp, datetime):
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return int(timestamp.timestamp())
        
    raise ValueError(f"Unsupported timestamp type: {type(timestamp)}")

def get_current_timestamp():
    """Get current Unix timestamp"""
    return int(time.time())

def get_current_time_edt():
    """Get current time in Eastern timezone (HH:MM:SS AM/PM)"""
    now = datetime.now(ET_TZ)
    return now.strftime("%I:%M:%S %p")

def get_current_time_georgia():
    """Get current time in Eastern timezone (HH:MM:SS) - legacy name kept for compatibility"""
    now = datetime.now(ET_TZ)
    return now.strftime("%H:%M:%S")

def format_timestamp(timestamp, fmt="%Y-%m-%d %I:%M:%S %p", timezone_name="US/Eastern"):
    """
    Format a unix timestamp to a human-readable string
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        fmt: Format string, default includes AM/PM format
        timezone_name: Timezone name (default: US/Eastern for EDT/EST)
        
    Returns:
        str: Formatted timestamp
    """
    tz = pytz.timezone(timezone_name)
    dt = datetime.fromtimestamp(timestamp, tz)
    return dt.strftime(fmt)

def timestamp_to_datetime(timestamp, tz=None):
    """
    Convert unix timestamp to datetime object with specified timezone
    
    Args:
        timestamp: Unix timestamp
        tz: Timezone (default: UTC)
    
    Returns:
        datetime: Datetime object with specified timezone
    """
    if tz is None:
        tz = timezone.utc
    return datetime.fromtimestamp(timestamp, tz)

def format_timestamp_edt(timestamp):
    """
    Format timestamp in EDT with AM/PM
    
    Args:
        timestamp: Unix timestamp
    
    Returns:
        str: EDT timestamp with AM/PM in format YYYY-MM-DD HH:MM:SS AM/PM EDT
    """
    dt = datetime.fromtimestamp(timestamp, ET_TZ)
    formatted = dt.strftime("%Y-%m-%d %I:%M:%S %p EDT")
    return formatted

def is_timestamp_within_range(timestamp, start_time=None, end_time=None):
    """
    Check if a timestamp is within a specified range
    
    Args:
        timestamp: Unix timestamp to check
        start_time: Unix timestamp for start of range (or None for no lower bound)
        end_time: Unix timestamp for end of range (or None for no upper bound)
        
    Returns:
        bool: True if timestamp is within range, False otherwise
    """
    if start_time is not None and timestamp < start_time:
        return False
        
    if end_time is not None and timestamp > end_time:
        return False
        
    return True 