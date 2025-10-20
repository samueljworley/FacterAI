"""
CachedLambdaRetrievalService: Fast retrieval using your AWS OpenSearch Lambda URL
"""
import time
import os
from dotenv import load_dotenv
load_dotenv()
import requests
from typing import List, Dict, Any, Optional
from .response_context import Chunk, ResponseContext, context_manager

class CachedLambdaRetrievalService:
    """Fast retrieval service using your AWS OpenSearch Lambda URL"""
    
    def __init__(self):
        self.max_chunks = 12
        self.lambda_url = os.getenv('LAMBDA_SEARCH_URL')
        if not self.lambda_url:
            raise RuntimeError("LAMBDA_SEARCH_URL not found in environment variables")
        
        print(f"✅ Initializing Lambda retrieval service with URL: {self.lambda_url}")
    
    def retrieve(self, query: str, size: int = 20) -> ResponseContext:
        """
        Fast retrieval using your AWS OpenSearch Lambda URL
        """
        start_time = time.time()
        
        try:
            # Use Lambda search for fast retrieval
            papers = self._search_with_lambda(query, size)
            
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
    
    def _search_with_lambda(self, query: str, size: int) -> List[Dict[str, Any]]:
        """Search using your AWS OpenSearch Lambda URL"""
        
        try:
            # Call your Lambda search URL
            params = {"q": query, "size": size}
            response = requests.get(self.lambda_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract papers from the response
            papers = []
            if 'hits' in data:
                for item in data['hits']:
                    paper = {
                        "pmid": item.get('pmid', ''),
                        "title": item.get('title', 'Untitled'),
                        "authors": item.get('authors', []),
                        "journal": item.get('journal', ''),
                        "publication_date": item.get('year', ''),
                        "abstract": item.get('abstract', item.get('snippet', '')),
                        "score": item.get('score', 0.0),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{item.get('pmid', '')}/" if item.get('pmid') else None
                    }
                    papers.append(paper)
            
            return papers
            
        except Exception as e:
            print(f"❌ Lambda search failed: {e}")
            return []
    
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
cached_lambda_retrieval_service = CachedLambdaRetrievalService()
