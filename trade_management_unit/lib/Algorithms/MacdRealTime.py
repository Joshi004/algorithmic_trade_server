class RealTimeMACD: 
    def __init__(self):
        # Initialize EMAs, MACD line, and Signal line as None
        self.ema12 = None
        self.ema26 = None
        self.__macd_line = None
        self.__signal_line = None

    # Function to calculate EMA
    def calculate_ema(self, previous_ema, close_price, n):
        # If there's no previous EMA, return the close price as the first EMA
        if previous_ema is None:
            return close_price
        else:
            # Calculate the weight multiplier 'k'
            k = 2 / (n + 1)
            # Calculate and return the EMA using the formula:
            # EMA = (Close - Previous EMA) * k + Previous EMA
            return close_price * k + previous_ema * (1 - k)

    # Function to update EMAs, MACD line, and Signal line with each new closing price
    def update(self, close_price):
        # Update 12-period and 26-period EMAs with the new closing price
        self.ema12 = self.calculate_ema(self.ema12, close_price, 12)
        self.ema26 = self.calculate_ema(self.ema26, close_price, 26)

        # Update MACD line by subtracting 26-period EMA from 12-period EMA
        self.__macd_line = self.ema12 - self.ema26

        # Update Signal line as a 9-period EMA of the MACD line
        self.__signal_line = self.calculate_ema(self.__signal_line, self.__macd_line, 9)

    # Getter method for macd_line
    def get_macd_line(self):
        return self.__macd_line

    # Getter method for signal_line
    def get_signal_line(self):
        return self.__signal_line






'''

RealTimeMACD is a class that calculates the MACD in real-time.
calculate_ema is a method that calculates an Exponential Moving Average (EMA) for a given period n.
update is a method that updates the EMAs, MACD line, and Signal line with each new closing price.
macd_calculator is an instance of the RealTimeMACD class.
The for loop at the end simulates receiving new trade ticks data and updating the MACD values accordingly.
Please note that this code assumes that you’re receiving trade ticks data in the form of a list of closing prices (trade_ticks). You’ll need to replace this with your actual data source.

'''