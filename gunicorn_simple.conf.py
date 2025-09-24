"""
gunicorn_simple.conf.py
=======================

Simple Gunicorn configuration for production deployment.
"""

import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))
worker_class = 'sync'  # Use sync workers for simplicity
timeout = 30
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'daraz-scraper-api'

# Preload app
preload_app = True
