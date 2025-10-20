#from db.dynamodb_handler import DynamoDBHandler
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
from db.vector_store import VectorStore
from openai import OpenAI
import os
from decimal import Decimal
import numpy as np
from db.reranker import SearchReranker

class PaperProcessor:
    def __init__(self):
        #self.db = DynamoDBHandler()
        self.vector_store = VectorStore()
        self.reranker = SearchReranker()
        #self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def preview_paper_metadata(self, paper: Dict) -> Dict:
        """
        Format paper metadata for preview before storing
        """
        document_id = self._generate_document_id(paper['title'])
        primary_category = paper.get('categories', ['General'])[0]
        
        return {
            'document_id': document_id,
            'category': primary_category,  # Required sort key for DynamoDB
            'title': paper.get('title', ''),
            'authors': paper.get('authors', ''),
            'publication_date': paper.get('publication_date', ''),
            'journal': paper.get('journal', ''),
            'abstract': paper.get('abstract', ''),
            'categories': paper.get('categories', []),
            'keywords': paper.get('keywords', []),
            'full_text_hash': paper.get('full_text_hash') or self._generate_hash(paper.get('full_text', '')),
            's3_link': paper.get('s3_link'),
            # New fields from your schema
            'embedding_vector': paper.get('embedding_vector', []),
            'text_chunks': paper.get('text_chunks', []),
            'citation_count': paper.get('citation_count', 0),
            # Metadata timestamps
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    def store_selected_paper(self, paper_metadata: Dict) -> bool:
        """Store paper metadata and embedding"""
        try:
            # Generate embedding from abstract
            embedding = self.generate_embedding(paper_metadata['abstract'])
            
            # Convert embedding floats to Decimals for DynamoDB
            paper_metadata['embedding_vector'] = [Decimal(str(x)) for x in embedding]
            
            # Store in DynamoDB
            self.db.insert_paper(**paper_metadata)
            
            # Store in FAISS with category
            self.vector_store.add_embedding(
                paper_metadata['document_id'],
                paper_metadata['category'],
                embedding
            )
            
            return True
        except Exception as e:
            print(f"Error storing paper: {str(e)}")
            return False

    def search_similar_papers(self, query: str, k: int = 10) -> List[Dict]:
        """Search for similar papers using hybrid search"""
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Initial semantic search with FAISS (get more results)
        initial_results = self.vector_store.search(query_embedding, k=k*4)
        
        # Fetch full metadata from DynamoDB
        papers = []
        sources = set()  # Track unique sources
        for doc_id, category, score in initial_results:
            paper = self.db.get_paper(doc_id, category)
            if paper:
                source = paper.get('journal', '').lower()
                # Only add if we don't have too many from same source
                if source not in sources or len([p for p in papers if p.get('journal', '').lower() == source]) < 2:
                    paper['similarity_score'] = float(score)
                    papers.append(paper)
                    sources.add(source)
                    
                if len(papers) >= k:  # Stop once we have enough diverse papers
                    break
                    
        return papers

    def search_similar_papers_by_category(self, query: str, category: str, k: int = 5) -> List[Dict]:
        """Search for similar papers within a specific category"""
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Search FAISS
        similar_papers = self.vector_store.search(query_embedding, k * 2)  # Get more results to filter
        
        # Filter and fetch results
        results = []
        for doc_id, paper_category, score in similar_papers:
            if paper_category == category:  # Only include papers from specified category
                paper = self.db.get_paper(doc_id, paper_category)
                if paper:
                    paper['similarity_score'] = score
                    results.append(paper)
            if len(results) >= k:  # Stop once we have enough results
                break
                
        return results

    def _generate_document_id(self, title: str) -> str:
        """Generate a unique document ID based on title"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return hashlib.md5(f"{title}{timestamp}".encode()).hexdigest()[:16]

    def _generate_hash(self, text: str) -> str:
        """Generate hash for full text"""
        return hashlib.sha256(text.encode()).hexdigest() 