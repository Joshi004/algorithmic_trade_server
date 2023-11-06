from django.db import connection

class Database:
    def __init__(self):
        self.cursor = connection.cursor()

    def table_exists(self, table_name):
        self.cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
        return len(self.cursor.fetchall()) > 0

    def create_hd_table(self, table_name):
        self.cursor.execute(f"""
            CREATE TABLE `{table_name}` (
                id INT AUTO_INCREMENT,
                open DECIMAL(10, 2),
                close DECIMAL(10, 2),
                high DECIMAL(10, 2),
                low DECIMAL(10, 2),
                date DATETIME,
                PRIMARY KEY (id)
            )
        """)
        connection.commit()

    def fetch_history_data(self, table_name):
        self.cursor.execute(f"SELECT * FROM `{table_name}` ORDER BY date")
        rows = self.cursor.fetchall()

        # Convert each row to a dictionary
        data = []
        for row in rows:
            data.append({
                'open': float(row[1]),
                'close': float(row[2]),
                'high': float(row[3]),
                'low': float(row[4]),
                'date': row[5]
            })

        return data

    def update_historical_data(self, symbol, interval, data):
        if not data:
            print("No data to update.")
            return

        table_name = f"hd__{interval}__{symbol}"
        
        # Delete all existing data from the table
        self.cursor.execute(f"DELETE FROM `{table_name}`")
        
        # Prepare the data for bulk insert
        values = [(record['open'], record['close'], record['high'], record['low'], record['date']) for record in data]
        
        # Perform the bulk insert
        self.cursor.executemany(f"""
            INSERT INTO `{table_name}` (open, close, high, low, date) 
            VALUES (%s, %s, %s, %s, %s)
        """, values)
        
        connection.commit()


