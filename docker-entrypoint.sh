#!/bin/bash
set -e

# Wait for the database to be ready
until nc -z -v -w30 ats-db 3306
do
  echo "Waiting for database connection..."
  sleep 5
done

echo "✅ Database connection established!"

# Apply database migrations first
echo "🔄 Applying database migrations..."
python manage.py migrate

echo "✅ All migrations applied successfully!"

# Apply seed data (this will now check migrations internally)
echo "🌱 Applying seed data..."
python manage.py seed_data

echo "✅ Seed data applied successfully!"

echo "🚀 Starting application..."

# Execute the command passed to the container
exec "$@" 