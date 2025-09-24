#!/usr/bin/env python3
"""
run_production_windows.py
=========================

Windows-compatible production server using Waitress.
This is the recommended way to run Flask apps in production on Windows.
"""

import os
import sys
import logging
from waitress import serve
from app_production import app

def setup_logging():
    """Setup production logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('production.log', mode='a')
        ]
    )

def main():
    """Start the production server"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Get configuration from environment
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    threads = int(os.environ.get('THREADS', '4'))
    
    logger.info(f"Starting Daraz Scraper API on {host}:{port}")
    logger.info(f"Using {threads} threads")
    logger.info("Server ready for production use!")
    
    # Start the server
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        url_scheme='http',
        ident='Daraz-Scraper-API'
    )

if __name__ == '__main__':
    main()
