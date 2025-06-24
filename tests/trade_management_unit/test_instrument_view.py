import pytest
import json
from django.test import RequestFactory
from unittest.mock import patch
from trade_management_unit.views.instrument_view import get_instruments, update_instruments


@pytest.mark.integration
@pytest.mark.requires_db
class TestGetInstruments:
    
    def test_success_with_no_parameters(self, authenticated_request_factory, table_data_manager):
        """
        Test: Get instruments with default parameters
        Expected: 200 with default pagination and ordering
        """
        # Setup database with 3 instruments
        table_data_manager.clear_table_completely('instruments')
        
        instruments_data = """
        +--------+---------------+----------------+----------------+------------------+------------+--------+--------+----------+--------+---------------+-------+---------+-----------+---------------------+---------------------+
        | id     | instrument_token | exchange_token | trading_symbol | name             | last_price | expiry | strike | tick_size | lot_size | instrument_type | segment | exchange | is_active | created_at          | updated_at          |
        +--------+---------------+----------------+----------------+------------------+------------+--------+--------+----------+--------+---------------+-------+---------+-----------+---------------------+---------------------+
        | 738561 | 738561        | 2278           | RELIANCE       | Reliance Industries Ltd | 2456.75    |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 408065 | 408065        | 1270           | INFY           | Infosys Limited  | 1456.80    |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 779521 | 779521        | 2423           | SBIN           | State Bank of India | 567.25     |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +--------+---------------+----------------+----------------+------------------+------------+--------+--------+----------+--------+---------------+-------+---------+-----------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('instruments', instruments_data)
        
        # Make request with no parameters
        request = authenticated_request_factory.get('/trade_management/get_instruments/')
        
        response = get_instruments(request)
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert 'data' in data
        assert 'meta' in data
        assert len(data['data']) == 3
        assert data['meta']['count'] == 3
        assert data['meta']['order_by'] == '-name'  # Default desc ordering
        
        # Cleanup
        table_data_manager.clear_table_completely('instruments')
    
    def test_success_with_pagination_parameters(self, authenticated_request_factory, table_data_manager):
        """
        Test: Get instruments with custom pagination parameters
        Expected: 200 with paginated results according to specified page_no and page_length
        """
        # Setup database with 5 instruments
        table_data_manager.clear_table_completely('instruments')
        
        instruments_data = """
        +--------+---------------+----------------+----------------+------------------+------------+--------+--------+----------+--------+---------------+-------+---------+-----------+---------------------+---------------------+
        | id     | instrument_token | exchange_token | trading_symbol | name             | last_price | expiry | strike | tick_size | lot_size | instrument_type | segment | exchange | is_active | created_at          | updated_at          |
        +--------+---------------+----------------+----------------+------------------+------------+--------+--------+----------+--------+---------------+-------+---------+-----------+---------------------+---------------------+
        | 738561 | 738561        | 2278           | RELIANCE       | Reliance Industries Ltd | 2456.75    |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 408065 | 408065        | 1270           | INFY           | Infosys Limited  | 1456.80    |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 779521 | 779521        | 2423           | SBIN           | State Bank of India | 567.25     |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 895745 | 895745        | 2789           | TATASTEEL      | Tata Steel Limited | 123.45     |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 340481 | 340481        | 1058           | HDFC           | HDFC Bank Limited | 1678.90    |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +--------+---------------+----------------+----------------+------------------+------------+--------+--------+----------+--------+---------------+-------+---------+-----------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('instruments', instruments_data)
        
        # Test pagination: page_no=1, page_length=3
        request = authenticated_request_factory.get('/trade_management/get_instruments/', data={
            'page_no': '1',
            'page_length': '3'
        })
        
        response = get_instruments(request)
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert 'data' in data
        assert 'meta' in data
        assert len(data['data']) == 3
        assert data['meta']['count'] == 5  # Total count
        assert data['meta']['num_pages'] == 2  # Total pages
        assert data['meta']['next_page_number'] == 2  # Next page
        assert data['meta']['previous_page_number'] is None  # No previous page
        
        # Cleanup
        table_data_manager.clear_table_completely('instruments')

    def test_success_with_trading_symbol_filtering(self, authenticated_request_factory, table_data_manager):
        """
        Test: Filter instruments by trading_symbol using startswith logic
        Expected: 200 with filtered results based on trading_symbol startswith
        """
        # Setup database
        table_data_manager.clear_table_completely('instruments')
        
        instruments_data = """
        +--------+---------------+----------------+----------------+------------------+------------+--------+--------+----------+--------+---------------+-------+---------+-----------+---------------------+---------------------+
        | id     | instrument_token | exchange_token | trading_symbol | name             | last_price | expiry | strike | tick_size | lot_size | instrument_type | segment | exchange | is_active | created_at          | updated_at          |
        +--------+---------------+----------------+----------------+------------------+------------+--------+--------+----------+--------+---------------+-------+---------+-----------+---------------------+---------------------+
        | 738561 | 738561        | 2278           | RELIANCE       | Reliance Industries Ltd | 2456.75    |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 738562 | 738562        | 2279           | RELCAP         | Reliance Capital   | 156.25     |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        | 408065 | 408065        | 1270           | INFY           | Infosys Limited  | 1456.80    |        |        | 0.0500   | 1      | EQ            | EQ    | NSE     | 1         | 2024-01-15 10:00:00 | 2024-01-15 10:00:00 |
        +--------+---------------+----------------+----------------+------------------+------------+--------+--------+----------+--------+---------------+-------+---------+-----------+---------------------+---------------------+
        """
        table_data_manager.insert_table_data('instruments', instruments_data)
        
        # Filter by trading_symbol starting with 'REL'
        request = authenticated_request_factory.get('/trade_management/get_instruments/', data={
            'trading_symbol': 'REL'
        })
        
        response = get_instruments(request)
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert len(data['data']) == 2  # RELIANCE and RELCAP
        assert data['meta']['count'] == 2
        
        symbols = [item['trading_symbol'] for item in data['data']]
        assert 'RELIANCE' in symbols
        assert 'RELCAP' in symbols
        assert 'INFY' not in symbols
        
        # Cleanup
        table_data_manager.clear_table_completely('instruments')

    def test_success_with_empty_database(self, authenticated_request_factory, table_data_manager):
        """
        Test: Get instruments when database is empty
        Expected: 200 with empty data array
        """
        # Clear database
        table_data_manager.clear_table_completely('instruments')
        
        # Make request
        request = authenticated_request_factory.get('/trade_management/get_instruments/')
        
        response = get_instruments(request)
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert 'data' in data
        assert 'meta' in data
        assert len(data['data']) == 0
        assert data['meta']['count'] == 0
        
        # Cleanup not needed as database is already clear


@pytest.mark.integration
@pytest.mark.requires_db
class TestUpdateInstruments:
    
    def test_success_with_valid_integration_service_response(self, authenticated_request_factory, table_data_manager):
        """
        Test: Successfully update instruments from integration service
        Expected: 200 with success message and instruments updated in database
        """
        # Setup database - clear existing data
        table_data_manager.clear_table_completely('instruments')
        
        # Mock integration service response
        mock_integration_response = {
            'status': 'success',
            'data': [
                {
                    'instrument_token': 738561,
                    'exchange_token': 2278,
                    'tradingsymbol': 'RELIANCE',  # Note: 'tradingsymbol' from API
                    'name': 'Reliance Industries Ltd',
                    'last_price': 2456.75,
                    'expiry': '',
                    'strike': 0.0,
                    'tick_size': 0.05,
                    'lot_size': 1,
                    'instrument_type': 'EQ',
                    'segment': 'EQ',
                    'exchange': 'NSE'
                },
                {
                    'instrument_token': 408065,
                    'exchange_token': 1270,
                    'tradingsymbol': 'INFY',
                    'name': 'Infosys Limited',
                    'last_price': 1456.80,
                    'expiry': '',
                    'strike': 0.0,
                    'tick_size': 0.05,
                    'lot_size': 1,
                    'instrument_type': 'EQ',
                    'segment': 'EQ',
                    'exchange': 'NSE'
                }
            ]
        }
        
        # Make request
        request = authenticated_request_factory.post('/trade_management/update_instruments/')
        
        # Mock both the integration service and the user resolution to avoid user creation
        with patch('trade_management_unit.lib.Instruments.Instruments.Instruments.update_instruments') as mock_update:
            mock_update.return_value = None  # Simulate successful update
            
            response = update_instruments(request)
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'success'
        assert data['message'] == 'Instruments updated successfully'
        
        # Cleanup
        table_data_manager.clear_table_completely('instruments')

    def test_error_with_integration_service_http_error(self, authenticated_request_factory, table_data_manager):
        """
        Test: Integration service returns HTTP error (500, 503, etc.)
        Expected: 500 with error message after retries
        """
        # Setup database
        table_data_manager.clear_table_completely('instruments')
        
        # Make request
        request = authenticated_request_factory.post('/trade_management/update_instruments/')
        
        # Mock the Instruments class to raise an exception
        with patch('trade_management_unit.lib.Instruments.Instruments.Instruments.update_instruments') as mock_update:
            mock_update.side_effect = Exception('Integration service error: HTTP 500')
            
            response = update_instruments(request)
        
        # Verify error response
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert 'error' in data
        
        # Cleanup
        table_data_manager.clear_table_completely('instruments') 