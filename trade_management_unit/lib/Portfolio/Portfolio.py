import logging
from django.core import serializers
import json
from kiteconnect import KiteConnect
from trade_management_unit.lib.common.EnvFile import EnvFile
from trade_management_unit.lib.Kite.KiteUser import KiteUser
from trade_management_unit.models.Instrument import Instrument
from trade_management_unit.models.DummyAccount import DummyAccount
from trade_management_unit.models.Trade import Trade

class Portfolio:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.kite = KiteUser().get_instance()      


    def get_holdings(self, params):
        try:
            holdings = self.kite.holdings()
            response = {"data":holdings, "status":"success"}
        except Exception as e:
            logging.error(e)
            response = {"data":None, "status":"failure", "message":str(e)}
        return response
    
    def get_available_margin(self):
        try:
            margins = self.kite.margins()
            # Below response hirarchy might have issue please checkthe response first
            response = {"data": margins['equity']['available']['live_balance'], "status": "success"}
        except Exception as e:
            logging.error(e)
            response = {"data": None, "status": "failure", "message": str(e)}
        return response

    def get_current_balance_including_margin(self,user_id,dummy):
        used_amrgin = float(Trade.get_total_margin(user_id,dummy))
        if(dummy):
            shown_balance = float(DummyAccount.get_attribute(user_id,"current_balance"))
            current_balance = shown_balance -used_amrgin
            return current_balance
        else:
            shown_balance =  self.get_available_margin()
            current_balance = shown_balance -used_amrgin
            return current_balance


    def get_positions(self, params):
        try:
            positions = self.kite.positions()
            response = {"data":positions, "status":"success"}
        except Exception as e:
            logging.error(e)
            response = {"data":None, "status":"failure", "message":str(e)}
        return response

    def get_orders(self, params):
        try:
            positions = self.kite.orders()
            response = {"data":positions, "status":"success"}
        except Exception as e:
            logging.error(e)
            response = {"data":None, "status":"failure", "message":str(e)}
        return response

    def get_order_trades(self, params):
        try:
            order_id = params["order_id"]
            positions = self.kite.order_trades(order_id)
            response = {"data":positions, "status":"success"}
        except Exception as e:
            logging.error(e)
            response = {"data":None, "status":"failure", "message":str(e)}
        return response

    def get_order_history(self, params):
        try:
            order_id = params["order_id"]
            positions = self.kite.order_history(order_id)
            response = {"data":positions, "status":"success"}
        except Exception as e:
            logging.error(e)
            response = {"data":None, "status":"failure", "message":str(e)}
        return response
    
    def place_order(self, params):
        try:
            # Validate the parameters and raise an exception if any of them is invalid or missing
            self._validate_params(params)

            # Extract the parameters from the input dictionary and convert them to the required types using the _convert_param method
            trading_symbol = self._convert_param(params, "trading_symbol", str)
            exchange = self._convert_param(params, "exchange", str)
            transaction_type = self._convert_param(params, "transaction_type", str)
            order_type = self._convert_param(params, "order_type", str)
            quantity = self._convert_param(params, "quantity", int) # Convert to int
            product = self._convert_param(params, "product", str)
            validity = self._convert_param(params, "validity", str)
            price = self._convert_param(params, "price", float) # Convert to float if not None
            trigger_price = self._convert_param(params, "trigger_price", float) # Convert to float if not None
            disclosed_quantity = self._convert_param(params, "disclosed_quantity", int) # Convert to int if not None
            squareoff = self._convert_param(params, "squareoff", float) # Convert to float if not None
            stoploss = self._convert_param(params, "stoploss", float) # Convert to float if not None
            trailing_stoploss = self._convert_param(params, "trailing_stoploss", float) # Convert to float if not None
            tag = self._convert_param(params, "tag", str)

            # Place the order using the Kite Connect API
            order_id = self.kite.place_order(
                tradingsymbol=trading_symbol,
                exchange=exchange,
                transaction_type=transaction_type,
                order_type=order_type,
                quantity=quantity,
                product=product,
                validity=validity,
                price=price,
                trigger_price=trigger_price,
                disclosed_quantity=disclosed_quantity,
                variety="regular",
                squareoff=squareoff,
                stoploss=stoploss,
                trailing_stoploss=trailing_stoploss,
                tag=tag
            )

            # Return a success response with the order id
            response = {"order_id":order_id, "status":"success"}
        except Exception as e:
            logging.error(e)
            # Return a failure response with the error message
            response = {"data":None, "status":"failure", "message":str(e)}
        return response

    def _validate_params(self, params):
        # Check if the params dictionary is empty or None
        if not params or not isinstance(params, dict):
            raise ValueError("params must be a non-empty dictionary")

        # Check if the trading_symbol parameter is valid
        trading_symbol = params.get("trading_symbol", None)
        if not trading_symbol or not isinstance(trading_symbol, str):
            raise ValueError("trading_symbol must be a non-empty string")

        # Check if the exchange parameter is valid
        exchange = params.get("exchange", None)
        if not exchange or not isinstance(exchange, str):
            raise ValueError("exchange must be a non-empty string")

        # Check if the transaction_type parameter is valid
        transaction_type = params.get("transaction_type", None)
        if not transaction_type or transaction_type not in ["BUY", "SELL"]:
            raise ValueError("transaction_type must be either BUY or SELL")

        # Check if the order_type parameter is valid
        order_type = params.get("order_type", None)
        if not order_type or order_type not in ["MARKET", "LIMIT", "SL", "SL-M"]:
            raise ValueError("order_type must be one of MARKET, LIMIT, SL, SL-M")

        # Check if the quantity parameter is valid and convert it to int type
        quantity = params.get("quantity", None)
        if quantity:
            quantity = int(quantity) # Convert to int
        if not quantity or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")

        # Check if the product parameter is valid
        product = params.get("product", None)
        if not product or product not in ["NRML", "MIS", "CNC", "CO", "BO"]:
            raise ValueError("product must be one of NRML, MIS, CNC, CO, BO")

        # Check if the validity parameter is valid
        validity = params.get("validity", None)
        if not validity or validity not in ["DAY", "IOC", "GTC", "GTD"]:
            raise ValueError("validity must be one of DAY, IOC, GTC, GTD")

        # Check if the price parameter is valid and convert it to float type if not None
        price = params.get("price", None)
        if price:
            price = float(price) # Convert to float
        if order_type == "LIMIT" and (not price or not isinstance(price, (int, float)) or price <= 0):
            raise ValueError("price must be a positive number for LIMIT orders")

        # Check if the trigger_price parameter is valid and convert it to float type if not None
        trigger_price = params.get("trigger_price", None)
        if trigger_price:
            trigger_price = float(trigger_price) # Convert to float
        if order_type in ["SL", "SL-M"] and (not trigger_price or not isinstance(trigger_price, (int, float)) or trigger_price <= 0):
            raise ValueError("trigger_price must be a positive number for SL and SL-M orders")

        # Check if the disclosed_quantity parameter is valid and convert it to int type if not None
        disclosed_quantity = params.get("disclosed_quantity", None)
        if disclosed_quantity:
            disclosed_quantity = int(disclosed_quantity) # Convert to int
        if disclosed_quantity and (not isinstance(disclosed_quantity, int) or disclosed_quantity <= 0 or disclosed_quantity > quantity):
            raise ValueError("disclosed_quantity must be a positive integer less than or equal to quantity")

        # Check if the squareoff parameter is valid and convert it to float type if not None
        squareoff = params.get("squareoff", None)
        if squareoff:
            squareoff = float(squareoff) # Convert to float
        if product == "BO" and (not squareoff or not isinstance(squareoff, (int, float)) or squareoff <= 0):
            raise ValueError("squareoff must be a positive number for BO orders")

        # Check if the stoploss parameter is valid and convert it to float type if not None
        stoploss = params.get("stoploss", None)
        if stoploss:
            stoploss = float(stoploss) # Convert to float
        if product in ["BO", "CO"] and (not stoploss or not isinstance(stoploss, (int, float)) or stoploss <= 0):
            raise ValueError("stoploss must be a positive number for BO and CO orders")

        # Check if the trailing_stoploss parameter is valid and convert it to float type if not None
        trailing_stoploss = params.get("trailing_stoploss", None)
        if trailing_stoploss:
            trailing_stoploss = float(trailing_stoploss) # Convert to float
        if product == "BO" and trailing_stoploss and (not isinstance(trailing_stoploss, (int, float)) or trailing_stoploss <= 0):
            raise ValueError("trailing_stoploss must be a positive number for BO orders")

        # Check if the tag parameter is valid
        tag = params.get("tag", None)
        if tag and (not isinstance(tag, str) or len(tag) > 8):
            raise ValueError("tag must be a string with a maximum length of 8 characters")

    def _convert_param(self, params, key, type):
        """
        This is a private method to check and convert a parameter from the input dictionary to the required type.
        It returns the converted value of the parameter if it is not None, otherwise it returns None.

        Parameters:
        - params: A dictionary containing the parameters for the place_order function.
        - key: The key of the parameter in the dictionary.
        - type: The type to which the parameter should be converted. It can be either int, float, or str.

        For example, self._convert_param(params, "quantity", int) will return the value of params["quantity"] as an int type,
        or None if params["quantity"] is None.
        """
        # Check if the parameter exists in the dictionary and is not None
        value = params.get(key, None)
        if value is not None:
            # Convert the parameter to the required type using the built-in function
            value = type(value)
        
        return value
