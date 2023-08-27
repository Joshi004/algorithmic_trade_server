#!/bin/bash

# Read each line in the .env file
while IFS= read -r line
do
  # Split the line into key and value
  IFS='=' read -ra KV <<< "$line"

  # Trim leading and trailing spaces from key and value
  key=$(echo "${KV[0]}" | xargs)
  value=$(echo "${KV[1]}" | xargs)

  # Check if both key and value exist
  if [ -n "$key" ] && [ -n "$value" ]; then
    # Export the variable
    export $key=$value
    echo "Exported: $key=$value"
  fi
done < ".env"


echo "Starting the application"
python manage.py runserver