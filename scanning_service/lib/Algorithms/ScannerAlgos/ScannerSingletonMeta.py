from abc import ABCMeta

class ScannerSingletonMeta(ABCMeta):
    """
    Metaclass for creating singleton scanner instances based on algorithm type and frequency.
    One instance per unique combination of (algorithm_type, frequency).
    """
    # Create an empty dictionary to store the instances
    _instances = {}

    '''This is to make sure that subcless must implemet these methods. Not using ABC to avoid Metaclass Conflicts '''
    def __init__(cls, name, bases, namespace):
        """Initialize the metaclass"""
        super().__init__(name, bases, namespace)

    # Override the __call__ method to control the creation of instances
    def __call__(cls, algorithm_type, frequency, *args, **kwargs):
        """
        Create or return existing singleton instance for (algorithm_type, frequency) combination.
        
        Args:
            algorithm_type: Type of algorithm (e.g., "udts", "rsi_divergence")
            frequency: Trading frequency (e.g., "5-minute", "10-minute")
            *args, **kwargs: Additional arguments passed to __init__
            
        Returns:
            Singleton instance for the specific algorithm+frequency combination
        """
        # Create unique identifier for this algorithm+frequency combination
        unique_class_identifier = f"{algorithm_type}__{frequency}"

        # Check if the instance already exists in the dictionary
        if unique_class_identifier not in cls._instances:
            # If not, create a new instance and store it in the dictionary
            cls._instances[unique_class_identifier] = super(ScannerSingletonMeta, cls).__call__(algorithm_type, frequency, *args, **kwargs)
            # New singleton scanner instance created
            pass
        else:
            # Returning existing singleton scanner instance
            pass

        # Return the instance for the algorithm+frequency combination
        return cls._instances[unique_class_identifier]

    @classmethod
    def get_active_instances(cls):
        """Get all active singleton instances for debugging/monitoring"""
        return dict(cls._instances)

    @classmethod  
    def clear_instances(cls):
        """Clear all instances - useful for testing"""
        cls._instances.clear()
        # All singleton scanner instances cleared