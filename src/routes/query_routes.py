from flask import Flask, request, jsonify
from src.data.source_manager import DataSourceManager
from src.llm.llm_client import LLMClient

app = Flask(__name__)

@app.route("/process-query", methods=["POST"])
def process_query():
    try:
        data = request.get_json()
        query = data.get("query")
        query_type = data.get("type", "concept")  # Since Concepts was selected in screenshot
        
        print(f"Processing query: {query} of type: {query_type}")  # Debug log
        
        source_manager = DataSourceManager()
        sources = source_manager.get_sources(query, query_type)
        
        llm_client = LLMClient()
        response = llm_client.analyze_query(query, sources, query_type)
        
        if isinstance(response, str):  # Ensure response is string
            return jsonify({
                "response": response,
                "sources": sources
            })
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
            
    except Exception as e:
        print(f"Error processing query: {str(e)}")  # Debug log
        return jsonify({"error": str(e)}), 500 