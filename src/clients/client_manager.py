from typing import Dict, List, Any, Set
from .europepmc_client import EuropePMCClient
from .arxiv_client import ArxivClient
import re
from datetime import datetime
import os
USE_PUBMED = os.getenv("USE_PUBMED", "0") == "1"
if USE_PUBMED:
    from .pubmed_client import PubMedClient


class ResearchClientManager:
    """Manages multiple research paper clients with subject-based routing."""
    
    # Define subject keywords for classification
    SUBJECT_KEYWORDS = {
        'biology': {
            'cell', 'plant', 'animal', 'organism', 'biology', 'protein', 
            'dna', 'rna', 'enzyme', 'metabolism', 'photosynthesis', 
            'mitochondria', 'chloroplast', 'nucleus', 'membrane'
        },
        'medical': {
            'disease', 'health', 'medical', 'clinical', 'patient', 'therapy', 'drug',
            'treatment', 'symptoms', 'diagnosis', 'cancer', 'medicine', 'hospital',
            'doctor', 'pharmaceutical', 'surgery'
        },
        'physics': {
            'physics', 'quantum', 'particle', 'energy', 'force', 'motion', 'gravity',
            'electromagnetic', 'mechanics', 'relativity', 'thermodynamics', 'atoms'
        },
        'math': {
            'mathematics', 'algebra', 'geometry', 'calculus', 'theorem', 'equation',
            'probability', 'statistics', 'mathematical', 'numerical', 'computation',
            'vector', 'orthogonal', 'projection', 'linear algebra', 'matrix', 'space',
            'basis', 'dimension', 'subspace', 'transformation'
        },
        'computer_science': {
            'computer science', 'algorithm', 'programming', 'software',
            'artificial intelligence', 'network architecture',  # more specific terms
        }
    }
    
    def __init__(self):
        """Initialize clients for different sources."""
        self.clients = {
            #'pubmed': PubMedClient(),
            'europepmc': EuropePMCClient(),
            'arxiv': ArxivClient()
        }
        if USE_PUBMED:
            self.clients['pubmed'] = PubMedClient()
        # Map subjects to appropriate clients
        self.subject_to_clients = {
            'medical': ['pubmed', 'europepmc'],
            'physics': ['arxiv'],
            'math': ['arxiv'],
            'computer_science': ['arxiv']
        }
    

    def _classify_query(self, query: str) -> Set[str]:
        """Classify the query into relevant subject areas."""
        query_lower = query.lower()
        subjects = set()
        
        # Check each subject's keywords
        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    subjects.add(subject)
                    break
        
        print(f"Query '{query}' classified as subjects: {subjects}")
        
        # If no specific subject is detected, use all subjects
        if not subjects:
            print("No specific subject detected, using all sources")
            return set(self.subject_to_clients.keys())
            
        return subjects
    
    def _get_relevant_clients(self, subjects: Set[str]) -> List[str]:
        """Get list of relevant clients based on subjects."""
        relevant_clients = set()
        for subject in subjects:
            relevant_clients.update(self.subject_to_clients.get(subject, []))
        
        # If no relevant clients found, use all clients
        if not relevant_clients:
            relevant_clients = set(self.clients.keys())
            
        print(f"Selected clients: {relevant_clients}")
        return list(relevant_clients)
    
    async def search_all(self, query: str, max_results_per_source: int = 3) -> List[Dict[str, Any]]:
        """Search across relevant sources based on query classification."""
        all_results = []
        
        # Classify query and get relevant clients
        subjects = self._classify_query(query)
        relevant_clients = self._get_relevant_clients(subjects)
        
        print(f"Searching with query: '{query}'")
        print(f"Using clients: {relevant_clients}")
        
        # Search using relevant clients
        for client_name in relevant_clients:
            client = self.clients[client_name]
            try:
                print(f"\nSearching {client_name}...")
                results = await client.search(query, max_results_per_source)
                print(f"Found {len(results)} results from {client_name}")
                
                # Tag each result with its source if not already tagged
                for result in results:
                    if 'source' not in result:
                        result['source'] = client_name
                    print(f"Paper from {client_name}: {result.get('title', 'No title')}")
                
                all_results.extend(results)
                
            except Exception as e:
                print(f"Error searching {client_name}: {str(e)}")
        
        print(f"\nTotal results found: {len(all_results)}")
        
        # Sort results by relevance
        sorted_results = self._sort_by_relevance(all_results, query)
        
        return sorted_results[:max_results_per_source * len(relevant_clients)]
    
    def _sort_by_relevance(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Sort results by relevance to query."""
        for result in results:
            score = 0
            
            # Title match weight
            if query.lower() in result.get('title', '').lower():
                score += 3
            
            # Abstract match weight
            if query.lower() in result.get('abstract', '').lower():
                score += 2
            
            result['relevance_score'] = score
        
        sorted_results = sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Remove scoring information before returning
        for result in sorted_results:
            result.pop('relevance_score', None)
            
        return sorted_results
    
    def calculate_relevance_score(self, paper: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for a paper based on multiple factors."""
        score = 0.0
        query_terms = set(re.findall(r'\w+', query.lower()))
        
        # Title relevance (0-3 points)
        title = paper.get('title', '').lower()
        title_terms = set(re.findall(r'\w+', title))
        title_match = len(query_terms.intersection(title_terms)) / len(query_terms)
        score += title_match * 3
        
        # Abstract relevance (0-2 points)
        abstract = paper.get('abstract', '').lower()
        abstract_terms = set(re.findall(r'\w+', abstract))
        abstract_match = len(query_terms.intersection(abstract_terms)) / len(query_terms)
        score += abstract_match * 2
        
        # Recency (0-1 points)
        try:
            pub_date = paper.get('publication_date', '')
            if pub_date:
                year = int(pub_date[:4])
                current_year = datetime.now().year
                recency = max(0, 1 - (current_year - year) / 10)  # Newer papers score higher
                score += recency
        except (ValueError, TypeError):
            pass
        
        # Citation count or journal impact (if available)
        if paper.get('citation_count'):
            score += min(paper['citation_count'] / 100, 1)  # Max 1 point for citations
            
        return round(score, 2)
    
    def select_best_papers(self, papers: List[Dict[str, Any]], query: str, max_results: int) -> List[Dict[str, Any]]:
        """Select the best papers ensuring source diversity."""
        if not papers:
            return []
            
        # Sort all papers by relevance score
        sorted_papers = sorted(papers, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Initialize selection tracking
        selected = []
        source_counts = {}
        min_per_source = max_results // len(self.clients)  # Ensure minimum representation
        
        # First pass: ensure minimum representation from each source
        for paper in sorted_papers:
            source = paper['source']
            if source_counts.get(source, 0) < min_per_source:
                selected.append(paper)
                source_counts[source] = source_counts.get(source, 0) + 1
                
        # Second pass: fill remaining slots with best papers regardless of source
        remaining_slots = max_results - len(selected)
        if remaining_slots > 0:
            unselected = [p for p in sorted_papers if p not in selected]
            selected.extend(unselected[:remaining_slots])
        
        # Sort final selection by relevance score
        selected.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Remove scoring information before returning
        for paper in selected:
            paper.pop('relevance_score', None)
        
        return selected
    
    async def get_paper_details(self, paper_id: str, source: str) -> Dict[str, Any]:
        """Get paper details from specified source."""
        if source not in self.clients:
            raise ValueError(f"Unknown source: {source}")
        
        return await self.clients[source].get_paper_details(paper_id) 
