"""
Common utilities for the scanning service.
"""
from datetime import datetime
import pytz


def current_ist():
    """
    Get current time in IST (Indian Standard Time) without timezone info.
    
    Returns:
        datetime: Current datetime in IST without timezone information
    """
    ist = pytz.timezone('Asia/Kolkata')
    return get_date_without_time_zone(datetime.now(ist))


def get_date_without_time_zone(date_obj):
    """
    Remove timezone information from a datetime object.
    
    Args:
        date_obj: Datetime object with timezone
        
    Returns:
        datetime: Datetime object without timezone
    """
    date_str = str(date_obj)
    date_str = date_str.split(".")[0]
    return get_date_obj(date_str)


def get_date_obj(date_string):
    """
    Convert date string to datetime object.
    
    Args:
        date_string: Date string in format "%Y-%m-%d %H:%M:%S"
        
    Returns:
        datetime: Parsed datetime object
    """
    date_str = date_string.split("+")[0].split(".")[0]
    date_format = "%Y-%m-%d %H:%M:%S"
    date_object = datetime.strptime(date_str, date_format)
    return date_object 