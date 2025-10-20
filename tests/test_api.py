import pytest
from app import create_app
from src.database.db_manager import DatabaseManager
from config.config import config

@pytest.fixture
def app():
    """Create and configure a test application instance."""
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()

def test_search_endpoint(client):
    """Test the search endpoint."""
    response = client.get('/api/search?query=cancer')
    assert response.status_code == 200
    data = response.get_json()
    assert 'papers' in data
    assert 'article_count' in data

def test_research_question_endpoint(client):
    """Test the research question endpoint."""
    response = client.post('/api/research_question', 
                         json={'question': 'What are the latest findings on COVID-19?'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'papers' in data
    assert 'article_count' in data

def test_paper_endpoint(client):
    """Test the paper details endpoint."""
    # Use a known PMID for testing
    test_pmid = '33152271'  # Example PMID
    response = client.get(f'/api/paper/{test_pmid}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'pmid' in data
    assert 'title' in data
    assert 'authors' in data 