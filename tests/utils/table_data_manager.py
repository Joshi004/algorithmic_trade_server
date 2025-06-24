"""
Table Data Manager for handling ASCII table format test data.

This utility allows you to:
1. Load test data from readable ASCII table format (like MySQL output)
2. Track what data was inserted by each instance
3. Clean up only the data inserted by that specific instance
4. Support multiple tables per test instance
5. Make test data creation more readable and manageable

Usage Examples:
    # Create a data manager instance
    data_manager = TableDataManager()
    
    # Load data from ASCII table format
    users_table = '''
    +------------+----------------------+----------------------------------+------------+-----------+
    | email      | public_id            | first_name                       | last_name  | is_active |
    +------------+----------------------+----------------------------------+------------+-----------+
    | admin@ats.com | 4820c5b92843468ca4fbe4e037a77281 | Admin      |            | 1         |
    | test@ats.com  | 4bb01ea6e2d24e1b86aa282eafaac3f1 | Test       | User       | 1         |
    +------------+----------------------+----------------------------------+------------+-----------+
    '''
    
    # Insert the data
    data_manager.insert_table_data('users', users_table)
    
    # Run your tests...
    
    # Clean up only data inserted by this instance
    data_manager.cleanup()
"""

import re
import uuid
from typing import Dict, List, Any, Optional, Set
from django.db import connection, transaction
from datetime import datetime, date
from decimal import Decimal


class TableDataManager:
    """
    Manages test data from ASCII table format with instance-based tracking and cleanup.
    """
    
    def __init__(self):
        """Initialize the data manager with tracking."""
        self.inserted_data: Dict[str, List[Dict[str, Any]]] = {}
        self.insertion_order: List[str] = []
        self._instance_id = str(uuid.uuid4())[:8]
        
    def insert_table_data(self, table_name: str, ascii_table: str) -> int:
        """
        Insert data from ASCII table format into database.
        
        Args:
            table_name: Name of the database table
            ascii_table: ASCII table format string (like MySQL output)
            
        Returns:
            Number of rows inserted
            
        Example:
            table_data = '''
            +--------+------------------+--------+
            | name   | email            | active |
            +--------+------------------+--------+
            | John   | john@example.com | 1      |
            | Jane   | jane@example.com | 0      |
            +--------+------------------+--------+
            '''
            count = manager.insert_table_data('users', table_data)
        """
        # Parse the ASCII table
        parsed_data = self._parse_ascii_table(ascii_table)
        
        if not parsed_data['rows']:
            return 0
        
        # Insert data into database
        inserted_count = self._insert_parsed_data(table_name, parsed_data)
        
        # Track inserted data for cleanup
        if table_name not in self.inserted_data:
            self.inserted_data[table_name] = []
            self.insertion_order.append(table_name)
        
        self.inserted_data[table_name].extend(parsed_data['rows'])
        
        return inserted_count
    
    def insert_multiple_tables(self, tables_data: Dict[str, str]) -> Dict[str, int]:
        """
        Insert data for multiple tables.
        
        Args:
            tables_data: Dictionary mapping table names to ASCII table data
            
        Returns:
            Dictionary mapping table names to number of rows inserted
            
        Example:
            tables = {
                'users': users_table_ascii,
                'user_broker_credentials': credentials_table_ascii
            }
            results = manager.insert_multiple_tables(tables)
        """
        results = {}
        
        for table_name, ascii_table in tables_data.items():
            results[table_name] = self.insert_table_data(table_name, ascii_table)
        
        return results
    
    def cleanup(self, specific_tables: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Clean up data inserted by this instance.
        
        Args:
            specific_tables: If provided, only clean these tables. Otherwise clean all.
            
        Returns:
            Dictionary mapping table names to number of rows deleted
        """
        results = {}
        
        # Determine which tables to clean
        tables_to_clean = specific_tables if specific_tables else list(self.inserted_data.keys())
        
        # Clean in reverse insertion order to handle foreign keys
        for table_name in reversed(self.insertion_order):
            if table_name in tables_to_clean and table_name in self.inserted_data:
                deleted_count = self._cleanup_table_data(table_name)
                results[table_name] = deleted_count
        
        # Remove cleaned tables from tracking
        for table_name in tables_to_clean:
            if table_name in self.inserted_data:
                del self.inserted_data[table_name]
            if table_name in self.insertion_order:
                self.insertion_order.remove(table_name)
        
        return results
    
    def get_inserted_data(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get the data that was inserted for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of dictionaries representing the inserted rows
        """
        return self.inserted_data.get(table_name, [])
    
    def get_all_inserted_tables(self) -> List[str]:
        """
        Get list of all tables that have data inserted by this instance.
        
        Returns:
            List of table names
        """
        return list(self.inserted_data.keys())
    
    def clear_table_completely(self, table_name: str) -> int:
        """
        Clear ALL data from a table (not just data inserted by this instance).
        Use with caution!
        
        Args:
            table_name: Name of the table to clear
            
        Returns:
            Number of rows deleted
        """
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            
            cursor.execute(f"DELETE FROM {table_name}")
            return count
    
    def _parse_ascii_table(self, ascii_table: str) -> Dict[str, Any]:
        """
        Parse ASCII table format into structured data.
        
        Args:
            ascii_table: ASCII table string
            
        Returns:
            Dictionary with 'columns' and 'rows' keys
        """
        lines = [line.strip() for line in ascii_table.strip().split('\n') if line.strip()]
        
        # Filter out separator lines (lines with only +, -, |)
        data_lines = [line for line in lines if not re.match(r'^[+\-|]+$', line)]
        
        if len(data_lines) < 2:
            return {'columns': [], 'rows': []}
        
        # First line should be headers
        header_line = data_lines[0]
        columns = self._parse_table_row(header_line)
        
        # Remaining lines are data
        rows = []
        for line in data_lines[1:]:
            row_data = self._parse_table_row(line)
            if len(row_data) == len(columns):
                # Create dictionary mapping column names to values
                row_dict = {}
                for i, value in enumerate(row_data):
                    column_name = columns[i]
                    row_dict[column_name] = self._convert_value(value)
                rows.append(row_dict)
        
        return {
            'columns': columns,
            'rows': rows
        }
    
    def _parse_table_row(self, line: str) -> List[str]:
        """
        Parse a single row from ASCII table format.
        
        Args:
            line: Single line from ASCII table
            
        Returns:
            List of cell values
        """
        # Remove leading/trailing |
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]
        
        # Split by | and clean each cell
        cells = [cell.strip() for cell in line.split('|')]
        return cells
    
    def _convert_value(self, value: str) -> Any:
        """
        Convert string value to appropriate Python type.
        
        Args:
            value: String value from table
            
        Returns:
            Converted value (int, float, bool, None, or string)
        """
        if not value or value.upper() == 'NULL':
            return None
        
        # Boolean conversion
        if value.upper() in ('TRUE', 'FALSE'):
            return value.upper() == 'TRUE'
        
        # Integer conversion (including 0/1 for boolean fields)
        if value.isdigit():
            return int(value)
        
        # Float conversion
        try:
            if '.' in value:
                return float(value)
        except ValueError:
            pass
        
        # UUID detection (simple heuristic)
        if len(value) == 32 and all(c in '0123456789abcdef' for c in value.lower()):
            return value
        
        # Date/datetime detection (basic patterns)
        if re.match(r'\d{4}-\d{2}-\d{2}', value):
            try:
                if 'T' in value or ' ' in value:
                    # Datetime
                    return datetime.fromisoformat(value.replace('T', ' ').replace('Z', ''))
                else:
                    # Date
                    return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Return as string
        return value
    
    def _insert_parsed_data(self, table_name: str, parsed_data: Dict[str, Any]) -> int:
        """
        Insert parsed data into database.
        
        Args:
            table_name: Target table name
            parsed_data: Parsed table data
            
        Returns:
            Number of rows inserted
        """
        if not parsed_data['rows']:
            return 0
        
        columns = parsed_data['columns']
        rows = parsed_data['rows']
        
        # Build INSERT query
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        query = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        
        # Prepare values for insertion
        values_list = []
        for row in rows:
            row_values = []
            for col in columns:
                value = row.get(col)
                row_values.append(value)
            values_list.append(row_values)
        
        # Execute insertion
        with connection.cursor() as cursor:
            cursor.executemany(query, values_list)
            return len(values_list)
    
    def _cleanup_table_data(self, table_name: str) -> int:
        """
        Clean up data for a specific table that was inserted by this instance.
        
        This tries to identify and delete only the rows that were inserted
        by this instance, based on the tracked data.
        
        Args:
            table_name: Name of table to clean
            
        Returns:
            Number of rows deleted
        """
        if table_name not in self.inserted_data:
            return 0
        
        inserted_rows = self.inserted_data[table_name]
        if not inserted_rows:
            return 0
        
        deleted_count = 0
        
        # Try to delete rows based on a combination of fields
        # This is a best-effort approach - for perfect cleanup, 
        # you might want to add a tracking field to your tables
        
        with connection.cursor() as cursor:
            for row in inserted_rows:
                # Build WHERE clause based on available fields
                where_conditions = []
                where_values = []
                
                for column, value in row.items():
                    if value is not None:
                        where_conditions.append(f"{column} = %s")
                        where_values.append(value)
                
                if where_conditions:
                    where_clause = " AND ".join(where_conditions)
                    delete_query = f"DELETE FROM {table_name} WHERE {where_clause}"
                    
                    cursor.execute(delete_query, where_values)
                    deleted_count += cursor.rowcount
        
        return deleted_count
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get information about a table structure.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information
        """
        with connection.cursor() as cursor:
            cursor.execute(f"DESCRIBE {table_name}")
            columns_info = cursor.fetchall()
            
            columns = []
            for col_info in columns_info:
                columns.append({
                    'name': col_info[0],
                    'type': col_info[1],
                    'null': col_info[2] == 'YES',
                    'key': col_info[3],
                    'default': col_info[4],
                    'extra': col_info[5]
                })
        
        return {
            'name': table_name,
            'columns': columns
        }
    
    def export_table_as_ascii(self, table_name: str, where_clause: str = None) -> str:
        """
        Export table data as ASCII table format.
        
        Args:
            table_name: Table to export
            where_clause: Optional WHERE clause
            
        Returns:
            ASCII table format string
        """
        # Get table data
        with connection.cursor() as cursor:
            query = f"SELECT * FROM {table_name}"
            if where_clause:
                query += f" WHERE {where_clause}"
            
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        
        if not rows:
            return f"-- No data in table {table_name}"
        
        # Convert to string representation
        str_rows = []
        for row in rows:
            str_row = []
            for value in row:
                if value is None:
                    str_row.append('NULL')
                else:
                    str_row.append(str(value))
            str_rows.append(str_row)
        
        # Calculate column widths
        col_widths = []
        for i, col in enumerate(columns):
            max_width = len(col)
            for row in str_rows:
                max_width = max(max_width, len(row[i]))
            col_widths.append(max_width + 2)  # Add padding
        
        # Build ASCII table
        lines = []
        
        # Top border
        border_line = '+' + '+'.join('-' * width for width in col_widths) + '+'
        lines.append(border_line)
        
        # Header row
        header_cells = []
        for i, col in enumerate(columns):
            header_cells.append(f" {col:<{col_widths[i]-1}}")
        lines.append('|' + '|'.join(header_cells) + '|')
        
        # Separator
        lines.append(border_line)
        
        # Data rows
        for row in str_rows:
            data_cells = []
            for i, value in enumerate(row):
                data_cells.append(f" {value:<{col_widths[i]-1}}")
            lines.append('|' + '|'.join(data_cells) + '|')
        
        # Bottom border
        lines.append(border_line)
        
        return '\n'.join(lines)


# Convenience function for common usage patterns
def create_test_data_manager():
    """
    Create a new TableDataManager instance.
    
    Returns:
        New TableDataManager instance
    """
    return TableDataManager()


def insert_test_tables(tables_data: Dict[str, str]) -> TableDataManager:
    """
    Convenience function to create a manager and insert multiple tables.
    
    Args:
        tables_data: Dictionary mapping table names to ASCII table data
        
    Returns:
        TableDataManager instance that can be used for cleanup
        
    Example:
        tables = {
            'users': users_ascii_table,
            'credentials': credentials_ascii_table
        }
        manager = insert_test_tables(tables)
        # ... run tests ...
        manager.cleanup()  # Clean up all inserted data
    """
    manager = TableDataManager()
    manager.insert_multiple_tables(tables_data)
    return manager 