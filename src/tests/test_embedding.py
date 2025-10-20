import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.embeddings.embedder import TextEmbedder
from db.dynamodb_handler import DynamoDBHandler
import numpy as np

def test_save_embedding():
    # Create a test chunk
    test_chunk = {
        'pmid': '12345678',
        'text': 'This is a test chunk of text.',
        'embedding': np.random.rand(1536),  # Random embedding vector
        'publication_date': '2024-01-15',
        'journal': 'Nature Communications',
        'authors': ['Smith, John', 'Doe, Jane'],
        'title': 'Test Paper Title',
        'chunk_index': 0,
        'total_chunks': 1
    }
    
    # Try to save it
    handler = DynamoDBHandler()
    result = handler.save_embedding(test_chunk)
    
    print(f"Save result: {result}")

if __name__ == "__main__":
    test_save_embedding() 