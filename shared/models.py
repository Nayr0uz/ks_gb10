import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

# NOTE: These are Neo4j Graph Node representations
# No longer using SQLAlchemy ORM - using simple data classes instead

class User:
    """Neo4j User Node representation"""
    def __init__(self, id: str, full_name: str, email: str, password_hash: str = None, created_at: str = None):
        self.id = id
        self.full_name = full_name
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at

class ServiceCategory:
    """Neo4j ServiceCategory Node representation"""
    def __init__(self, id: int, name: str, description: str = None, created_at: str = None):
        self.id = id
        self.name = name
        self.description = description
        self.created_at = created_at

class Document:
    """Neo4j Document Node representation"""
    def __init__(self, id: str, category_id: int, title: str, document_source: str = None, 
                 publication_date: str = None, file_hash: str = None, file_name: str = None, created_at: str = None):
        self.id = id
        self.category_id = category_id
        self.title = title
        self.document_source = document_source
        self.publication_date = publication_date
        self.file_hash = file_hash
        self.file_name = file_name
        self.created_at = created_at

class DocumentChunk:
    """Neo4j DocumentChunk Node representation"""
    def __init__(self, id: str, document_id: str, content: str, embedding: list = None, 
                 doc_metadata: Dict[str, Any] = None, created_at: str = None):
        self.id = id
        self.document_id = document_id
        self.content = content
        self.embedding = embedding
        self.doc_metadata = doc_metadata or {}
        self.created_at = created_at

class ChatSession:
    """Neo4j ChatSession Node representation"""
    def __init__(self, id: str, user_id: str, document_id: str, session_name: str = None, 
                 created_at: str = None, updated_at: str = None):
        self.id = id
        self.user_id = user_id
        self.document_id = document_id
        self.session_name = session_name
        self.created_at = created_at
        self.updated_at = updated_at

class ChatMessage:
    """Neo4j ChatMessage Node representation"""
    def __init__(self, id: str, session_id: str, message_type: str, content: str, 
                 doc_metadata: Dict[str, Any] = None, created_at: str = None):
        self.id = id
        self.session_id = session_id
        self.message_type = message_type  # 'user' or 'assistant'
        self.content = content
        self.doc_metadata = doc_metadata or {}
        self.created_at = created_at

class Presentation:
    """Neo4j Presentation Node representation"""
    def __init__(self, id: str, title: str, scope: str, topic: str = None, detail_level: str = None,
                 difficulty: str = None, slide_style: str = None, num_slides: int = None,
                 include_diagrams: bool = False, include_code_examples: bool = False,
                 status: str = "pending", output_file_path: str = None, created_at: str = None):
        self.id = id
        self.title = title
        self.scope = scope
        self.topic = topic
        self.detail_level = detail_level
        self.difficulty = difficulty
        self.slide_style = slide_style
        self.num_slides = num_slides
        self.include_diagrams = include_diagrams
        self.include_code_examples = include_code_examples
        self.status = status
        self.output_file_path = output_file_path
        self.created_at = created_at
