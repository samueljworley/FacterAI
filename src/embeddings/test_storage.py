import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from embedder import TextEmbedder
from faiss_index import FAISSIndexManager
#from db.dynamodb_handler import DynamoDBHandler
from dotenv import load_dotenv

def test_storage():
    # Load environment variables
    load_dotenv()
    
    print("\n=== Testing Storage Systems ===")
    
    # Initialize components
    index_path = os.path.join(os.path.dirname(__file__), "research_index")
    index_manager = FAISSIndexManager(index_path=index_path)
    #dynamo = DynamoDBHandler()
    
    # 1. Check if index exists
    print("\nChecking FAISS index...")
    success = index_manager.load()
    print(f"FAISS index loaded: {success}")
    print(f"Number of vectors in FAISS: {index_manager.index.ntotal}")
    print(f"Number of metadata entries: {len(index_manager.metadata)}")
    
    # 2. Check DynamoDB
    print("\nChecking DynamoDB storage...")
    if len(index_manager.metadata) > 0:
        # Test first chunk
        chunk_id = index_manager.metadata[0]['chunk_id']
        print(f"Looking up chunk: {chunk_id}")
        
        #dynamo_chunk = dynamo.get_embedding(chunk_id)
        #if dynamo_chunk:
            #print("✓ Successfully retrieved chunk from DynamoDB")
            #print(f"Text preview: {dynamo_chunk['text'][:100]}...")
        #else:
            #print("✗ Failed to retrieve chunk from DynamoDB")
    
    print("\n=== Storage Test Complete ===")

if __name__ == "__main__":
    test_storage() 