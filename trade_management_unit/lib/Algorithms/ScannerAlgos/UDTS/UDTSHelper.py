from trade_management_unit.models.AlgoUdtsScanRecord import AlgoUdtsScanRecord

class UdtsHelper:
    def __init__(self):
        pass

    def fetch_udts_record_for_trade(self,trade_id):
        try:
            result = AlgoUdtsScanRecord.fetch_udts_record(trade_id)
            data = {
                "trade_id": int(result.trade_id),
                "support_price": float(result.support_price),
                "resistance_price": float(result.resistance_price),
                "support_strength": float(result.support_strength),
                "resistance_strength": float(result.resistance_strength),
                "movement_potential": float(result.movement_potential),
                "movement_potential": result.trade_id,
                "volume": int(result.volume)
                }
            meta = {
                "size":1
            }
        except AlgoUdtsScanRecord.DoesNotExist:
            return {
                "data": None,
                "meta": {"size": 0}
            }
        response = {"data":data,"meta":meta}
        return response

