@echo off
REM start_production.bat
REM Windows production startup script for Daraz Scraper API

echo Starting Daraz Scraper API in production mode...

REM Set environment variables
set FLASK_ENV=production
set FLASK_DEBUG=False
set HOST=0.0.0.0
set PORT=5000
set THREADS=4

echo Environment configured:
echo - Host: %HOST%
echo - Port: %PORT%
echo - Threads: %THREADS%
echo - Environment: %FLASK_ENV%

echo.
echo Starting production server...
python run_production_windows.py
