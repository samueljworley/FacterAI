from flask import Blueprint, request, jsonify
from src.app.services.db_service import DBService
import logging
import traceback
import json
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG for more detail

@feedback_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    try:
        logger.debug("=== Starting Feedback Submission ===")
        data = request.get_json()
        logger.debug(f"Raw incoming data: {json.dumps(data, indent=2)}")
        
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
        
        # Add these debug logs
        logger.debug("Numeric values received:")
        logger.debug(f"clarity: {data.get('clarity')}")
        logger.debug(f"interpretation: {data.get('interpretation')}")
        logger.debug(f"relevance: {data.get('relevance')}")
        logger.debug(f"depth: {data.get('depth')}")
        logger.debug(f"citations_quality: {data.get('citations_quality')}")
        logger.debug(f"reasoning: {data.get('reasoning')}")
        
        # After formatting
        logger.debug("Formatted numeric values:")
        logger.debug(f"ai_clarity: {formatted_data.get('ai_clarity')}")
        logger.debug(f"paper_interpretation: {formatted_data.get('paper_interpretation')}")
        logger.debug(f"topic_relevance: {formatted_data.get('topic_relevance')}")
        logger.debug(f"response_depth: {formatted_data.get('response_depth')}")
        logger.debug(f"citations_quality: {formatted_data.get('citations_quality')}")
        logger.debug(f"ai_reasoning: {formatted_data.get('ai_reasoning')}")
        
        logger.debug(f"Formatted data for storage: {json.dumps(formatted_data, indent=2)}")
        
        # Store in DynamoDB
        db = DBService()
        result = db.store_feedback(formatted_data)
        logger.debug(f"Store feedback result: {result}")
        
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