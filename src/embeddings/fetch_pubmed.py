from typing import List, Dict, Optional
from Bio import Entrez
import time
import os
# src/embeddings/fetch_pubmed.py

# Make this module import-safe even if Biopython isn't installed
# Make this module safe to import even if Biopython isn't installed.
try:
    from Bio import Entrez  # type: ignore
except Exception:
    Entrez = None


class PubMedFetcher:
    def __init__(self, *args, **kwargs):
        if Entrez is None:
            raise RuntimeError("PubMed disabled or Biopython not installed")

    def fetch(self, *args, **kwargs):
        if Entrez is None:
            raise RuntimeError("PubMed disabled or Biopython not installed")
        # ... logic using Entrez ...

        
#     def fetch_abstracts(self, query: str, max_results: int = 10) -> List[Dict]:
#         """Fetch abstracts from PubMed for a given query"""
#         try:
#             print(f"Searching PubMed for: {query}")
#             # Search for paper IDs
#             handle = Entrez.esearch(db="pubmed", 
#                                   term=query, 
#                                   retmax=max_results,
#                                   sort="relevance")
#             results = Entrez.read(handle)
#             handle.close()
#             time.sleep(self.rate_limit)
# 
#             print(f"Found {len(results.get('IdList', []))} results")
#             
#             papers = []
#             for pmid in results.get("IdList", []):
#                 try:
#                     handle = Entrez.efetch(db="pubmed", 
#                                          id=pmid, 
#                                          rettype="medline", 
#                                          retmode="text")
#                     paper = {
#                         "pmid": pmid,
#                         "title": "",
#                         "abstract": "",
#                         "authors": [],
#                         "year": "",
#                         "journal": ""
#                     }
#                     
#                     # Parse Medline format
#                     current_field = None
#                     current_content = []
#                     
#                     for line in handle:
#                         line = line.strip()
#                         if not line: continue
#                         
#                         if line.startswith("TI  - "): 
#                             paper["title"] = line[6:]
#                             current_field = "title"
#                         elif line.startswith("AB  - "): 
#                             paper["abstract"] = line[6:]
#                             current_field = "abstract"
#                         elif line.startswith("AU  - "): 
#                             paper["authors"].append(line[6:])
#                         elif line.startswith("DP  - "): 
#                             paper["year"] = line[6:10]
#                         elif line.startswith("JT  - "):
#                             paper["journal"] = line[6:]
#                         elif line.startswith("      ") and current_field:
#                             # Continue previous field
#                             if current_field == "title":
#                                 paper["title"] += " " + line.strip()
#                             elif current_field == "abstract":
#                                 paper["abstract"] += " " + line.strip()
#                     
#                     papers.append(paper)
#                     handle.close()
#                     time.sleep(self.rate_limit)
#                     print(f"Retrieved paper: {paper['title'][:50]}...")
#                     
#                 except Exception as e:
#                     print(f"Error fetching paper {pmid}: {str(e)}")
#                     continue
#                 
#             return papers
#             
#         except Exception as e:
#             print(f"Error in PubMed search: {str(e)}")
#             return [] 