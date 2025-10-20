"""
UnifiedController: Orchestrates retrieval and generation
"""
import asyncio
import time
from typing import Dict, List, Any, Tuple
from .deduplicated_retrieval_service import deduplicated_retrieval_service
from .token_optimized_generation_service import token_optimized_generation_service, InsufficientEvidenceError
from .response_context import ResponseContext, ResponseContextManager, Chunk

class UnifiedController:
    """Main controller that orchestrates retrieval and generation"""
    
    def __init__(self):
        self.retrieval_service = deduplicated_retrieval_service
        self.generation_service = token_optimized_generation_service
        self.context_manager = ResponseContextManager()

    async def process_query(self, query: str, query_type: str = "research") -> Dict[str, Any]:
        """
        Process a query with proper dependency ordering:
        1. Retrieve papers and create context
        2. Generate summary and answer in parallel
        """
        try:
            # Step 1: Retrieve papers and create context
            context = self.retrieval_service.retrieve(query, size=20)
            
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
            # This will be handled by the caller
            raise
        except Exception as e:
            raise RuntimeError(f"Summary generation failed: {str(e)}")
    
    async def _generate_answer_safe(self, request_id: str) -> Dict[str, Any]:
        """Generate answer with error handling"""
        try:
            return await self.generation_service.generate_long_answer(request_id)
        except InsufficientEvidenceError:
            # This will be handled by the caller
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
                "journal": "",  # Will be extracted from title if needed
                "year": "",     # Will be extracted from title if needed
                "snippet": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                "score": getattr(chunk, 'score', None),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{chunk.pmid_or_doi}/" if chunk.pmid_or_doi else None
            }
            citations.append(citation)
        
        return citations

# Global instance
unified_controller = UnifiedController()
