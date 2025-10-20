import requests
from typing import List, Dict, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
import time

class PubMedClient:
    """Client for interacting with the PubMed API."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize PubMed client.
        
        Args:
            api_key (str, optional): NCBI API key for higher rate limits
        """
        self.api_key = api_key
        self.rate_limit = 0.34  # 3 requests per second without API key
        
    def search_papers(self, query: str, max_results: int = 100) -> List[str]:
        """Search for papers matching the query and return their PMIDs.
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            List[str]: List of PMIDs
        """
        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'json',
            'sort': 'relevance'
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
            
        response = requests.get(f"{self.BASE_URL}/esearch.fcgi", params=params)
        time.sleep(self.rate_limit)  # Respect rate limits
        
        if response.status_code == 200:
            data = response.json()
            return data['esearchresult']['idlist']
        else:
            raise Exception(f"PubMed search failed: {response.status_code}")
            
    def fetch_paper_details(self, pmid: str) -> Dict:
        """Fetch detailed information for a specific paper.
        
        Args:
            pmid (str): PubMed ID
            
        Returns:
            Dict: Paper metadata
        """
        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'xml'
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
            
        response = requests.get(f"{self.BASE_URL}/efetch.fcgi", params=params)
        time.sleep(self.rate_limit)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch paper {pmid}: {response.status_code}")
            
        # Parse XML response
        tree = ET.fromstring(response.content)
        article = tree.find('.//Article')
        
        if article is None:
            raise Exception(f"No article data found for PMID {pmid}")
            
        # Extract metadata
        return {
            'pmid': pmid,
            'title': self._safe_find_text(article, './/ArticleTitle'),
            'abstract': self._safe_find_text(article, './/Abstract/AbstractText'),
            'authors': self._extract_authors(article),
            'journal': self._safe_find_text(article, './/Journal/Title'),
            'publication_date': self._extract_publication_date(article),
            'doi': self._safe_find_text(article, './/ELocationID[@EIdType="doi"]'),
            'keywords': self._extract_keywords(article)
        }
        
    def _safe_find_text(self, element: ET.Element, xpath: str) -> str:
        """Safely extract text from XML element."""
        found = element.find(xpath)
        return found.text if found is not None else ''
        
    def _extract_authors(self, article: ET.Element) -> List[str]:
        """Extract author names from article XML."""
        authors = []
        author_list = article.findall('.//Author')
        
        for author in author_list:
            last_name = self._safe_find_text(author, './LastName')
            fore_name = self._safe_find_text(author, './ForeName')
            if last_name and fore_name:
                authors.append(f"{last_name} {fore_name}")
                
        return authors
        
    def _extract_publication_date(self, article: ET.Element) -> str:
        """Extract and format publication date."""
        pub_date = article.find('.//PubDate')
        if pub_date is None:
            return ''
            
        year = self._safe_find_text(pub_date, './Year')
        month = self._safe_find_text(pub_date, './Month')
        day = self._safe_find_text(pub_date, './Day')
        
        try:
            if year and month and day:
                return datetime(int(year), int(month), int(day)).strftime('%Y-%m-%d')
            elif year and month:
                return datetime(int(year), int(month), 1).strftime('%Y-%m')
            elif year:
                return year
            else:
                return ''
        except ValueError:
            return year
            
    def _extract_keywords(self, article: ET.Element) -> List[str]:
        """Extract keywords from article XML."""
        keywords = []
        keyword_list = article.findall('.//Keyword')
        
        for keyword in keyword_list:
            if keyword.text:
                keywords.append(keyword.text.strip())
                
        return keywords
