from trade_management_unit.lib.Algorithms.TrackerAlgos.MACD.JustMACD import JustMACD
from trade_management_unit.lib.Algorithms.TrackerAlgos.SLTO.UdtsSlto import UdtsSlto
class TrackerAlgoFactory:
    def __init__(self):
        pass

    def get_instance(self, traking_algo_name,*params):
        if(traking_algo_name == "just_macd"):
            return JustMACD(params)
        elif(traking_algo_name == "slto__solo"):
            return UdtsSlto(params)
        else:
            raise  ValueError(f"Tracking Algorithm {traking_algo_name} not found")


