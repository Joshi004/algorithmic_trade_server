
import logging
from kiteconnect import KiteConnect
from trade_management_unit.lib.common.EnvFile import EnvFile
import pandas as pd
from trade_management_unit.models.Instrument import Instrument
from django.utils.dateparse import parse_date
from django.db.models import Q
from django.core.paginator import Paginator
from django.core import serializers
import json

class Instruments:
    def __init__(self,params):
        self.env = EnvFile('.env')
        logging.basicConfig(level=logging.DEBUG)
        self.api_key = self.env.read("api_key")
        self.api_secret = self.env.read("api_secret")
        self.access_token = self.env.read("access_token")
        self.kite = KiteConnect(api_key=self.api_key)
        self.kite.set_access_token(self.access_token)

    def fetch_instruments(self, req_params):
        query = Q()
        starts_with_fields = ['trading_symbol', 'name']
        pagination_ordering_params = ['page_no', 'page_length', 'order_by', 'sort_type']

        # Iterate over each parameter in req_params
        for field, value in req_params.items():
            if field not in pagination_ordering_params:
                if field in starts_with_fields:
                    # If the field is in starts_with_fields, use the __startswith lookup
                    query &= Q(**{f'{field}__istartswith': value})
                else:
                    # Otherwise, do an exact match
                    query &= Q(**{f'{field}__iexact': value})

        # Use the constructed Q object to filter the Instrument objects
        instruments = Instrument.objects.filter(query)

        # Get pagination parameters from request
        page_length = int(req_params.get('page_length', '50'))
        page_no = int(req_params.get('page_no', '1'))
        order_by = req_params.get('order_by', 'name')
        sort_type = req_params.get('sort_type', 'asc')

        if sort_type.lower() == 'desc':
            order_by = '-' + order_by
        instruments = instruments.order_by(order_by)
        paginator = Paginator(instruments, page_length)
        page_obj = paginator.get_page(page_no)

        data = json.loads(serializers.serialize('json', page_obj.object_list))
        
        return {
            'data': data,
            'meta': {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
                'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'order_by': order_by,
            }
        }

    def update_instruments(self):     
        print("In update_instruments with params")
        instrument_dump=self.kite.instruments()
        instrument_df = pd.DataFrame(instrument_dump)

        instrument_dict = instrument_df.to_dict('records')

        # Create Instrument instances
        instrument_instances = [
            Instrument(
                instrument_token=instrument['instrument_token'],
                exchange_token=instrument['exchange_token'],
                trading_symbol=instrument['tradingsymbol'],
                name=instrument['name'],
                last_price=instrument['last_price'],
                expiry = parse_date(instrument['expiry']) if isinstance(instrument['expiry'], str) else None,
                strike=instrument['strike'],
                tick_size=instrument['tick_size'],
                lot_size=instrument['lot_size'],
                instrument_type=instrument['instrument_type'],
                segment=instrument['segment'],
                exchange=instrument['exchange']
            )
            for instrument in instrument_dict
        ]
        Instrument.objects.bulk_create(instrument_instances)