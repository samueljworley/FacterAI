import os
import sys
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.app.services.paper_service import PaperService
from datetime import datetime

async def test_paper_pipeline():
    service = PaperService()
    
    # Test with a known recent paper about microplastics
    query = "microplastics in drinking water"
    print(f"\n🔍 Testing search with query: {query}")
    
    papers = await service.search_papers(query, query_type='research')
    
    print(f"\n📊 Found {len(papers)} papers")
    for paper in papers:
        print(f"\n📑 Paper Details:")
        print(f"Title: {paper.get('title')}")
        print(f"Date: {paper.get('publication_date')}")
        print(f"Journal: {paper.get('journal')}")
        print(f"Citations: {paper.get('citation_count', 0)}")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(test_paper_pipeline()) 