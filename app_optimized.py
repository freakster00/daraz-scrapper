"""
app_optimized.py
===============

High-performance Flask application with:
- Async request handling
- Memory-efficient streaming responses
- Connection pooling
- Rate limiting
- Caching
"""

import asyncio
import json
import time
from typing import Dict, Any, List
from flask import Flask, jsonify, request, Response, stream_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from contextlib import asynccontextmanager
import weakref
import gc

from scraper_optimized import MemoryOptimizedScraper, search_products_async

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global cache for scraper instances (weak references to avoid memory leaks)
_scraper_cache = weakref.WeakValueDictionary()

def create_app() -> Flask:
    """Factory to create and configure the optimized Flask application"""
    app = Flask(__name__)
    
    # Configure rate limiting
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["100 per hour", "10 per minute"]
    )
    
    # Memory usage tracking
    app.config['MEMORY_TRACKING'] = True
    
    @app.route("/")
    def index():
        """Return a simple HTML landing page describing the API"""
        return (
            "<h1>Daraz Scraper API - Optimized</h1>"
            "<p>High-performance, memory-optimized API for scraping Daraz products.</p>"
            "<h2>Endpoints:</h2>"
            "<ul>"
            "<li><code>/test</code> - Test endpoint</li>"
            "<li><code>/api/search?query=&lt;keywords&gt;&limit=&lt;number&gt;</code> - Search products</li>"
            "<li><code>/api/search/stream?query=&lt;keywords&gt;&limit=&lt;number&gt;</code> - Stream results</li>"
            "<li><code>/api/search/batch</code> - Batch search (POST)</li>"
            "<li><code>/health</code> - Health check</li>"
            "</ul>"
            "<h2>Features:</h2>"
            "<ul>"
            "<li>✅ Async processing</li>"
            "<li>✅ Memory optimization</li>"
            "<li>✅ Connection pooling</li>"
            "<li>✅ Rate limiting</li>"
            "<li>✅ Streaming responses</li>"
            "<li>✅ Batch processing</li>"
            "</ul>"
        )
    
    @app.route("/test")
    def test_endpoint():
        """Simple test endpoint to verify the API is working"""
        return jsonify({
            "status": "success",
            "message": "Daraz Scraper API (Optimized) is working!",
            "features": [
                "Async processing",
                "Memory optimization", 
                "Connection pooling",
                "Rate limiting",
                "Streaming responses",
                "Batch processing"
            ],
            "endpoints": {
                "test": "/test",
                "search": "/api/search?query=<keywords>&limit=<number>",
                "search_stream": "/api/search/stream?query=<keywords>&limit=<number>",
                "search_batch": "/api/search/batch (POST)",
                "health": "/health",
                "home": "/"
            },
            "example_usage": "/api/search?query=toothpaste&limit=5"
        }), 200
    
    @app.route("/health")
    def health_check():
        """Health check endpoint"""
        import psutil
        import os
        
        # Get memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return jsonify({
            "status": "healthy",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "memory_usage": {
                "rss": memory_info.rss,  # Resident Set Size
                "vms": memory_info.vms,  # Virtual Memory Size
                "percent": process.memory_percent()
            },
            "active_connections": len(_scraper_cache)
        }), 200
    
    @app.route("/api/search")
    @limiter.limit("20 per minute")
    async def api_search():
        """Optimized JSON API endpoint with async processing"""
        query = request.args.get("query", type=str)
        limit = request.args.get("limit", default=10, type=int)
        max_concurrent = request.args.get("max_concurrent", default=5, type=int)
        
        if not query:
            return jsonify({"error": "Missing required parameter: query"}), 400
        
        if limit > 100:
            return jsonify({"error": "Limit cannot exceed 100"}), 400
        
        try:
            start_time = time.time()
            
            # Use async scraper
            results = await search_products_async(
                query=query,
                max_results=limit,
                max_concurrent=max_concurrent
            )
            
            processing_time = time.time() - start_time
            
            return jsonify({
                "query": query,
                "results": results,
                "count": len(results),
                "processing_time": round(processing_time, 2),
                "memory_optimized": True
            }), 200
            
        except Exception as e:
            logger.error(f"Error in api_search: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/search/stream")
    @limiter.limit("10 per minute")
    async def api_search_stream():
        """Streaming API endpoint for large result sets"""
        query = request.args.get("query", type=str)
        limit = request.args.get("limit", default=10, type=int)
        max_concurrent = request.args.get("max_concurrent", default=5, type=int)
        
        if not query:
            return jsonify({"error": "Missing required parameter: query"}), 400
        
        if limit > 1000:
            return jsonify({"error": "Limit cannot exceed 1000 for streaming"}), 400
        
        def generate():
            """Generator for streaming JSON response"""
            try:
                # Start JSON array
                yield '{"query": "' + query + '", "results": ['
                
                first = True
                count = 0
                
                async def process_products():
                    nonlocal first, count
                    async with MemoryOptimizedScraper(max_concurrent) as scraper:
                        async for product in scraper.search_products_streaming(query, limit):
                            if not first:
                                yield ','
                            else:
                                first = False
                            
                            yield json.dumps(product.to_dict(), ensure_ascii=False)
                            count += 1
                            
                            # Force garbage collection every 10 products
                            if count % 10 == 0:
                                gc.collect()
                
                # Run async generator in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    async_gen = process_products()
                    while True:
                        try:
                            chunk = loop.run_until_complete(async_gen.__anext__())
                            yield chunk
                        except StopAsyncIteration:
                            break
                finally:
                    loop.close()
                
                # End JSON array
                yield f'], "count": {count}, "streaming": true}}'
                
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                yield f'{{"error": "{str(e)}"}}'
        
        return Response(
            generate(),
            mimetype='application/json',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'  # Disable nginx buffering
            }
        )
    
    @app.route("/api/search/batch", methods=['POST'])
    @limiter.limit("5 per minute")
    async def api_search_batch():
        """Batch search endpoint for multiple queries"""
        try:
            data = request.get_json()
            if not data or 'queries' not in data:
                return jsonify({"error": "Missing 'queries' in request body"}), 400
            
            queries = data['queries']
            if not isinstance(queries, list) or len(queries) > 10:
                return jsonify({"error": "Queries must be a list with max 10 items"}), 400
            
            max_results_per_query = data.get('max_results_per_query', 5)
            max_concurrent = data.get('max_concurrent', 3)
            
            start_time = time.time()
            results = {}
            
            async with MemoryOptimizedScraper(max_concurrent) as scraper:
                async for batch_result in scraper.search_products_batch(
                    queries, 
                    max_results_per_query
                ):
                    results.update(batch_result)
            
            processing_time = time.time() - start_time
            
            return jsonify({
                "queries": queries,
                "results": results,
                "total_products": sum(len(products) for products in results.values()),
                "processing_time": round(processing_time, 2),
                "batch_processing": True
            }), 200
            
        except Exception as e:
            logger.error(f"Error in batch search: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Error handlers
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            "error": "Rate limit exceeded",
            "message": str(e.description)
        }), 429
    
    @app.errorhandler(500)
    def internal_error_handler(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500
    
    # Cleanup on app shutdown
    @app.teardown_appcontext
    def cleanup(error):
        """Cleanup resources on app shutdown"""
        if error:
            logger.error(f"App context error: {error}")
        
        # Clear scraper cache
        _scraper_cache.clear()
        gc.collect()
    
    return app

# Create the app instance
app = create_app()

# For development
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    
    # Use async-capable WSGI server for production
    if os.environ.get("FLASK_ENV") == "production":
        from gunicorn.app.base import BaseApplication
        
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
        
        options = {
            'bind': f'0.0.0.0:{port}',
            'workers': 4,
            'worker_class': 'gevent',
            'worker_connections': 1000,
            'max_requests': 1000,
            'max_requests_jitter': 50,
            'preload_app': True,
            'timeout': 30,
            'keepalive': 2,
        }
        
        StandaloneApplication(app, options).run()
    else:
        # Development server
        app.run(host="0.0.0.0", port=port, debug=True)
