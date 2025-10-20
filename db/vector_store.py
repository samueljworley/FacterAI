import faiss
import numpy as np
from typing import List, Dict, Tuple
import pickle
import os

class VectorStore:
    def __init__(self, dimension: int = 1536):  # Default for OpenAI embeddings
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(self.dimension)
        self.paper_metadata = []  # Store (document_id, category) pairs
        self.index_file = 'faiss_index.pkl'
        self.load_index()

    def load_index(self):
        """Load existing index if it exists"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.index = saved_data['index']
                    self.paper_metadata = saved_data.get('paper_metadata', [])
            except Exception as e:
                print(f"Error loading index: {e}. Creating new index.")
                self.index = faiss.IndexFlatL2(self.dimension)
                self.paper_metadata = []

    def save_index(self):
        """Save index to disk"""
        with open(self.index_file, 'wb') as f:
            pickle.dump({
                'index': self.index,
                'paper_metadata': self.paper_metadata
            }, f)

    def add_embedding(self, document_id: str, category: str, embedding: List[float]):
        """Add a single paper embedding to the index"""
        vector = np.array([embedding], dtype=np.float32)
        self.index.add(vector)
        self.paper_metadata.append((document_id, category))
        self.save_index()

    def search(self, query_embedding: List[float], k: int = 5) -> List[Tuple[str, str, float]]:
        """Search for similar papers, returns [(document_id, category, score)]"""
        if self.index.ntotal == 0:  # If index is empty
            return []
            
        # Limit k to number of items in index
        k = min(k, self.index.ntotal)
        
        query_vector = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(query_vector, k)
        
        # Filter out invalid results and duplicates
        seen = set()
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.paper_metadata):
                doc_id, category = self.paper_metadata[idx]
                if doc_id not in seen and dist < 1e10:  # Filter extreme values
                    seen.add(doc_id)
                    results.append((doc_id, category, float(dist)))
        
        return results 