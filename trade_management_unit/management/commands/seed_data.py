import os
import glob
import re
from django.core.management.base import BaseCommand
from django.db import connection, transaction, IntegrityError
from pathlib import Path
from django.conf import settings
from django.apps import apps

class Command(BaseCommand):
    help = 'Seeds the database with initial data from seed files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force execution even if seeds were already applied',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        # Check if the seed tracking table exists, if not create it
        self.setup_seed_tracking()
        
        # Get all seed files
        base_dir = settings.BASE_DIR
        sql_seed_files = glob.glob(os.path.join(base_dir, 'data', '*.sql'))
        
        for seed_file in sql_seed_files:
            seed_name = os.path.basename(seed_file)
            
            # Check if seed was already applied
            if not force and self.is_seed_applied(seed_name):
                self.stdout.write(self.style.WARNING(f'Seed {seed_name} was already applied. Skipping.'))
                continue
            
            # Apply the seed
            try:
                with transaction.atomic():
                    self.apply_seed(seed_file)
                    self.mark_seed_as_applied(seed_name)
                self.stdout.write(self.style.SUCCESS(f'Successfully applied seed {seed_name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to apply seed {seed_name}: {str(e)}'))
    
    def setup_seed_tracking(self):
        """Create a table to track which seeds have been applied"""
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seed_tracker (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    seed_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def is_seed_applied(self, seed_name):
        """Check if a seed was already applied"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM seed_tracker WHERE seed_name = %s", [seed_name])
            result = cursor.fetchone()
            return result[0] > 0
    
    def mark_seed_as_applied(self, seed_name):
        """Mark a seed as applied in the tracker"""
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO seed_tracker (seed_name) VALUES (%s)", [seed_name])
    
    def apply_seed(self, seed_file):
        """Apply a seed file to the database"""
        with open(seed_file, 'r') as f:
            sql_content = f.read()
        
        # Split the SQL content into individual statements
        # This simple approach assumes statements end with semicolons
        statements = re.split(r';\s*$', sql_content, flags=re.MULTILINE)
        statements = [stmt.strip() for stmt in statements if stmt.strip()]
        
        with connection.cursor() as cursor:
            for statement in statements:
                # Skip empty statements
                if not statement:
                    continue
                
                # Check if it's an INSERT statement
                if statement.upper().startswith('INSERT'):
                    # Modify to handle duplicates
                    table_match = re.search(r'INSERT INTO (\w+)', statement)
                    if table_match:
                        table_name = table_match.group(1)
                        try:
                            # Try executing the insert as is
                            cursor.execute(statement)
                        except IntegrityError:
                            self.stdout.write(self.style.WARNING(
                                f'Duplicate record detected in {table_name}. Skipping this insert.'
                            ))
                else:
                    # Execute other statements as is
                    cursor.execute(statement)
    
    def get_model_for_table(self, table_name):
        """Get the Django model class for a table name"""
        for model in apps.get_models():
            if hasattr(model._meta, 'db_table') and model._meta.db_table == table_name:
                return model
        return None 