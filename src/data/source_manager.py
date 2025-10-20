from typing import List, Dict, Any
#import boto3
from faiss import Index
import wikipedia
import requests
from bs4 import BeautifulSoup
from db.reranker import SearchReranker
from src.embeddings.embedder import TextEmbedder
from src.embeddings.faiss_index import FAISSIndexManager
import numpy as np
import os
USE_PUBMED = os.getenv("USE_PUBMED", "0") == "1"

if USE_PUBMED:
    from src.data_collection.pubmed_client import PubMedClient
    from src.embeddings.fetch_pubmed import PubMedFetcher
else:
    PubMedClient = None      # type: ignore
    PubMedFetcher = None     # type: ignore

class DataSourceManager:
    def __init__(self):
        """Initialize connections to different data sources"""
        try:
            print("Initializing DataSourceManager...")
            
            # Initialize PubMed fetcher with email
            
            self.pubmed_client = PubMedClient(...) if USE_PUBMED else None
            self.pubmed_fetcher = PubMedFetcher(...) if USE_PUBMED else None

            
            # Rest of your initialization...
            self.faiss_research = None
            self.reranker = SearchReranker()
             # Initialize PubMed client
            #self.s3 = boto3.client('s3')
            self.embedder = TextEmbedder(api_key=os.getenv('OPENAI_API_KEY'))
            self.index_manager = FAISSIndexManager(index_path="src/embeddings/research_index")
            
            # Load the FAISS index with detailed error checking
            try:
                print("Loading FAISS index from:", self.index_manager.index_path)
                self.index_manager.load()
                # Verify index is loaded
                if self.index_manager.index is not None:
                    print("FAISS index loaded successfully")
                    # Try a test search to verify functionality
                    test_embedding = np.zeros(1536)  # Adjust dimension if needed
                    test_results = self.index_manager.search(test_embedding, k=1)
                    print(f"FAISS index test search successful. Index is operational.")
                else:
                    print("WARNING: FAISS index loaded but appears to be empty")
            except Exception as e:
                print(f"ERROR loading FAISS index: {str(e)}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"ERROR in __init__: {str(e)}")
            import traceback
            traceback.print_exc()
        
    def get_sources(self, query: str, query_type: str = "research") -> Dict[str, Any]:
        """Get relevant sources for a query"""
        print(f"\n=== Starting source search for query: {query} ===")  # Debug log
        
        try:
            if query_type != "research":
                print("Not a research query, skipping source search")  # Debug log
                return {"sources": []}

            sources = []
            
            # 1. Search FAISS index
            print("Searching FAISS index...")  # Debug log
            query_embedding = self.embedder.get_embedding(query)
            faiss_results = self.index_manager.search(query_embedding, k=3)
            print(f"FAISS results found: {len(faiss_results)}")  # Debug log
            
            # 2. Search PubMed
            print("Searching PubMed...")  # Debug log
            pubmed_results = self._get_research_papers(query)
            pubmed_sources = pubmed_results.get("sources", [])
            print(f"PubMed results found: {len(pubmed_sources)}")  # Debug log
            
            if not faiss_results and not pubmed_sources:
                print("WARNING: No results found in either FAISS or PubMed")  # Debug log
                return {"sources": []}

            # 3. Combine and deduplicate results
            seen_titles = set()
            
            # Add FAISS results
            for result in faiss_results:
                title = result.get('title', '').lower()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    sources.append({
                        'title': result.get('title', 'Untitled'),
                        'authors': result.get('authors', []),
                        'abstract': result.get('text', ''),
                        'year': result.get('year', ''),
                        'journal': result.get('journal', ''),
                        'score': float(1 - result.get('distance', 0))
                    })
                    print(f"Added FAISS result: {title}")  # Debug log
            
            # Add PubMed results
            for paper in pubmed_sources:
                title = paper.get('title', '').lower()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    sources.append(self._format_source(paper))
                    print(f"Added PubMed result: {title}")  # Debug log

            print(f"\nFinal results: {len(sources)} total sources")  # Debug log
            return {"sources": sources[:5]}  # Return top 5 combined results

        except Exception as e:
            print(f"ERROR in get_sources: {str(e)}")  # Debug log
            import traceback
            traceback.print_exc()  # Print full stack trace
            return {"sources": []}

    def _format_source(self, source: Dict) -> Dict:
        """Format a source into a standardized structure"""
        return {
            'title': source.get('title', ''),
            'authors': source.get('authors', []),
            'abstract': source.get('abstract', ''),
            'year': source.get('year', ''),
            'journal': source.get('journal', ''),
            'pmid': source.get('pmid', '')
        }

    def _get_research_papers(self, query: str) -> Dict[str, Any]:
        """Search PubMed and rerank results"""
        try:
            # Format query for better PubMed results
            print("Original query:", query)
            
            # Use the actual user query instead of hardcoded microplastics query
            pubmed_query = query
            
            print("Using PubMed query:", pubmed_query)
            
            # Search PubMed
            papers = self.pubmed_fetcher.fetch_abstracts(pubmed_query, max_results=10)
            
            if not papers:
                print("No results with primary query, trying broader search...")
                # Try a broader backup query using the original query terms
                backup_query = query.replace("[Title/Abstract]", "")
                papers = self.pubmed_fetcher.fetch_abstracts(backup_query, max_results=10)
            
            print(f"Found {len(papers)} papers")
            
            if papers:
                # Format papers for the response
                formatted_papers = []
                for paper in papers:
                    formatted_paper = self._format_source(paper)
                    formatted_papers.append(formatted_paper)
                    print(f"Added paper: {formatted_paper['title']}")
                
                return {"type": "research", "sources": formatted_papers}
            
            return {"type": "research", "sources": []}
            
        except Exception as e:
            print(f"Error in research paper search: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"type": "research", "sources": []}

    def _get_solution_sources(self, query: str) -> Dict[str, Any]:
        """Get mathematical/physics solution sources"""
        return {"type": "solution", "sources": []}

    def _get_concept_sources(self, query: str) -> Dict[str, Any]:
        """Get concept explanation sources"""
        try:
            print(f"Searching Wikipedia for: {query}")  # Debug print
            wiki_results = self._search_wikipedia(query)
            print(f"Wiki results: {wiki_results}")  # Debug print
            
            sources = {
                "type": "concept",
                "sources": {
                    "wikipedia": wiki_results,
                    "openstax": []  # Placeholder for now
                }
            }
            return sources
            
        except Exception as e:
            print(f"Error in _get_concept_sources: {str(e)}")
            return {"type": "concept", "sources": []}

    def _get_coding_sources(self, query: str) -> Dict[str, Any]:
        """Get coding-related sources"""
        return {"type": "coding", "sources": []}

    # Individual source methods
    def _query_wolfram(self, query: str) -> Dict[str, Any]:
        """Query Wolfram Alpha API"""
        # Implement Wolfram Alpha API call
        pass

    def _solve_with_sympy(self, query: str) -> Dict[str, Any]:
        """Use SymPy for mathematical solutions"""
        # Implement SymPy solution
        pass

    def _search_khan_academy(self, query: str) -> Dict[str, Any]:
        """Search Khan Academy content"""
        # Implement Khan Academy API/scraping
        pass

    def _search_wikipedia(self, query: str) -> List[Dict[str, str]]:
        """Search Wikipedia articles"""
        try:
            print(f"Searching Wikipedia for: {query}")  # Debug log
            results = wikipedia.search(query, results=3)
            pages = []
            
            for title in results:
                try:
                    page = wikipedia.page(title, auto_suggest=False)  # Disable auto-suggest for exact matches
                    pages.append({
                        "title": page.title,
                        "summary": page.summary[:500] + "...",  # Truncate long summaries
                        "url": page.url
                    })
                except (wikipedia.exceptions.DisambiguationError, 
                       wikipedia.exceptions.PageError) as e:
                    print(f"Wikipedia error for {title}: {str(e)}")
                    continue
                
            print(f"Found {len(pages)} Wikipedia pages")  # Debug log
            return pages
            
        except Exception as e:
            print(f"Wikipedia search error: {str(e)}")
            return []

    def _search_openstax(self, query: str) -> Dict[str, Any]:
        """Search OpenStax content"""
        # Implement OpenStax API/scraping
        pass

    def _search_stackoverflow(self, query: str) -> Dict[str, Any]:
        """Search Stack Overflow questions/answers"""
        # Implement Stack Exchange API
        pass

    def _search_github_discussions(self, query: str) -> Dict[str, Any]:
        """Search GitHub discussions"""
        # Implement GitHub API
        pass

    def test_pubmed_search(self):
        """Test function to verify PubMed search"""
        try:
            print("\n=== Testing PubMed Search ===")
            
            # Test with a general query instead of hardcoded microplastics
            test_query = "health effects of diet"
            print(f"Testing query: {test_query}")
            
            papers = self.pubmed_fetcher.fetch_abstracts(test_query, max_results=5)
            
            print(f"\nFound {len(papers)} papers:")
            for i, paper in enumerate(papers, 1):
                print(f"\n{i}. Title: {paper.get('title', 'No title')}")
                print(f"   Authors: {', '.join(paper.get('authors', []))}")
                print(f"   Year: {paper.get('year', 'No year')}")
                
            return papers
            
        except Exception as e:
            print(f"Test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return [] 