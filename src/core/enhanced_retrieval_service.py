"""
Enhanced retrieval service with compositional query support
"""
import time
import os
import requests
import re
from typing import List, Dict, Any, Optional, Tuple
from .response_context import Chunk, ResponseContext, context_manager
from .query_parser import query_parser, ExtractedEntities
from dotenv import load_dotenv

load_dotenv()

class EnhancedRetrievalService:
    """Enhanced retrieval service with compositional query filtering"""
    
    def __init__(self):
        self.max_chunks = 15
        self.min_chunks = 6
        self.lambda_url = os.getenv('LAMBDA_SEARCH_URL')
        if not self.lambda_url:
            raise RuntimeError("LAMBDA_SEARCH_URL not found in environment variables")
        
        print(f"✅ Initializing enhanced retrieval service with URL: {self.lambda_url}")
    
    def retrieve(self, query: str, size: int = 20) -> ResponseContext:
        """
        Enhanced retrieval with compositional query filtering
        """
        start_time = time.time()
        
        try:
            # Parse query for entities
            entities = query_parser.extract_entities(query)
            
            # Get initial results from Lambda
            initial_papers = self._search_with_lambda(query, size * 2)  # Get more for filtering
            
            # Apply intersection filtering for compositional queries
            if entities.is_compositional:
                filtered_papers = self._apply_intersection_filter(initial_papers, entities)
                
                # If insufficient results, try expanding synonyms
                if len(filtered_papers) < self.min_chunks:
                    print(f"⚠️ Insufficient results ({len(filtered_papers)}), expanding synonyms...")
                    entities_expanded = self._expand_entities(entities)
                    filtered_papers = self._apply_intersection_filter(initial_papers, entities_expanded)
                
                # If still insufficient, return insufficient evidence
                if len(filtered_papers) < self.min_chunks:
                    return self._create_insufficient_evidence_context(query, len(filtered_papers))
                
                papers = filtered_papers
            else:
                papers = initial_papers
            
            # Limit to max_chunks
            papers = papers[:self.max_chunks]
            
            # Convert to chunks
            selected_chunks = self._convert_papers_to_chunks(papers)
            
            retrieval_latency = (time.time() - start_time) * 1000
            
            # Create response context
            context = context_manager.create_context(
                query=query,
                selected_chunks=selected_chunks,
                retrieval_latency_ms=retrieval_latency
            )
            
            # Add telemetry
            self._log_telemetry(query, len(initial_papers), len(papers), entities)
            
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
    
    def _apply_intersection_filter(self, papers: List[Dict[str, Any]], entities: ExtractedEntities) -> List[Dict[str, Any]]:
        """Filter papers to those containing both X and Y entities"""
        filtered_papers = []
        
        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
            
            # Check if text contains any X terms AND any Y terms
            has_x = any(self._contains_term(text, term) for term in entities.x_terms)
            has_y = any(self._contains_term(text, term) for term in entities.y_terms)
            
            if has_x and has_y:
                # Calculate proximity score
                proximity_score = self._calculate_proximity_score(text, entities)
                paper['proximity_score'] = proximity_score
                filtered_papers.append(paper)
        
        # Sort by proximity score (higher is better)
        filtered_papers.sort(key=lambda x: x.get('proximity_score', 0), reverse=True)
        
        return filtered_papers
    
    def _contains_term(self, text: str, term: str) -> bool:
        """Check if text contains term with word boundaries"""
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _calculate_proximity_score(self, text: str, entities: ExtractedEntities) -> float:
        """Calculate proximity score for entity co-occurrence"""
        sentences = re.split(r'[.!?]+', text)
        max_proximity = 0.0
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check if sentence contains both entities
            has_x = any(self._contains_term(sentence_lower, term) for term in entities.x_terms)
            has_y = any(self._contains_term(sentence_lower, term) for term in entities.y_terms)
            
            if has_x and has_y:
                # Calculate token distance within sentence
                x_positions = []
                y_positions = []
                
                for term in entities.x_terms:
                    if self._contains_term(sentence_lower, term):
                        x_positions.extend(self._find_term_positions(sentence_lower, term))
                
                for term in entities.y_terms:
                    if self._contains_term(sentence_lower, term):
                        y_positions.extend(self._find_term_positions(sentence_lower, term))
                
                if x_positions and y_positions:
                    min_distance = min(abs(x - y) for x in x_positions for y in y_positions)
                    # Convert distance to score (closer = higher score)
                    proximity = max(0, 1.0 - (min_distance / 50.0))  # 50 token max distance
                    max_proximity = max(max_proximity, proximity)
        
        return max_proximity
    
    def _find_term_positions(self, text: str, term: str) -> List[int]:
        """Find positions of term in text"""
        positions = []
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            positions.append(match.start())
        return positions
    
    def _expand_entities(self, entities: ExtractedEntities) -> ExtractedEntities:
        """Expand entities with additional synonyms"""
        expanded_x = []
        expanded_y = []
        
        for term in entities.x_terms:
            expanded_x.extend(query_parser._expand_terms(term))
        
        for term in entities.y_terms:
            expanded_y.extend(query_parser._expand_terms(term))
        
        return ExtractedEntities(
            x_terms=list(set(expanded_x)),
            y_terms=list(set(expanded_y)),
            is_compositional=entities.is_compositional,
            original_query=entities.original_query
        )
    
    def _create_insufficient_evidence_context(self, query: str, count: int) -> ResponseContext:
        """Create context for insufficient evidence"""
        retrieval_latency = 0  # No actual retrieval time
        
        context = context_manager.create_context(
            query=query,
            selected_chunks=[],
            retrieval_latency_ms=retrieval_latency
        )
        
        # Add insufficient evidence marker
        context.insufficient_evidence = True
        context.evidence_count = count
        
        return context
    
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
    
    def _log_telemetry(self, query: str, initial_count: int, final_count: int, entities: ExtractedEntities):
        """Log telemetry data"""
        print(f"📊 Telemetry - Query: '{query}'")
        print(f"   Initial results: {initial_count}")
        print(f"   Final results: {final_count}")
        print(f"   Compositional: {entities.is_compositional}")
        if entities.is_compositional:
            print(f"   X terms: {entities.x_terms}")
            print(f"   Y terms: {entities.y_terms}")

# Global instance
enhanced_retrieval_service = EnhancedRetrievalService()
