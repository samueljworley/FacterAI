from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from .models import Base, Paper, Author, Keyword

class DatabaseManager:
    """Handles all database operations."""
    
    def __init__(self, connection_string: str):
        """Initialize database connection.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.engine = create_engine(connection_string)
        self._SessionFactory = sessionmaker(bind=self.engine)
        self.session = scoped_session(self._SessionFactory)
        
    def init_db(self):
        """Create all database tables."""
        Base.metadata.create_all(self.engine)
        
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.session()
        
    def add_paper(self, paper_data: Dict) -> Paper:
        """Add a new paper to the database.
        
        Args:
            paper_data: Dictionary containing paper metadata
            
        Returns:
            Paper: Created paper object
        """
        session = self.get_session()
        try:
            # Check if paper already exists
            existing_paper = session.query(Paper).filter_by(pmid=paper_data['pmid']).first()
            if existing_paper:
                # Refresh the paper to ensure all relationships are loaded
                session.refresh(existing_paper)
                return existing_paper
                
            # Handle publication date formatting
            pub_date = paper_data.get('publication_date')
            if pub_date:
                # If only year is provided, set to January 1st of that year
                if len(pub_date) == 4:  # Just year
                    pub_date = f"{pub_date}-01-01"
                elif len(pub_date) == 7:  # Year and month
                    pub_date = f"{pub_date}-01"
            
            # Create new paper
            paper = Paper(
                pmid=paper_data['pmid'],
                title=paper_data['title'],
                abstract=paper_data['abstract'],
                journal=paper_data['journal'],
                publication_date=pub_date,
                doi=paper_data.get('doi'),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{paper_data['pmid']}"
            )
            
            # Add authors
            for author_name in paper_data['authors']:
                author = session.query(Author).filter_by(name=author_name).first()
                if not author:
                    author = Author(name=author_name)
                paper.authors.append(author)
                
            # Add keywords
            for word in paper_data.get('keywords', []):
                keyword = session.query(Keyword).filter_by(word=word).first()
                if not keyword:
                    keyword = Keyword(word=word)
                paper.keywords.append(keyword)
                
            session.add(paper)
            session.commit()
            
            # Refresh the paper to ensure all relationships are loaded
            session.refresh(paper)
            return paper
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
    def search_papers(self, query: str, limit: int = 10) -> List[Paper]:
        """Search for papers in the database.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List[Paper]: Matching papers
        """
        with self.get_session() as session:
            return session.query(Paper)\
                .filter(Paper.title.ilike(f'%{query}%'))\
                .limit(limit)\
                .all()
