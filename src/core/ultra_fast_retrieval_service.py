"""
UltraFastRetrievalService: Maximum speed optimization
"""
import time
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from .response_context import Chunk, ResponseContext, context_manager

class UltraFastRetrievalService:
    """Ultra-fast retrieval service targeting <200ms"""
    
    def __init__(self):
        self.max_chunks = 8  # Reduce for speed
        self.pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.session = None
    
    async def retrieve(self, query: str, size: int = 12) -> ResponseContext:
        """
        Ultra-fast retrieval targeting <200ms
        """
        start_time = time.time()
        
        try:
            # Create session if needed
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=3),  # 3 second timeout
                    connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
                )
            
            # Single combined request for maximum speed
            papers = await self._ultra_fast_pubmed_search(query, size)
            
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
    
    async def _ultra_fast_pubmed_search(self, query: str, size: int) -> List[Dict[str, Any]]:
        """Ultra-fast PubMed search with minimal requests"""
        
        # Single request to get both IDs and details
        search_url = f"{self.pubmed_base_url}/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": size,
            "sort": "relevance"
        }
        
        async with self.session.get(search_url, params=search_params) as response:
            if response.status != 200:
                raise RuntimeError(f"PubMed search failed: {response.status}")
            
            search_data = await response.json()
            pmids = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not pmids:
                return []
            
            # Get details in single batch request
            return await self._fetch_details_batch(pmids[:size])
    
    async def _fetch_details_batch(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fetch all details in single batch request"""
        
        details_url = f"{self.pubmed_base_url}/esummary.fcgi"
        details_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json"
        }
        
        async with self.session.get(details_url, params=details_params) as response:
            if response.status != 200:
                raise RuntimeError(f"PubMed details failed: {response.status}")
            
            details_data = await response.json()
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
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()

# Global instance
ultra_fast_retrieval_service = UltraFastRetrievalService()
