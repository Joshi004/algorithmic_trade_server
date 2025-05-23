class TradeSessionMeta(type):
    # Create an empty dictionary to store the instances
    _instances = {}

    '''This is to make sure that subcless must implemet these methods. Not using ABC to avoid Metaclass Conflicts '''
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)


    # Override the __call__ method to control the creation of instances
    def __call__(cls, *args, **kwargs):
        # Get the symbol from the arguments
        unique_class_identifier = str(args[4]) + "__" + args[0] + "__" + args[1] + "__" + args[2] + "__" + args[3]

        # Check if the symbol already exists in the dictionary
        if unique_class_identifier not in cls._instances:
            # If not, create a new instance and store it in the dictionary
            cls._instances[unique_class_identifier] = super(TradeSessionMeta, cls).__call__(*args, **kwargs)

        # Return the instance for the symbol
        return cls._instances[unique_class_identifier]

    def remove_instance(cls, user_id, scanning_algo_name, tracking_algo_name, trading_freq, dummy):
        unique_class_identifier = str(dummy) + "__" + user_id + "__" + scanning_algo_name + "__" + tracking_algo_name + "__" + trading_freq
        if unique_class_identifier in cls._instances:
            del cls._instances[unique_class_identifier]

    def get_working_trade_sessions(cls):
        return cls._instances.values()


