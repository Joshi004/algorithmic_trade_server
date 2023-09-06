from trade_management_unit.lib.Algorithms.JustMACD import JustMACD
class AlgoFactory:
    def __init__(self):
        pass

    def get_instance(self, name, *params):
        if(name == "just_macd"):
            return JustMACD(params)
        else:
            raise  ValueError(f"Algorithm {name} not found")

