import os
import glob
import re
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from trade_management_unit.models.SeedTracker import SeedTracker


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
        
        # Ensure all migrations are applied before seeding
        self.ensure_migrations_applied()
        
        # Get all seed files
        base_dir = settings.BASE_DIR
        sql_seed_files = glob.glob(os.path.join(base_dir, 'data', '*.sql'))
        
        if not sql_seed_files:
            self.stdout.write(self.style.WARNING('No seed files found in data/ directory'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(sql_seed_files)} seed files'))
        
        for seed_file in sql_seed_files:
            seed_name = os.path.basename(seed_file)
            
            # Check if seed was already applied
            if not force and SeedTracker.is_seed_applied(seed_name):
                self.stdout.write(self.style.WARNING(f'Seed {seed_name} was already applied. Skipping.'))
                continue
            
            # Apply the seed
            try:
                with transaction.atomic():
                    self.apply_seed(seed_file)
                    SeedTracker.mark_seed_as_applied(seed_name)
                self.stdout.write(self.style.SUCCESS(f'Successfully applied seed {seed_name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to apply seed {seed_name}: {str(e)}'))
                if not force:
                    raise  # Stop on error unless force is used

    def ensure_migrations_applied(self):
        """Ensure all migrations are applied before running seeds"""
        self.stdout.write("Checking migration status...")
        
        # Check if there are any unapplied migrations
        try:
            from django.db.migrations.executor import MigrationExecutor
            from django.db import DEFAULT_DB_ALIAS
            
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            
            if plan:
                self.stdout.write(self.style.WARNING(
                    f"Found {len(plan)} unapplied migrations. Running migrations first..."
                ))
                call_command('migrate', verbosity=0)
                self.stdout.write(self.style.SUCCESS("All migrations applied successfully."))
            else:
                self.stdout.write(self.style.SUCCESS("All migrations are up to date."))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking migrations: {str(e)}"))
            raise

    def apply_seed(self, seed_file):
        """Apply a seed file to the database - ONLY INSERT statements allowed"""
        with open(seed_file, 'r') as f:
            sql_content = f.read()
        
        # Split the SQL content into individual statements
        statements = re.split(r';\s*$', sql_content, flags=re.MULTILINE)
        statements = [stmt.strip() for stmt in statements if stmt.strip()]
        
        executed_count = 0
        skipped_count = 0
        
        with connection.cursor() as cursor:
            for statement in statements:
                # Skip empty statements and comments
                if not statement or statement.startswith('--'):
                    continue
                
                # Only allow INSERT statements for seed data
                if not statement.upper().startswith('INSERT'):
                    self.stdout.write(self.style.WARNING(
                        f'Skipping non-INSERT statement in seed file: {statement[:50]}...'
                    ))
                    skipped_count += 1
                    continue
                
                try:
                    # Execute the insert statement
                    cursor.execute(statement)
                    executed_count += 1
                    
                except IntegrityError as e:
                    if 'Duplicate entry' in str(e) or 'already exists' in str(e):
                        self.stdout.write(self.style.WARNING(
                            f'⚠ Skipping duplicate entry: {statement[:50]}...'
                        ))
                        skipped_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(
                            f'✗ Integrity error: {str(e)}'
                        ))
                        raise
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'✗ Error executing statement: {str(e)}'
                    ))
                    self.stdout.write(self.style.ERROR(f'Statement: {statement}'))
                    raise
        
        self.stdout.write(self.style.SUCCESS(
            f'Seed completed: {executed_count} statements executed, {skipped_count} skipped'
        )) 