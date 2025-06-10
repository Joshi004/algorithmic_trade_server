"""
Database utilities for the scanning service.
Provides common database operations without tight coupling to specific models.
"""
from typing import Dict, Any, Optional
from django.db import connection
from scanning_service.lib.utils.logger import log


def insert_record(table_name: str, data: Dict[str, Any]) -> bool:
    """
    Insert a single record into the specified table using raw SQL.
    Automatically adds created_at timestamp if not present.
    
    Args:
        table_name: Name of the database table
        data: Dictionary where keys are column names and values are the values to insert
        
    Returns:
        bool: True if insert was successful, False otherwise
        
    Example:
        insert_record('scanner_events', {
            'event_id': 'evt_123',
            'event_type': 'eligible_instrument_found',
            'trade_session_id': 'session_456',
            'timestamp': datetime.now(),
            'instrument_id': '738561',
            'trading_symbol': 'RELIANCE',
            'market_price': 2475.30
        })
    """
    if not data:
        log("No data provided for database insert", level="warning")
        return False
    
    try:
        # Create a copy to avoid modifying original data
        db_data = data.copy()
        
        # Auto-add created_at if not present and timestamp field exists
        if 'created_at' not in db_data and 'timestamp' in db_data:
            db_data['created_at'] = db_data['timestamp']
        
        # Prepare column names and placeholders
        columns = list(db_data.keys())
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        # Build INSERT SQL
        insert_sql = f"""
            INSERT INTO {table_name} ({column_names}) 
            VALUES ({placeholders})
        """
        
        # Prepare values in the same order as columns
        values = [db_data[col] for col in columns]
        
        # Execute the insert
        with connection.cursor() as cursor:
            cursor.execute(insert_sql, values)
        
        log(f"Successfully inserted record into {table_name}")
        return True
        
    except Exception as e:
        log(f"Failed to insert record into {table_name}: {str(e)}", level="error")
        return False


def insert_batch_records(table_name: str, records: list[Dict[str, Any]]) -> int:
    """
    Insert multiple records into the specified table using raw SQL batch operation.
    Automatically adds created_at timestamp if not present.
    
    Args:
        table_name: Name of the database table
        records: List of dictionaries where each dict represents a record to insert
        
    Returns:
        int: Number of successfully inserted records
        
    Example:
        insert_batch_records('scanner_events', [
            {'event_id': 'evt_123', 'trading_symbol': 'RELIANCE'},
            {'event_id': 'evt_124', 'trading_symbol': 'HDFCBANK'}
        ])
    """
    if not records:
        log("No records provided for batch database insert", level="warning")
        return 0
    
    try:
        # Create copies and auto-add created_at for all records
        db_records = []
        for record in records:
            db_record = record.copy()
            # Auto-add created_at if not present and timestamp field exists
            if 'created_at' not in db_record and 'timestamp' in db_record:
                db_record['created_at'] = db_record['timestamp']
            db_records.append(db_record)
        
        # Ensure all records have the same columns after processing
        first_record_keys = set(db_records[0].keys())
        for i, record in enumerate(db_records):
            if set(record.keys()) != first_record_keys:
                log(f"Record {i} has different columns than first record. Skipping batch insert.", level="error")
                return 0
        
        # Prepare column names and placeholders
        columns = list(first_record_keys)
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        # Build INSERT SQL
        insert_sql = f"""
            INSERT INTO {table_name} ({column_names}) 
            VALUES ({placeholders})
        """
        
        # Prepare all values for batch insert
        all_values = []
        for record in db_records:
            values = [record[col] for col in columns]
            all_values.append(values)
        
        # Execute batch insert
        with connection.cursor() as cursor:
            cursor.executemany(insert_sql, all_values)
        
        inserted_count = len(db_records)
        log(f"Successfully inserted {inserted_count} records into {table_name}")
        return inserted_count
        
    except Exception as e:
        log(f"Failed to insert batch records into {table_name}: {str(e)}", level="error")
        return 0


def execute_query(sql: str, params: Optional[list] = None) -> Optional[list]:
    """
    Execute a custom SQL query and return results.
    
    Args:
        sql: SQL query string
        params: Optional list of parameters for the query
        
    Returns:
        list: Query results as list of tuples, or None if error
    """
    try:
        with connection.cursor() as cursor:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            results = cursor.fetchall()
            log(f"Successfully executed query, returned {len(results)} rows")
            return results
            
    except Exception as e:
        log(f"Failed to execute query: {str(e)}", level="error")
        return None