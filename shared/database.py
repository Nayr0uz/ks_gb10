import os
import json
from typing import Optional, List, Dict, Any
import logging
from contextlib import asynccontextmanager
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable
import asyncio

logger = logging.getLogger(__name__)

# Global lock for category initialization across all instances
_categories_init_lock = asyncio.Lock()

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.driver = None
        self.username = "neo4j"
        self.password = "enbd_password"
        self._categories_initialized = False
        
        # Parse connection string if needed
        if "@" in database_url:
            # Format: neo4j://user:pass@host:port
            parts = database_url.split("://")[1]
            creds, host_port = parts.split("@")
            self.username, self.password = creds.split(":")
            self.bolt_uri = f"neo4j://{host_port}"
        else:
            self.bolt_uri = database_url

    async def initialize(self):
        """Initialize Neo4j driver connection"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.bolt_uri,
                auth=(self.username, self.password)
            )
            # Test connection
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            logger.info("Neo4j database connection pool initialized")
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")
            raise

    async def close(self):
        """Close Neo4j driver connection"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection pool closed")

    async def initialize_categories(self):
        """Initialize default service categories in Neo4j (only if they don't exist)"""
        # Use global lock to prevent race conditions across all instances
        async with _categories_init_lock:
            # Check if already initialized in this instance
            if self._categories_initialized:
                logger.info("Service categories already initialized in this instance")
                return
            
            try:
                # Check if categories already exist in the database
                count_query = "MATCH (sc:ServiceCategory) RETURN COUNT(sc) as count"
                result = await self.fetch_one(count_query)
                existing_count = result.get("count", 0) if result else 0
                
                # Only initialize if we don't have exactly 9 categories
                if existing_count == 9:
                    logger.info("Service categories already initialized (9 found in database)")
                    self._categories_initialized = True
                    return
                
                # If we have the wrong number, clean up and reinitialize in a single transaction
                if existing_count > 0:
                    logger.info(f"Found {existing_count} categories, cleaning up before reinitializing...")
                    await self.execute_write("MATCH (sc:ServiceCategory) DETACH DELETE sc")
                
                # Create all 9 categories in a single transaction for atomicity
                categories_data = [
                    {"id": 1, "name": "Accounts & Savings", "description": "Documents about deposit accounts, current and savings accounts, and related terms."},
                    {"id": 2, "name": "Loans", "description": "Documents covering personal, mortgage, auto, and business loan products and terms."},
                    {"id": 3, "name": "Cards", "description": "Information on debit, credit, and prepaid card products and fees."},
                    {"id": 4, "name": "Investments", "description": "Materials related to investment products, mutual funds, and wealth services."},
                    {"id": 5, "name": "Business & Corporate Banking", "description": "Services and products tailored for corporate and business customers."},
                    {"id": 6, "name": "Insurance (Bancassurance)", "description": "Insurance products offered through the bank (bancassurance)."},
                    {"id": 7, "name": "Digital & E-Banking", "description": "Digital channels, mobile and online banking services, and related security guidance."},
                    {"id": 8, "name": "Payroll Services", "description": "Payroll and salary account services for employers and employees."},
                    {"id": 9, "name": "General Information", "description": "General bank information, annual reports, and documents that span multiple categories."},
                ]
                
                # Create all categories in one transaction
                batch_query = """
                UNWIND $categories as cat
                MERGE (sc:ServiceCategory {id: cat.id})
                ON CREATE SET sc.name = cat.name, sc.description = cat.description, sc.created_at = datetime()
                ON MATCH SET sc.name = cat.name, sc.description = cat.description
                RETURN sc.id, sc.name
                """
                
                result = await self.execute_query(batch_query, {"categories": categories_data})
                created_count = len(result) if result else 0
                
                self._categories_initialized = True
                logger.info(f"Service categories initialized successfully ({created_count} categories ensured)")
            except Exception as e:
                logger.error(f"Failed to initialize service categories: {e}")
                # Don't raise - this should not block application startup

    @asynccontextmanager
    async def get_session(self):
        """Get a Neo4j session context manager"""
        if not self.driver:
            raise RuntimeError("Neo4j driver not initialized. Call initialize() first.")
        
        session = self.driver.session()
        try:
            yield session
        finally:
            await session.close()

    @asynccontextmanager
    async def get_connection(self):
        """Compatibility wrapper for presentation service - translates SQL operations to Neo4j"""
        class MockConnection:
            """SQL-to-Neo4j adapter for presentation service compatibility"""
            def __init__(self, db_manager):
                self.db = db_manager
            
            async def fetchval(self, sql_query: str, *args):
                """Translate SQL INSERT...RETURNING to Neo4j create operations"""
                if "INSERT INTO presentations" in sql_query:
                    # SQL: INSERT INTO presentations (...) VALUES (...) RETURNING id
                    title, scope, topic, detail_level, difficulty, slide_style, num_slides, include_diagrams, include_code_examples = args
                    presentation_id = await self.db.create_presentation(
                        title=title, scope=scope, topic=topic, detail_level=detail_level,
                        difficulty=difficulty, slide_style=slide_style, num_slides=num_slides,
                        include_diagrams=include_diagrams, include_code_examples=include_code_examples
                    )
                    return presentation_id
                raise NotImplementedError(f"SQL query not supported: {sql_query}")
            
            async def fetchrow(self, sql_query: str, *args):
                """Execute Cypher or SQL SELECT single-row queries to Neo4j fetch operations"""
                # Check if this is a Cypher query (starts with MATCH, CALL, WITH, RETURN, etc.)
                if sql_query.strip().upper().startswith(("MATCH", "CALL", "WITH", "RETURN", "CREATE", "MERGE")):
                    # Direct Cypher query execution
                    async with self.db.get_session() as session:
                        # Build Neo4j parameters: {"1": value1, "2": value2, ...}
                        params = {str(i+1): arg for i, arg in enumerate(args)}
                        result = await session.run(sql_query, parameters=params)
                        records = await result.data()
                        return records[0] if records else None
                
                # SQL pattern matching for backward compatibility
                # SQL: SELECT * FROM presentations WHERE id = $1
                if "presentations" in sql_query and args and "WHERE id" in sql_query:
                    presentation_id = args[0]
                    result = await self.db.get_presentation(presentation_id)
                    return result if result else None
                # SQL: SELECT * FROM documents WHERE (name/title ILIKE/LIKE %search% OR file_name ILIKE/LIKE %search%) LIMIT 1
                elif "documents" in sql_query:
                    # The presentation service searches for documents by title or file name
                    # This handles: SELECT id, title, file_name FROM documents WHERE (title ILIKE $1 OR file_name ILIKE $1) OR ... LIMIT 1
                    if args:
                        search_term = args[0].strip('%').lower() if args[0] else None
                        if search_term:
                            result = await self.db.get_document_by_title(search_term)
                            if result:
                                return {"id": result.get("id"), "title": result.get("title"), "file_name": result.get("file_name")}
                    # Fallback: return first document
                    docs = await self.db.get_all_documents()
                    if docs:
                        return {"id": docs[0].get("id"), "title": docs[0].get("title"), "file_name": docs[0].get("file_name")}
                    return None
                # SQL: SELECT * FROM document_chunks WHERE document_id = $1 LIMIT 1
                elif "document_chunks" in sql_query and args:
                    document_id = args[0]
                    chunks = await self.db.get_document_chunks(document_id, 1)
                    return chunks[0] if chunks else None
                raise NotImplementedError(f"Query not supported: {sql_query}")
            
            async def fetch(self, sql_query: str, *args):
                """Execute Cypher or SQL SELECT multi-row queries to Neo4j fetch operations"""
                # Check if this is a Cypher query (starts with MATCH, CALL, WITH, RETURN, etc.)
                if sql_query.strip().upper().startswith(("MATCH", "CALL", "WITH", "RETURN", "CREATE", "MERGE")):
                    # Direct Cypher query execution
                    async with self.db.get_session() as session:
                        # Build Neo4j parameters: {"1": value1, "2": value2, ...}
                        params = {str(i+1): arg for i, arg in enumerate(args)}
                        result = await session.run(sql_query, parameters=params)
                        records = await result.data()
                        return records if records else []
                
                # SQL pattern matching for backward compatibility
                # SQL: SELECT * FROM presentations LIMIT $1
                if "presentations" in sql_query:
                    limit = args[0] if args else 50
                    results = await self.db.list_presentations(limit)
                    return [{"id": r.get("id"), "title": r.get("title"), "status": r.get("status"),
                            "output_file_path": r.get("output_file_path"), "created_at": r.get("created_at")} for r in results]
                # SQL: SELECT * FROM document_chunks WHERE document_id = $1 LIMIT $2
                elif "document_chunks" in sql_query and args:
                    document_id = args[0]
                    limit = args[1] if len(args) > 1 else 30
                    chunks = await self.db.get_document_chunks(document_id, limit)
                    return [{"id": c.get("id"), "content": c.get("content")} for c in chunks]
                raise NotImplementedError(f"Query not supported: {sql_query}")
            
            async def execute(self, sql_query: str, *args):
                """Execute Cypher or SQL UPDATE/DELETE queries to Neo4j update operations"""
                # Check if this is a Cypher query (starts with MATCH, CALL, WITH, RETURN, CREATE, MERGE, DELETE, etc.)
                if sql_query.strip().upper().startswith(("MATCH", "CALL", "WITH", "RETURN", "CREATE", "MERGE", "DELETE", "DETACH")):
                    # Direct Cypher query execution
                    async with self.db.get_session() as session:
                        # Build Neo4j parameters: {"1": value1, "2": value2, ...}
                        params = {str(i+1): arg for i, arg in enumerate(args)}
                        result = await session.run(sql_query, parameters=params)
                        await result.consume()
                    return None
                
                # SQL pattern matching for backward compatibility
                if "UPDATE presentations" in sql_query:
                    # SQL: UPDATE presentations SET status = $1, content = $2 WHERE id = $3
                    if "status" in sql_query and "content" in sql_query and "output_file_path" not in sql_query:
                        status, content, presentation_id = args[0], args[1], args[2]
                        await self.db.update_presentation_content(presentation_id, content, status)
                    # SQL: UPDATE presentations SET status = $1, output_file_path = $2, content = $3 WHERE id = $4
                    elif "status" in sql_query and "output_file_path" in sql_query and "content" in sql_query:
                        status, output_file_path, content, presentation_id = args[0], args[1], args[2], args[3]
                        await self.db.update_presentation_content(presentation_id, content, status)
                        await self.db.update_presentation_file_path(presentation_id, output_file_path)
                    # SQL: UPDATE presentations SET output_file_path = $1 WHERE id = $2
                    elif "output_file_path" in sql_query:
                        file_path, presentation_id = args[0], args[1]
                        await self.db.update_presentation_file_path(presentation_id, file_path)
                    return None
                raise NotImplementedError(f"Query not supported: {sql_query}")
        
        yield MockConnection(self)

    async def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results as a list of dicts"""
        async with self.get_session() as session:
            result = await session.run(query, parameters=params or {})
            records = await result.data()
            return records

    async def execute_write(self, query: str, params: Dict[str, Any] = None) -> Any:
        """Execute a write transaction (CREATE, UPDATE, DELETE)"""
        async with self.get_session() as session:
            result = await session.run(query, parameters=params or {})
            summary = await result.consume()
            return summary

    async def fetch_one(self, query: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single record"""
        results = await self.execute_query(query, params)
        return results[0] if results else None

    async def fetch_val(self, query: str, params: Dict[str, Any] = None) -> Any:
        """Fetch a single value from the first result"""
        result = await self.fetch_one(query, params)
        if result:
            # Get the first value from the first key
            return next(iter(result.values())) if result else None
        return None

    # ===============================================
    # === Document & Category Methods ===
    # ===============================================

    async def get_service_categories(self) -> List[Dict[str, Any]]:
        """Get all service categories"""
        query = """
        MATCH (sc:ServiceCategory)
        RETURN sc.id as id, sc.name as name, sc.description as description, sc.created_at as created_at
        ORDER BY sc.name
        """
        return await self.execute_query(query)

    async def get_documents_by_category(self, category_id: str) -> List[Dict[str, Any]]:
        """Get documents by a specific service category"""
        query = """
        MATCH (sc:ServiceCategory {id: $category_id})-[:HAS_DOCUMENTS]->(d:Document)
        RETURN 
            d.id as id, d.category_id as category_id, d.title as title, 
            d.document_source as document_source, d.publication_date as publication_date,
            d.file_hash as file_hash, d.file_name as file_name, d.created_at as created_at,
            sc.name as category_name
        ORDER BY d.title
        """
        return await self.execute_query(query, {"category_id": category_id})

    async def check_document_exists(self, file_hash: str) -> bool:
        """Check if a document exists by its file hash"""
        query = """
        MATCH (d:Document {file_hash: $file_hash})
        RETURN COUNT(d) > 0 as exists
        """
        result = await self.fetch_one(query, {"file_hash": file_hash})
        return result.get("exists", False) if result else False

    async def insert_document(self, doc_data: Dict[str, Any]) -> str:
        """Insert a new document and return its ID"""
        doc_id = doc_data.get('id') or f"doc_{doc_data['file_hash'][:8]}"
        query = """
        MERGE (sc:ServiceCategory {id: $category_id})
        ON CREATE SET sc.name = CASE WHEN $category_id = 1 THEN 'Accounts & Savings'
                                     WHEN $category_id = 2 THEN 'Loans'
                                     WHEN $category_id = 3 THEN 'Cards'
                                     WHEN $category_id = 4 THEN 'Investments'
                                     WHEN $category_id = 5 THEN 'Business & Corporate Banking'
                                     WHEN $category_id = 6 THEN 'Insurance (Bancassurance)'
                                     WHEN $category_id = 7 THEN 'Digital & E-Banking'
                                     WHEN $category_id = 8 THEN 'Payroll Services'
                                     ELSE 'General Information' END,
                       sc.created_at = datetime()
        MERGE (d:Document {id: $id})
        ON CREATE SET d.category_id = $category_id,
                      d.title = $title,
                      d.document_source = $document_source,
                      d.publication_date = $publication_date,
                      d.file_hash = $file_hash,
                      d.file_name = $file_name,
                      d.created_at = datetime()
        ON MATCH SET d.category_id = $category_id,
                     d.title = $title,
                     d.document_source = $document_source,
                     d.publication_date = $publication_date,
                     d.file_hash = $file_hash,
                     d.file_name = $file_name
        MERGE (sc)-[:HAS_DOCUMENTS]->(d)
        RETURN d.id as id
        """
        result = await self.fetch_one(query, {
            "id": doc_id,
            "category_id": doc_data['category_id'],
            "title": doc_data['title'],
            "document_source": doc_data.get('document_source'),
            "publication_date": doc_data.get('publication_date'),
            "file_hash": doc_data['file_hash'],
            "file_name": doc_data.get('file_name')
        })
        return result.get("id") if result else doc_id

    async def bulk_insert_chunks(self, chunks_data: List[Dict[str, Any]]):
        """Bulk insert document chunks and their embeddings"""
        if not chunks_data:
            return

        # Create a Cypher query that handles multiple chunks efficiently
        for chunk in chunks_data:
            chunk_id = f"chunk_{chunk['document_id']}_{hash(chunk['content']) & 0xffffffff}"
            query = """
            MATCH (d:Document {id: $document_id})
            MERGE (c:Chunk {id: $chunk_id})
            ON CREATE SET c.content = $content,
                         c.embedding = $embedding,
                         c.metadata = $metadata,
                         c.created_at = datetime()
            ON MATCH SET c.content = $content,
                        c.embedding = $embedding,
                        c.metadata = $metadata
            MERGE (d)-[:HAS_CHUNK]->(c)
            """
            
            embedding = chunk.get('embedding')
            embedding_str = json.dumps(embedding) if isinstance(embedding, list) else None

            await self.execute_write(query, {
                "document_id": chunk['document_id'],
                "chunk_id": chunk_id,
                "content": chunk['content'],
                "embedding": embedding_str,
                "metadata": json.dumps(chunk.get('metadata') or {})
            })

    # ===============================================
    # === Chat Session Methods ===
    # ===============================================

    async def create_chat_session(self, user_id: str, document_id: str, session_name: str = None) -> str:
        """Create a new chat session for a specific document"""
        session_id = f"session_{user_id}_{document_id}_{hash(session_name or '') & 0xffffffff}"
        query = """
        MATCH (d:Document {id: $document_id})
        CREATE (cs:ChatSession {
            id: $session_id,
            user_id: $user_id,
            document_id: $document_id,
            session_name: $session_name,
            created_at: datetime(),
            updated_at: datetime()
        })
        CREATE (cs)-[:ABOUT]->(d)
        RETURN cs.id as id
        """
        result = await self.fetch_one(query, {
            "session_id": session_id,
            "user_id": user_id,
            "document_id": document_id,
            "session_name": session_name
        })
        return result.get("id") if result else session_id

    async def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session details by its ID"""
        query = """
        MATCH (cs:ChatSession {id: $session_id})
        OPTIONAL MATCH (cs)-[:ABOUT]->(d:Document)
        RETURN 
            cs.id as id, cs.user_id as user_id, cs.document_id as document_id,
            cs.session_name as session_name, cs.created_at as created_at, cs.updated_at as updated_at,
            d.title as document_title
        """
        return await self.fetch_one(query, {"session_id": session_id})

    async def add_chat_message(self, session_id: str, message_type: str, content: str, metadata: Dict = None) -> str:
        """Add a new message to a chat session"""
        msg_id = f"msg_{session_id}_{hash(content) & 0xffffffff}"
        query = """
        MATCH (cs:ChatSession {id: $session_id})
        CREATE (m:Message {
            id: $msg_id,
            message_type: $message_type,
            content: $content,
            metadata: $metadata,
            created_at: datetime()
        })
        CREATE (cs)-[:HAS_MESSAGE]->(m)
        RETURN m.id as id
        """
        metadata_json = json.dumps(metadata) if metadata else None
        result = await self.fetch_one(query, {
            "msg_id": msg_id,
            "session_id": session_id,
            "message_type": message_type,
            "content": content,
            "metadata": metadata_json
        })
        return result.get("id") if result else msg_id

    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the chat history for a given session"""
        query = """
        MATCH (cs:ChatSession {id: $session_id})-[:HAS_MESSAGE]->(m:Message)
        RETURN m.message_type as message_type, m.content as content, m.metadata as metadata, m.created_at as created_at
        ORDER BY m.created_at ASC
        LIMIT $limit
        """
        return await self.execute_query(query, {"session_id": session_id, "limit": limit})

    async def get_user_chat_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all chat sessions for a specific user"""
        query = """
        MATCH (u:User {id: $user_id})-[:HAS_SESSION]->(cs:ChatSession)
        OPTIONAL MATCH (cs)-[:ABOUT]->(d:Document)
        OPTIONAL MATCH (d)-[:IN_CATEGORY]->(sc:ServiceCategory)
        RETURN 
            cs.id as id, cs.user_id as user_id, cs.document_id as document_id,
            cs.session_name as session_name, cs.created_at as created_at, cs.updated_at as updated_at,
            d.title as document_title, sc.name as category_name
        ORDER BY cs.updated_at DESC
        """
        try:
            return await self.execute_query(query, {"user_id": user_id})
        except Exception as e:
            logger.error(f"Error fetching chat sessions for user {user_id}: {e}", exc_info=True)
            return []


    # ===============================================
    # === User Methods ===
    # ===============================================

    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user"""
        query = """
        CREATE (u:User {
            id: $id,
            full_name: $full_name,
            email: $email,
            password_hash: $password_hash,
            created_at: datetime()
        })
        RETURN u.id as id
        """
        result = await self.fetch_one(query, user_data)
        return result.get("id") if result else user_data.get("id")

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        query = """
        MATCH (u:User {email: $email})
        RETURN u.id as id, u.full_name as full_name, u.email as email, u.password_hash as password_hash, u.created_at as created_at
        """
        return await self.fetch_one(query, {"email": email})

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        query = """
        MATCH (u:User {id: $user_id})
        RETURN u.id as id, u.full_name as full_name, u.email as email, u.created_at as created_at
        """
        return await self.fetch_one(query, {"user_id": user_id})

    # ===============================================
    # === Presentation Methods ===
    # ===============================================

    async def create_presentation(self, title: str, scope: str, topic: Optional[str] = None,
                                     detail_level: Optional[str] = None, difficulty: Optional[str] = None,
                                     slide_style: Optional[str] = None, num_slides: Optional[int] = None,
                                     include_diagrams: bool = False, include_code_examples: bool = False) -> str:
        """Create a new presentation node in Neo4j"""
        import uuid
        presentation_id = str(uuid.uuid4())
        query = """
        CREATE (p:Presentation {
            id: $id,
            title: $title,
            scope: $scope,
            topic: $topic,
            detail_level: $detail_level,
            difficulty: $difficulty,
            slide_style: $slide_style,
            num_slides: $num_slides,
            include_diagrams: $include_diagrams,
            include_code_examples: $include_code_examples,
            status: 'processing',
            content: '',
            output_file_path: '',
            created_at: datetime()
        })
        RETURN p.id as id
        """
        result = await self.fetch_one(query, {
            "id": presentation_id,
            "title": title,
            "scope": scope,
            "topic": topic,
            "detail_level": detail_level,
            "difficulty": difficulty,
            "slide_style": slide_style,
            "num_slides": num_slides,
            "include_diagrams": include_diagrams,
            "include_code_examples": include_code_examples
        })
        return result.get("id") if result else presentation_id

    async def get_presentation(self, presentation_id: str) -> Optional[Dict[str, Any]]:
        """Get a presentation by ID"""
        query = """
        MATCH (p:Presentation {id: $id})
        RETURN p.id as id, p.title as title, p.scope as scope, p.topic as topic,
               p.detail_level as detail_level, p.difficulty as difficulty,
               p.slide_style as slide_style, p.num_slides as num_slides,
               p.include_diagrams as include_diagrams, p.include_code_examples as include_code_examples,
               p.status as status, p.content as content, p.output_file_path as output_file_path,
               p.created_at as created_at
        """
        return await self.fetch_one(query, {"id": presentation_id})

    async def update_presentation_content(self, presentation_id: str, content: str, status: str = 'completed') -> bool:
        """Update presentation content and status"""
        query = """
        MATCH (p:Presentation {id: $id})
        SET p.content = $content, p.status = $status, p.updated_at = datetime()
        RETURN p.id
        """
        result = await self.fetch_one(query, {
            "id": presentation_id,
            "content": content,
            "status": status
        })
        return result is not None

    async def update_presentation_file_path(self, presentation_id: str, file_path: str) -> bool:
        """Update presentation output file path"""
        query = """
        MATCH (p:Presentation {id: $id})
        SET p.output_file_path = $file_path
        RETURN p.id
        """
        result = await self.fetch_one(query, {
            "id": presentation_id,
            "file_path": file_path
        })
        return result is not None

    async def list_presentations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all presentations"""
        query = """
        MATCH (p:Presentation)
        RETURN p.id as id, p.title as title, p.scope as scope, p.status as status,
               p.created_at as created_at, p.output_file_path as output_file_path
        ORDER BY p.created_at DESC
        LIMIT $limit
        """
        return await self.execute_query(query, {"limit": limit})

    async def get_document_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Find a document by title (for presentation generation)"""
        query = """
        MATCH (d:Document)
        WHERE d.title CONTAINS $title OR d.file_name CONTAINS $title
        RETURN d.id as id, d.title as title, d.file_name as file_name, d.category_id as category_id
        ORDER BY d.created_at DESC
        LIMIT 1
        """
        return await self.fetch_one(query, {"title": title})

    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents in the database"""
        query = """
        MATCH (d:Document)
        RETURN d.id as id, d.title as title, d.file_name as file_name, d.category_id as category_id, d.created_at as created_at
        ORDER BY d.created_at DESC
        """
        return await self.execute_query(query)

    async def get_document_chunks(self, document_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Get chunks for a specific document"""
        query = """
        MATCH (d:Document {id: $document_id})-[:HAS_CHUNK]->(c:Chunk)
        RETURN c.id as id, c.content as content, c.embedding as embedding, c.metadata as metadata
        ORDER BY c.id
        LIMIT $limit
        """
        return await self.execute_query(query, {"document_id": document_id, "limit": limit})


# ===============================================
# === Global Database Manager Instance ===
# ===============================================

db_manager = None

def get_database() -> DatabaseManager:
    """Singleton accessor for the DatabaseManager instance"""
    global db_manager
    if not db_manager:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set.")
        db_manager = DatabaseManager(database_url)
    return db_manager