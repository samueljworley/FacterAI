from db.vector_store import VectorStore
from db.paper_processor import PaperProcessor
import hashlib

def test_vector_operations():
    processor = PaperProcessor()
    
    # Multiple test papers across different categories
    test_papers = [
        {
            'document_id': 'ai_paper_1',
            'category': 'AI',
            'title': 'Deep Learning Applications',
            'abstract': 'This paper explores deep learning applications in various fields including computer vision and NLP.',
            'authors': 'Smith, J.',
            'publication_date': '2024-03-20',
            'journal': 'AI Journal',
            'categories': ['AI', 'Deep Learning'],
            'keywords': ['deep learning', 'neural networks'],
            'citation_count': 10,
            'full_text_hash': hashlib.sha256('deep learning content'.encode()).hexdigest()
        },
        {
            'document_id': 'med_paper_1',
            'category': 'Healthcare',
            'title': 'AI in Medical Diagnosis',
            'abstract': 'Application of artificial intelligence in medical diagnosis and patient care.',
            'authors': 'Johnson, M.',
            'publication_date': '2024-03-19',
            'journal': 'Medical AI Review',
            'categories': ['Healthcare', 'AI'],
            'keywords': ['medical diagnosis', 'healthcare AI'],
            'citation_count': 15,
            'full_text_hash': hashlib.sha256('medical ai content'.encode()).hexdigest()
        },
        {
            'document_id': 'ai_paper_2',
            'category': 'AI',
            'title': 'Transformer Architecture',
            'abstract': 'Detailed analysis of transformer architecture in natural language processing.',
            'authors': 'Brown, K.',
            'publication_date': '2024-03-18',
            'journal': 'AI Journal',
            'categories': ['AI', 'NLP'],
            'keywords': ['transformers', 'NLP'],
            'citation_count': 20,
            'full_text_hash': hashlib.sha256('transformer content'.encode()).hexdigest()
        }
    ]
    
    # Store all papers
    print("Storing test papers...")
    for paper in test_papers:
        success = processor.store_selected_paper(paper)
        print(f"Stored {paper['title']}: {success}")
    
    print("\nTesting searches:")
    
    # Test 1: General AI search
    print("\n1. Searching for AI-related papers:")
    results = processor.search_similar_papers("artificial intelligence and deep learning", k=3)
    print_results(results)
    
    # Test 2: Medical-specific search
    print("\n2. Searching for medical papers:")
    results = processor.search_similar_papers("medical diagnosis healthcare", k=3)
    print_results(results)
    
    # Test 3: Category-filtered search
    print("\n3. Searching AI papers only in Healthcare category:")
    results = processor.search_similar_papers_by_category(
        query="artificial intelligence", 
        category="Healthcare",
        k=3
    )
    print_results(results)

def print_results(results):
    print(f"\nFound {len(results)} papers:")
    for paper in results:
        print(f"- {paper['title']} (Category: {paper['category']}, Score: {paper.get('similarity_score', 'N/A')})")

if __name__ == "__main__":
    test_vector_operations() 