from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys
from datetime import datetime
import logging
from contextlib import asynccontextmanager
from typing import List
from uuid import UUID


# Add shared modules to path
sys.path.append('/app/shared')

# Import the refactored models
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    service: str
    version: str

class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: str

class ChatResponse(BaseModel):
    session_id: str
    response: str
    intent: str = "general"
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
    id: str  # Changed from UUID to str since we generate it as a string
    user_id: str
    document_id: str  # Changed from int to str since Neo4j document IDs are strings
    session_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageModel] = []

    class Config:
        from_attributes = True

class SessionCreationRequest(BaseModel):
    user_id: str
    document_id: Optional[int] = None
    book_title: Optional[str] = None
    session_name: Optional[str] = None
from database import get_database, DatabaseManager
from utils import setup_logging, get_redis
from chat_service import ChatService

# Setup logging
setup_logging("chat-service")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to initialize and close resources."""
    # Startup
    logger.info("Starting ENBD Chat Service...")
    
    db = get_database()
    await db.initialize()
    
    redis_manager = get_redis()
    
    app.state.chat_service = ChatService(db, redis_manager)
    
    logger.info("ENBD Chat Service started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down ENBD Chat Service...")
    await db.close()
    redis_manager.disconnect()

app = FastAPI(
    title="ENBD Chat Service",
    description="Handles intelligent chat sessions with internal bank documents.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (configure appropriately for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_chat_service() -> ChatService:
    """Dependency injector for the ChatService."""
    return app.state.chat_service

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Provides a health check endpoint for monitoring."""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.utcnow(),
        service="enbd-chat-service",
        version="1.0.0"
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Handles sending a message to an existing chat session.
    """
    try:
        logger.info(f"Chat message received for session: {request.session_id}")
        response = await chat_service.handle_chat(request)
        return response
    except ValueError as e:
        logger.warning(f"Value error during chat: {e}")
        raise HTTPException(status_code=404, detail=str(e)) # e.g., Session not found
    except Exception as e:
        logger.error(f"Error handling chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

# ===============================================
# === Session Management Endpoints ===
# ===============================================

@app.post("/sessions", response_model=ChatSessionModel, status_code=201)
async def create_session(
    request: SessionCreationRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Creates a new chat session for a specific document.
    Accepts either document_id or book_title.
    """
    try:
        session = await chat_service.create_session(
            user_id=request.user_id,
            document_id=request.document_id,
            book_title=request.book_title,
            session_name=request.session_name
        )
        return session
    except ValueError as e:
        logger.warning(f"Could not create session: {e}")
        raise HTTPException(status_code=404, detail=str(e)) # e.g., Document not found
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create session.")

@app.get("/sessions", response_model=List[ChatSessionModel])
async def get_user_sessions(
    user_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Retrieves all chat sessions for a specific user.
    Query parameter: user_id (required)
    """
    try:
        if not user_id or user_id.strip() == "":
            raise HTTPException(status_code=400, detail="user_id query parameter is required.")
        logger.info(f"Fetching chat sessions for user_id: {user_id}")
        sessions = await chat_service.get_user_sessions(user_id)
        logger.info(f"Found {len(sessions)} sessions for user {user_id}")
        return sessions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user sessions for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user sessions: {str(e)}")

@app.get("/sessions/{session_id}/history", response_model=List[ChatMessageModel])
async def get_chat_history(
    session_id: str,
    limit: int = 100,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Retrieves the message history for a specific chat session.
    """
    try:
        history = await chat_service.get_session_history(session_id, limit)
        return history
    except Exception as e:
        logger.error(f"Error getting chat history for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False) # Changed port to 8001 to avoid conflict with ingestion service
