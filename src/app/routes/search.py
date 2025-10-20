from flask import Blueprint, request, jsonify, current_app
from src.app.services.paper_service import PaperService
from src.app.services.ai_service import AIService
import os

search_bp = Blueprint('search', __name__)

# Initialize services
paper_service = PaperService()
ai_service = AIService()

@search_bp.route('/search', methods=['POST'])
async def search():
    try:
        data = request.get_json()
        query = data.get('query', '')
        query_type = data.get('query_type', 'research')
        
        papers = await paper_service.search_papers(query, query_type)
        result = await ai_service.process_query(query, query_type, papers)
        
        return jsonify(result)
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@search_bp.route('/search', methods=['POST'])
async def search_async():
    query = request.json.get('query', '')
    
    if not current_app.ai_service.validate_query(query):
        return jsonify({
            'error': 'Invalid query. Please provide a more detailed question.'
        }), 400

    try:
        result = await current_app.ai_service.process_query(query)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'error': 'Error processing query',
            'details': str(e)
        }), 500 