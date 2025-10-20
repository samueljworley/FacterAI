from openai import OpenAI
from typing import List, Dict, Any
from config.config import config

class LLMClient:
    """Client for interacting with OpenAI's GPT."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        
    def analyze_papers(self, papers: List[Dict[str, Any]], question: str) -> str:
        """Analyze papers and generate an answer to the user's question."""
        try:
            system_prompt = """You are a research assistant analyzing scientific papers.
            
Your task is to synthesize findings from provided papers to answer research questions.

Core Requirements:
1. ONLY use information explicitly stated in the provided papers
2. Cite every claim with (Paper X) format
3. Be precise about study findings - no generalizing beyond the data
4. Acknowledge when papers don't address aspects of the question
5. Highlight any conflicting findings between papers

Response Structure:
1. Direct Answer: Concise summary of key findings
2. Evidence Analysis: Detailed breakdown of relevant findings from each paper
3. Limitations: Explicitly state what aspects of the question remain unanswered

Remember: Quality over quantity. Better to acknowledge gaps than make unsupported claims."""

            # Debug logging
            print("\n=== System Prompt ===")
            print(system_prompt)
            
            user_prompt = self._construct_prompt(papers, question)
            print("\n=== User Prompt ===")
            print(user_prompt)

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            # Debug logging
            print("\n=== AI Response ===")
            print(response.choices[0].message.content)
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"LLM Analysis error: {str(e)}")
            raise Exception(f"LLM analysis failed: {str(e)}")
            
    def _construct_prompt(self, papers: List[Dict[str, Any]], question: str) -> str:
        """Construct prompt for the LLM using papers and question."""
        # Debug logging
        print(f"Constructing prompt for question: {question}")
        print(f"Number of papers: {len(papers)}")
        
        prompt_parts = [f"Research Question: {question}\n\nAvailable Research Papers:\n"]
        
        # Add papers with clear numbering
        for i, paper in enumerate(papers, 1):
            print(f"Processing paper {i}: {paper.get('title', 'No title')}")  # Debug logging
            
            authors = paper.get('authors', 'No authors listed')
            if isinstance(authors, list):
                authors = ', '.join(authors)
            
            paper_text = [
                f"Paper {i}:",
                f"Title: {paper.get('title', 'No title')}",
                f"Authors: {authors}",
                f"Journal: {paper.get('journal', 'Journal not specified')}",
                f"Year: {paper.get('publication_date', 'Date not specified')}",
                f"Abstract: {paper.get('abstract', 'No abstract available')}\n"
            ]
            prompt_parts.append('\n'.join(paper_text))
        
        prompt_parts.append("""
Please analyze these papers to answer the research question. Remember:
- Only use information from these papers
- Cite specific papers for each claim using (Paper X) format
- If certain aspects aren't covered by these papers, acknowledge those gaps
- Do not make up or infer additional references

Provide your analysis structured as:
1. Comprehensive Answer
2. Key Findings from the Papers
3. Important Limitations or Gaps in the Research
""")
        
        final_prompt = '\n'.join(prompt_parts)
        print("Prompt constructed successfully")  # Debug logging
        return final_prompt 