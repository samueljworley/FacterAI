import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.dynamodb_handler import DynamoDBHandler
import boto3

def test_paper_operations():
    db = DynamoDBHandler()
    
    # Test data
    test_paper = {
        'document_id': 'test123',
        'category': 'AI',
        'title': 'Test Research Paper',
        'authors': 'John Doe, Jane Smith',
        'publication_date': '2024-03-20',
        'journal': 'Journal of Testing',
        'abstract': 'This is a test abstract',
        'categories': ['AI', 'Testing'],
        'keywords': ['research', 'test', 'example'],
        'full_text_hash': 'abc123hash',
        's3_link': 's3://bucket/test-paper.pdf'
    }
    
    # Insert paper
    insert_response = db.insert_paper(**test_paper)
    print("Insert response:", insert_response)
    
    # Retrieve paper
    retrieved_paper = db.get_paper('test123', 'AI')
    print("Retrieved paper:", retrieved_paper)
    
    # Update paper
    update_response = db.update_paper('test123', 'AI', {
        'abstract': 'Updated abstract',
        'keywords': ['research', 'test', 'example', 'updated']
    })
    print("Update response:", update_response)
    
    # Delete paper
    delete_response = db.delete_paper('test123', 'AI')
    print("Delete response:", delete_response)

def test_aws_connection():
    try:
        # Test DynamoDB connection
        dynamodb = boto3.resource('dynamodb')
        
        # List all tables to verify access
        client = boto3.client('dynamodb')
        tables = client.list_tables()
        
        print("Successfully connected to AWS!")
        print("Available DynamoDB tables:", tables['TableNames'])
        
        # Check if our specific table exists
        if 'sagemind-metadata' in tables['TableNames']:
            print("✅ 'sagemind-metadata' table found!")
        else:
            print("❌ 'sagemind-metadata' table not found. We may need to create it.")
            
    except Exception as e:
        print("Error connecting to AWS:", str(e))

if __name__ == "__main__":
    test_paper_operations()
    test_aws_connection() 