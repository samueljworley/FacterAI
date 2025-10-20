import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import requests
import json
from typing import List, Dict
from collections import defaultdict
from datetime import datetime
from src.app.services.paper_service import PaperService
import asyncio

async def test_search():
    service = PaperService()
    
    # Test query about microplastics
    query = "What are the health impacts of microplastics?"
    print(f"\n🔍 Testing query: {query}")
    
    # Get search results
    results = await service.search_papers(query, "research")
    
    # Display results
    print("\n📊 Search Results:")
    for i, paper in enumerate(results, 1):
        print(f"\n{i}. 📄 Paper Details:")
        print(f"   Title: {paper.get('title', 'No title')}")
        print(f"   Authors: {paper.get('authors', 'Unknown')}")
        print(f"   Journal: {paper.get('journal', 'Unknown')}")
        print(f"   Year: {paper.get('publication_date', 'Unknown')}")
        print(f"   Citations: {paper.get('citation_count', 0)} 📚")
        
        # Show abstract preview
        abstract = paper.get('abstract', '')
        if abstract:
            print(f"\n   Abstract Preview:")
            print(f"   {abstract[:200]}...")
        print("-" * 80)

from db.dynamodb_handler import DynamoDBHandler

def analyze_sources():
    dynamo = DynamoDBHandler()
    table = dynamo.dynamodb.Table('research_embeddings')
    response = table.scan()
    items = response['Items']
    
    journals = {}
    years = {}
    citation_counts = []

    missing_metadata = 0
    low_impact_chunks = []

    for item in items:
        chunk_id = item.get('chunk_id', 'unknown')
        metadata = item.get('metadata', {})
        
        # Handle metadata whether it's a dict or string
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                print(f"⚠️ Invalid metadata for chunk: {chunk_id}")
                missing_metadata += 1
                continue
        
        if not metadata:
            missing_metadata += 1
            continue

        journal = metadata.get('journal', 'Unknown')
        year = metadata.get('year', 'Unknown')
        citations = metadata.get('citation_count', 0)

        # Count journal and year
        journals[journal] = journals.get(journal, 0) + 1
        years[year] = years.get(year, 0) + 1
        citation_counts.append(citations)

        # Flag low-impact articles
        try:
            if int(citations) == 0 and int(year) < 2020:
                low_impact_chunks.append((chunk_id, journal, year))
        except:
            continue

    total = len(items)
    print(f"\n📊 Corpus Summary")
    print(f"- Total chunks: {total}")
    print(f"- Chunks with valid metadata: {total - missing_metadata}")
    print(f"- Chunks missing metadata: {missing_metadata}")
    
    print(f"\n🏛️ Top Journals:")
    for j in sorted(journals.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"- {j[0]}: {j[1]} papers")
        
    print(f"\n📅 Publication Years:")
    for y in sorted(years.items()):
        print(f"- {y[0]}: {y[1]} papers")
        
    if citation_counts:
        avg = sum(citation_counts) / len(citation_counts)
        print(f"\n📈 Citation Statistics:")
        print(f"- Average citations: {avg:.1f}")
        print(f"- Max citations: {max(citation_counts)}")

    if low_impact_chunks:
        print(f"\n⚠️ Low-Impact Chunks (0 citations & pre-2020):")
        for cid, j, y in low_impact_chunks[:10]:
            print(f"- {cid} ({j}, {y})")

def display_results(results: List[Dict]):
    print(f"\n📊 Found {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. 📄 Paper Details:")
        print(f"   Title: {result.get('title', 'No title')}")
        print(f"   PMID: {result.get('document_id', 'Unknown')}")
        print(f"   Journal: {result.get('journal', 'Unknown')}")
        print(f"   Year: {result.get('publication_date', 'Unknown')}")
        print(f"   Citations: {result.get('citation_count', 0)} 📚")
        print(f"   Authors: {result.get('authors', 'Unknown')}")
        
        # Scores might be strings or floats
        relevance = float(result.get('relevance_score', 0))
        citation_score = float(result.get('citation_score', 0))
        final_score = float(result.get('rerank_score', 0))
        
        print(f"\n   Ranking Scores:")
        print(f"   - Relevance:    {relevance:.3f} 🎯")
        print(f"   - Citation:     {citation_score:.3f} 📊")
        print(f"   - Final Score:  {final_score:.3f} ⭐")
        
        # Show abstract preview
        abstract = result.get('abstract', '')
        if abstract:
            print(f"\n   Abstract Preview:")
            print(f"   {abstract[:200]}...\n")
        print("-" * 80)

def analyze_corpus(chunks: List[Dict]):
    journals = defaultdict(int)
    years = defaultdict(int)
    citations = []
    valid_metadata = 0
    
    for chunk in chunks:
        metadata = json.loads(chunk.get('metadata', '{}')) if isinstance(chunk.get('metadata'), str) else chunk.get('metadata', {})
        if metadata:
            valid_metadata += 1
            journals[metadata.get('journal', 'Unknown')] += 1
            
            # Get actual publication year
            year = metadata.get('year', datetime.now().year)
            years[year] += 1
            
            citations.append(metadata.get('citation_count', 0))
    
    print("\n📊 Corpus Summary")
    print(f"- Total chunks: {len(chunks)}")
    print(f"- Chunks with valid metadata: {valid_metadata}")
    print(f"- Chunks missing metadata: {len(chunks) - valid_metadata}")
    
    print("\n🏛️ Top Journals:")
    for journal, count in sorted(journals.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"- {journal}: {count} papers")
    
    print("\n📅 Publication Years:")
    for year in sorted(years.keys()):
        print(f"- {year}: {years[year]} papers")
    
    if citations:
        print("\n📈 Citation Statistics:")
        print(f"- Average citations: {sum(citations)/len(citations):.1f}")
        print(f"- Max citations: {max(citations)}")

if __name__ == "__main__":
    asyncio.run(test_search()) 