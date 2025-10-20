from openai import OpenAI
from typing import List, Dict, Any
from config.config import config
from src.embeddings.embedder import TextEmbedder
from src.embeddings.faiss_index import FAISSIndexManager
import os

class LLMClient:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.embedder = TextEmbedder(api_key=config.OPENAI_API_KEY)
        self.index_manager = FAISSIndexManager(index_path="src/embeddings/research_index")
        self.index_manager.load()
        
    def analyze_query(self, query: str, sources: Dict[str, Any], query_type: str) -> str:
        try:
            # First get relevant papers using FAISS
            if query_type == "research":
                query_embedding = self.embedder.get_embedding(query)
                search_results = self.index_manager.search(query_embedding, k=5)
                
                # Format search results into sources
                sources = {
                    'sources': [{
                        'title': result.get('title', 'Untitled'),
                        'authors': result.get('authors', []),
                        'abstract': result.get('text', ''),
                        'year': result.get('year', ''),
                        'journal': result.get('journal', '')
                    } for result in search_results]
                }
            
            system_prompt = self._get_system_prompt(query_type)
            sources_text = self._format_sources(sources)
            
            # Check if we have actual sources
            has_sources = bool(sources.get('sources', []))
            
            if has_sources:
                enhanced_query = f"""Based on these research papers:

{sources_text}

Please answer this question: {query}

Requirements:
1. ALWAYS cite papers using (Author et al., Year) format
2. Every factual claim must have a citation
3. Synthesize information from multiple papers when possible
4. Note any limitations or gaps in the research
5. Include a "References" section at the end listing all cited papers

Format your response with:
- Clear section headings
- In-text citations (Author et al., Year)
- A "References" section at the end
- Explicit notes about any limitations"""
            else:
                enhanced_query = f"""Please answer this question: {query}

Note: No specific research papers were found for this query. Please:
1. Provide a general explanation based on scientific understanding
2. Clearly state that specific research citations are not available
3. Suggest what kind of research would be valuable
4. Note that this is general knowledge rather than specific study findings"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_query}
                ],
                temperature=0.2  # Lower temperature for more consistent citation format
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"LLM Analysis error: {str(e)}")
            raise Exception(f"Error in LLM analysis: {str(e)}")
    
    def _get_system_prompt(self, query_type: str) -> str:
        prompts = {
            "research": """You are a scientific research assistant. When analyzing papers:
1. Always cite specific papers using [Paper X] format
2. Draw from multiple sources when possible
3. Be explicit about limitations
4. Note when information is not available
5. Maintain scientific accuracy""",
            
            "concept": """You are an expert teacher explaining concepts clearly.
                Focus on:
                1. Clear, simple explanations
                2. Relevant examples
                3. Step-by-step breakdowns
                4. Visual analogies when helpful
                5. Common applications""",
            
            "solution_based": """You are a math/physics tutor helping solve problems.
                Please:
                1. Break down the problem
                2. Show step-by-step solution
                3. Explain each step
                4. Provide the final answer
                5. Add helpful tips""",
            
            "coding": """You are a programming mentor helping with code.
                Please:
                1. Explain the concept
                2. Show code examples
                3. Highlight best practices
                4. Note potential pitfalls
                5. Suggest improvements"""
        }
        
        return prompts.get(query_type, prompts["concept"])  # Default to concept 
    
    def _format_sources(self, sources: Dict[str, Any]) -> str:
        """Format sources into a string for the prompt"""
        if not sources or not isinstance(sources, dict):
            return "No scientific papers found."
            
        sources_list = sources.get('sources', [])
        if not sources_list:
            return "No scientific papers found."
            
        formatted_sources = []
        for idx, source in enumerate(sources_list, 1):
            if isinstance(source, dict):
                title = source.get('title', 'Untitled')
                authors = source.get('authors', 'Unknown authors')
                abstract = source.get('abstract', 'No abstract available')
                
                formatted_sources.append(f"""Paper {idx}:
Title: {title}
Authors: {authors}
Abstract: {abstract}
---""")
            
        return "\n".join(formatted_sources) if formatted_sources else "No scientific papers found." 

    def _get_research_papers(self, query: str) -> Dict[str, Any]:
        """Your existing FAISS search for research papers"""
        # Your existing implementation
        return {"type": "research", "sources": []} 