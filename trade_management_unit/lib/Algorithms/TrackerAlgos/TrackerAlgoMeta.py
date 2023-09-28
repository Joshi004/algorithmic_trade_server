class TrackerAlgoMeta(type):
    # Create an empty dictionary to store the instances
    _instances = {}

    '''This is to make sure that subcless must implemet these methods. Not using ABC to avoid Metaclass Conflicts '''
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)


    # Override the __call__ method to control the creation of instances
    def __call__(cls, *args, **kwargs):
        # Get the symbol from the arguments
        unique_class_identifier = args[0] + "__" + args[1]

        # Check if the symbol already exists in the dictionary
        if unique_class_identifier not in cls._instances:
            # If not, create a new instance and store it in the dictionary
            cls._instances[unique_class_identifier] = super(TrackerAlgoMeta, cls).__call__(*args, **kwargs)

        # Return the instance for the symbol
        return cls._instances[unique_class_identifier]