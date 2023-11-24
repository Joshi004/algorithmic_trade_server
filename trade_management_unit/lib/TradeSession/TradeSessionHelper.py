from trade_management_unit.models.TradeSession import TradeSession
from trade_management_unit.lib.TradeSession.TradeSessionMeta import TradeSessionMeta
from trade_management_unit.lib.TradeSession.TradeSession import TradeSession as TradeSessionLib
from trade_management_unit.lib.Kite.KiteTickhandler import KiteTickhandler
from trade_management_unit.models.Algorithm import Algorithm
from trade_management_unit.lib.Trade.trade import Trade
from trade_management_unit.models.Trade import Trade as TradeModel
from trade_management_unit.Constants.TmuConstants import *
from trade_management_unit.lib.common.Utils.Utils import *


class TradeSessionHelper():
    def __init__(self):
        pass

    def fetch_trade_session_info(self,query_params):
            is_active = query_params.get("is_active")
            session_id = query_params.get("session_id")
            user_id = query_params.get("user_id")
            dummy = query_params.get("dummy")

            if is_active is not None:
                is_active = bool(int(is_active))
            if dummy is not None:
                dummy = bool(int(dummy))

            query = self.get_query(is_active,session_id,user_id,dummy)
                    # Execute the SQL query
            trade_session_objects = TradeSession.objects.raw(query)

            trade_sessions = []
            for session in trade_session_objects:
                trade_sessions.append({
                    "net_profit": session.net_profit,
                    "id": session.id,
                    "started_at": session.started_at,
                    "closed_at": session.closed_at,
                    "dummy": session.dummy,
                    "is_active": session.is_active,
                    "user_id": session.user_id,
                    "trading_frequency": session.trading_frequency,
                    "scanning_algorithm_name": session.scanning_algorithm_name,
                    "tracking_algorithm_name": session.tracking_algorithm_name,
                })

            response = {
                "data": {
                    "trade_sessions": trade_sessions,
                },
                "meta": {
                    "trade_sessions_count": len(trade_sessions)
                }
            }
            return response

    def get_query(self,is_active,session_id,user_id,dummy):
        sql_query = """
        SELECT sum(td.net_profit) as net_profit ,ts.id,ts.started_at,ts.closed_at,ts.dummy,ts.is_active,ts.user_id,ts.trading_frequency, sa.display_name AS scanning_algorithm_name, ta.display_name AS tracking_algorithm_name
        FROM trade_sessions ts
        INNER JOIN algorithms sa ON ts.scanning_algorithm_id = sa.id
        INNER JOIN algorithms ta ON ts.tracking_algorithm_id = ta.id
        LEFT JOIN trades td ON td.trade_session_id = ts.id
        WHERE 1 = 1
        """

    # Add conditions to the SQL query based on the provided filters
        if is_active is not None:
            sql_query += " AND ts.is_active = %s" % int(is_active)
        if session_id is not None:
            sql_query += " AND ts.id = %s" % session_id
        if user_id is not None:
            sql_query += " AND ts.user_id = %s" % user_id
        if dummy is not None:
            sql_query += " AND ts.dummy = %s" % int(dummy)

        sql_query += " GROUP BY ts.id"

        return sql_query

    def resume_trade_session(self,trade_session_id):
        trade_session_instance, ts_db_object = self.__get_trade_session_object__(trade_session_id)
        response = trade_session_instance.track_active_trade_instruments()
        return response


    def are_sessions_active(self, trade_session_ids):
        response = {"data": [], "meta": {"size": 0}}
        for trade_session_id in trade_session_ids:
            ts_object = TradeSession.objects.get(id=trade_session_id)
            status = 'terminated'
            if  ts_object.is_active:
                scanning_algorithm_name = Algorithm.objects.get(id=ts_object.scanning_algorithm_id).name
                tracking_algorithm_name = Algorithm.objects.get(id=ts_object.tracking_algorithm_id).name
                trade_session_status = TradeSessionLib.check_if_session_exists(ts_object.user_id, scanning_algorithm_name, tracking_algorithm_name, ts_object.trading_frequency, ts_object.dummy)
                status = 'active' if trade_session_status else 'paused'
            response["data"].append({"trade_session_id": trade_session_id, "status": status})
        response["meta"]["size"] = len(response["data"])
        return response



    def terminate_trade_session(self,trade_session_id):
        try:
            trade_session_instance, ts_db_object = self.__get_trade_session_object__(trade_session_id)
        except TradeSession.DoesNotExist:
            return {"data":{"trade_session_id":int(trade_session_id)},"meta":{}}
        # Unregister From Scanner Instance
        trade_session_instance.scanning_algo_instance.unregister_trade_session(trade_session_instance)
        self.unregister_from_kite_and_terminate_all_trades(trade_session_instance)
        trade_session_instance.tracking_algo_instance.unregister_trade_session(trade_session_instance)
        # Terminate Trade Session
        self.close_session_object_and_terminate_session(trade_session_instance, ts_db_object)
        return {"data":{"trade_session_id": int(trade_session_id)},"meta":{}}


        # unsubscribe on if there is no active trade with this instrument

    def close_session_object_and_terminate_session(self,trade_session_instance, ts_db_object):
        ts_db_object.is_active = False
        ts_db_object.closed_at = current_ist()
        ts_db_object.save()
        user_id = trade_session_instance.user_id
        scanning_algo_name = trade_session_instance.scanning_algo_name
        tracking_algo_name = trade_session_instance.tracking_algo_name
        trading_freq = trade_session_instance.trading_freq
        dummy = trade_session_instance.dummy
        # Remove the instance
        TradeSessionMeta.remove_instance(TradeSessionMeta, user_id, scanning_algo_name, tracking_algo_name, trading_freq, dummy)


    def unregister_from_kite_and_terminate_all_trades(self, trade_session_instance):
        trade_session_instance.track_active_trade_instruments()
        all_trades = TradeModel.objects.filter(trade_session_id=trade_session_instance.trade_session_id, is_active=True)

        # Get all instrument_ids from the trades
        instrument_ids = [trade.instrument_id for trade in all_trades]
        if(len(instrument_ids) == 0 ):
            return
        #Unregister From KiteTickerHandleer
        trade_session_instance.kite_tick_handler.unregister_trade_session(instrument_ids,trade_session_instance)

        # Generate trading symbols using the token_to_symbol_map
        trading_symbols = [trade_session_instance.token_to_symbol_map[id] for id in instrument_ids]

        # Join the trading symbols with commas
        symbols_string = ','.join(trading_symbols)

        # Call get_quotes API once for all symbols
        quotes = Trade().get_quotes({"symbol": symbols_string, "exchange": DEFAULT_EXCHANGE})

        for trade in all_trades:
            instrument_object = self.get_formated_instrument_object(trade, trade_session_instance, quotes)
            trade_session_instance.tracking_algo_instance.process_tracker_actions(instrument_object, trade_session_instance.trade_session_id, trade_session_instance.user_id, trade_session_instance.dummy)


    def get_formated_instrument_object(self, trade, trade_session_instance, quotes):
        instrument_id = trade.instrument_id
        trading_symbol = trade_session_instance.token_to_symbol_map[instrument_id]
        key = DEFAULT_EXCHANGE+":"+trading_symbol
        quote = quotes["data"][key]  # Get the quote for this symbol


        return {
            "trading_symbol": trading_symbol,
            "instrument_token": instrument_id,
            "trade_freqency": trade_session_instance.trading_freq,
            "required_action": OrderType.BUY if trade.view == "short" else OrderType.SELL,
            "indicator_data": {},
            "market_data": {
                "market_price": quote['last_price'],  # Fill in the market data from the quote
                "last_quantity": quote['last_quantity'],
                "volume": quote['volume'],
            }
        }






    def __get_trade_session_object__(self,trade_session_id):
        kite_tick_handler = KiteTickhandler()
        kit_connect_object = kite_tick_handler.get_kite_ticker_instance()
        kit_connect_object.connect(threaded=True)

        ts_object = TradeSession.objects.get(id=trade_session_id,is_active=True)
        scanning_algorithm_name = Algorithm.objects.get(id=ts_object.scanning_algorithm_id).name
        tracking_algorithm_name = Algorithm.objects.get(id=ts_object.tracking_algorithm_id).name
        trade_session = TradeSessionLib(ts_object.user_id,scanning_algorithm_name,tracking_algorithm_name,ts_object.trading_frequency,ts_object.dummy,kite_tick_handler,kit_connect_object)
        return trade_session,ts_object

