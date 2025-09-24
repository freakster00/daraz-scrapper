"""
app.py
=======

This module defines a small Flask application that exposes a simple
JSON API over the scraper defined in ``scraper.py``. The root route
``/`` serves a human‑readable landing page, while ``/api/search``
accepts a GET request with a ``query`` parameter and an optional
``limit``. It returns a JSON array of seller details for products
appearing on Daraz in the same order they appear in the web search.

To run this application locally, install the dependencies from
``requirements.txt`` and execute ``python app.py``. When deployed on
Render, a ``Procfile`` is included so that Gunicorn can serve the app.
"""

from __future__ import annotations

import os
from flask import Flask, jsonify, request

from scraper import search_products


def create_app() -> Flask:
    """Factory to create and configure the Flask application instance."""
    app = Flask(__name__)

    @app.route("/")
    def index():
        """Return a simple HTML landing page describing the API."""
        return (
            "<h1>Daraz Scraper API</h1>"
            "<p>Use <code>/api/search?query=&lt;keywords&gt;</code> to search for products "
            "and retrieve seller details for the top results.</p>"
        )

    @app.route("/test")
    def test_endpoint():
        """Simple test endpoint to verify the API is working."""
        return jsonify({
            "status": "success",
            "message": "Daraz Scraper API is working!",
            "endpoints": {
                "test": "/test",
                "search": "/api/search?query=<keywords>&limit=<number>",
                "home": "/"
            },
            "example_usage": "/api/search?query=toothpaste&limit=5"
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
                "product_url" keys. If an error occurs during scraping, the
                "seller_name" and "seller_location" fields may be null.
            400 Bad Request: When no ``query`` parameter is provided.
        """
        query = request.args.get("query", type=str)
        limit = request.args.get("limit", default=10, type=int)
        if not query:
            return jsonify({"error": "Missing required parameter: query"}), 400
        try:
            results = search_products(query, max_results=limit)
        except Exception as exc:
            # On unexpected errors, return a 500 and include a message
            return jsonify({"error": str(exc)}), 500
        return jsonify(results), 200

    return app


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    # When running locally, pick up the port from the environment (useful for Heroku/Render)
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)