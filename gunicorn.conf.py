"""
gunicorn.conf.py
================

Production Gunicorn configuration for the Daraz scraper API.
Optimized for high performance, memory efficiency, and scalability.
"""

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gevent')
worker_connections = int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', '1000'))
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '50'))

# Timeout settings
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '30'))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '2'))
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30'))

# Logging
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'daraz-scraper-api'

# Server mechanics
daemon = False
pidfile = os.environ.get('GUNICORN_PIDFILE', '/tmp/gunicorn.pid')
user = os.environ.get('GUNICORN_USER', None)
group = os.environ.get('GUNICORN_GROUP', None)
tmp_upload_dir = None

# SSL (if needed)
keyfile = os.environ.get('GUNICORN_KEYFILE', None)
certfile = os.environ.get('GUNICORN_CERTFILE', None)

# Preload app for better performance
preload_app = True

# Worker lifecycle hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Daraz Scraper API server...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Daraz Scraper API server...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Daraz Scraper API server is ready. Workers: %s", server.cfg.workers)

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Server is ready. Spawning workers")

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.info("Worker exited (pid: %s)", worker.pid)

def on_exit(server):
    """Called just before exiting."""
    server.log.info("Shutting down Daraz Scraper API server...")

# Environment variables for the application
raw_env = [
    'FLASK_ENV=production',
    'PYTHONPATH=/app',
]

# Security headers
def post_fork(server, worker):
    """Add security headers and optimizations after worker fork"""
    import os
    os.environ['FLASK_ENV'] = 'production'
    
    # Set memory limits if available
    try:
        import resource
        # Set memory limit to 512MB per worker
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    except ImportError:
        pass
