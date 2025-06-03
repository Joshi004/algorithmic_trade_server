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


def convert_redis_stream_data(data: Union[Dict[str, Any], Dict[str, str]], operation: str = 'flatten', separator: str = '_') -> Dict[str, Union[str, Any]]:
    """
    Universal function to convert data between flat and nested formats for Redis streams.
    
    Args:
        data: Data to convert
        operation: 'flatten' to flatten nested data, 'unflatten' to restore nested structure
        separator: Separator for nested keys (default: '_')
        
    Returns:
        Converted data
        
    Raises:
        ValueError: If operation is not 'flatten' or 'unflatten'
        
    Examples:
        >>> nested_data = {"user": {"id": 123}, "status": "active"}
        >>> flat_data = convert_redis_stream_data(nested_data, 'flatten')
        >>> flat_data
        {'user_id': '123', 'status': 'active'}
        
        >>> restored_data = convert_redis_stream_data(flat_data, 'unflatten')
        >>> restored_data
        {'user': {'id': '123'}, 'status': 'active'}
    """
    if operation == 'flatten':
        return flatten_dict(data, separator=separator)
    elif operation == 'unflatten':
        return unflatten_dict(data, separator=separator)
    else:
        raise ValueError(f"Operation must be 'flatten' or 'unflatten', got: {operation}")


def smart_type_conversion(value: str) -> Union[str, int, float, bool, None, list, dict]:
    """
    Smart conversion of string values from Redis back to appropriate Python types.
    Useful when unflattening data that needs type restoration.
    
    Args:
        value: String value from Redis
        
    Returns:
        Converted value with appropriate type
        
    Examples:
        >>> smart_type_conversion('123')
        123
        >>> smart_type_conversion('true')
        True
        >>> smart_type_conversion('null')
        None
        >>> smart_type_conversion('["item1", "item2"]')
        ['item1', 'item2']
    """
    if value == '':
        return None
    
    # Try to parse as JSON first (handles lists, dicts, booleans, null)
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Try to parse as integer
    try:
        return int(value)
    except ValueError:
        pass
    
    # Try to parse as float
    try:
        return float(value)
    except ValueError:
        pass
    
    # Return as string if nothing else works
    return value


def unflatten_dict_with_types(flattened_data: Dict[str, str], separator: str = '_') -> Dict[str, Any]:
    """
    Unflatten data with smart type conversion.
    Combines unflattening with type restoration for better data fidelity.
    
    Args:
        flattened_data: Flattened data from Redis stream
        separator: Separator used for nested keys (default: '_')
        
    Returns:
        Reconstructed nested dictionary with restored types
        
    Examples:
        >>> flattened = {'user_id': '123', 'user_active': 'true', 'metadata': ''}
        >>> unflatten_dict_with_types(flattened)
        {'user': {'id': 123, 'active': True}, 'metadata': None}
    """
    result = {}
    
    for key, value in flattened_data.items():
        # Convert value to appropriate type
        converted_value = smart_type_conversion(value)
        
        if separator in key:
            # Handle nested keys
            parts = key.split(separator)
            current = result
            
            # Navigate/create nested structure
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the final value with type conversion
            current[parts[-1]] = converted_value
        else:
            # Direct key
            result[key] = converted_value
    
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
        with_types: Whether to perform smart type conversion (default: False)
        
    Returns:
        Restored nested data
    """
    if with_types:
        return unflatten_dict_with_types(flattened_data)
    else:
        return unflatten_dict(flattened_data) 