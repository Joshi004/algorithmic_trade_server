import logging
import requests
from django.conf import settings
import pandas as pd
from trade_management_unit.models.Instrument import Instrument
from django.utils.dateparse import parse_date
from django.db.models import Q
from django.core.paginator import Paginator
from django.core import serializers
from django.db import transaction
from django.db import connection
import json


class Instruments:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.integration_service_url = getattr(settings, 'INTEGRATION_SERVICE_URL', 'http://localhost:8000/integration')
        self.headers = {
            'X-Internal-Service-Token': getattr(settings, 'INTERNAL_SERVICE_TOKEN', 'internal-service-secret-token-change-in-production')
        }

    def fetch_instruments(self, req_params):
        query = Q()
        starts_with_fields = ['trading_symbol', 'name']
        pagination_ordering_params = ['page_no', 'page_length', 'order_by', 'sort_type']
        starts_with_query = Q()
        # Iterate over each parameter in req_params
        for field, value in req_params.items():
            if field not in pagination_ordering_params:
                if field in starts_with_fields:
                    # If the field is in starts_with_fields, use the __startswith lookup
                    starts_with_query |= Q(**{f'{field}__istartswith': value})
                    starts_with_query |= Q(**{f'{field}__iexact': value})
                else:
                    # Otherwise, do an exact match
                    query &= Q(**{f'{field}__iexact': value})

    # Combine the two Q objects
        query &= starts_with_query
        # Use the constructed Q object to filter the Instrument objects
        instruments = Instrument.objects.filter(query).values('instrument_token', 'exchange_token', 'trading_symbol', 'name', 'last_price', 'expiry', 'strike', 'tick_size', 'lot_size', 'instrument_type', 'segment', 'exchange').distinct()

        # Get pagination parameters from request
        page_length = int(req_params.get('page_length', '50'))
        page_no = int(req_params.get('page_no', '1'))
        order_by = req_params.get('order_by', 'name')
        sort_type = req_params.get('sort_type', 'desc')

        if sort_type.lower() == 'desc':
            order_by = '-' + order_by
        instruments = instruments.order_by(order_by)
        paginator = Paginator(instruments, page_length)
        page_obj = paginator.get_page(page_no)  
        data = list(page_obj.object_list)
        # data = json.loads(serializers.serialize('json', page_obj.object_list))

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

    def update_instruments(self, user_id):
        """
        Fetch instruments from integration service and update the database.
        
        Args:
            user_id: User ID to use for the integration service call
        """
        try:
            # Call integration service to get instruments
            api_url = f"{self.integration_service_url}/get_instruments/"
            api_params = {'user_id': user_id}
            
            response = requests.get(api_url, params=api_params, headers=self.headers)
            
            if response.status_code != 200:
                logging.error(f"Failed to fetch instruments from integration service: {response.status_code}")
                raise Exception(f"Integration service returned status {response.status_code}")
                
            response_data = response.json()
            
            if response_data.get('status') != 'success':
                error_msg = response_data.get('error', 'Unknown error from integration service')
                logging.error(f"Integration service returned error: {error_msg}")
                raise Exception(f"Integration service error: {error_msg}")
                
            instruments_data = response_data.get('data', [])
            
            if not instruments_data:
                logging.warning("No instruments data received from integration service")
                raise Exception("No instruments data received from integration service")
                
            # Convert to DataFrame for processing
            instrument_df = pd.DataFrame(instruments_data)
            instrument_dict = instrument_df.to_dict('records')

            # Create Instrument instances
            instrument_instances = [
                Instrument(
                    id=instrument['instrument_token'],
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
            
            # Update database with new instruments
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('SET FOREIGN_KEY_CHECKS=0;')
                    cursor.execute('DELETE FROM instruments')
                    cursor.execute('SET FOREIGN_KEY_CHECKS=1;')
                Instrument.objects.bulk_create(instrument_instances)
                
            logging.info(f"Successfully updated {len(instrument_instances)} instruments")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error calling integration service: {str(e)}")
            raise Exception(f"Failed to connect to integration service: {str(e)}")
        except Exception as e:
            logging.error(f"Error updating instruments: {str(e)}")
            raise
