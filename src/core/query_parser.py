"""
Query parsing and entity extraction for compositional queries
"""
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ExtractedEntities:
    """Extracted entities from a compositional query"""
    x_terms: List[str]
    y_terms: List[str]
    is_compositional: bool
    original_query: str

class QueryParser:
    """Parser for extracting entities from compositional queries"""
    
    def __init__(self):
        # Common domain synonyms
        self.synonyms = {
            'microplastics': ['microplastics', 'microplastic', 'plastic particles', 'nanoplastics', 'plastic debris'],
            'testosterone': ['testosterone', 'test', 'androgen', 'male hormone', 'T'],
            'alzheimer': ['alzheimer', 'alzheimer\'s', 'dementia', 'cognitive decline', 'neurodegeneration'],
            'cancer': ['cancer', 'tumor', 'neoplasm', 'malignancy', 'carcinoma'],
            'diabetes': ['diabetes', 'diabetic', 'blood sugar', 'glucose', 'insulin'],
            'inflammation': ['inflammation', 'inflammatory', 'swelling', 'irritation'],
            'cardiovascular': ['cardiovascular', 'heart', 'cardiac', 'circulatory', 'vascular'],
            'immune': ['immune', 'immunity', 'immunological', 'defense', 'resistance'],
            'oxidative': ['oxidative', 'oxidation', 'free radicals', 'antioxidant'],
            'stress': ['stress', 'stressor', 'pressure', 'tension']
        }
        
        # Compositional query patterns
        self.patterns = [
            # "effect/impact of X on Y"
            r'(?:effect|impact|influence|role)\s+of\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+on\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
            # "does X affect Y"
            r'does\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+affect\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
            # "X and Y association/relationship"
            r'([^,\s]+(?:\s+[^,\s]+)*?)\s+and\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+(?:association|relationship|correlation|link)',
            # "X vs Y"
            r'([^,\s]+(?:\s+[^,\s]+)*?)\s+vs\.?\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
            # "X compared to Y"
            r'([^,\s]+(?:\s+[^,\s]+)*?)\s+compared\s+to\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
            # "X treatment for Y"
            r'([^,\s]+(?:\s+[^,\s]+)*?)\s+treatment\s+for\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
            # "X in Y"
            r'([^,\s]+(?:\s+[^,\s]+)*?)\s+in\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
        ]
    
    def extract_entities(self, query: str) -> ExtractedEntities:
        """Extract X and Y entities from compositional queries"""
        query_lower = query.lower().strip()
        
        # Try each pattern
        for pattern in self.patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                x_raw = match.group(1).strip()
                y_raw = match.group(2).strip()
                
                # Expand with synonyms
                x_terms = self._expand_terms(x_raw)
                y_terms = self._expand_terms(y_raw)
                
                return ExtractedEntities(
                    x_terms=x_terms,
                    y_terms=y_terms,
                    is_compositional=True,
                    original_query=query
                )
        
        # Single entity query - extract main terms
        main_terms = self._extract_main_terms(query)
        return ExtractedEntities(
            x_terms=main_terms,
            y_terms=[],
            is_compositional=False,
            original_query=query
        )
    
    def _expand_terms(self, term: str) -> List[str]:
        """Expand a term with synonyms"""
        term_lower = term.lower()
        expanded = [term]  # Include original term
        
        # Find matching synonym groups
        for key, synonyms in self.synonyms.items():
            if any(syn in term_lower for syn in synonyms):
                expanded.extend(synonyms)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for t in expanded:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique_terms.append(t)
        
        return unique_terms
    
    def _extract_main_terms(self, query: str) -> List[str]:
        """Extract main terms from single-entity queries"""
        # Remove common stop words
        stop_words = {'what', 'is', 'the', 'best', 'for', 'how', 'does', 'work', 'treatment', 'therapy'}
        
        words = re.findall(r'\b\w+\b', query.lower())
        main_terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Expand with synonyms
        expanded = []
        for term in main_terms:
            expanded.extend(self._expand_terms(term))
        
        return list(set(expanded))  # Remove duplicates

# Global instance
query_parser = QueryParser()
