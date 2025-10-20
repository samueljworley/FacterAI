"""
UltraFastController: Maximum speed optimization
"""
import asyncio
import time
from typing import Dict, List, Any
from .ultra_fast_retrieval_service import ultra_fast_retrieval_service
from .generation_service import generation_service, InsufficientEvidenceError
from .response_context import ResponseContext, ResponseContextManager, Chunk

class UltraFastController:
    """Ultra-fast controller targeting <200ms retrieval"""
    
    def __init__(self):
        self.retrieval_service = ultra_fast_retrieval_service
        self.generation_service = generation_service
        self.context_manager = ResponseContextManager()

    async def process_query(self, query: str, query_type: str = "research") -> Dict[str, Any]:
        """
        Process query with maximum speed optimizations
        """
        try:
            # Step 1: Ultra-fast retrieval (target: <200ms)
            context = await self.retrieval_service.retrieve(query, size=8)
            
            # Step 2: Generate summary and answer in parallel
            summary_task = asyncio.create_task(
                self._generate_summary_safe(context.request_id)
            )
            answer_task = asyncio.create_task(
                self._generate_answer_safe(context.request_id)
            )
            
            # Wait for both to complete
            summary_result, answer_result = await asyncio.gather(
                summary_task, answer_task, return_exceptions=True
            )
            
            # Handle results
            if isinstance(summary_result, Exception):
                summary_result = self.generation_service.get_insufficient_evidence_template(query)
            
            if isinstance(answer_result, Exception):
                answer_result = self.generation_service.get_insufficient_evidence_template(query)
            
            # Format response
            return {
                "success": True,
                "request_id": context.request_id,
                "query": query,
                "summary": summary_result.get("summary", ""),
                "answer": answer_result.get("answer", ""),
                "citations": self._format_citations_for_ui(context.selected_chunks),
                "retrieval_latency_ms": context.retrieval_latency_ms,
                "summary_latency_ms": summary_result.get("generation_latency_ms", 0),
                "answer_latency_ms": answer_result.get("generation_latency_ms", 0),
                "total_chunks": len(context.selected_chunks),
                "chunks_used_summary": summary_result.get("chunks_used", 0),
                "chunks_used_answer": answer_result.get("chunks_used", 0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "summary": "",
                "answer": "",
                "citations": [],
                "retrieval_latency_ms": 0,
                "summary_latency_ms": 0,
                "answer_latency_ms": 0
            }

    async def _generate_summary_safe(self, request_id: str) -> Dict[str, Any]:
        """Generate summary with error handling"""
        try:
            return await self.generation_service.generate_quick_summary(request_id)
        except InsufficientEvidenceError:
            raise
        except Exception as e:
            raise RuntimeError(f"Summary generation failed: {str(e)}")
    
    async def _generate_answer_safe(self, request_id: str) -> Dict[str, Any]:
        """Generate answer with error handling"""
        try:
            return await self.generation_service.generate_long_answer(request_id)
        except InsufficientEvidenceError:
            raise
        except Exception as e:
            raise RuntimeError(f"Answer generation failed: {str(e)}")
    
    def _format_citations_for_ui(self, chunks) -> List[Dict[str, Any]]:
        """Format chunks for UI display"""
        citations = []
        
        for chunk in chunks:
            citation = {
                "pmid": chunk.pmid_or_doi,
                "title": chunk.title,
                "journal": "",
                "year": "",
                "snippet": chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text,  # Shorter for speed
                "score": getattr(chunk, 'score', None),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{chunk.pmid_or_doi}/" if chunk.pmid_or_doi else None
            }
            citations.append(citation)
        
        return citations

# Global instance
ultra_fast_controller = UltraFastController()
