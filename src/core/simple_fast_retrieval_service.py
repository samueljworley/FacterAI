"""
SimpleFastRetrievalService: Fast retrieval without heavy ML models
"""
import time
import requests
from typing import List, Dict, Any, Optional
from .response_context import Chunk, ResponseContext, context_manager

class SimpleFastRetrievalService:
    """Simple fast retrieval service using direct PubMed API"""
    
    def __init__(self):
        self.max_chunks = 8
        self.pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def retrieve(self, query: str, size: int = 12) -> ResponseContext:
        """
        Fast retrieval using direct PubMed API calls
        """
        start_time = time.time()
        
        try:
            # Fast PubMed search
            papers = self._fast_pubmed_search(query, size)
            
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
    
    def _fast_pubmed_search(self, query: str, size: int) -> List[Dict[str, Any]]:
        """Fast PubMed search without heavy ML models"""
        
        # Step 1: Search for PMIDs (fast)
        search_url = f"{self.pubmed_base_url}/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": size,
            "sort": "relevance"  # Use PubMed's built-in relevance
        }
        
        search_response = requests.get(search_url, params=search_params, timeout=5)
        
        if search_response.status_code != 200:
            raise RuntimeError(f"PubMed search failed: {search_response.status_code}")
        
        search_data = search_response.json()
        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        
        if not pmids:
            return []
        
        # Step 2: Get paper details (batch)
        papers = self._fetch_paper_details_batch(pmids[:size])
        
        return papers
    
    def _fetch_paper_details_batch(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fetch all details in single batch request"""
        
        details_url = f"{self.pubmed_base_url}/esummary.fcgi"
        details_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json"
        }
        
        details_response = requests.get(details_url, params=details_params, timeout=5)
        
        if details_response.status_code != 200:
            raise RuntimeError(f"PubMed details failed: {details_response.status_code}")
        
        details_data = details_response.json()
        papers = []
        
        for pmid in pmids:
            paper_info = details_data.get("result", {}).get(pmid, {})
            if paper_info:
                papers.append({
                    "pmid": pmid,
                    "title": paper_info.get("title", "Untitled"),
                    "authors": self._format_authors_fast(paper_info.get("authors", [])),
                    "journal": paper_info.get("source", ""),
                    "publication_date": paper_info.get("pubdate", ""),
                    "abstract": paper_info.get("abstract", "")[:500],  # Truncate for speed
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })
        
        return papers
    
    def _format_authors_fast(self, authors: List[Dict]) -> str:
        """Fast author formatting"""
        if not authors:
            return ""
        
        # Just take first 3 authors for speed
        author_names = []
        for author in authors[:3]:
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
simple_fast_retrieval_service = SimpleFastRetrievalService()
