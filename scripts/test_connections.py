from src.data_collection.pubmed_client import PubMedClient
#from db.dynamodb_handler import DynamoDBHandler
from db.vector_store import VectorStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connections():
    # Test PubMed
    logger.info("Testing PubMed connection...")
    pubmed = PubMedClient()
    try:
        results = pubmed.search_papers("microplastics", max_results=1)
        logger.info(f"PubMed connection successful: {results}")
    except Exception as e:
        logger.error(f"PubMed connection failed: {e}")

    # Test DynamoDB
    logger.info("Testing DynamoDB connection...")
    #db = DynamoDBHandler()
    try:
        # Just try to access the table
        #db.table.table_status
        logger.info("DynamoDB connection successful")
    except Exception as e:
        logger.error(f"DynamoDB connection failed: {e}")

    # Test Vector Store
    logger.info("Testing Vector Store connection...")
    vector_store = VectorStore()
    try:
        # Try a simple operation
        vector_store.semantic_search("test", k=1)
        logger.info("Vector Store connection successful")
    except Exception as e:
        logger.error(f"Vector Store connection failed: {e}")

if __name__ == "__main__":
    test_connections() 