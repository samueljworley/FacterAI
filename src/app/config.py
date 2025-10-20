import os

class Config:
    DEBUG = True
    # Add other config variables (DB settings, API keys, etc.)
    PUBMED_API_KEY = os.getenv('PUBMED_API_KEY')  # You'll need to get this from NCBI
    AWS_REGION = os.getenv('AWS_REGION', 'us-west-1')
    DYNAMODB_TABLE = 'sagemind-metadata' 