import aiohttp
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SemanticScholarClient:
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    async def get_citation_count(self, pmid: str) -> int:
        """Get citation count for a PubMed ID"""
        try:
            # Add delay to respect rate limits
            await asyncio.sleep(1.0)  # 1 second delay between requests
            
            url = f"{self.BASE_URL}/paper/PMID:{pmid}?fields=citationCount"
            headers = {
                'User-Agent': 'SageMind Research Assistant'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Citation count for {pmid}: {data.get('citationCount', 0)}")
                        return data.get('citationCount', 0)
                    elif response.status == 429:  # Too Many Requests
                        logger.warning(f"Rate limit hit for {pmid}, waiting longer...")
                        await asyncio.sleep(2)  # Wait longer on rate limit
                        return await self.get_citation_count(pmid)  # Retry
                    else:
                        logger.error(f"API error: {response.status}")
                        return 0
        except Exception as e:
            logger.error(f"Error fetching citations: {str(e)}")
            return 0

    async def search_papers(self, query: str):
        """Search papers using Semantic Scholar API."""
        # TODO: Implement actual API call
        return []  # Placeholder empty list for now