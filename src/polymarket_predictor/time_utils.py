import datetime
import pytz
from typing import Optional

# Import constants from global constants file
from src.constants import ET_TIMEZONE

def get_current_et_time():
    """
    Get the current time in Eastern Time (ET) timezone.
    
    Returns:
        datetime: Current datetime in ET timezone
    """
    return datetime.datetime.now(ET_TIMEZONE)

def convert_to_et(dt):
    """
    Convert a naive datetime to Eastern Time (ET) timezone.
    If the datetime is already timezone-aware, convert it to ET.
    
    Args:
        dt: A datetime object
        
    Returns:
        datetime: The datetime in ET timezone
    """
    if dt.tzinfo is None:
        # Assume it's already in ET if no timezone is specified
        return ET_TIMEZONE.localize(dt)
    else:
        # Convert to ET if it has another timezone
        return dt.astimezone(ET_TIMEZONE)

def parse_timestamp(timestamp_str: str) -> Optional[datetime.datetime]:
    """
    Parse a timestamp string in YYYY:MM:DD:HH:MM:SS format and convert to timezone-aware 
    Eastern Time datetime, carefully handling DST transitions.
    
    Args:
        timestamp_str: Timestamp string in YYYY:MM:DD:HH:MM:SS format
        
    Returns:
        datetime: Timezone-aware datetime object in Eastern Time, or None if parsing fails
    """
    try:
        parts = timestamp_str.split(':')
        if len(parts) != 6:
            print(f"Warning: Invalid timestamp format '{timestamp_str}' - expected YYYY:MM:DD:HH:MM:SS")
            return None
            
        year, month, day, hour, minute, second = map(int, parts)
        
        # Create naive datetime
        naive_dt = datetime.datetime(year, month, day, hour, minute, second)
        
        # Try to localize to Eastern Time, safely handling DST transitions
        try:
            # First attempt with is_dst=None (let pytz figure it out)
            dt = ET_TIMEZONE.localize(naive_dt, is_dst=None)
        except pytz.exceptions.AmbiguousTimeError:
            # During DST "fall back", the hour repeats - default to the first (DST) instance
            print(f"Note: Ambiguous time during DST transition: {naive_dt}. Using DST=True.")
            dt = ET_TIMEZONE.localize(naive_dt, is_dst=True)
        except pytz.exceptions.NonExistentTimeError:
            # During DST "spring forward", there's a missing hour - adjust forward
            print(f"Note: Non-existent time during DST transition: {naive_dt}. Adding 1 hour.")
            dt = ET_TIMEZONE.localize(naive_dt + datetime.timedelta(hours=1))
            
        return dt
        
    except Exception as e:
        print(f"Error parsing timestamp {timestamp_str}: {e}")
        return None 