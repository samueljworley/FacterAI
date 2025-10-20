from .paper_service import PaperService
from .ai_service import AIService
from flask import Flask

def init_services(app: Flask):
    """Initialize all services with app configuration."""
    app.ai_service = AIService(app.config['ANTHROPIC_API_KEY'])
    # app.db_service = DynamoDBService(app)  # This is causing the error

# Add other service imports as needed 