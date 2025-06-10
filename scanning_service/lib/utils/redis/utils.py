"""
Redis Data Utilities for flattening and unflattening data structures.
Centralized utility functions for Redis stream data operations used across all services.
"""
import json
from typing import Dict, Any, Union


def flatten_dict(data: Dict[str, Any], parent_key: str = '', separator: str = '_') -> Dict[str, str]:
    """
    Flatten nested dictionary for Redis stream format.
    Redis streams require flat key-value pairs.
    
    Args:
        data: Dictionary to flatten
        parent_key: Parent key for nested items
        separator: Separator for nested keys (default: '_')
        
    Returns:
        Flattened dictionary with string values
        
    Examples:
        >>> data = {"user": {"id": 123, "name": "John"}, "status": "active"}
        >>> flatten_dict(data)
        {'user_id': '123', 'user_name': 'John', 'status': 'active'}
        
        >>> data = {"config": {"settings": {"debug": True}}}
        >>> flatten_dict(data)
        {'config_settings_debug': 'True'}
    """
    items = []
    
    for key, value in data.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        
        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            items.extend(flatten_dict(value, new_key, separator).items())
        elif isinstance(value, (list, tuple)):
            # Convert lists/tuples to JSON strings
            items.append((new_key, json.dumps(value)))
        elif value is None:
            # Convert None to empty string
            items.append((new_key, ''))
        else:
            # Convert everything else to string
            items.append((new_key, str(value)))
    
    return dict(items)


def unflatten_dict(flattened_data: Dict[str, str], separator: str = '_') -> Dict[str, Any]:
    """
    Convert flattened Redis stream data back to nested structure.
    
    Args:
        flattened_data: Flattened data from Redis stream
        separator: Separator used for nested keys (default: '_')
        
    Returns:
        Reconstructed nested dictionary
        
    Examples:
        >>> flattened = {'user_id': '123', 'user_name': 'John', 'status': 'active'}
        >>> unflatten_dict(flattened)
        {'user': {'id': '123', 'name': 'John'}, 'status': 'active'}
        
        >>> flattened = {'config_settings_debug': 'True'}
        >>> unflatten_dict(flattened)
        {'config': {'settings': {'debug': 'True'}}}
    """
    result = {}
    
    for key, value in flattened_data.items():
        if separator in key:
            # Handle nested keys (e.g., "algorithm_config_scanning_algorithm_id")
            parts = key.split(separator)
            current = result
            
            # Navigate/create nested structure
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the final value
            current[parts[-1]] = value
        else:
            # Direct key
            result[key] = value
    
    return result





# Convenience functions for specific use cases
def prepare_for_redis_stream(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Prepare data for Redis stream publishing.
    Alias for flatten_dict with standard separator.
    
    Args:
        data: Data to prepare for Redis stream
        
    Returns:
        Flattened data ready for Redis stream
    """
    return flatten_dict(data)


def restore_from_redis_stream(flattened_data: Dict[str, str], with_types: bool = False) -> Dict[str, Any]:
    """
    Restore data from Redis stream format.
    
    Args:
        flattened_data: Flattened data from Redis stream
        with_types: Whether to perform smart type conversion (default: False - currently ignored)
        
    Returns:
        Restored nested data
    """
    # Type conversion functionality removed - always use basic unflatten
    return unflatten_dict(flattened_data) 