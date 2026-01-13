from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys
from datetime import datetime
import logging
from contextlib import asynccontextmanager

# Add shared modules to path
sys.path.append('/app/shared')

from shared.models import Document, ServiceCategory
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DocumentModel(BaseModel):
    id: Optional[str] = None  # Changed to str for UUID
    category_id: Optional[int] = None
    title: str
    document_source: Optional[str] = None
    publication_date: Optional[str] = None
    file_hash: str
    file_name: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class ServiceCategoryModel(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    service: str
    version: str
from database import get_database, DatabaseManager
from utils import setup_logging, get_redis, calculate_file_hash
from ingestion_service import IngestionService

# Setup logging
setup_logging("ingestion-service")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to initialize and close resources."""
    # Startup
    logger.info("Starting ENBD Ingestion Service...")
    
    db = get_database()
    await db.initialize()
    
    redis_manager = get_redis()
    
    app.state.ingestion_service = IngestionService(db, redis_manager)
    
    logger.info("ENBD Ingestion Service started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down ENBD Ingestion Service...")
    await db.close()
    redis_manager.disconnect()

app = FastAPI(
    title="ENBD Document Ingestion Service",
    description="Processes and ingests internal bank documents for the ENBD intelligent chat system.",
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

def get_ingestion_service() -> IngestionService:
    """Dependency injector for the IngestionService."""
    return app.state.ingestion_service

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Provides a health check endpoint for monitoring."""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.utcnow(),
        service="enbd-ingestion-service",
        version="1.0.0"
    )

@app.post("/upload", response_model=DocumentModel)
async def upload_document(
    file: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Uploads and processes a document file (PDF, TXT)."""
    logger.info(f"Received file upload: {file.filename}")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file provided.")
    
    try:
        document = await ingestion_service.process_document(
            content=content,
            filename=file.filename,
            mime_type=file.content_type or "application/octet-stream"
        )
        logger.info(f"Successfully processed document: {document.title}")
        
        # Convert Document object to dict for Pydantic serialization
        return {
            "id": document.id,
            "category_id": document.category_id,
            "title": document.title,
            "document_source": document.document_source,
            "publication_date": document.publication_date,
            "file_hash": document.file_hash,
            "file_name": document.file_name,
            "created_at": document.created_at
        }

    except ValueError as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower():
            logger.warning(f"Duplicate document upload attempt: {file.filename}")
            # If a duplicate is uploaded, fetch and return the existing document's data
            file_hash = calculate_file_hash(content)
            existing_document = await ingestion_service.get_document_by_hash(file_hash)
            if existing_document:
                return {
                    "id": existing_document.id,
                    "category_id": existing_document.category_id,
                    "title": existing_document.title,
                    "document_source": existing_document.document_source,
                    "publication_date": existing_document.publication_date,
                    "file_hash": existing_document.file_hash,
                    "file_name": existing_document.file_name,
                    "created_at": existing_document.created_at
                }
            raise HTTPException(status_code=409, detail="This document already exists.")
        
        elif "unsupported file type" in error_msg.lower():
            logger.warning(f"Unsupported file type for: {file.filename}")
            raise HTTPException(status_code=415, detail="Unsupported file type. Please upload a PDF or TXT file.")
        
        else:
            logger.error(f"ValueError during processing: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

    except Exception as e:
        logger.error(f"An unexpected error occurred during file upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred during processing.")

@app.get("/documents", response_model=list[DocumentModel])
async def list_documents(
    category_id: int = None,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Lists all documents, with an option to filter by service category ID."""
    try:
        documents = await ingestion_service.list_documents(category_id)
        return documents
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve documents.")

@app.get("/service-categories", response_model=list[ServiceCategoryModel])
async def list_service_categories(
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Lists all available service categories for documents."""
    try:
        categories = await ingestion_service.list_service_categories()
        return categories
    except Exception as e:
        logger.error(f"Error listing categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve service categories.")

@app.get("/documents/{document_id}", response_model=DocumentModel)
async def get_document(
    document_id: int,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Retrieves a specific document by its ID."""
    try:
        document = await ingestion_service.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found.")
        return document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve document.")

@app.delete("/documents/{document_id}", status_code=200)
async def delete_document(
    document_id: int,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Deletes a document and its associated data by its ID."""
    try:
        success = await ingestion_service.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"message": "Document deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete document.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
