@echo off
REM run_production.bat
REM Production startup script for Daraz Scraper API

echo Starting Daraz Scraper API in production mode...

REM Set environment variables
set FLASK_ENV=production
set FLASK_DEBUG=False
set GUNICORN_WORKERS=4
set GUNICORN_WORKER_CLASS=gevent
set GUNICORN_WORKER_CONNECTIONS=1000
set GUNICORN_MAX_REQUESTS=1000
set GUNICORN_TIMEOUT=30
set GUNICORN_LOG_LEVEL=info

REM Install dependencies if needed
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo Starting Gunicorn server...
gunicorn --config gunicorn.conf.py app_production:app
