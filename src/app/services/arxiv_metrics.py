from typing import Dict, Optional

class ArxivMetrics:
    def __init__(self):
        # Category impact weights based on typical citation patterns
        self.category_weights = {
            'physics.hep-th': 0.9,  # High Energy Physics - Theory
            'physics.hep-ex': 0.85,  # High Energy Physics - Experimental
            'astro-ph': 0.8,        # Astrophysics
            'cond-mat': 0.75,       # Condensed Matter
            'math': 0.7,            # Mathematics
            'cs.AI': 0.85,          # Computer Science - AI
            'cs.ML': 0.85,          # Machine Learning
            'q-bio': 0.7,           # Quantitative Biology
            'default': 0.5
        }

    def get_paper_weight(self, category: str, citation_count: int = 0) -> float:
        """Calculate paper weight based on category and citations"""
        base_weight = self.category_weights.get(category, self.category_weights['default'])
        citation_impact = min(citation_count * 0.01, 0.5)  # Cap citation impact at 0.5
        return base_weight + citation_impact

    def format_arxiv_identifier(self, arxiv_id: str) -> str:
        """Format arXiv identifier for citation"""
        return f"arXiv:{arxiv_id}" 