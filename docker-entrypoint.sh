#!/bin/bash
set -e

# Wait for the database to be ready
until nc -z -v -w30 ats-db 3306
do
  echo "Waiting for database connection..."
  sleep 5
done

# Apply database migrations
python manage.py migrate

# Start server
exec python manage.py runserver 0.0.0.0:8000 