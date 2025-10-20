from datetime import datetime
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Association table for papers and keywords
paper_keywords = Table('paper_keywords', Base.metadata,
    Column('paper_id', Integer, ForeignKey('papers.id')),
    Column('keyword_id', Integer, ForeignKey('keywords.id'))
)

# Association table for papers and authors
paper_authors = Table('paper_authors', Base.metadata,
    Column('paper_id', Integer, ForeignKey('papers.id')),
    Column('author_id', Integer, ForeignKey('authors.id'))
)

class Paper(Base):
    """Research paper model."""
    __tablename__ = 'papers'

    id = Column(Integer, primary_key=True)
    pmid = Column(String(20), unique=True, index=True)
    title = Column(String(500), nullable=False)
    abstract = Column(Text)
    journal = Column(String(255))
    publication_date = Column(Date)
    doi = Column(String(100))
    url = Column(String(500))
    created_at = Column(Date, default=datetime.utcnow)
    
    # Relationships
    authors = relationship('Author', secondary=paper_authors, back_populates='papers')
    keywords = relationship('Keyword', secondary=paper_keywords, back_populates='papers')

class Author(Base):
    """Author model."""
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    
    # Relationships
    papers = relationship('Paper', secondary=paper_authors, back_populates='authors')

class Keyword(Base):
    """Keyword model."""
    __tablename__ = 'keywords'

    id = Column(Integer, primary_key=True)
    word = Column(String(100), nullable=False, unique=True)
    
    # Relationships
    papers = relationship('Paper', secondary=paper_keywords, back_populates='keywords')
