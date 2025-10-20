"""
Sentence-level retrieval service with co-mention enforcement and AD disambiguation
"""
import time
from dataclasses import dataclass
import os
import requests
import re
from typing import List, Dict, Any, Optional, Tuple
from .response_context import Chunk, ResponseContext, context_manager
from .sentence_level_parser import sentence_level_parser, ExtractedEntities
from dotenv import load_dotenv

load_dotenv()

@dataclass
class EvidenceSentence:
    """Evidence sentence with citation info"""
    text: str
    chunk_id: str
    doc_id: str
    relation_cue_count: int

@dataclass
class EnhancedChunk:
    """Enhanced chunk with evidence sentences"""
    chunk: Chunk
    evidence_sentences: List[EvidenceSentence]
    doc_id: str
    cross_encoder_score: float
    relation_bonus: float
    total_score: float

class SentenceLevelRetrievalService:
    """Retrieval service with sentence-level co-mention enforcement"""
    
    def __init__(self):
        self.max_chunks = 15
        self.min_chunks = 3
        self.min_docs = 3
        self.min_evidence_sentences = 3
        self.lambda_url = os.getenv('LAMBDA_SEARCH_URL')
        if not self.lambda_url:
            raise RuntimeError("LAMBDA_SEARCH_URL not found in environment variables")
        
        print(f"✅ Initializing sentence-level retrieval service with URL: {self.lambda_url}")
    
    def retrieve(self, query: str, size: int = 20) -> ResponseContext:
        """
        Sentence-level retrieval with co-mention enforcement
        """
        start_time = time.time()
        
        try:
            # Parse query for entities
            entities = sentence_level_parser.extract_entities(query)
            
            # Get initial results from Lambda (RRF top 200)
            initial_papers = self._search_with_lambda(query, 200)
            
            # Apply sentence-level filtering for compositional queries
            if entities.is_compositional:
                enhanced_chunks = self._apply_sentence_level_filter(initial_papers, entities)
                
                # Check if we have sufficient evidence
                if len(enhanced_chunks) < self.min_chunks:
                    return self._create_insufficient_evidence_context(query, len(enhanced_chunks))
                
                # Check if we have sufficient distinct docs
                distinct_docs = len(set(chunk.doc_id for chunk in enhanced_chunks))
                if distinct_docs < self.min_docs:
                    return self._create_insufficient_evidence_context(query, len(enhanced_chunks))
                
                # Check total evidence sentences
                total_evidence = sum(len(chunk.evidence_sentences) for chunk in enhanced_chunks)
                if total_evidence < self.min_evidence_sentences:
                    return self._create_insufficient_evidence_context(query, len(enhanced_chunks))
                
                # Convert to regular chunks for response context
                selected_chunks = [chunk.chunk for chunk in enhanced_chunks[:self.max_chunks]]
                
                # Store enhanced data for generation
                context = context_manager.create_context(
                    query=query,
                    selected_chunks=selected_chunks,
                    retrieval_latency_ms=(time.time() - start_time) * 1000
                )
                context.enhanced_chunks = enhanced_chunks[:self.max_chunks]
                
            else:
                # Single entity query - normal processing
                papers = initial_papers[:self.max_chunks]
                selected_chunks = self._convert_papers_to_chunks(papers)
                
                context = context_manager.create_context(
                    query=query,
                    selected_chunks=selected_chunks,
                    retrieval_latency_ms=(time.time() - start_time) * 1000
                )
            
            # Add telemetry
            self._log_telemetry(query, len(initial_papers), len(enhanced_chunks) if entities.is_compositional else len(selected_chunks), entities)
            
            return context
            
        except Exception as e:
            raise RuntimeError(f"Retrieval failed: {str(e)}")
    
    def _search_with_lambda(self, query: str, size: int) -> List[Dict[str, Any]]:
        """Search using your AWS OpenSearch Lambda URL"""
        try:
            params = {"q": query, "size": size}
            response = requests.get(self.lambda_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            papers = []
            
            if 'hits' in data:
                for item in data['hits']:
                    paper = {
                        "pmid": item.get('pmid', ''),
                        "title": item.get('title', 'Untitled'),
                        "authors": item.get('authors', []),
                        "journal": item.get('journal', ''),
                        "publication_date": item.get('year', ''),
                        "abstract": item.get('abstract', item.get('snippet', '')),
                        "score": item.get('score', 0.0),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{item.get('pmid', '')}/" if item.get('pmid') else None
                    }
                    papers.append(paper)
            
            return papers
            
        except Exception as e:
            print(f"❌ Lambda search failed: {e}")
            return []
    
    def _apply_sentence_level_filter(self, papers: List[Dict[str, Any]], entities: ExtractedEntities) -> List[EnhancedChunk]:
        """Apply sentence-level co-mention filtering"""
        enhanced_chunks = []
        
        for i, paper in enumerate(papers):
            # Create chunk
            chunk = Chunk(
                id=str(i + 1),
                title=paper.get('title', 'Untitled'),
                pmid_or_doi=paper.get('pmid', ''),
                section="Abstract",
                text=paper.get('abstract', '')
            )
            
            # Split into sentences
            sentences = self._split_into_sentences(f"{chunk.title} {chunk.text}")
            
            # Find evidence sentences
            evidence_sentences = []
            for sentence in sentences:
                if self._sentence_contains_both_entities(sentence, entities):
                    relation_cue_count = self._count_relation_cues(sentence)
                    evidence_sentence = EvidenceSentence(
                        text=sentence,
                        chunk_id=chunk.id,
                        doc_id=chunk.pmid_or_doi,
                        relation_cue_count=relation_cue_count
                    )
                    evidence_sentences.append(evidence_sentence)
            
            # Keep chunk only if it has evidence sentences
            if evidence_sentences:
                # Calculate scores
                cross_encoder_score = paper.get('score', 0.0)
                relation_bonus = sum(sentence.relation_cue_count for sentence in evidence_sentences) * 0.1
                total_score = cross_encoder_score + relation_bonus
                
                enhanced_chunk = EnhancedChunk(
                    chunk=chunk,
                    evidence_sentences=evidence_sentences,
                    doc_id=chunk.pmid_or_doi,
                    cross_encoder_score=cross_encoder_score,
                    relation_bonus=relation_bonus,
                    total_score=total_score
                )
                enhanced_chunks.append(enhanced_chunk)
        
        # Sort by total score
        enhanced_chunks.sort(key=lambda x: x.total_score, reverse=True)
        
        return enhanced_chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting - can be enhanced with more sophisticated NLP
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _sentence_contains_both_entities(self, sentence: str, entities: ExtractedEntities) -> bool:
        """Check if sentence contains both X and Y entities with AD disambiguation"""
        sentence_lower = sentence.lower()
        
        # Check X terms
        has_x = any(self._contains_term(sentence_lower, term) for term in entities.x_terms)
        
        # Check Y terms
        has_y = any(self._contains_term(sentence_lower, term) for term in entities.y_terms)
        
        # If Y contains AD, also check disambiguators
        if entities.disambiguators:
            has_disambiguator = any(self._contains_term(sentence_lower, disambiguator) for disambiguator in entities.disambiguators)
            return has_x and has_y and has_disambiguator
        
        return has_x and has_y
    
    def _contains_term(self, text: str, term: str) -> bool:
        """Check if text contains term with word boundaries"""
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _count_relation_cues(self, sentence: str) -> int:
        """Count relation cues in sentence"""
        sentence_lower = sentence.lower()
        count = 0
        for cue in sentence_level_parser.relation_cues:
            if cue in sentence_lower:
                count += 1
        return count
    
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
    
    def _create_insufficient_evidence_context(self, query: str, count: int) -> ResponseContext:
        """Create context for insufficient evidence"""
        context = context_manager.create_context(
            query=query,
            selected_chunks=[],
            retrieval_latency_ms=0
        )
        
        # Add insufficient evidence marker
        context.insufficient_evidence = True
        context.evidence_count = count
        
        return context
    
    def _log_telemetry(self, query: str, initial_count: int, final_count: int, entities: ExtractedEntities):
        """Log detailed telemetry data"""
        print(f"📊 Sentence-Level Telemetry - Query: '{query}'")
        print(f"   RRF candidates: {initial_count}")
        print(f"   Chunks after co-mention: {final_count}")
        print(f"   Compositional: {entities.is_compositional}")
        if entities.is_compositional:
            print(f"   X terms: {entities.x_terms}")
            print(f"   Y terms: {entities.y_terms}")
            print(f"   Disambiguators: {entities.disambiguators}")

# Global instance
sentence_level_retrieval_service = SentenceLevelRetrievalService()
