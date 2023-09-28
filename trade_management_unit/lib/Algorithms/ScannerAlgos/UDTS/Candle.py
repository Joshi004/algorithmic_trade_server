class Candle:
    def __init__(self, prop: dict) -> None:
        self.open: float = float(prop["open"])
        self.close: float =float(prop["close"])
        self.high: float = float(prop["high"])
        self.low: float = float(prop["low"])
        self.date: str = prop["date"]
        # Use the ternary operator to set the colour
        self.colour: str = "GREEN" if self.close > self.open else "RED" if self.close < self.open else "WHITE"