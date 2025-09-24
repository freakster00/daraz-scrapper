"""
config.py
=========

Configuration file for the optimized Daraz scraper with:
- Performance tuning parameters
- Memory optimization settings
- Connection pool configuration
- Rate limiting settings
"""

import os
from typing import Dict, Any

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Scraper performance settings
    MAX_CONCURRENT_REQUESTS = int(os.environ.get('MAX_CONCURRENT_REQUESTS', '10'))
    MAX_CONCURRENT_PER_HOST = int(os.environ.get('MAX_CONCURRENT_PER_HOST', '5'))
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '30'))
    CONNECTION_POOL_SIZE = int(os.environ.get('CONNECTION_POOL_SIZE', '100'))
    
    # Memory optimization settings
    BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '10'))
    MAX_RESULTS_PER_QUERY = int(os.environ.get('MAX_RESULTS_PER_QUERY', '100'))
    MAX_BATCH_QUERIES = int(os.environ.get('MAX_BATCH_QUERIES', '10'))
    
    # Rate limiting settings
    RATE_LIMIT_PER_HOUR = os.environ.get('RATE_LIMIT_PER_HOUR', '100')
    RATE_LIMIT_PER_MINUTE = os.environ.get('RATE_LIMIT_PER_MINUTE', '10')
    RATE_LIMIT_BATCH = os.environ.get('RATE_LIMIT_BATCH', '5')
    
    # Caching settings
    CACHE_ENABLED = os.environ.get('CACHE_ENABLED', 'True').lower() == 'true'
    CACHE_TTL = int(os.environ.get('CACHE_TTL', '300'))  # 5 minutes
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Daraz specific settings
    DARAZ_BASE_URL = 'https://www.daraz.com.np'
    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    # Performance monitoring
    ENABLE_METRICS = os.environ.get('ENABLE_METRICS', 'True').lower() == 'true'
    METRICS_INTERVAL = int(os.environ.get('METRICS_INTERVAL', '60'))  # seconds

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    MAX_CONCURRENT_REQUESTS = 5
    BATCH_SIZE = 5
    MAX_RESULTS_PER_QUERY = 20

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    MAX_CONCURRENT_REQUESTS = 20
    BATCH_SIZE = 15
    MAX_RESULTS_PER_QUERY = 100
    CACHE_ENABLED = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    MAX_CONCURRENT_REQUESTS = 2
    BATCH_SIZE = 2
    MAX_RESULTS_PER_QUERY = 5
    CACHE_ENABLED = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name: str = None) -> Config:
    """Get configuration based on environment"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])

# Performance optimization presets
PERFORMANCE_PRESETS = {
    'low_memory': {
        'MAX_CONCURRENT_REQUESTS': 3,
        'BATCH_SIZE': 5,
        'MAX_RESULTS_PER_QUERY': 20,
        'CONNECTION_POOL_SIZE': 50
    },
    'balanced': {
        'MAX_CONCURRENT_REQUESTS': 10,
        'BATCH_SIZE': 10,
        'MAX_RESULTS_PER_QUERY': 50,
        'CONNECTION_POOL_SIZE': 100
    },
    'high_performance': {
        'MAX_CONCURRENT_REQUESTS': 20,
        'BATCH_SIZE': 15,
        'MAX_RESULTS_PER_QUERY': 100,
        'CONNECTION_POOL_SIZE': 200
    }
}

def apply_performance_preset(preset_name: str) -> Dict[str, Any]:
    """Apply a performance preset configuration"""
    if preset_name not in PERFORMANCE_PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}")
    
    return PERFORMANCE_PRESETS[preset_name]
