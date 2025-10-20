from flask import Flask, request, jsonify, render_template
#import requests
import xml.etree.ElementTree as ET
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS
#from src.api.routes import api
#from src.database.db_manager import DatabaseManager
from config.config import config
import asyncio
from functools import wraps
#from db.paper_processor import PaperProcessor
#from typing import Dict, List
#from src.ai.explanation_generator import ExplanationGenerator
#from uuid import uuid4
#from datetime import datetime
#import boto3
#from botocore.exceptions import ClientError
#import re
#from src.data.source_manager import DataSourceManager
#from src.llm.llm_client import LLMClient

#from src.app.routes.search import search_bp  # Add this import


import os, importlib.util
has_boto3 = importlib.util.find_spec("boto3") is not None
print("APP_VERSION:", os.getenv("APP_VERSION","?"), "HAS_BOTO3:", has_boto3, flush=True)



# Load environment variables


# Initialize services

#paper_service = PaperService()

def create_app():
    load_dotenv()
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder='src/templates',
        static_folder='src/static'
    )
    # very top of the file, after: app = Flask(__name__)
    import os
    print("APP BOOT, APP_VERSION:", os.getenv("APP_VERSION","?"), flush=True)

    @app.get("/health")
    def health(): return "ok", 200
    # Root route
    @app.get("/")
    def home():
        return render_template("search_v2.html")

    
    
    from src.app.services.ai_service import AIService
    #from src.app.services.paper_service import PaperService
    #from src.routes.search_routes import init_semantic_search_routes  # Add 'src.'
    #import search_client  # <-- the helper we created
    # from src.routes.answer_routes import init_answer_routes
    from src.routes.unified_routes import init_unified_routes
    #from src.routes.fast_unified_routes import init_fast_unified_routes
    #from src.routes.ultra_fast_routes import init_ultra_fast_routes
    from src.core.model_cache import model_cache  # New unified routes
    import traceback
    from werkzeug.exceptions import HTTPException
    import traceback

    @app.errorhandler(Exception)
    def handle_any_error(e):
        # show full stack in logs so you can debug
        traceback.print_exc()
        # let normal HTTP errors (like 404 for missing static files) pass through
        if isinstance(e, HTTPException):
            return e
    # everything else is a real 500
        return jsonify(error=str(e), type=e.__class__.__name__), 500

    init_unified_routes(app) #THIS WAS ON LINE 109, CHANGING AS OF OCT 7 
    print("HANDLER: unified_routes")
   

    
    from src.routes.search_routes import search_bp
    app.register_blueprint(search_bp, name="search_api", url_prefix="/api")
    print("HANDLER: search_routes")
    


    

    ai_service = AIService()


    # CORS (fine to keep)
    allowed = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
    CORS(app, resources={r"/api/*": {
        "origins": allowed or [
            "http://localhost:3000", "http://127.0.0.1:3000",
            "https://facter.it.com", "https://www.facter.it.com",
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
    }})
    # Config
    app.config.from_object(config)
    


    # ---- REGISTER ONLY UNIFIED ROUTES ----
    # init_semantic_search_routes(app)   # ❌ disable
    # init_answer_routes(app)            # ❌ disable
                 # ✅ keep
    # init_fast_unified_routes(app)      # ❌ disable
    # init_ultra_fast_routes(app)        # ❌ disable

    # Models cache (keep)
    model_cache.initialize_models()

    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    return app

    
    

    

 

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

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5001, debug=config.DEBUG)
