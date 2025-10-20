"""
Ultra-fast routes for maximum performance
"""
from flask import Blueprint, request, jsonify
import asyncio
import threading
from ..core.ultra_fast_controller import ultra_fast_controller

ultra_fast_bp = Blueprint('ultra_fast_routes', __name__)

def init_ultra_fast_routes(app):
    @app.route("/api/ultra-fast-search", methods=["POST"])
    def ultra_fast_search():
        data = request.get_json(silent=True) or {}
        query = data.get("query")
        query_type = data.get("query_type", "research")

        if not query:
            return jsonify({"error": "Query parameter is required"}), 400

        try:
            # Create a new event loop in a thread
            def run_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(ultra_fast_controller.process_query(query, query_type))
                finally:
                    loop.close()
            
            result = run_async()
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    app.register_blueprint(ultra_fast_bp)
