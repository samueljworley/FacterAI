from typing import List, Dict
from openai import OpenAI
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

class TextEmbedder:
    def __init__(self, api_key: str, model: str = "text-embedding-ada-002"):
        """Initialize embedder with OpenAI API key"""
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text using OpenAI API"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {str(e)}")
            raise
            
    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings for a list of text chunks"""
        embedded_chunks = []
        
        for chunk in chunks:
            try:
                # Get embedding for chunk text
                embedding = self.get_embedding(chunk['text'])
                
                # Add embedding to chunk metadata
                chunk_with_embedding = {
                    **chunk,
                    'embedding': np.array(embedding, dtype=np.float32)
                }
                embedded_chunks.append(chunk_with_embedding)
                
            except Exception as e:
                print(f"Failed to embed chunk {chunk['chunk_id']}: {str(e)}")
                continue
                
        return embedded_chunks 