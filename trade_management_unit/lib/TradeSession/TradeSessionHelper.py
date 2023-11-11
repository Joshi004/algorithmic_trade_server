from trade_management_unit.models.TradeSession import TradeSession
from trade_management_unit.models.Algorithm import Algorithm
from django.db import connection
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

            query = self.get_query(is_active,session_id,dummy)
                    # Execute the SQL query
            trade_session_objects = TradeSession.objects.raw(query, [user_id])

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

    def get_query(self,is_active,session_id,dummy):
        sql_query = """
        SELECT sum(td.net_profit) as net_profit ,ts.id,ts.started_at,ts.closed_at,ts.dummy,ts.is_active,ts.user_id,ts.trading_frequency, sa.display_name AS scanning_algorithm_name, ta.display_name AS tracking_algorithm_name
        FROM trade_sessions ts
        INNER JOIN algorithms sa ON ts.scanning_algorithm_id = sa.id
        INNER JOIN algorithms ta ON ts.tracking_algorithm_id = ta.id
        LEFT JOIN trades td ON td.trade_session_id = ts.id
        WHERE ts.user_id = %s
        """

    # Add conditions to the SQL query based on the provided filters
        if is_active is not None:
            sql_query += " AND ts.is_active = %s" % int(is_active)
        if session_id is not None:
            sql_query += " AND ts.id = %s" % session_id
        if dummy is not None:
            sql_query += " AND ts.dummy = %s" % int(dummy)

        sql_query += " GROUP BY ts.id"

        return sql_query
