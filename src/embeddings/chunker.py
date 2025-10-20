from typing import List
import nltk
from nltk.tokenize import sent_tokenize

# Download both required NLTK resources
nltk.download('punkt')
nltk.download('punkt_tab')

class TextChunker:
    def __init__(self, target_size: int = 200):
        """Initialize chunker with target chunk size in words"""
        self.target_size = target_size

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks of approximately target_size words"""
        # Split into sentences
        sentences = sent_tokenize(text)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            
            if current_size + sentence_words > self.target_size and current_chunk:
                # Join current chunk and add to chunks
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_words
            else:
                current_chunk.append(sentence)
                current_size += sentence_words
        
        # Add any remaining text
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

    def chunk_paper(self, paper: dict) -> List[dict]:
        """Chunk a paper's title and abstract into segments"""
        # Combine title and abstract
        full_text = f"{paper['title']} {paper['abstract']}"
        chunks = self.chunk_text(full_text)
        
        # Create chunk metadata
        chunked_papers = []
        for i, chunk in enumerate(chunks):
            chunked_papers.append({
                'chunk_id': f"{paper['pmid']}_{i}",
                'pmid': paper['pmid'],
                'text': chunk,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'authors': paper['authors'],
                'year': paper['year']
            })
            
        return chunked_papers 