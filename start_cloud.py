#!/usr/bin/env python3
"""
start_cloud.py
==============

Cloud startup script for the Daraz scraper API.
Optimized for deployment on Render, Heroku, and other cloud platforms.
"""

import os
import sys
import logging
from waitress import serve
from app_cloud import app

def setup_logging():
    """Setup cloud logging configuration"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Start the cloud server"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Get configuration from environment
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    threads = int(os.environ.get('THREADS', '2'))  # Reduced for cloud
    
    logger.info(f"Starting Daraz Scraper API on {host}:{port}")
    logger.info(f"Using {threads} threads")
    logger.info("Server ready for cloud deployment!")
    
    # Start the server
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        url_scheme='https' if os.environ.get('HTTPS', 'false').lower() == 'true' else 'http',
        ident='Daraz-Scraper-API-Cloud'
    )

if __name__ == '__main__':
    main()
