import requests
from typing import List, Dict, Optional

class SemanticScholarClient:
    BASE_URL = "https://api.semanticscholar.org/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.headers = {
            "Accept": "application/json"
        }
        if api_key:
            self.headers["x-api-key"] = api_key

    async def search_papers(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for papers using Semantic Scholar API"""
        url = f"{self.BASE_URL}/paper/search"
        
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,authors,year,venue,url,paperId"
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Format the response to match our existing paper structure
        papers = []
        for paper in data.get("data", []):
            papers.append({
                "pmid": paper.get("paperId"),  # Using paperId as our identifier
                "title": paper.get("title", ""),
                "abstract": paper.get("abstract", ""),
                "journal": f"{paper.get('venue', '')} ({paper.get('year', '')})",
                "url": paper.get("url", ""),
                "source": "semantic_scholar"
            })
            
        return papers 