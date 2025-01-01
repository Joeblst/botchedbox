#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Print commands and their arguments as they are executed (optional for debugging)
#set -x

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Collect static files (if needed)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the Django application (replace with your desired server command)
echo "Starting the Django server..."
exec "$@"
