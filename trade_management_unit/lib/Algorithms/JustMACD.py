from trade_management_unit.lib.Indicators.MACD.RealTimeMACD import RealTimeMACD
class JustMACD:
    def __init__(self,*params):
        pass

    def set_algorithm(self,KiteTickerObj):
        KiteTickerObj.set_indicators([RealTimeMACD])
        print("Algorithm Set")
        return KiteTickerObj


