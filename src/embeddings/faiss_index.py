from typing import List, Dict, Optional
import faiss
import numpy as np
import json
import os
import sys

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

#from db.dynamodb_handler import DynamoDBHandler

class FAISSIndexManager:
    def __init__(self, dimension: int = 1536, index_path: str = "research_index"):
        """Initialize FAISS index manager
        
        Args:
            dimension: Dimension of embeddings (1536 for text-embedding-ada-002)
            index_path: Base path for storing index and metadata
        """
        self.dimension = dimension
        self.index_path = index_path
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata: List[Dict] = []
        #self.dynamo = DynamoDBHandler()
        
        # Create directory if it doesn't exist
        os.makedirs(index_path, exist_ok=True)
        
    def add_chunks(self, chunks: List[Dict]) -> None:
        """Add chunks with embeddings to both FAISS and DynamoDB"""
        if not chunks:
            return
            
        # Extract embeddings and metadata
        embeddings = []
        new_metadata = []
        
        for chunk in chunks:
            embeddings.append(chunk['embedding'])
            metadata = {k:v for k,v in chunk.items() if k != 'embedding'}
            new_metadata.append(metadata)
            
            # Save to DynamoDB
            self.dynamo.save_embedding(chunk)
            
        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Add to FAISS index
        self.index.add(embeddings_array)
        
        # Update metadata
        self.metadata.extend(new_metadata)
        
    def search(self, query_embedding: List[float], k: int = 5) -> List[Dict]:
        """Search for k nearest neighbors"""
        # Convert list to numpy array
        query_array = np.array(query_embedding, dtype=np.float32)
        
        # Reshape query if needed
        if len(query_array.shape) == 1:
            query_array = query_array.reshape(1, -1)
            
        # Search index
        distances, indices = self.index.search(query_array, k)
        
        # Get metadata for results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata):  # Ensure valid index
                result = {
                    **self.metadata[idx],
                    'distance': float(distances[0][i])
                }
                results.append(result)
                
        return results
        
    def save(self) -> None:
        """Save index and metadata to disk"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.index_path, exist_ok=True)
            print(f"Saving to directory: {os.path.abspath(self.index_path)}")  # Debug print
            
            # Save FAISS index
            index_file = os.path.join(self.index_path, "research.index")
            print(f"Saving index to: {os.path.abspath(index_file)}")
            print(f"Index contains {self.index.ntotal} vectors")
            faiss.write_index(self.index, index_file)
            
            # Save metadata
            metadata_file = os.path.join(self.index_path, "metadata.json")
            print(f"Saving metadata to: {metadata_file}")
            print(f"Metadata contains {len(self.metadata)} items")
            with open(metadata_file, "w") as f:
                json.dump(self.metadata, f)
            
        except Exception as e:
            print(f"Error saving index: {str(e)}")

    def load(self) -> bool:
        """Load index and metadata from disk"""
        try:
            # Load FAISS index
            index_file = os.path.join(self.index_path, "research.index")
            print(f"Loading index from: {index_file}")
            if os.path.exists(index_file):
                self.index = faiss.read_index(index_file)
                print(f"Loaded index with {self.index.ntotal} vectors")
            else:
                print(f"Index file not found: {index_file}")
            
            # Load metadata
            metadata_file = os.path.join(self.index_path, "metadata.json")
            print(f"Loading metadata from: {metadata_file}")
            if os.path.exists(metadata_file):
                with open(metadata_file, "r") as f:
                    self.metadata = json.load(f)
                print(f"Loaded metadata with {len(self.metadata)} items")
            else:
                print(f"Metadata file not found: {metadata_file}")
            
            return True
            
        except Exception as e:
            print(f"Error loading index: {str(e)}")
            return False 