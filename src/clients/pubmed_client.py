from typing import List, Dict, Any
from .base_client import ResearchClient
import aiohttp
import asyncio
from datetime import datetime
# src/clients/pubmed_client.py

# Make this module import-safe even if aiohttp isn't installed
# Make this module safe to import even if aiohttp isn't installed.
try:
    import aiohttp  # type: ignore
except Exception:
    aiohttp = None


class PubMedClient:
    def __init__(self, *args, **kwargs):
        if aiohttp is None:
            # Fail only if someone actually tries to construct it.
            raise RuntimeError("PubMed disabled or aiohttp not installed")

    async def search(self, *args, **kwargs):
        if aiohttp is None:
            raise RuntimeError("PubMed disabled or aiohttp not installed")
        # ... real logic using aiohttp.ClientSession() ...

    """Client for interacting with PubMed API."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search PubMed for papers matching the query."""
        try:
            async with aiohttp.ClientSession() as session:
                # First get IDs
                search_url = f"{self.BASE_URL}/esearch.fcgi"
                params = {
                    'db': 'pubmed',
                    'term': query,
                    'retmax': max_results,
                    'retmode': 'json'
                }
                
                print(f"Searching PubMed with params: {params}")
                async with session.get(search_url, params=params) as response:
                    if response.status == 200:
                        search_data = await response.json()
                        ids = search_data.get('esearchresult', {}).get('idlist', [])
                        print(f"Found {len(ids)} PubMed IDs")
                        
                        # Then get details for each ID
                        papers = []
                        for i, pmid in enumerate(ids):
                            try:
                                # Add delay to respect rate limits (3 requests per second)
                                if i > 0:
                                    await asyncio.sleep(0.34)  # ~3 requests per second
                                
                                print(f"Fetching details for PMID: {pmid}")
                                paper = await self.get_paper_details(pmid)
                                if paper and isinstance(paper, dict):
                                    papers.append(paper)
                                else:
                                    print(f"No valid paper data returned for PMID {pmid}")
                            except Exception as e:
                                print(f"Error getting details for PMID {pmid}: {str(e)}")
                                continue
                        
                        return papers
                    else:
                        print(f"PubMed search error: {await response.text()}")
                        return []
        except Exception as e:
            print(f"PubMed search error: {str(e)}")
            return []
    
    async def get_paper_details(self, paper_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific paper."""
        try:
            print(f"Getting paper details for PMID: {paper_id}")
            async with aiohttp.ClientSession() as session:
                # Use esummary instead of efetch for better JSON support
                fetch_url = f"{self.BASE_URL}/esummary.fcgi"
                params = {
                    'db': 'pubmed',
                    'id': paper_id,
                    'retmode': 'json'
                }
                
                print(f"Fetching from: {fetch_url} with params: {params}")
                async with session.get(fetch_url, params=params) as response:
                    print(f"Response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"Response data type: {type(data)}")
                        print(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        return self.format_paper(data)
                    else:
                        error_text = await response.text()
                        print(f"PubMed fetch error for {paper_id}: {error_text}")
                        return {}
        except Exception as e:
            print(f"PubMed fetch error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def format_paper(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format PubMed paper data into standardized structure."""
        try:
            # Debug logging
            print("Formatting PubMed paper data...")
            print(f"Paper data type: {type(paper_data)}")
            print(f"Paper data keys: {list(paper_data.keys()) if isinstance(paper_data, dict) else 'Not a dict'}")
            
            # Handle different response formats
            if not isinstance(paper_data, dict):
                print(f"Paper data is not a dict: {paper_data}")
                return {}
            
            # Try different possible structures
            article_set = None
            
            # Try esummary format first (this is what we're using now)
            if 'result' in paper_data:
                result = paper_data.get('result', {})
                if isinstance(result, dict):
                    # Find the actual paper data (it's nested under the PMID)
                    paper_info = None
                    for key, value in result.items():
                        if key != 'uids' and isinstance(value, dict):
                            paper_info = value
                            break
                    
                    if paper_info:
                        # Extract authors from the author list
                        authors = []
                        author_list = paper_info.get('authors', [])
                        if isinstance(author_list, list):
                            for author in author_list:
                                if isinstance(author, dict):
                                    name = author.get('name', '')
                                    if name:
                                        authors.append(name)
                        
                        formatted = {
                            'title': paper_info.get('title', ''),
                            'abstract': paper_info.get('abstract', ''),
                            'authors': authors,
                            'journal': paper_info.get('fulljournalname', ''),
                            'publication_date': paper_info.get('pubdate', ''),
                            'pmid': paper_info.get('uid', ''),
                            'source': 'pubmed'
                        }
                        print(f"Successfully formatted PubMed paper (esummary): {formatted['title']}")
                        return formatted
            
            # Try PubmedArticleSet (fallback)
            if 'PubmedArticleSet' in paper_data:
                article_set = paper_data.get('PubmedArticleSet', {})
            # Try PubmedArticle directly (fallback)
            elif 'PubmedArticle' in paper_data:
                article_set = [paper_data.get('PubmedArticle', {})]
            
            if not article_set:
                print("No article set found in response")
                return {}
                
            if isinstance(article_set, list) and len(article_set) > 0:
                article = article_set[0]
            elif isinstance(article_set, dict):
                article = article_set
            else:
                print(f"Unexpected article_set format: {type(article_set)}")
                return {}
            
            medline_citation = article.get('MedlineCitation', {})
            article_info = medline_citation.get('Article', {})
            
            # Extract authors
            author_list = article_info.get('AuthorList', [])
            authors = []
            for author in author_list:
                if isinstance(author, dict):  # Ensure author is a dictionary
                    last_name = author.get('LastName', '')
                    fore_name = author.get('ForeName', '')
                    authors.append(f"{last_name} {fore_name}".strip())
            
            # Format the paper
            formatted = {
                'title': article_info.get('ArticleTitle', ''),
                'abstract': article_info.get('Abstract', {}).get('AbstractText', [''])[0] if article_info.get('Abstract') else '',
                'authors': authors,
                'journal': article_info.get('Journal', {}).get('Title', ''),
                'publication_date': self._extract_date(article_info.get('Journal', {}).get('PubDate', {})),
                'pmid': medline_citation.get('PMID', ''),
                'source': 'pubmed'
            }
            
            print(f"Successfully formatted PubMed paper: {formatted['title']}")
            return formatted
            
        except Exception as e:
            print(f"Error formatting PubMed paper: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _extract_date(self, pub_date: Dict[str, Any]) -> str:
        """Extract publication date in a consistent format."""
        try:
            # Handle MedlineDate format first
            if 'MedlineDate' in pub_date:
                # Extract year from formats like "2023 Jan-Feb" or "2023"
                medline_date = pub_date['MedlineDate']
                year = medline_date.split()[0]
                return year if year.isdigit() else ''
            
            # Handle structured date
            year = pub_date.get('Year', '')
            month = pub_date.get('Month', '')
            day = pub_date.get('Day', '')
            
            # Validate year isn't in the future
            current_year = datetime.now().year
            if year and year.isdigit():
                if int(year) > current_year:
                    return str(current_year)
                return str(year)
            
            return ''
        except Exception as e:
            print(f"Date extraction error: {str(e)}")
            return '' 