"""
Grounded generation service that enforces both entities in citations
"""
import os
import time
from typing import List, Dict, Any
from openai import AsyncOpenAI
from .response_context import ResponseContext, Chunk, context_manager
from .query_parser import query_parser

class InsufficientEvidenceError(Exception):
    """Raised when there's insufficient evidence for generation"""
    pass

class GroundedGenerationService:
    """Service for generating responses with grounded prompts and entity validation"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-3.5-turbo"
    
    async def generate_quick_summary(self, request_id: str) -> Dict[str, Any]:
        """Generate a quick summary using the shared context with entity validation"""
        start_time = time.time()
        
        try:
            context = context_manager.validate_context(request_id)
            
            # Check for insufficient evidence
            if hasattr(context, 'insufficient_evidence') and context.insufficient_evidence:
                return self._create_insufficient_evidence_response("summary", context)
            
            # Parse query for entities
            entities = query_parser.extract_entities(context.query)
            
            # Validate citations contain both entities for compositional queries
            if entities.is_compositional:
                validated_chunks = self._validate_citations(context.selected_chunks, entities)
                if len(validated_chunks) < 3:  # Minimum for summary
                    return self._create_insufficient_evidence_response("summary", context)
                context.selected_chunks = validated_chunks
            
            prompt = self._build_grounded_prompt(context, "summary", entities)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(entities)},
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
        """Generate a detailed answer using the shared context with entity validation"""
        start_time = time.time()
        
        try:
            context = context_manager.validate_context(request_id)
            
            # Check for insufficient evidence
            if hasattr(context, 'insufficient_evidence') and context.insufficient_evidence:
                return self._create_insufficient_evidence_response("answer", context)
            
            # Parse query for entities
            entities = query_parser.extract_entities(context.query)
            
            # Validate citations contain both entities for compositional queries
            if entities.is_compositional:
                validated_chunks = self._validate_citations(context.selected_chunks, entities)
                if len(validated_chunks) < 6:  # Minimum for detailed answer
                    return self._create_insufficient_evidence_response("answer", context)
                context.selected_chunks = validated_chunks
            
            prompt = self._build_grounded_prompt(context, "detailed", entities)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(entities)},
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
    
    def _validate_citations(self, chunks: List[Chunk], entities) -> List[Chunk]:
        """Validate that citations contain both entities"""
        validated_chunks = []
        
        for chunk in chunks:
            text = f"{chunk.title} {chunk.text}".lower()
            
            # Check if text contains both X and Y terms
            has_x = any(self._contains_term(text, term) for term in entities.x_terms)
            has_y = any(self._contains_term(text, term) for term in entities.y_terms)
            
            if has_x and has_y:
                validated_chunks.append(chunk)
        
        return validated_chunks
    
    def _contains_term(self, text: str, term: str) -> bool:
        """Check if text contains term with word boundaries"""
        import re
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _get_system_prompt(self, entities) -> str:
        """Get the grounded system prompt based on query type"""
        base_prompt = "You are a scientific assistant. Use ONLY the provided passages. If a claim is not directly supported, respond with 'Unknown based on provided sources.' Cite every factual sentence with [ID] from the provided citations array. Do not invent citations."
        
        if entities.is_compositional:
            return base_prompt + f" For this compositional query about {', '.join(entities.x_terms)} and {', '.join(entities.y_terms)}, only make claims that are directly supported by passages that mention BOTH entities. If a passage only mentions one entity, do not use it to make claims about their relationship."
        else:
            return base_prompt
    
    def _build_grounded_prompt(self, context: ResponseContext, response_type: str, entities) -> str:
        """Build grounded prompt with entity validation"""
        citations_text = self._format_citations(context.selected_chunks)
        
        if response_type == "summary":
            if entities.is_compositional:
                prompt = f"""Based on the following research passages, provide a concise 3-5 sentence summary of the relationship between {', '.join(entities.x_terms)} and {', '.join(entities.y_terms)}.

Citations:
{citations_text}

Provide a brief overview that directly addresses the relationship using only the provided sources. Each claim must be supported by passages that mention BOTH entities. Cite each claim with [ID]."""
            else:
                prompt = f"""Based on the following research passages, provide a concise 3-5 sentence summary of the findings related to: {context.query}

Citations:
{citations_text}

Provide a brief overview that directly addresses the query using only the provided sources. Cite each claim with [ID]."""
        
        else:  # detailed
            if entities.is_compositional:
                prompt = f"""Based on the following research passages, provide a comprehensive analysis of the relationship between {', '.join(entities.x_terms)} and {', '.join(entities.y_terms)}.

Citations:
{citations_text}

Provide a detailed analysis that:
1. Directly addresses the relationship between the entities
2. Cites specific findings using [ID] format
3. Only makes claims supported by passages mentioning BOTH entities
4. Notes any limitations or uncertainties
5. Uses only the provided sources

If information about the relationship is not available in the provided sources, state "Unknown based on provided sources."
"""
            else:
                prompt = f"""Based on the following research passages, provide a comprehensive answer to: {context.query}

Citations:
{citations_text}

Provide a detailed analysis that:
1. Directly addresses the query
2. Cites specific findings using [ID] format
3. Notes any limitations or uncertainties
4. Uses only the provided sources

If information is not available in the provided sources, state "Unknown based on provided sources."
"""
        
        return prompt
    
    def _format_citations(self, chunks: List[Chunk]) -> str:
        """Format chunks as citations with IDs"""
        citations = []
        
        for i, chunk in enumerate(chunks, 1):
            citation = f"[{i}] {chunk.title}"
            if chunk.pmid_or_doi:
                citation += f" (PMID/DOI: {chunk.pmid_or_doi})"
            citation += f" - {chunk.section}"
            citations.append(citation)
        
        return "\n".join(citations)
    
    def _create_insufficient_evidence_response(self, response_type: str, context: ResponseContext) -> Dict[str, Any]:
        """Create response for insufficient evidence"""
        if response_type == "summary":
            message = f"Insufficient evidence: Only {getattr(context, 'evidence_count', 0)} relevant studies found that mention both entities. More research is needed to provide a reliable summary."
        else:
            message = f"Insufficient evidence: Only {getattr(context, 'evidence_count', 0)} relevant studies found that mention both entities. More research is needed to provide a detailed analysis."
        
        return {
            response_type: message,
            "generation_latency_ms": 0,
            "chunks_used": 0,
            "request_id": context.request_id
        }

# Global instance
grounded_generation_service = GroundedGenerationService()
