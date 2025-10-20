from flask import Blueprint, request, jsonify, render_template
from src.app.services.ai_service import AIService
from src.app.services.paper_service import PaperService
from src.app.services.db_service import DBService
from src.embeddings.faiss_index import FAISSIndexManager
from src.embeddings.embedder import TextEmbedder
import os
import logging
import traceback
import json
from datetime import datetime
from functools import wraps
import asyncio

# Initialize services
ai_service = AIService()
paper_service = PaperService()
db_service = DBService()

# Initialize embedding services
embedder = TextEmbedder(api_key=os.getenv('OPENAI_API_KEY'))
index_manager = FAISSIndexManager(index_path="src/embeddings/research_index")

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # Changed from DEBUG to INFO

def async_route(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

# Main routes blueprint
main_routes = Blueprint('main', __name__)

@main_routes.route('/')
def index():
    """Main application page"""
    return render_template('index.html')

@main_routes.route('/search', methods=['POST'])
@async_route
async def search():
    """Main search endpoint"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        query_type = data.get('query_type', 'research')
        
        # Get papers first
        papers = await paper_service.search_papers(query, query_type)
        
        # Pass papers to AI service
        result = await ai_service.process_query(
            query=query,
            query_type=query_type,
            papers=papers
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@main_routes.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback"""
    try:
        logger.info("=== Starting Feedback Submission ===")
        data = request.get_json()
        # logger.debug(f"Raw incoming data: {json.dumps(data, indent=2)}")  # Commented out verbose logging
        
        if not data:
            logger.error("No feedback data received")
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
            
        # Ensure numeric fields are integers
        numeric_fields = {
            'clarity': 'ai_clarity',
            'interpretation': 'paper_interpretation',
            'relevance': 'topic_relevance',
            'depth': 'response_depth',
            'citations_quality': 'citations_quality',
            'reasoning': 'ai_reasoning'
        }
        
        # Create new dict with correct field names
        formatted_data = {
            'feedback_id': data.get('feedback_id'),
            'user_query': data.get('user_query'),
            'ai_response': data.get('ai_response'),
            'question_type': data.get('question_type'),
            'topics': data.get('topics', []),
            'strength_tags': data.get('strength_tags') or data.get('tags', {}).get('strengths', []),
            'weakness_tags': data.get('weakness_tags') or data.get('tags', {}).get('weaknesses', []),
            'timestamp': datetime.now().isoformat(),
            'revised_prompt': data.get("revised_prompt"),
            'revised_response': data.get("revised_response"),
            'revised_clarity': data.get("revised_metrics", {}).get("clarity"),
            'revised_paper_interpretation': data.get("revised_metrics", {}).get("interpretation"),
            'revised_topic_relevance': data.get("revised_metrics", {}).get("relevance"),
            'revised_depth': data.get("revised_metrics", {}).get("depth"),
            'revised_citations_quality': data.get("revised_metrics", {}).get("citations_quality"),
            'revised_reasoning': data.get("revised_metrics", {}).get("reasoning"),
            'revised_strength_tags': data.get('revised_strength_tags') or data.get('revised_tags', {}).get('strengths', []),
            'revised_weakness_tags': data.get('revised_weakness_tags') or data.get('revised_tags', {}).get('weaknesses', []),
        }
        
        # Add numeric fields with proper conversion
        for frontend_name, db_name in numeric_fields.items():
            try:
                value = data.get(frontend_name)
                if value is not None:
                    formatted_data[db_name] = int(value)
                    logger.debug(f"Converted {frontend_name} to {db_name}: {formatted_data[db_name]}")
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting {frontend_name}: {str(e)}")
                formatted_data[db_name] = 4  # Default value
        
        logger.debug(f"Formatted data for storage: {json.dumps(formatted_data, indent=2)}")
        
        # Store in DynamoDB
        result = db_service.store_feedback(formatted_data)
        # logger.debug(f"Store feedback result: {result}")  # Commented out verbose logging
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback submitted successfully'
        })
    except Exception as e:
        logger.error(f"Feedback submission error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@main_routes.route('/semantic-search', methods=['POST'])
def semantic_search():
    """Semantic search endpoint"""
    try:
        data = request.get_json()
        query = data.get('query')
        k = data.get('k', 5)
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
            
        query_embedding = embedder.get_embedding(query)
        results = index_manager.search(query_embedding, k=k)
        
        return jsonify({
            "success": True,
            "query": query,
            "results": [{
                "text": r['text'],
                "pmid": r['pmid'],
                "score": float(1 - r['distance']),
                "metadata": {
                    "authors": r.get('authors', []),
                    "year": r.get('year'),
                    "chunk_index": r.get('chunk_index')
                }
            } for r in results]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500 