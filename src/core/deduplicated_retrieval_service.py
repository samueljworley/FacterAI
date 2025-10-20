"""
Deduplicated retrieval service with inflammation evidence tightening and relation scoring
"""
import time
import os
import requests
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .response_context import Chunk, ResponseContext, context_manager
from .working_query_parser import working_query_parser, ExtractedEntities
from dotenv import load_dotenv

load_dotenv()

@dataclass
class EvidenceSentence:
    """Evidence sentence with citation info"""
    text: str
    chunk_id: str
    doc_id: str
    relation_cue_count: int
    study_type_prior: float = 0.0

@dataclass
class DeduplicatedChunk:
    """Deduplicated chunk with aggregated evidence sentences"""
    chunk: Chunk
    evidence_sentences: List[EvidenceSentence]
    doc_id: str
    cross_encoder_score: float
    relation_bonus: float
    study_type_prior: float
    total_score: float
    evidence_count: int

class DeduplicatedRetrievalService:
    """Retrieval service with deduplication and inflammation evidence tightening"""
    
    def __init__(self):
        self.max_chunks = 12
        self.min_chunks = 6
        self.min_docs = 3
        self.max_evidence_sentences = 10
        self.token_budget = 1200
        self.lambda_url = os.getenv('LAMBDA_SEARCH_URL')
        if not self.lambda_url:
            raise RuntimeError("LAMBDA_SEARCH_URL not found in environment variables")
        
        # Inflammation evidence patterns
        self.inflammation_patterns = [
            r'\b(?:neuro)?inflammation\b',
            r'\bglial activation\b',
            r'\bmicroglia(?:l)? activation\b',
            r'\bastrocyte activation\b',
            r'\bcytokine(?:s)?\b',
            r'\binterleukin\b',
            r'\bTNF-α\b',
            r'\bIL-1β\b',
            r'\bCRP\b',
            r'\bNF-κB\b'
        ]
        
        # Negative patterns for inflammatory diseases
        self.negative_inflammation_patterns = [
            r'\binflammatory bowel disease\b',
            r'\binflammatory myopathy\b',
            r'\binflammatory arthritis\b',
            r'\binflammatory neuropathy\b',
            r'\binflammatory cardiomyopathy\b'
        ]
        
        # Relation cues for scoring
        self.relation_cues = [
            r'\bassociated with\b',
            r'\blinked to\b',
            r'\bincreases?\b',
            r'\breduces?\b',
            r'\belevated\b',
            r'\bdecreased\b',
            r'\bpredicts?\b',
            r'\bcorrelates?\b',
            r'\brisk\b',
            r'\bodds ratio\b',
            r'\bhazard ratio\b',
            r'\bno significant\b'
        ]
        
        # Study type priors
        self.study_type_priors = {
            'meta': 0.25,
            'rct': 0.25,
            'systematic review': 0.25,
            'human': 0.15,
            'clinical': 0.15,
            'observational': 0.15,
            'animal': 0.05,
            'mouse': 0.05,
            'rat': 0.05,
            'in vitro': 0.0,
            'cell': 0.0
        }
        
        print(f"✅ Initializing deduplicated retrieval service with URL: {self.lambda_url}")
    
    def retrieve(self, query: str, size: int = 20) -> ResponseContext:
        """
        Deduplicated retrieval with inflammation evidence tightening
        """
        start_time = time.time()
        
        try:
            # Parse query for entities
            entities = working_query_parser.extract_entities(query)
            
            # Get initial results from Lambda (RRF top 200)
            initial_papers = self._search_with_lambda(query, 200)
            
            # Apply sentence-level filtering for compositional queries
            if entities.is_compositional:
                enhanced_chunks = self._apply_sentence_level_filter(initial_papers, entities)
                
                # Deduplicate by PMID/DOI
                deduplicated_chunks = self._deduplicate_chunks(enhanced_chunks)
                
                # Check if we have sufficient evidence
                if len(deduplicated_chunks) < self.min_chunks:
                    return self._create_insufficient_evidence_context(query, len(deduplicated_chunks))
                
                # Check if we have sufficient distinct docs
                distinct_docs = len(set(chunk.doc_id for chunk in deduplicated_chunks))
                if distinct_docs < self.min_docs:
                    return self._create_insufficient_evidence_context(query, len(deduplicated_chunks))
                
                # Select top chunks
                selected_chunks = deduplicated_chunks[:self.max_chunks]
                
                # Convert to regular chunks for response context
                regular_chunks = [chunk.chunk for chunk in selected_chunks]
                
                # Store enhanced data for generation
                context = context_manager.create_context(
                    query=query,
                    selected_chunks=regular_chunks,
                    retrieval_latency_ms=(time.time() - start_time) * 1000
                )
                context.enhanced_chunks = selected_chunks
                
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
    
    def _apply_sentence_level_filter(self, papers: List[Dict[str, Any]], entities: ExtractedEntities) -> List[DeduplicatedChunk]:
        """Apply sentence-level co-mention filtering with inflammation tightening"""
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
            
            # Find evidence sentences with inflammation tightening
            evidence_sentences = []
            for sentence in sentences:
                if self._sentence_contains_both_entities(sentence, entities):
                    # Apply inflammation evidence gate if X is inflammation
                    if self._is_inflammation_query(entities) and not self._passes_inflammation_gate(sentence, entities):
                        continue
                    
                    relation_cue_count = self._count_relation_cues(sentence)
                    study_type_prior = self._get_study_type_prior(paper)
                    
                    evidence_sentence = EvidenceSentence(
                        text=sentence,
                        chunk_id=chunk.id,
                        doc_id=chunk.pmid_or_doi,
                        relation_cue_count=relation_cue_count,
                        study_type_prior=study_type_prior
                    )
                    evidence_sentences.append(evidence_sentence)
            
            # Keep chunk only if it has evidence sentences
            if evidence_sentences:
                # Calculate scores
                cross_encoder_score = paper.get('score', 0.0)
                relation_bonus = sum(sentence.relation_cue_count for sentence in evidence_sentences) * 0.1
                study_type_prior = max(sentence.study_type_prior for sentence in evidence_sentences)
                total_score = cross_encoder_score + relation_bonus + study_type_prior
                
                enhanced_chunk = DeduplicatedChunk(
                    chunk=chunk,
                    evidence_sentences=evidence_sentences,
                    doc_id=chunk.pmid_or_doi,
                    cross_encoder_score=cross_encoder_score,
                    relation_bonus=relation_bonus,
                    study_type_prior=study_type_prior,
                    total_score=total_score,
                    evidence_count=len(evidence_sentences)
                )
                enhanced_chunks.append(enhanced_chunk)
        
        # Sort by total score
        enhanced_chunks.sort(key=lambda x: x.total_score, reverse=True)
        
        return enhanced_chunks
    
    def _deduplicate_chunks(self, chunks: List[DeduplicatedChunk]) -> List[DeduplicatedChunk]:
        """Deduplicate chunks by PMID/DOI, aggregating evidence sentences"""
        doc_map = {}
        
        for chunk in chunks:
            doc_id = chunk.doc_id
            if doc_id in doc_map:
                # Aggregate evidence sentences
                doc_map[doc_id].evidence_sentences.extend(chunk.evidence_sentences)
                doc_map[doc_id].evidence_count += chunk.evidence_count
                # Keep the highest score
                if chunk.total_score > doc_map[doc_id].total_score:
                    doc_map[doc_id].total_score = chunk.total_score
                    doc_map[doc_id].cross_encoder_score = chunk.cross_encoder_score
                    doc_map[doc_id].relation_bonus = chunk.relation_bonus
                    doc_map[doc_id].study_type_prior = chunk.study_type_prior
            else:
                doc_map[doc_id] = chunk
        
        # Convert back to list and sort
        deduplicated = list(doc_map.values())
        deduplicated.sort(key=lambda x: x.total_score, reverse=True)
        
        return deduplicated
    
    def _is_inflammation_query(self, entities: ExtractedEntities) -> bool:
        """Check if X entity is inflammation"""
        inflammation_terms = ['inflammation', 'inflammatory', 'swelling', 'irritation']
        return any(term in entities.x_terms for term in inflammation_terms)
    
    def _passes_inflammation_gate(self, sentence: str, entities: ExtractedEntities) -> bool:
        """Check if sentence passes inflammation evidence gate"""
        sentence_lower = sentence.lower()
        
        # Check for explicit inflammation patterns
        has_inflammation_pattern = any(re.search(pattern, sentence_lower, re.IGNORECASE) for pattern in self.inflammation_patterns)
        
        if not has_inflammation_pattern:
            return False
        
        # Check for negative patterns (inflammatory diseases)
        has_negative_pattern = any(re.search(pattern, sentence_lower, re.IGNORECASE) for pattern in self.negative_inflammation_patterns)
        
        if has_negative_pattern:
            # Check if the disease is explicitly in the query
            query_lower = entities.original_query.lower()
            disease_in_query = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in self.negative_inflammation_patterns)
            if not disease_in_query:
                return False
        
        return True
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
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
        for pattern in self.relation_cues:
            if re.search(pattern, sentence_lower, re.IGNORECASE):
                count += 1
        return count
    
    def _get_study_type_prior(self, paper: Dict[str, Any]) -> float:
        """Get study type prior from paper metadata"""
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        
        for study_type, prior in self.study_type_priors.items():
            if study_type in text:
                return prior
        
        return 0.0
    
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
        print(f"📊 Deduplicated Telemetry - Query: '{query}'")
        print(f"   RRF candidates: {initial_count}")
        print(f"   Chunks after co-mention: {final_count}")
        print(f"   Compositional: {entities.is_compositional}")
        if entities.is_compositional:
            print(f"   X terms: {entities.x_terms}")
            print(f"   Y terms: {entities.y_terms}")
            print(f"   Disambiguators: {entities.disambiguators}")

# Global instance
deduplicated_retrieval_service = DeduplicatedRetrievalService()
