"""
CachedFAISSRetrievalService: Fast retrieval using cached FAISS search
"""
import time
import os
from typing import List, Dict, Any, Optional
from .response_context import Chunk, ResponseContext, context_manager
from .model_cache import model_cache
from src.embeddings.embedder import TextEmbedder
from src.embeddings.faiss_index import FAISSIndexManager

class CachedFAISSRetrievalService:
    """Fast retrieval service using cached FAISS search"""
    
    def __init__(self):
        self.max_chunks = 12
        self.embedder = None
        self.index_manager = None
        self._initialize_cached_components()
    
    def _initialize_cached_components(self):
        """Initialize cached components for fast retrieval"""
        try:
            # Use cached models for embedding
            print("✅ Initializing cached FAISS retrieval service...")
            
            # Initialize embedder with cached models
            self.embedder = TextEmbedder(api_key=os.getenv('OPENAI_API_KEY'))
            
            # Initialize FAISS index manager
            self.index_manager = FAISSIndexManager(index_path="src/embeddings/research_index")
            self.index_manager.load()
            
            print(f"✅ FAISS index loaded with {self.index_manager.index.ntotal} vectors")
            
        except Exception as e:
            print(f"❌ Failed to initialize cached FAISS components: {e}")
            raise
    
    def retrieve(self, query: str, size: int = 20) -> ResponseContext:
        """
        Fast retrieval using cached FAISS search
        """
        start_time = time.time()
        
        try:
            # Use FAISS search for fast retrieval
            papers = self._search_with_faiss(query, size)
            
            # Convert to chunks
            selected_chunks = self._convert_papers_to_chunks(papers)
            selected_chunks = selected_chunks[:self.max_chunks]
            
            retrieval_latency = (time.time() - start_time) * 1000
            
            # Create response context
            context = context_manager.create_context(
                query=query,
                selected_chunks=selected_chunks,
                retrieval_latency_ms=retrieval_latency
            )
            
            return context
            
        except Exception as e:
            raise RuntimeError(f"Retrieval failed: {str(e)}")
    
    def _search_with_faiss(self, query: str, size: int) -> List[Dict[str, Any]]:
        """Search using cached FAISS index"""
        
        try:
            # Get query embedding
            query_embedding = self.embedder.get_embedding(query)
            
            # Search FAISS index
            results = self.index_manager.search(query_embedding, k=size)
            
            # Convert FAISS results to paper format
            papers = []
            for result in results:
                paper = {
                    "pmid": result.get('pmid', ''),
                    "title": self._extract_title_from_text(result.get('text', '')),
                    "authors": result.get('authors', []),
                    "journal": result.get('journal', ''),
                    "publication_date": result.get('year', ''),
                    "abstract": result.get('text', ''),
                    "score": float(1 - result.get('distance', 1.0)),  # Convert distance to score
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{result.get('pmid', '')}/" if result.get('pmid') else None
                }
                papers.append(paper)
            
            return papers
            
        except Exception as e:
            print(f"❌ FAISS search failed: {e}")
            return []
    
    def _extract_title_from_text(self, text: str) -> str:
        """Extract title from text (first line or first sentence)"""
        if not text:
            return "Untitled"
        
        # Try to get first line as title
        first_line = text.split('\n')[0].strip()
        if first_line and len(first_line) < 200:  # Reasonable title length
            return first_line
        
        # Fallback: first sentence
        first_sentence = text.split('.')[0].strip()
        if first_sentence and len(first_sentence) < 200:
            return first_sentence
        
        # Last resort: first 100 characters
        return text[:100].strip() + "..." if len(text) > 100 else text.strip()
    
    def _convert_papers_to_chunks(self, papers: List[Dict[str, Any]]) -> List[Chunk]:
        """Convert paper data to Chunk objects"""
        chunks = []
        
        for i, paper in enumerate(papers):
            try:
                chunk = Chunk(
                    id=str(i + 1),
                    title=paper.get('title', 'Untitled'),
                    pmid_or_doi=paper.get('pmid', ''),
                    section="Abstract",
                    text=paper.get('abstract', '')
                )
                chunks.append(chunk)
            except Exception as e:
                print(f"Error converting paper {i} to chunk: {e}")
                continue
        
        return chunks

# Global instance
cached_faiss_retrieval_service = CachedFAISSRetrievalService()
