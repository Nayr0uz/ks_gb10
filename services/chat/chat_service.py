import logging
from typing import List, Optional, Dict, Any
import json
import os
from database import DatabaseManager
import requests
import httpx
import openai
from memory import SimpleMemoryManager
from langchain_ollama import ChatOllama
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from uuid import UUID
from langchain_openai import ChatOpenAI

import sys
sys.path.append('/app/shared')

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"

class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: str

class ChatResponse(BaseModel):
    session_id: str
    response: str
    metadata: Optional[Dict[str, Any]] = None

class ChatMessageModel(BaseModel):
    id: int
    session_id: str
    message_type: str
    content: str
    doc_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionModel(BaseModel):
    id: str
    user_id: str
    document_id: str
    session_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageModel] = []

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

logger = logging.getLogger(__name__)

def get_clean_v1_url(env_var: str, default: str) -> str:
    # raw_url = os.getenv(env_var, default).rstrip("/")
    raw_url = os.getenv(env_var, default).strip().rstrip("/")
    # Ensure it ends with /v1 exactly once
    if raw_url.endswith("/v1"):
        return raw_url
    return f"{raw_url}/v1"

class ChatService:
    def __init__(self, db_manager: DatabaseManager, redis_manager: Any):
        self.db = db_manager
        self.redis = redis_manager


        # Initialize LangChain components
        self.embeddings = OpenAIEmbeddings(
            model=os.getenv("OLLAMA_EMBEDDING_MODEL", "Qwen3-Embedding-4B-Q8_0"),
            base_url=get_clean_v1_url("OLLAMA_BASE_URL", "http://172.24.77.77:8090"),
            api_key="sk-no-key-required")
        
        # Check backend type - default to 'ollama' but allow 'openai' for llama.cpp/vLLM
        backend_type = os.getenv("LLM_BACKEND_TYPE", "openai").lower()
        
        if backend_type == "openai":
            # Best for llama.cpp / vLLM
            self.llm = ChatOpenAI(
                model=os.getenv("CHAT_MODEL_NAME", "gpt-oss-120b"),
                temperature=float(os.getenv("CHAT_MODEL_TEMPERATURE", "0.7")),
                base_url=get_clean_v1_url("LLM_OPENAI_BASE_URL", "http://172.24.77.77:8089"),
                api_key="sk-no-key-required",
                streaming=True
            )
            logger.info(f"Initialized ChatOpenAI at {self.llm.openai_api_base}")
        else:
            # Fallback for native Ollama (Stripping /v1 if present)
            raw_url = os.getenv("OLLAMA_BASE_URL", "http://172.24.77.77:8090")
            clean_ollama_url = raw_url.replace("/v1", "").rstrip("/")
            self.llm = ChatOllama(
                model=os.getenv("CHAT_MODEL_NAME", "gpt-oss-120b"),
                base_url=clean_ollama_url,
            )
            logger.info(f"Initialized ChatOllama at {self.llm.base_url}")
        
        self.connection_string = os.getenv("DATABASE_URL")
        self.memory_manager = SimpleMemoryManager(self.db)
        
        self._setup_prompts()
    
    def _setup_prompts(self):
        """Setup the prompt template for RAG."""
        pass

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """Handles a user's chat message for a given session."""
        try:
            # 1. Get the session details from the database
            session = await self.db.get_chat_session(request.session_id)
            if not session:
                raise ValueError(f"Chat session with ID '{request.session_id}' not found.")
            
            document_id = session['document_id']
            document_title = session['document_title']

            # 2. Search for relevant document chunks
            relevant_context = await self.search_document_chunks(request.message, document_id)
            
            # 3. Prepare the prompt with context
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are an expert AI assistant for Emirates NBD Bank (ENBD). Your primary function is to answer questions accurately and exclusively based on the provided context from the bank's internal documents.

You are currently consulting the document titled: "{document_title}"

**Core Instructions:**
1.  **Strictly Adhere to Context:** 
       - For banking queries, your answers MUST be derived solely from the information provided in the document context below
       - Only provide information that exists in the document context

2.  **Smart Response Handling:**
    - For greetings (hi, hello, hey, etc.): respond warmly and professionally, then ask how you can help with banking questions
    - For casual conversation: Maintain friendly professionalism but guide users toward banking topics
    - For bank-related questions: If no relevant information is found in the document context, say "I'm sorry, but I couldn't find specific information about that in our current document. Is there something else I can help you with?"

3.  **Be Clear and Concise:** 
        Provide direct answers. If the document provides details, structure your response with a direct answer followed by a more detailed explanation, using bullet points for clarity when listing features or details.

4.  **Maintain Conversation Flow:**
    - Respond naturally to greetings and pleasantries
    - Handle small talk professionally but warmly
    - For bank queries, focus on accurate information from the document provided
    - If unsure, encourage questions about ENBD's services

5.  **Document Context Usage:**
    - The information below is directly from the document, use it to answer comprehensively
    - Cite relevant details when appropriate
    - Do not make up information that is not in the context
    
    
Example Interaction:
User: What is the interest rate for a personal loan?
*You use the `search_internal_document` tool with a query like "personal loan interest rate"*
*The tool returns: "The interest rate for personal loans is a variable rate set at 5% above the EIBOR benchmark."*
Your Response: The interest rate for personal loans is a variable rate, which is set at 5% above the EIBOR benchmark.
"""),
                ("human", f"Document context:\n{relevant_context}\n\nUser question: {request.message}")
            ])
            
            # 4. Generate response
            chain = prompt | self.llm | StrOutputParser()
            response_text = await chain.ainvoke({})
            
            logger.info(f"Response generated. Response length: {len(response_text)} characters")
            
            # 5. Save the conversation turn to the database
            await self.db.add_chat_message(
                request.session_id, MessageType.USER.value, request.message
            )
            await self.db.add_chat_message(
                request.session_id, MessageType.ASSISTANT.value, response_text
            )
            
            chat_response = ChatResponse(
                response=response_text,
                session_id=str(session['id']),
                metadata={"document_title": document_title}
            )
            logger.info(f"Returning ChatResponse with response length: {len(chat_response.response)}")
            return chat_response
            
        except Exception as e:
            logger.error(f"Error handling chat request for session {request.session_id}: {e}", exc_info=True)
            raise

    async def search_document_chunks(self, query: str, document_id: str) -> str:
        """
        Searches Neo4j for document chunks related to the given query.
        Uses semantic similarity on embeddings or falls back to text matching.
        """
        logger.info(f"Executing document search for doc_id={document_id} with query: '{query}'")
        try:
            # Get embedding for the query
            query_embedding = await self.embeddings.aembed_query(query)
            logger.info(f"Generated query embedding with {len(query_embedding)} dimensions")
            
            # Query Neo4j to get all chunks for this document with their embeddings
            chunks_query = """
            MATCH (d:Document {id: $document_id})-[:HAS_CHUNK]->(c:Chunk)
            RETURN c.id as id, c.content as content, c.embedding as embedding
            LIMIT 20
            """
            
            chunks = await self.db.execute_query(chunks_query, {"document_id": document_id})
            logger.info(f"Found {len(chunks)} chunks for document {document_id}")
            
            if not chunks:
                logger.warning(f"No chunks found in document {document_id}")
                return "No relevant information found in the document for this query."
            
            # Calculate similarity scores for each chunk
            chunk_scores = []
            for chunk in chunks:
                try:
                    embedding_str = chunk.get('embedding')
                    if not embedding_str:
                        logger.debug(f"Chunk {chunk['id']} has no embedding, skipping")
                        continue
                    
                    # Parse embedding from JSON string
                    chunk_embedding = json.loads(embedding_str) if isinstance(embedding_str, str) else embedding_str
                    
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                    chunk_scores.append({
                        'id': chunk['id'],
                        'content': chunk['content'],
                        'similarity': similarity
                    })
                except Exception as e:
                    logger.warning(f"Failed to process chunk {chunk['id']}: {e}")
                    continue
            
            # Sort by similarity and get top results
            chunk_scores.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Filter by similarity threshold
            relevant_chunks = [c for c in chunk_scores if c['similarity'] > 0.3]
            
            if relevant_chunks:
                logger.info(f"Found {len(relevant_chunks)} relevant chunks with similarity > 0.3")
                combined_context = "\n\n---\n\n".join([c['content'] for c in relevant_chunks[:10]])
                return combined_context
            else:
                logger.warning(f"No chunks with sufficient similarity for query: '{query}'")
                
                # Fallback: text-based search using keyword matching
                logger.info("Attempting text-based fallback search...")
                words = [w.strip().lower() for w in query.split() if len(w.strip()) > 2]
                
                if not words:
                    return "No relevant information found in the document for this query."
                
                # Find chunks that contain any of the query words
                text_matches = []
                for chunk_score in chunk_scores:
                    content_lower = chunk_score['content'].lower()
                    word_count = sum(1 for word in words if word in content_lower)
                    if word_count > 0:
                        text_matches.append({
                            **chunk_score,
                            'word_matches': word_count
                        })
                
                if text_matches:
                    # Sort by number of word matches
                    text_matches.sort(key=lambda x: x['word_matches'], reverse=True)
                    logger.info(f"Text-based fallback found {len(text_matches)} chunks")
                    combined_context = "\n\n---\n\n".join([c['content'] for c in text_matches[:10]])
                    return combined_context
                else:
                    return "No relevant information found in the document for this query."
            pass
        except (openai.APIConnectionError, httpx.ConnectError, ConnectionRefusedError) as e:
            logger.error(f"CRITICAL: Could not connect to AI server. Error: {e}")
            return "Error: AI Inference server unreachable."
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}", exc_info=True)
            return "An error occurred while searching the document."

    def _cosine_similarity(self, vec1: list, vec2: list) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        if len(vec1) != len(vec2):
            logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)

    # ===============================================
    # === Session Management API Methods ===
    # ===============================================

    async def create_session(self, user_id: str, document_id: str = None, book_title: str = None, session_name: str = None) -> ChatSessionModel:
        """Creates a new chat session for a given document."""
        try:
            # If book_title is provided instead of document_id, look it up
            if not document_id and book_title:
                doc = await self.db.fetch_one("MATCH (d:Document {title: $title}) RETURN d.id as id", {"title": book_title})
                if not doc:
                    raise ValueError(f"Document with title '{book_title}' not found.")
                document_id = doc['id']
            
            if not document_id:
                raise ValueError("Either document_id or book_title must be provided.")
            
            # Check if document exists to prevent sessions for non-existent docs
            document = await self.db.fetch_one("MATCH (d:Document {id: $id}) RETURN d.title as title", {"id": document_id})
            if not document:
                raise ValueError(f"Document with ID {document_id} not found.")

            session_id = await self.db.create_chat_session(
                user_id=user_id,
                document_id=document_id,
                session_name=session_name or f"Chat about {document['title']}"
            )
            
            session_data = await self.db.get_chat_session(session_id)
            
            # Convert Neo4j DateTime objects to ISO format strings
            if session_data and hasattr(session_data.get('created_at'), 'to_native'):
                session_data['created_at'] = session_data['created_at'].to_native().isoformat()
            if session_data and hasattr(session_data.get('updated_at'), 'to_native'):
                session_data['updated_at'] = session_data['updated_at'].to_native().isoformat()
            
            return ChatSessionModel(**session_data)
            
        except Exception as e:
            logger.error(f"Error creating session: {e}", exc_info=True)
            raise

    async def get_session_history(self, session_id: str, limit: int = 100) -> List[Dict]:
        """Gets the full message history for a session."""
        try:
            return await self.db.get_chat_history(session_id, limit)
        except Exception as e:
            logger.error(f"Error getting chat history for session {session_id}: {e}", exc_info=True)
            raise

    async def get_user_sessions(self, user_id: str) -> List[ChatSessionModel]:
        """Gets all chat sessions for a specific user."""
        try:
            sessions_data = await self.db.get_user_chat_sessions(user_id)
            result = []
            for s in sessions_data:
                # Convert Neo4j DateTime objects to ISO format strings
                created_at = s['created_at']
                updated_at = s['updated_at']
                if hasattr(created_at, 'to_native'):
                    created_at = created_at.to_native().isoformat()
                if hasattr(updated_at, 'to_native'):
                    updated_at = updated_at.to_native().isoformat()
                
                result.append(ChatSessionModel(
                    id=s['id'],
                    user_id=s['user_id'],
                    document_id=s['document_id'],
                    session_name=s['session_name'],
                    created_at=created_at,
                    updated_at=updated_at,
                    messages=[]
                ))
            return result
        except Exception as e:
            logger.error(f"Error getting user sessions for user {user_id}: {e}", exc_info=True)
            raise

