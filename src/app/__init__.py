from flask import Flask
from .config import Config

from .services import init_services
#from src.app.routes.search import search_bp
#from src.app.routes.feedback import feedback_bp

def create_app(config_class=Config):
    app = Flask(__name__, 
        template_folder='templates',
        static_folder='static')
    app.config.from_object(config_class)
    
    # Initialize services (DB, AI, etc.)
    init_services(app)
    
    # Register all routes
    
    
    # Register blueprints
   # app.register_blueprint(search_bp)
   # app.register_blueprint(feedback_bp)
    
    return app 