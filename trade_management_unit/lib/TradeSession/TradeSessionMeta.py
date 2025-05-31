class TradeSessionMeta(type):
    # Create an empty dictionary to store the instances
    _instances = {}

    '''This is to make sure that subcless must implemet these methods. Not using ABC to avoid Metaclass Conflicts '''
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)


    # Override the __call__ method to control the creation of instances
    def __call__(cls, *args, **kwargs):
        # Get the unique identifier from the arguments
        # args: user_id, scanning_algorithm_id, initiation_algorithm_id, termination_algorithm_id, trading_frequency, is_dummy
        unique_class_identifier = str(args[5]) + "__" + str(args[0]) + "__" + str(args[1]) + "__" + str(args[2]) + "__" + str(args[3]) + "__" + str(args[4])

        # Check if the identifier already exists in the dictionary
        if unique_class_identifier not in cls._instances:
            # If not, create a new instance and store it in the dictionary
            cls._instances[unique_class_identifier] = super(TradeSessionMeta, cls).__call__(*args, **kwargs)

        # Return the instance for the identifier
        return cls._instances[unique_class_identifier]

    def remove_instance(cls, user_id, scanning_algo_id, initiation_algo_id, termination_algo_id, trading_freq, is_dummy):
        unique_class_identifier = str(is_dummy) + "__" + str(user_id) + "__" + str(scanning_algo_id) + "__" + str(initiation_algo_id) + "__" + str(termination_algo_id) + "__" + str(trading_freq)
        if unique_class_identifier in cls._instances:
            del cls._instances[unique_class_identifier]

    def get_working_trade_sessions(cls):
        return cls._instances.values()


