import os
from dotenv import load_dotenv
from typing import Optional
from fetch_pubmed import PubMedFetcher
from chunker import TextChunker
from embedder import TextEmbedder
from faiss_index import FAISSIndexManager

# Load environment variables from .env file
load_dotenv()

class ResearchIndexBuilder:
    def __init__(
        self,
        openai_api_key: str,
        email: str,
        pubmed_api_key: Optional[str] = None,
        index_path: str = os.path.join(os.path.dirname(__file__), "research_index")
    ):
        """Initialize the index builder with necessary components"""
        self.fetcher = PubMedFetcher(email=email, api_key=pubmed_api_key)
        self.chunker = TextChunker(target_size=200)
        self.embedder = TextEmbedder(api_key=openai_api_key)
        print(f"Using index path: {index_path}")
        self.index_manager = FAISSIndexManager(index_path=index_path)
        
    def build_index(self, query: str, max_papers: int = 100) -> None:
        """Build search index from PubMed papers"""
        try:
            print(f"Fetching papers for query: {query}")
            papers = self.fetcher.fetch_abstracts(query, max_results=max_papers)
            print(f"Found {len(papers)} papers")
            
            # Process each paper
            for i, paper in enumerate(papers, 1):
                print(f"Processing paper {i}/{len(papers)}")
                
                # Chunk the paper
                chunks = self.chunker.chunk_paper(paper)
                print(f"Created {len(chunks)} chunks")
                
                # Generate embeddings
                embedded_chunks = self.embedder.embed_chunks(chunks)
                print(f"Generated embeddings for {len(embedded_chunks)} chunks")
                
                # Add to index
                self.index_manager.add_chunks(embedded_chunks)
                
            # Save index and metadata
            print("Saving index...")
            self.index_manager.save()
            print("Index built successfully!")
            
        except Exception as e:
            print(f"Error building index: {str(e)}")
            raise

def main():
    # Get API keys from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")
    pubmed_api_key = os.getenv("PUBMED_API_KEY")
    email = os.getenv("PUBMED_EMAIL")
    
    if not all([openai_api_key, email]):
        raise ValueError("Missing required environment variables")
        
    # Initialize builder
    builder = ResearchIndexBuilder(
        openai_api_key=openai_api_key,
        email=email,
        pubmed_api_key=pubmed_api_key
    )
    
    # Build index for specific topics
    queries = [
        "microplastic ingestion effects",
        "climate change health impacts",
        "artificial intelligence ethics"
    ]
    
    for query in queries:
        print(f"\nBuilding index for: {query}")
        builder.build_index(query, max_papers=50)

if __name__ == "__main__":
    main() 