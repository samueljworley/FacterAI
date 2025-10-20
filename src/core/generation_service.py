"""
GenerationService: Handles LLM generation with grounded prompts
"""
import time
import asyncio
from typing import Dict, List, Any
from openai import AsyncOpenAI
import os
from .response_context import ResponseContext, context_manager

class InsufficientEvidenceError(Exception):
    """Raised when there's insufficient evidence for generation"""
    pass

class GenerationService:
    """Service for generating responses with grounded prompts"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-3.5-turbo"
    
    async def generate_quick_summary(self, request_id: str) -> Dict[str, Any]:
        """Generate a quick summary using the shared context"""
        start_time = time.time()
        
        try:
            # Validate context
            context = context_manager.validate_context(request_id)
            
            # Build grounded prompt
            prompt = self._build_grounded_prompt(context, "summary")
            
            # Generate response asynchronously
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            generation_latency = (time.time() - start_time) * 1000
            
            return {
                "summary": response.choices[0].message.content,
                "generation_latency_ms": generation_latency,
                "chunks_used": len(context.selected_chunks),
                "request_id": request_id
            }
            
        except ValueError as e:
            raise InsufficientEvidenceError(str(e))
        except Exception as e:
            raise RuntimeError(f"Summary generation failed: {str(e)}")
    
    async def generate_long_answer(self, request_id: str) -> Dict[str, Any]:
        """Generate a detailed answer using the shared context"""
        start_time = time.time()
        
        try:
            # Validate context
            context = context_manager.validate_context(request_id)
            
            # Build grounded prompt
            prompt = self._build_grounded_prompt(context, "detailed")
            
            # Generate response asynchronously
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
            
            generation_latency = (time.time() - start_time) * 1000
            
            return {
                "answer": response.choices[0].message.content,
                "generation_latency_ms": generation_latency,
                "chunks_used": len(context.selected_chunks),
                "request_id": request_id
            }
            
        except ValueError as e:
            raise InsufficientEvidenceError(str(e))
        except Exception as e:
            raise RuntimeError(f"Answer generation failed: {str(e)}")
    
    def _get_system_prompt(self) -> str:
        """Get the grounded system prompt"""
        return """You are a scientific assistant. Use ONLY the provided passages. If a claim is not directly supported, respond with 'Unknown based on provided sources.' Cite every factual sentence with [ID] from the provided citations array. Do not invent citations."""
    
    def _build_grounded_prompt(self, context: ResponseContext, response_type: str) -> str:
        """Build a grounded prompt with citations"""
        
        # Format citations
        citations_text = self._format_citations(context.selected_chunks)
        
        # Build the prompt based on response type
        if response_type == "summary":
            prompt = f"""Based on the following research passages, provide a concise 3-5 sentence summary of the findings related to: {context.query}

Citations:
{citations_text}

Provide a brief overview that directly addresses the query using only the provided sources. Cite each claim with [ID]."""
        
        else:  # detailed
            prompt = f"""Based on the following research passages, provide a comprehensive answer to: {context.query}

Citations:
{citations_text}

Provide a detailed analysis that:
1. Directly addresses the query
2. Cites specific findings using [ID] format
3. Notes any limitations or uncertainties
4. Uses only the provided sources

If information is not available in the provided sources, state "Unknown based on provided sources."."""
        
        return prompt
    
    def _format_citations(self, chunks: List) -> str:
        """Format chunks as citations with IDs"""
        citations = []
        
        for i, chunk in enumerate(chunks, 1):
            citation = f"[{i}] {chunk.title}"
            if chunk.pmid_or_doi:
                citation += f" (PMID: {chunk.pmid_or_doi})"
            if chunk.section:
                citation += f" - {chunk.section}"
            citation += f"\n{chunk.text[:500]}{'...' if len(chunk.text) > 500 else ''}"
            citations.append(citation)
        
        return "\n\n".join(citations)
    
    def get_insufficient_evidence_template(self, query: str) -> Dict[str, Any]:
        """Return template for insufficient evidence"""
        return {
            "summary": f"Based on the available sources, there is insufficient evidence to provide a comprehensive summary for: {query}. Please try a different search query or check if the sources are relevant to your question.",
            "answer": f"Based on the available sources, there is insufficient evidence to provide a detailed answer for: {query}. The retrieved sources may not contain relevant information, or the search may need to be refined. Please try a different search query or check if the sources are relevant to your question.",
            "generation_latency_ms": 0,
            "chunks_used": 0,
            "insufficient_evidence": True
        }

# Global instance
generation_service = GenerationService()
