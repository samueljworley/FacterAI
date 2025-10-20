"""
ResponseContext: Shared context for retrieval and generation
"""
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time

@dataclass
class Chunk:
    """Represents a text chunk from a research paper"""
    id: str
    title: str
    pmid_or_doi: str
    section: str
    text: str
    score: Optional[float] = None

@dataclass
class ResponseContext:
    """Shared context for a single request"""
    request_id: str
    query: str
    selected_chunks: List[Chunk]
    created_at: float
    retrieval_latency_ms: float = 0
    generation_latency_ms: float = 0

class ResponseContextManager:
    """Manages response contexts for concurrent requests"""
    
    def __init__(self):
        self._contexts: Dict[str, ResponseContext] = {}
        self._cleanup_interval = 300  # 5 minutes
        self._max_age = 600  # 10 minutes
    
    def create_context(self, query: str, selected_chunks: List[Chunk], retrieval_latency_ms: float = 0) -> ResponseContext:
        """Create a new response context"""
        request_id = str(uuid.uuid4())
        context = ResponseContext(
            request_id=request_id,
            query=query,
            selected_chunks=selected_chunks,
            created_at=time.time(),
            retrieval_latency_ms=retrieval_latency_ms
        )
        self._contexts[request_id] = context
        return context
    
    def get_context(self, request_id: str) -> Optional[ResponseContext]:
        """Get a response context by ID"""
        return self._contexts.get(request_id)
    
    def validate_context(self, request_id: str) -> ResponseContext:
        """Validate and return context, raising error if invalid"""
        context = self.get_context(request_id)
        if not context:
            raise ValueError(f"Invalid request_id: {request_id}")
        
        if not context.selected_chunks:
            raise ValueError("No selected chunks available for generation")
        
        return context
    
    def cleanup_old_contexts(self):
        """Remove old contexts to prevent memory leaks"""
        current_time = time.time()
        to_remove = []
        
        for request_id, context in self._contexts.items():
            if current_time - context.created_at > self._max_age:
                to_remove.append(request_id)
        
        for request_id in to_remove:
            del self._contexts[request_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about active contexts"""
        return {
            "active_contexts": len(self._contexts),
            "oldest_context": min((ctx.created_at for ctx in self._contexts.values()), default=0),
            "newest_context": max((ctx.created_at for ctx in self._contexts.values()), default=0)
        }

# Global instance
context_manager = ResponseContextManager()
