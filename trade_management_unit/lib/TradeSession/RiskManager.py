from trade_management_unit.models.DummyAccount import DummyAccount
from trade_management_unit.models.UserConfiguration import UserConfiguration
from trade_management_unit.lib.Portfolio.Portfolio import Portfolio
from  trade_management_unit.Constants.TmuConstants import *
class RiskManager:
    def __init__(self):
        pass

    def get_quantity_and_frictional_losses(self,action,market_price,support_price,resistance_price,user_id,dummy):
        unit_loss_potential =( market_price - support_price) if action == "buy" else (resistance_price-market_price) 
        balance_amount = self.get_balance_amount(user_id,dummy)
        risk_appetite  = self.get_risk_appetite(user_id)
        risk_amount = risk_appetite/100 * balance_amount
        quantity = risk_amount // unit_loss_potential
        
        frictional_losses = self.get_frictional_losses(TRADE_TYPE["intraday"],market_price,quantity,action=="buy")
        while(quantity>0):
             if ((unit_loss_potential*quantity + frictional_losses) < risk_amount):
                 break
             else:
                 quantity -= 1
                 frictional_losses = self.get_frictional_losses(TRADE_TYPE["intraday"],market_price,quantity,action=="buy")
        return quantity,frictional_losses
    
    def get_balance_amount(self, user_id,dummy):
        if dummy:
            return float(DummyAccount.get_attribute(user_id, "current_balance"))
        else:
            return Portfolio().get_available_margin()

    def get_risk_appetite(self,user_id):
        return UserConfiguration.get_attribute(user_id,"risk_appetite")
    

    def get_frictional_losses(self,trade_type,price, quantity, is_buy):
        brokerage = {
            "equity_delivery": 0,
            "equity_intraday": min(20, 0.0003 * price * quantity),
            "equity_futures": min(20, 0.0003 * price * quantity),
            "equity_options": min(20, 0.03 * quantity),
            "currency_futures": min(20, 0.03 * price * quantity),
            "currency_options": min(20, 0.03 * quantity),
            "commodity_futures": min(20, 0.03 * price * quantity),
            "commodity_options": min(20, 0.03 * quantity)
        }

        # Define the other charges for different types of trades and exchanges
        charges = {
            "equity_delivery": {
                "STT": 0.1 * price * quantity / 100,
                "exchange_transaction_charge": 0.00325 * price * quantity / 100,
                "dp_charge": 0 if is_buy else 16,
                "SEBI_charges": price * quantity / 100000000,
                "stamp_duty": (price * quantity * 0.015/100) if is_buy else 0
            },
            "equity_intraday": {
                "STT": 0 if is_buy else 0.025 * price * quantity / 100,
                "exchange_transaction_charge": 0.00325 * price * quantity / 100,
                "dp_charge": 0,
                "SEBI_charges": price * quantity / 100000000,
                "stamp_duty": (price * quantity * 0.003/100) if is_buy else 0
            },
            # ... add the charges for other types of trades and exchanges ...
        }

        charges[trade_type]["GST"] = (brokerage[trade_type] + charges[trade_type]["SEBI_charges"] + charges[trade_type]["exchange_transaction_charge"]) * 18 / 100

        # Calculate the total cost of the trade by adding the buy price, brokerage, and other charges
        total_charges = brokerage[trade_type] + sum(charges[trade_type].values())

        # Print all the components of expenses
        # print("Brokerage: ", brokerage[trade_type])
        # print("STT total: ", charges[trade_type]["STT"])
        # print("Exchange txn charge: ", charges[trade_type]["exchange_transaction_charge"])
        # print("dp_charge : ", charges[trade_type]["dp_charge"])
        # print("GST: ", charges[trade_type]["GST"])
        # print("SEBI charges: ", charges[trade_type]["SEBI_charges"])
        # print("Stamp duty: ", charges[trade_type]["stamp_duty"])

        # Return the total charges
        return total_charges