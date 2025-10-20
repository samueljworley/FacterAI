"""
Evidence-aware generation service that uses only evidence sentences
"""
import os
import time
from typing import List, Dict, Any
from openai import AsyncOpenAI
from .response_context import ResponseContext, Chunk, context_manager
from .sentence_level_parser import sentence_level_parser

class InsufficientEvidenceError(Exception):
    """Raised when there's insufficient evidence for generation"""
    pass

class EvidenceAwareGenerationService:
    """Service for generating responses using only evidence sentences"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-3.5-turbo"
    
    async def generate_quick_summary(self, request_id: str) -> Dict[str, Any]:
        """Generate a quick summary using only evidence sentences"""
        start_time = time.time()
        
        try:
            context = context_manager.validate_context(request_id)
            
            # Check for insufficient evidence
            if hasattr(context, 'insufficient_evidence') and context.insufficient_evidence:
                return self._create_insufficient_evidence_response("summary", context)
            
            # Parse query for entities
            entities = sentence_level_parser.extract_entities(context.query)
            
            # Use evidence sentences for compositional queries
            if entities.is_compositional and hasattr(context, 'enhanced_chunks'):
                evidence_text = self._format_evidence_sentences(context.enhanced_chunks)
                if not evidence_text:
                    return self._create_insufficient_evidence_response("summary", context)
            else:
                # Single entity query - use regular chunks
                evidence_text = self._format_citations(context.selected_chunks)
            
            prompt = self._build_evidence_aware_prompt(context, "summary", entities, evidence_text)
            
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
        """Generate a detailed answer using only evidence sentences"""
        start_time = time.time()
        
        try:
            context = context_manager.validate_context(request_id)
            
            # Check for insufficient evidence
            if hasattr(context, 'insufficient_evidence') and context.insufficient_evidence:
                return self._create_insufficient_evidence_response("answer", context)
            
            # Parse query for entities
            entities = sentence_level_parser.extract_entities(context.query)
            
            # Use evidence sentences for compositional queries
            if entities.is_compositional and hasattr(context, 'enhanced_chunks'):
                evidence_text = self._format_evidence_sentences(context.enhanced_chunks)
                if not evidence_text:
                    return self._create_insufficient_evidence_response("answer", context)
            else:
                # Single entity query - use regular chunks
                evidence_text = self._format_citations(context.selected_chunks)
            
            prompt = self._build_evidence_aware_prompt(context, "detailed", entities, evidence_text)
            
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
    
    def _format_evidence_sentences(self, enhanced_chunks) -> str:
        """Format evidence sentences with citation IDs"""
        evidence_sentences = []
        
        for chunk in enhanced_chunks:
            for i, evidence_sentence in enumerate(chunk.evidence_sentences):
                citation_id = f"{chunk.chunk.id}.{i+1}"
                evidence_sentences.append(f"[{citation_id}] {evidence_sentence.text}")
        
        return "\n".join(evidence_sentences)
    
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
    
    def _get_system_prompt(self, entities) -> str:
        """Get the evidence-aware system prompt"""
        base_prompt = "You are a scientific assistant. Use ONLY the provided evidence sentences. If a claim is not directly supported, respond with 'Unknown based on provided sources.' Cite every factual sentence with [ID] from the provided evidence. Do not invent citations."
        
        if entities.is_compositional:
            return base_prompt + f" For this compositional query about {', '.join(entities.x_terms)} and {', '.join(entities.y_terms)}, only make claims that are directly supported by evidence sentences that mention BOTH entities. Each evidence sentence has been pre-validated to contain both entities."
        else:
            return base_prompt
    
    def _build_evidence_aware_prompt(self, context: ResponseContext, response_type: str, entities, evidence_text: str) -> str:
        """Build evidence-aware prompt"""
        
        if response_type == "summary":
            if entities.is_compositional:
                prompt = f"""Based on the following evidence sentences, provide a concise 3-5 sentence summary of the relationship between {', '.join(entities.x_terms)} and {', '.join(entities.y_terms)}.

Evidence Sentences:
{evidence_text}

Provide a brief overview that directly addresses the relationship using only the provided evidence sentences. Each evidence sentence has been validated to contain both entities. Cite each claim with [ID]."""
            else:
                prompt = f"""Based on the following research passages, provide a concise 3-5 sentence summary of the findings related to: {context.query}

Evidence:
{evidence_text}

Provide a brief overview that directly addresses the query using only the provided sources. Cite each claim with [ID]."""
        
        else:  # detailed
            if entities.is_compositional:
                prompt = f"""Based on the following evidence sentences, provide a comprehensive analysis of the relationship between {', '.join(entities.x_terms)} and {', '.join(entities.y_terms)}.

Evidence Sentences:
{evidence_text}

Provide a detailed analysis that:
1. Directly addresses the relationship between the entities
2. Cites specific findings using [ID] format
3. Only makes claims supported by the pre-validated evidence sentences
4. Notes any limitations or uncertainties
5. Uses only the provided evidence

If information about the relationship is not available in the provided evidence, state "Unknown based on provided sources."
"""
            else:
                prompt = f"""Based on the following research passages, provide a comprehensive answer to: {context.query}

Evidence:
{evidence_text}

Provide a detailed analysis that:
1. Directly addresses the query
2. Cites specific findings using [ID] format
3. Notes any limitations or uncertainties
4. Uses only the provided sources

If information is not available in the provided sources, state "Unknown based on provided sources."
"""
        
        return prompt
    
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
evidence_aware_generation_service = EvidenceAwareGenerationService()
