"""
MockFastRetrievalService: For testing absolute minimum latency
"""
import time
import asyncio
from typing import List, Dict, Any, Optional
from .response_context import Chunk, ResponseContext, context_manager

class MockFastRetrievalService:
    """Mock service for testing minimum possible latency"""
    
    def __init__(self):
        self.max_chunks = 5
        # Pre-cached mock data
        self.mock_papers = [
            {
                "pmid": "12345678",
                "title": "Recent advances in Alzheimer's disease treatment",
                "authors": "Smith J, Johnson A, Brown K",
                "journal": "Nature Medicine",
                "publication_date": "2024",
                "abstract": "This study examines the latest treatments for Alzheimer's disease including anti-amyloid therapies and novel approaches to cognitive enhancement.",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/"
            },
            {
                "pmid": "12345679",
                "title": "Anti-amyloid antibody therapy in Alzheimer's patients",
                "authors": "Wilson M, Davis R, Lee S",
                "journal": "New England Journal of Medicine",
                "publication_date": "2024",
                "abstract": "Clinical trial results showing significant improvement in cognitive function with new anti-amyloid antibody treatments.",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345679/"
            },
            {
                "pmid": "12345680",
                "title": "Therapeutic approaches to neurodegenerative diseases",
                "authors": "Garcia P, Martinez L, Rodriguez C",
                "journal": "Science",
                "publication_date": "2024",
                "abstract": "Comprehensive review of current and emerging therapeutic strategies for treating neurodegenerative conditions including Alzheimer's disease.",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345680/"
            },
            {
                "pmid": "12345681",
                "title": "Cognitive enhancement through targeted therapy",
                "authors": "Chen W, Liu H, Zhang Y",
                "journal": "Cell",
                "publication_date": "2024",
                "abstract": "Novel approaches to cognitive enhancement using targeted molecular therapies for Alzheimer's disease patients.",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345681/"
            },
            {
                "pmid": "12345682",
                "title": "Early intervention strategies in Alzheimer's disease",
                "authors": "Taylor B, Anderson K, White J",
                "journal": "Lancet",
                "publication_date": "2024",
                "abstract": "Importance of early detection and intervention in Alzheimer's disease for optimal treatment outcomes.",
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345682/"
            }
        ]
    
    async def retrieve(self, query: str, size: int = 12) -> ResponseContext:
        """
        Mock retrieval with minimal latency
        """
        start_time = time.time()
        
        try:
            # Simulate minimal processing time
            await asyncio.sleep(0.01)  # 10ms simulation
            
            # Use mock data
            papers = self.mock_papers[:self.max_chunks]
            
            # Convert to chunks
            selected_chunks = self._convert_papers_to_chunks(papers)
            
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
mock_fast_retrieval_service = MockFastRetrievalService()
