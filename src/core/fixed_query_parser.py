"""
Fixed query parser that correctly handles compositional queries
"""
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ExtractedEntities:
    """Enhanced extracted entities with disambiguators"""
    x_terms: List[str]
    y_terms: List[str]
    disambiguators: List[str]
    is_compositional: bool
    original_query: str

class FixedQueryParser:
    """Fixed parser that correctly handles compositional queries"""
    
    def __init__(self):
        # Common domain synonyms
        self.synonyms = {
            'microplastics': ['microplastics', 'microplastic', 'plastic particles', 'nanoplastics', 'plastic debris'],
            'testosterone': ['testosterone', 'test', 'androgen', 'male hormone', 'T'],
            'alzheimer': ['alzheimer', 'alzheimer\'s', 'dementia', 'cognitive decline', 'neurodegeneration'],
            'cancer': ['cancer', 'tumor', 'neoplasm', 'malignancy', 'carcinoma'],
            'diabetes': ['diabetes', 'diabetic', 'blood sugar', 'glucose', 'insulin'],
            'inflammation': ['inflammation', 'inflammatory', 'swelling', 'irritation', 'inflammatory response'],
            'cardiovascular': ['cardiovascular', 'heart', 'cardiac', 'circulatory', 'vascular'],
            'immune': ['immune', 'immunity', 'immunological', 'defense', 'resistance'],
            'oxidative': ['oxidative', 'oxidation', 'free radicals', 'antioxidant'],
            'stress': ['stress', 'stressor', 'pressure', 'tension'],
            'creatine': ['creatine', 'creatinine', 'creatine supplementation', 'creatine monohydrate'],
            'kidney': ['kidney', 'renal', 'kidney function', 'egfr', 'creatinine', 'glomerular filtration']
        }
        
        # AD disambiguators to avoid atopic dermatitis, etc.
        self.ad_disambiguators = [
            "alzheimer", "alzheimer's", "ad", "aβ", "beta-amyloid", "amyloid", 
            "tau", "tauopathy", "hippocamp", "hippocampal", "cognitive", 
            "dementia", "neurodegeneration", "neurofibrillary", "plaques"
        ]
        
        # Clear compositional query patterns - try these FIRST
        self.compositional_patterns = [
            # "effect/impact of X on Y" - must have clear X and Y
            r'(?:effect|impact|influence|role)\s+of\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+on\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
            # "does X affect Y" - must have clear X and Y
            r'does\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+affect\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
            # "X and Y association/relationship" - must have clear X and Y
            r'([^,\s]+(?:\s+[^,\s]+)*?)\s+and\s+([^,\s]+(?:\s+[^,\s]+)*?)\s+(?:association|relationship|correlation|link)',
            # "X vs Y" - must have clear X and Y
            r'([^,\s]+(?:\s+[^,\s]+)*?)\s+vs\.?\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
            # "X compared to Y" - must have clear X and Y
            r'([^,\s]+(?:\s+[^,\s]+)*?)\s+compared\s+to\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
            # "X treatment for Y" - must have clear X and Y
            r'([^,\s]+(?:\s+[^,\s]+)*?)\s+treatment\s+for\s+([^,\s]+(?:\s+[^,\s]+)*?)(?:\s|$)',
        ]
        
        # Single entity patterns that should NOT be treated as compositional
        # These are more specific to avoid overriding compositional patterns
        self.single_entity_indicators = [
            r'does\s+.*\s+impair\s+',  # "does X impair Y" - single entity about X
            r'does\s+.*\s+improve\s+',  # "does X improve Y" - single entity about X
            r'does\s+.*\s+increase\s+', # "does X increase Y" - single entity about X
            r'does\s+.*\s+decrease\s+', # "does X decrease Y" - single entity about X
            r'how\s+does\s+',  # "how does X" - single entity
            r'what\s+are\s+the\s+effects\s+of\s+',  # "what are the effects of X" - single entity
            # Remove the problematic pattern that was overriding compositional queries
        ]
    
    def extract_entities(self, query: str) -> ExtractedEntities:
        """Extract X and Y entities with corrected logic"""
        query_lower = query.lower().strip()
        
        # FIRST: Try compositional patterns
        for pattern in self.compositional_patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                x_raw = match.group(1).strip()
                y_raw = match.group(2).strip()
                
                # Validate that X and Y are distinct entities
                if self._are_distinct_entities(x_raw, y_raw):
                    # Expand with synonyms
                    x_terms = self._expand_terms(x_raw)
                    y_terms = self._expand_terms(y_raw)
                    
                    # Add disambiguators if Y contains AD
                    disambiguators = []
                    if self._contains_ad(y_terms):
                        disambiguators = self.ad_disambiguators.copy()
                    
                    return ExtractedEntities(
                        x_terms=x_terms,
                        y_terms=y_terms,
                        disambiguators=disambiguators,
                        is_compositional=True,
                        original_query=query
                    )
        
        # SECOND: Check if this looks like a single-entity query
        if self._is_single_entity_query(query_lower):
            main_terms = self._extract_main_terms(query)
            return ExtractedEntities(
                x_terms=main_terms,
                y_terms=[],
                disambiguators=[],
                is_compositional=False,
                original_query=query
            )
        
        # FALLBACK: Single entity
        main_terms = self._extract_main_terms(query)
        return ExtractedEntities(
            x_terms=main_terms,
            y_terms=[],
            disambiguators=[],
            is_compositional=False,
            original_query=query
        )
    
    def _is_single_entity_query(self, query_lower: str) -> bool:
        """Check if this looks like a single-entity query"""
        # Check for single entity indicators
        for pattern in self.single_entity_indicators:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return True
        
        # Check if query is about one main topic with related concepts
        # e.g., "creatine supplementation and kidney function" is about creatine, not two separate entities
        if ' and ' in query_lower and not any(word in query_lower for word in ['association', 'relationship', 'correlation', 'link', 'vs', 'compared']):
            return True
        
        return False
    
    def _are_distinct_entities(self, x_raw: str, y_raw: str) -> bool:
        """Check if X and Y are distinct entities (not related concepts)"""
        # Single words can be distinct entities
        
        # If X and Y share many words, they might be related concepts
        x_words = set(x_raw.lower().split())
        y_words = set(y_raw.lower().split())
        overlap = len(x_words.intersection(y_words))
        
        # If more than 30% overlap, treat as single entity
        if overlap > 0.3 * min(len(x_words), len(y_words)):
            return False
        
        return True
    
    def _contains_ad(self, terms: List[str]) -> bool:
        """Check if terms contain AD-related terms"""
        ad_indicators = ['ad', 'alzheimer', 'dementia', 'cognitive']
        return any(any(indicator in term.lower() for indicator in ad_indicators) for term in terms)
    
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
        stop_words = {'what', 'is', 'the', 'best', 'for', 'how', 'does', 'work', 'treatment', 'therapy', 'in', 'adults', 'healthy'}
        
        words = re.findall(r'\b\w+\b', query.lower())
        main_terms = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Expand with synonyms
        expanded = []
        for term in main_terms:
            expanded.extend(self._expand_terms(term))
        
        return list(set(expanded))  # Remove duplicates

# Global instance
fixed_query_parser = FixedQueryParser()
