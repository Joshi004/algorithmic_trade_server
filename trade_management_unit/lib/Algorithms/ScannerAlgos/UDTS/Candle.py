class Candle:
    def __init__(self, prop: dict) -> None:
        self.open: float = prop["Open"]
        self.close: float = prop["Close"]
        self.high: float = prop["High"]
        self.low: float = prop["Low"]
        self.date: str = prop["Date"]
        # Use the ternary operator to set the colour
        self.colour: str = "green" if self.close > self.open else "red" if self.close < self.open else "white"