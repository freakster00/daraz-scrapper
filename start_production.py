#!/usr/bin/env python3
"""
start_production.py
===================

Production startup script for the Daraz scraper API.
Handles environment setup, logging configuration, and Gunicorn startup.
"""

import os
import sys
import logging
import signal
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def setup_logging():
    """Setup production logging configuration"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/tmp/daraz_scraper.log', mode='a')
        ]
    )
    
    # Set specific loggers
    logging.getLogger('gunicorn.error').setLevel(logging.INFO)
    logging.getLogger('gunicorn.access').setLevel(logging.INFO)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

def setup_environment():
    """Setup production environment variables"""
    # Set Flask environment
    os.environ.setdefault('FLASK_ENV', 'production')
    os.environ.setdefault('FLASK_DEBUG', 'False')
    
    # Set Gunicorn defaults
    os.environ.setdefault('GUNICORN_WORKERS', '4')
    os.environ.setdefault('GUNICORN_WORKER_CLASS', 'gevent')
    os.environ.setdefault('GUNICORN_WORKER_CONNECTIONS', '1000')
    os.environ.setdefault('GUNICORN_MAX_REQUESTS', '1000')
    os.environ.setdefault('GUNICORN_TIMEOUT', '30')
    os.environ.setdefault('GUNICORN_LOG_LEVEL', 'info')
    
    # Set scraper defaults
    os.environ.setdefault('MAX_CONCURRENT_REQUESTS', '10')
    os.environ.setdefault('BATCH_SIZE', '10')
    os.environ.setdefault('MAX_RESULTS_PER_QUERY', '100')

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def main():
    """Main production startup function"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup environment and logging
    setup_environment()
    setup_logging()
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Daraz Scraper API in production mode...")
    
    # Import and configure Gunicorn
    try:
        from gunicorn.app.base import BaseApplication
        from app import app
        
        class StandaloneApplication(BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()
            
            def load_config(self):
                config = {key: value for key, value in self.options.items()
                         if key in self.cfg.settings and value is not None}
                for key, value in config.items():
                    self.cfg.set(key.lower(), value)
            
            def load(self):
                return self.application
        
        # Gunicorn configuration
        options = {
            'bind': f"0.0.0.0:{os.environ.get('PORT', '5000')}",
            'workers': int(os.environ.get('GUNICORN_WORKERS', '4')),
            'worker_class': os.environ.get('GUNICORN_WORKER_CLASS', 'gevent'),
            'worker_connections': int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', '1000')),
            'max_requests': int(os.environ.get('GUNICORN_MAX_REQUESTS', '1000')),
            'max_requests_jitter': int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '50')),
            'timeout': int(os.environ.get('GUNICORN_TIMEOUT', '30')),
            'keepalive': int(os.environ.get('GUNICORN_KEEPALIVE', '2')),
            'preload_app': True,
            'accesslog': '-',
            'errorlog': '-',
            'loglevel': os.environ.get('GUNICORN_LOG_LEVEL', 'info'),
            'proc_name': 'daraz-scraper-api',
        }
        
        logger.info(f"Starting server with {options['workers']} workers on {options['bind']}")
        
        # Start the application
        StandaloneApplication(app, options).run()
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.info("Falling back to Flask development server...")
        
        # Fallback to Flask development server
        port = int(os.environ.get('PORT', '5000'))
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
