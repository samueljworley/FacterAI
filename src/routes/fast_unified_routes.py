"""
Fast unified routes for optimized performance
"""
from flask import Blueprint, request, jsonify
import asyncio
from ..core.fast_unified_controller import fast_unified_controller

fast_unified_bp = Blueprint('fast_unified_routes', __name__)

def init_fast_unified_routes(app):
    @app.route("/api/fast-search", methods=["POST"])
    def fast_search():
        data = request.get_json(silent=True) or {}
        query = data.get("query")
        query_type = data.get("query_type", "research")

        if not query:
            return jsonify({"error": "Query parameter is required"}), 400

        try:
            # Run the async function in the event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(fast_unified_controller.process_query(query, query_type))
            loop.close()
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    app.register_blueprint(fast_unified_bp)
