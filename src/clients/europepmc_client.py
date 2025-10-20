import aiohttp
from typing import List, Dict, Any
from .base_client import ResearchClient

class EuropePMCClient(ResearchClient):
    """Client for interacting with Europe PMC API."""
    
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search Europe PMC for papers matching the query."""
        try:
            async with aiohttp.ClientSession() as session:
                search_url = f"{self.BASE_URL}/search"
                params = {
                    'query': query,
                    'format': 'json',
                    'pageSize': max_results,
                    'resultType': 'core'
                }
                
                print(f"EuropePMC searching with URL: {search_url} and params: {params}")
                
                async with session.get(search_url, params=params) as response:
                    print(f"EuropePMC response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"EuropePMC raw response: {data}")
                        
                        results = data.get('resultList', {}).get('result', [])
                        print(f"Found {len(results)} results from EuropePMC")
                        
                        formatted_results = [self.format_paper(paper) for paper in results]
                        print(f"Formatted {len(formatted_results)} papers from EuropePMC")
                        
                        return formatted_results
                    else:
                        print(f"EuropePMC error response: {await response.text()}")
                        return []
        except Exception as e:
            print(f"EuropePMC search error: {str(e)}")
            return []
    
    async def get_paper_details(self, paper_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific paper."""
        try:
            async with aiohttp.ClientSession() as session:
                detail_url = f"{self.BASE_URL}/article/{paper_id}/fulltext/json"
                print(f"Fetching EuropePMC paper details: {detail_url}")
                
                async with session.get(detail_url) as response:
                    print(f"EuropePMC paper detail response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        return self.format_paper(data)
                    else:
                        print(f"EuropePMC paper detail error: {await response.text()}")
                        return {}
        except Exception as e:
            print(f"EuropePMC paper detail error: {str(e)}")
            return {}
    
    def format_paper(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format Europe PMC paper data into standardized structure."""
        try:
            print(f"Formatting EuropePMC paper: {paper_data.get('title', 'No title')}")
            
            # Extract authors
            authors = paper_data.get('authorList', {}).get('author', [])
            author_names = [
                f"{author.get('lastName', '')} {author.get('firstName', '')}"
                for author in authors
            ]
            
            formatted = {
                'title': paper_data.get('title', ''),
                'abstract': paper_data.get('abstractText', ''),
                'authors': author_names,
                'journal': paper_data.get('journalInfo', {}).get('journal', {}).get('title', ''),
                'publication_date': paper_data.get('firstPublicationDate', ''),
                'pmid': paper_data.get('pmid', ''),
                'doi': paper_data.get('doi', ''),
                'source': 'europepmc'
            }
            
            print(f"Formatted EuropePMC paper: {formatted}")
            return formatted
            
        except Exception as e:
            print(f"Error formatting EuropePMC paper: {str(e)}")
            return {} 