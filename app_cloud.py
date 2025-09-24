"""
app_cloud.py
============

Cloud-optimized Flask application for the Daraz scraper API.
Designed for deployment on platforms like Render, Heroku, etc.
"""

import os
import time
import logging
import threading
from flask import Flask, jsonify, request
from scraper import search_products

# Simple rate limiting
request_lock = threading.Lock()
last_request_time = [0]  # Use list to make it mutable

def create_app() -> Flask:
    """Factory to create and configure the Flask application instance."""
    app = Flask(__name__)
    
    # Cloud configuration
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Configure logging for cloud
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    @app.route("/")
    def index():
        """Return a simple HTML landing page describing the API."""
        return (
            "<h1>Daraz Scraper API - Cloud</h1>"
            "<p>High-performance API for scraping Daraz products.</p>"
            "<h2>Endpoints:</h2>"
            "<ul>"
            "<li><code>/test</code> - Test endpoint</li>"
            "<li><code>/api/search?query=&lt;keywords&gt;&limit=&lt;number&gt;</code> - Search products</li>"
            "<li><code>/health</code> - Health check</li>"
            "</ul>"
            "<h2>Features:</h2>"
            "<ul>"
            "<li>✅ Cloud optimized</li>"
            "<li>✅ Memory efficient</li>"
            "<li>✅ Error handling</li>"
            "<li>✅ Logging</li>"
            "<li>✅ Health monitoring</li>"
            "</ul>"
        )

    @app.route("/test")
    def test_endpoint():
        """Simple test endpoint to verify the API is working."""
        return jsonify({
            "status": "success",
            "message": "Daraz Scraper API (Cloud) is working!",
            "environment": os.environ.get('FLASK_ENV', 'production'),
            "endpoints": {
                "test": "/test",
                "search": "/api/search?query=<keywords>&limit=<number>",
                "health": "/health",
                "home": "/"
            },
            "example_usage": "/api/search?query=toothpaste&limit=5"
        }), 200

    @app.route("/health")
    def health_check():
        """Health check endpoint for monitoring."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return jsonify({
                "status": "healthy",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "environment": os.environ.get('FLASK_ENV', 'production'),
                "memory_usage": {
                    "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                    "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                    "percent": round(process.memory_percent(), 2)
                },
                "cpu_percent": round(process.cpu_percent(), 2)
            }), 200
        except ImportError:
            return jsonify({
                "status": "healthy",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "environment": os.environ.get('FLASK_ENV', 'production'),
                "note": "psutil not available for detailed metrics"
            }), 200

    @app.route("/api/search")
    def api_search():
        """JSON API endpoint that returns seller details for a search term.

        Query parameters:
            query (str): Required. The product keywords to search.
            limit (int): Optional. Maximum number of results to return. Defaults to 10.

        Response:
            200 OK: JSON array of product dictionaries. Each element has
                "product_name", "price", "seller_name", "seller_location",
                "product_url", "rank" keys.
            400 Bad Request: When no ``query`` parameter is provided.
            500 Internal Server Error: When scraping fails.
        """
        start_time = time.time()
        
        # Get query parameters
        query = request.args.get("query", type=str)
        limit = request.args.get("limit", default=10, type=int)
        
        # Validate parameters
        if not query:
            logger.warning("Missing query parameter")
            return jsonify({"error": "Missing required parameter: query"}), 400
        
        if limit > 50:  # Reduced limit for cloud deployment
            logger.warning(f"Limit too high: {limit}")
            return jsonify({"error": "Limit cannot exceed 50"}), 400
        
        if limit < 1:
            logger.warning(f"Limit too low: {limit}")
            return jsonify({"error": "Limit must be at least 1"}), 400
        
        try:
            # Simple rate limiting - prevent concurrent requests
            with request_lock:
                current_time = time.time()
                time_since_last = current_time - last_request_time[0]
                if time_since_last < 3:  # Minimum 3 seconds between requests for cloud
                    wait_time = 3 - time_since_last
                    logger.info(f"Rate limiting: waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                last_request_time[0] = time.time()
            
            logger.info(f"Searching for '{query}' with limit {limit}")
            
            # Perform the search
            results = search_products(query, max_results=limit)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Search completed in {processing_time:.2f}s, found {len(results)} results")
            
            return jsonify({
                "query": query,
                "results": results,
                "count": len(results),
                "processing_time": round(processing_time, 2),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }), 200
            
        except Exception as exc:
            processing_time = time.time() - start_time
            logger.error(f"Search failed for '{query}' after {processing_time:.2f}s: {str(exc)}")
            
            return jsonify({
                "error": "Search failed",
                "message": str(exc),
                "query": query,
                "processing_time": round(processing_time, 2)
            }), 500

    # Error handlers
    @app.errorhandler(404)
    def not_found_handler(e):
        return jsonify({
            "error": "Not found",
            "message": "The requested endpoint was not found"
        }), 404

    @app.errorhandler(405)
    def method_not_allowed_handler(e):
        return jsonify({
            "error": "Method not allowed",
            "message": "The requested method is not allowed for this endpoint"
        }), 405

    @app.errorhandler(500)
    def internal_error_handler(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500

    # Request logging middleware
    @app.before_request
    def log_request_info():
        logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")

    @app.after_request
    def log_response_info(response):
        logger.info(f"Response: {response.status_code} for {request.method} {request.path}")
        return response

    return app

# Create the app instance
app = create_app()

# For development
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
