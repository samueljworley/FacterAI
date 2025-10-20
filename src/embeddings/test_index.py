from embedder import TextEmbedder
from faiss_index import FAISSIndexManager
import os
from dotenv import load_dotenv

def test_search():
    # Load environment variables
    load_dotenv()
    
    # Use the same path as build_index.py
    index_path = os.path.join(os.path.dirname(__file__), "research_index")
    print(f"Loading index from: {index_path}")
    
    index_manager = FAISSIndexManager(index_path=index_path)
    success = index_manager.load()
    
    if not success:
        print("Failed to load index!")
        return
        
    print(f"Index loaded with {len(index_manager.metadata)} chunks")
    
    # Initialize embedder
    embedder = TextEmbedder(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Test queries
    test_queries = [
        "How do microplastics affect human health?",
        "What are the main impacts of climate change on public health?",
        "What are the ethical concerns in AI development?"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: {query}")
        
        # Get query embedding
        query_embedding = embedder.get_embedding(query)
        
        # Search
        results = index_manager.search(query_embedding, k=3)
        
        # Display results
        print(f"Top 3 results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Distance: {result['distance']:.3f}")
            print(f"PMID: {result['pmid']}")
            print(f"Text: {result['text'][:200]}...")

if __name__ == "__main__":
    test_search() 