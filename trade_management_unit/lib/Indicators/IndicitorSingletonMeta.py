class IndicitorSingletonMeta(type):
    # Create an empty dictionary to store the instances
    _instances = {}

    '''This is to make sure that subcless must implemet these methods. Not using ABC to avoid Metaclass Conflicts '''
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        if not hasattr(cls, 'update'):
            raise TypeError(f"Class {name} must implement 'update' method")
        if not hasattr(cls, 'append_information'):
            raise TypeError(f"Class {name} must implement 'append_information' method")


    # Override the __call__ method to control the creation of instances
    def __call__(cls, *args, **kwargs):
        # Get the symbol from the arguments
        unique_class_identifier = "Indictor__" + str(args[0])

        # Check if the symbol already exists in the dictionary
        if unique_class_identifier not in cls._instances:
            # If not, create a new instance and store it in the dictionary
            cls._instances[unique_class_identifier] = super(IndicitorSingletonMeta, cls).__call__(*args, **kwargs)

        # Return the instance for the symbol
        return cls._instances[unique_class_identifier]

    def remove_instance(cls, trade_id):
        unique_class_identifier = "Indictor__" + str(trade_id)
        if unique_class_identifier in cls._instances:
            del cls._instances[unique_class_identifier]
