import os
import sys
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.app.services.paper_service import PaperService
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_citation_fetching():
    service = PaperService()
    
    # Test with known PMIDs
    test_pmids = [
        "37918800",  # Recent paper about microplastics
        "34406342",  # Older paper that should have citations
        "33571421"   # Even older paper that should have more citations
    ]
    
    print("\n🔍 Testing Semantic Scholar citation fetching")
    
    for pmid in test_pmids:
        try:
            print(f"\n📑 Fetching citations for PMID: {pmid}")
            citations = await service._get_citation_count(pmid)
            print(f"Citations: {citations}")
            
            # Also get paper details to show context
            paper = await service._process_paper(pmid)
            if paper:
                print(f"Title: {paper.get('title')}")
                print(f"Date: {paper.get('publication_date')}")
                print(f"Journal: {paper.get('journal')}")
            print("-" * 80)
            
        except Exception as e:
            print(f"Error testing PMID {pmid}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_citation_fetching()) 