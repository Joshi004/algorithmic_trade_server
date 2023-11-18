from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Delete tables starting with hd__'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Execute the SHOW TABLES command
            cursor.execute("SHOW TABLES LIKE 'hd__%'")
            # Fetch all table names
            tables = cursor.fetchall()
            # Loop through all tables
            for table in tables:
                # Construct the DROP TABLE query
                drop_table_query = "DROP TABLE IF EXISTS `{}`".format(table[0])
                # Execute the DROP TABLE query
                cursor.execute(drop_table_query)
