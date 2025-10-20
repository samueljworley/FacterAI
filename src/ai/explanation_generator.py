from openai import OpenAI
from typing import Dict, List
import os

class ExplanationGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-3.5-turbo"  # Updated to match your current model
        
    def generate_layered_explanation(self, research_content: Dict) -> Dict:
        """
        Generates a multi-layered explanation of research content
        """
        # Step 1: Technical Summary
        technical_summary = self._generate_technical_summary(research_content)
        
        # Step 2: Plain Language Explanation
        simple_explanation = self._generate_simple_explanation(technical_summary)
        
        # Step 3: Key Takeaways
        key_points = self._extract_key_points(simple_explanation)
        
        # Step 4: Potential Questions
        follow_up_questions = self._generate_follow_up_questions(simple_explanation)
        
        return {
            "technical_summary": technical_summary,
            "simple_explanation": simple_explanation,
            "key_points": key_points,
            "follow_up_questions": follow_up_questions
        }

    def _generate_technical_summary(self, content: Dict) -> str:
        """Creates a technical summary of the research"""
        prompt = f"""
        Analyze this research content and create a technical summary:
        Title: {content.get('title', '')}
        Abstract: {content.get('abstract', '')}
        Key Findings: {content.get('findings', '')}
        
        Create a concise technical summary that captures the main research points.
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a research analyst synthesizing scientific findings."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    def _generate_simple_explanation(self, technical_summary: str) -> str:
        """Converts technical content into plain language"""
        prompt = f"""
        I need you to explain this medical research in a way that's easy to understand:
        ---
        {technical_summary}
        ---
        Please:
        1. Use everyday language, like you're explaining to a friend
        2. Include real-world examples or analogies
        3. Break complex ideas into simple steps
        4. Avoid medical jargon - if you must use it, explain what it means
        5. Focus on what this means for regular people

        Make it conversational and engaging, not academic.
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a friendly doctor who's great at explaining complex medical topics in simple terms. You make people feel comfortable asking questions and always explain things clearly without being condescending."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7  # Slightly more creative for conversational tone
        )
        return response.choices[0].message.content

    def _extract_key_points(self, explanation: str) -> List[str]:
        """Extracts main takeaways from the explanation"""
        prompt = f"""
        From this explanation, list the 3-5 most important takeaways:
        ---
        {explanation}
        ---
        Format each point as a clear, actionable insight.
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a clarity expert distilling complex information."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Split the response into individual points
        points = response.choices[0].message.content.split('\n')
        return [p.strip('- ').strip() for p in points if p.strip()]

    def _generate_follow_up_questions(self, explanation: str) -> List[str]:
        """Generates relevant follow-up questions"""
        prompt = f"""
        Based on this explanation, generate 3 follow-up questions that a curious learner might ask:
        ---
        {explanation}
        ---
        Create questions that explore practical applications or interesting implications.
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a curious student asking insightful questions."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Split the response into individual questions
        questions = response.choices[0].message.content.split('\n')
        return [q.strip('- ').strip() for q in questions if q.strip()] 