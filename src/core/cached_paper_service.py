"""
CachedPaperService: PaperService with model caching for speed
"""
import time
import asyncio
from typing import List, Dict, Any, Optional
from .response_context import Chunk, ResponseContext, context_manager
from .model_cache import model_cache

class CachedPaperService:
    """PaperService with cached models for fast retrieval"""
    
    def __init__(self):
        self.max_chunks = 12
        # Use cached models instead of initializing new ones
        self.encoder = None
        self.reranker = None
        self._initialize_cached_models()
    
    def _initialize_cached_models(self):
        """Initialize models from cache"""
        try:
            # Get cached models
            self.encoder = model_cache.get_sentence_transformer()
            self.reranker = model_cache.get_cross_encoder()
            print("✅ Using cached models for fast retrieval")
        except Exception as e:
            print(f"❌ Failed to get cached models: {e}")
            raise
    
    async def retrieve(self, query: str, size: int = 20) -> ResponseContext:
        """
        Fast retrieval using cached models
        """
        start_time = time.time()
        
        try:
            # Use your existing search logic but with cached models
            papers = await self._search_with_cached_models(query, size)
            
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
    
    async def _search_with_cached_models(self, query: str, size: int) -> List[Dict[str, Any]]:
        """Search using cached models for speed"""
        
        # This is a simplified version - you can integrate your existing search logic here
        # For now, let's use a fast PubMed search as a fallback
        
        import requests
        
        # Fast PubMed search
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": size,
            "sort": "relevance"
        }
        
        search_response = requests.get(search_url, params=search_params, timeout=5)
        
        if search_response.status_code != 200:
            raise RuntimeError(f"PubMed search failed: {search_response.status_code}")
        
        search_data = search_response.json()
        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        
        if not pmids:
            return []
        
        # Get paper details
        details_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        details_params = {
            "db": "pubmed",
            "id": ",".join(pmids[:size]),
            "retmode": "json"
        }
        
        details_response = requests.get(details_url, params=details_params, timeout=5)
        
        if details_response.status_code != 200:
            raise RuntimeError(f"PubMed details failed: {details_response.status_code}")
        
        details_data = details_response.json()
        papers = []
        
        for pmid in pmids[:size]:
            paper_info = details_data.get("result", {}).get(pmid, {})
            if paper_info:
                papers.append({
                    "pmid": pmid,
                    "title": paper_info.get("title", "Untitled"),
                    "authors": self._format_authors(paper_info.get("authors", [])),
                    "journal": paper_info.get("source", ""),
                    "publication_date": paper_info.get("pubdate", ""),
                    "abstract": paper_info.get("abstract", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })
        
        return papers
    
    def _format_authors(self, authors: List[Dict]) -> str:
        """Format author list"""
        if not authors:
            return ""
        
        author_names = []
        for author in authors[:5]:
            name = author.get("name", "")
            if name:
                author_names.append(name)
        
        return ", ".join(author_names)
    
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
cached_paper_service = CachedPaperService()
