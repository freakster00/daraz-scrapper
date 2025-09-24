#!/bin/bash
# run_production.sh
# Production startup script for Daraz Scraper API

echo "Starting Daraz Scraper API in production mode..."

# Set environment variables
export FLASK_ENV=production
export FLASK_DEBUG=False
export GUNICORN_WORKERS=4
export GUNICORN_WORKER_CLASS=gevent
export GUNICORN_WORKER_CONNECTIONS=1000
export GUNICORN_MAX_REQUESTS=1000
export GUNICORN_TIMEOUT=30
export GUNICORN_LOG_LEVEL=info

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting Gunicorn server..."
gunicorn --config gunicorn.conf.py app_production:app
