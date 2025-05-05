import logging
from kiteconnect import KiteConnect
from trade_management_unit.lib.common.EnvFile import EnvFile
from trade_management_unit.lib.Kite.KiteUser import KiteUser
from trade_management_unit.models.Instrument import Instrument
from trade_management_unit.models.Trade import Trade as TradeModel


class Trade:
    def __init__(self, user_id=1):
        logging.basicConfig(level=logging.DEBUG)
        self.user_id = user_id
        self.kite = KiteUser(user_id=user_id).get_instance()

    def validate_params(self, params):
        # Check if 'symbol' and 'exchange' are present in params
        if not all(key in params for key in ('symbol', 'exchange')):
            return {
                'status_code': 400,
                'error_message': 'Both "symbol" and "exchange" must be provided in params.'
            }

        symbols = [symbol.strip().upper() for symbol in params["symbol"].split(',') if symbol.strip()]  # Capitalizing the trading symbols, excluding empty symbols
        exchange = params["exchange"].strip().upper()  # Capitalizing the exchange

        # Check if 'symbols' and 'exchange' are valid fields in the Instrument model
        for symbol in symbols:
            if not Instrument.objects.filter(trading_symbol=symbol, exchange=exchange).exists():
                return {
                    'status_code': 400,
                    'error_message': f'The symbol "{symbol}" does not exist in the "{exchange}" exchange.'
                }

        return symbols, exchange

    def get_quotes(self, params):
        validation_result = self.validate_params(params)
        if isinstance(validation_result, dict):  # If validation failed, return the error message
            return validation_result

        symbols, exchange = validation_result


        instruments = [f"{exchange}:{symbol}" for symbol in symbols]  # Creating a list of instruments in the format accepted by Kite API
        quotes = self.kite.quote(*instruments)  # Fetching quotes for all instruments

        # Prepare the response with 'data' and 'meta'
        response = {
            'data': quotes,
            'meta': {
                'exchange': exchange,
                'data_length': len(quotes)
            }
        }

        return response

    def fetch_all_trades_info(self, trade_session_id):
        sql_query = """
        SELECT
            trades.id AS id, 
            trades.id AS trade_id,
            trades.started_at AS trade_start_time,
            trades.closed_at AS trade_end_time,
            trades.net_profit AS trade_net_profit,
            instruments.id AS instrument_id,
            instruments.name AS instrument_name,
            instruments.trading_symbol AS trading_symbol,
            trades.view AS trade_view,
            trades.max_price AS max_price,
            trades.min_price AS min_price,
            SUM(orders.frictional_losses) AS total_frictional_loss,
            SUM(CASE
                WHEN trades.view = 'long' AND orders.order_type = 'buy' THEN orders.quantity
                WHEN trades.view = 'short' AND orders.order_type = 'sell' THEN orders.quantity
                ELSE 0
            END) AS traded_quantity,
            GROUP_CONCAT(CASE
                WHEN orders.order_type = 'buy' THEN orders.price
                ELSE NULL
            END) AS buy_price,
            GROUP_CONCAT(CASE
                WHEN orders.order_type = 'sell' THEN orders.price
                ELSE NULL
            END) AS sell_price
        FROM trades
        INNER JOIN instruments ON trades.instrument_id = instruments.id
        LEFT JOIN orders ON trades.id = orders.trade_id
        WHERE trades.trade_session_id = %s
        GROUP BY trades.id
        """
        trades = TradeModel.objects.raw(sql_query, [trade_session_id])
        trdes_info = self.__get_formated_trades_info__(trades)
        return trdes_info

    def __get_formated_trades_info__(self,trades):
        trades_info = []
        for trade in trades:
            trade_dict = {
                'trade_id': int(trade.trade_id),
                'trade_start_time': trade.trade_start_time,
                'trade_end_time': trade.trade_end_time,
                'trade_net_profit': float(trade.trade_net_profit) if trade.trade_net_profit else None,
                'instrument' : {
                    'instrument_id': int(trade.instrument_id),
                    'instrument_name': trade.instrument_name,
                    'trading_symbol': trade.trading_symbol,},
                'trade_view': trade.trade_view,
                'max_price': float(trade.max_price) if trade.max_price else None,
                'min_price': float(trade.min_price) if trade.min_price else None,
                'total_frictional_loss': float(trade.total_frictional_loss) if trade.total_frictional_loss else None,
                'traded_quantity': float(trade.traded_quantity),
                'buy_price': float(trade.buy_price) if trade.buy_price else None,
                'sell_price': float(trade.sell_price) if trade.sell_price else None,
            }
            trades_info.append(trade_dict)
        resposne = {'data': trades_info, "meta": {"size": len(trades_info)}}
        return resposne

    def terminate_trades(self,trade_ids):
        pass

        
        

