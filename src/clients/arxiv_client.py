from typing import List, Dict, Any
from .base_client import ResearchClient
import aiohttp
import feedparser
import urllib.parse

class ArxivClient(ResearchClient):
    """Client for interacting with arXiv API."""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    # Map of arXiv categories for better search targeting
    CATEGORIES = {
        'physics': ['physics', 'cond-mat', 'quant-ph', 'gr-qc'],
        'math': ['math', 'math-ph'],
        'cs': ['cs'],
        'biology': ['q-bio'],
        'finance': ['q-fin'],
        'stats': ['stat'],
        'eess': ['eess'],  # Electrical Engineering and Systems Science
        'econ': ['econ']
    }
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search arXiv for papers matching the query."""
        try:
            # Format the search URL
            params = {
                'search_query': f'all:{query}',
                'start': 0,
                'max_results': max_results,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            print(f"\n=== arXiv Search Details ===")
            print(f"Query: {query}")
            print(f"Parameters: {params}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        content = await response.text()
                        print(f"Raw response received from arXiv")
                        
                        feed = feedparser.parse(content)
                        print(f"Total entries in feed: {len(feed.entries)}")
                        
                        papers = []
                        for entry in feed.entries:
                            paper = self.format_paper(entry)
                            if paper:
                                papers.append(paper)
                                print(f"Processed paper: {paper.get('title')} ({paper.get('arxiv_id')})")
                        
                        print(f"Successfully formatted {len(papers)} papers from arXiv")
                        return papers
                    else:
                        print(f"arXiv search error: Status {response.status}")
                        print(f"Error content: {await response.text()}")
                        return []
                        
        except Exception as e:
            print(f"arXiv search error: {str(e)}")
            print(f"Error type: {type(e)}")
            return []
    
    def format_paper(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Format arXiv paper data into standardized structure."""
        try:
            # Extract authors
            authors = [author.get('name', '') for author in entry.get('authors', [])]
            
            # Extract categories
            categories = [tag.get('term', '') for tag in entry.get('tags', [])]
            
            # Get primary category
            primary_category = entry.get('arxiv_primary_category', {}).get('term', '')
            
            # Format the paper
            formatted = {
                'title': entry.get('title', '').replace('\n', ' ').strip(),
                'abstract': entry.get('summary', '').replace('\n', ' ').strip(),
                'authors': authors,
                'publication_date': entry.get('published', ''),
                'journal': 'arXiv',  # arXiv is a preprint server
                'doi': entry.get('doi', ''),
                'arxiv_id': entry.get('id', '').split('/')[-1].split('v')[0],  # Extract base arXiv ID
                'categories': categories,
                'primary_category': primary_category,
                'source': 'arxiv',
                'url': entry.get('link', '')
            }
            
            print(f"Successfully formatted arXiv paper: {formatted['title']}")
            return formatted
            
        except Exception as e:
            print(f"Error formatting arXiv paper: {str(e)}")
            return {}
    
    async def get_paper_details(self, paper_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific paper."""
        try:
            params = {
                'id_list': paper_id,
                'max_results': 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        if feed.entries:
                            return self.format_paper(feed.entries[0])
                    return {}
                    
        except Exception as e:
            print(f"arXiv paper detail error: {str(e)}")
            return {}
    
    def _format_search_query(self, query: str) -> str:
        """Format the query for better arXiv results."""
        # Remove question words and common terms
        stop_words = {'what', 'how', 'why', 'when', 'where', 'is', 'are', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for'}
        terms = [word.lower() for word in query.split() if word.lower() not in stop_words]
        
        # Add relevant field qualifiers
        formatted_query = f"all:({' AND '.join(terms)})"
        
        # Add abstract and title boosting
        formatted_query += f" OR abs:({' AND '.join(terms)}) OR ti:({' AND '.join(terms)})"
        
        print(f"\n=== Query Formatting ===")
        print(f"Original: {query}")
        print(f"Formatted: {formatted_query}")
        
        return formatted_query 