from django.test import TestCase, Client
from django.urls import reverse
from trade_management_unit.models.Instrument import Instrument
import json

class InstrumentViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a sample instrument for testing
        self.instrument = Instrument.objects.create(
            instrument_token=123456,
            exchange_token=654321,
            trading_symbol='test',
            name='Test Instrument',
            last_price=100.00,
            expiry=None,
            strike=200.00,
            tick_size=0.05,
            lot_size=1,
            instrument_type='Test Type',
            segment='Test Segment',
            exchange='Test Exchange'
        )

    def test_update_instruments(self):
        response = self.client.get(reverse('update_instruments'))
        self.assertEqual(response.status_code, 200)
        # Add more assertions here based on what you expect the response to be

    def test_get_instruments(self):
        response = self.client.get(reverse('get_instruments'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Check if the response contains the instrument data
        self.assertEqual(data['data'][0]['fields']['trading_symbol'], 'test')
        self.assertEqual(data['data'][0]['fields']['name'], 'Test Instrument')

    def test_get_instruments_with_query_params(self):
        response = self.client.get(reverse('get_instruments'), {'trading_symbol': 'test'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Check if the response contains the instrument data
        self.assertEqual(data['data'][0]['fields']['trading_symbol'], 'test')
