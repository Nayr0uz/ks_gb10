
import logging
from typing import List, Optional
import asyncio
from datetime import datetime
import json
import sys
import tempfile
import os
import io

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from shared.models import Document
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DocumentModel(BaseModel):
    id: Optional[str] = None
    category_id: int
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
        from_attributes = True

class DocumentMetadata(BaseModel):
    category_id: int
    title: str
    document_source: Optional[str] = None
    publication_date: Optional[datetime] = None
    file_hash: str
    file_name: str
from database import DatabaseManager
from utils import calculate_file_hash, sanitize_title_for_table, extract_category_id, RedisManager, validate_file_type

sys.path.append('/app/shared')
logger = logging.getLogger(__name__)

def get_openai_url(env_var, default_port):
    # Get URL, strip any trailing slashes or existing /v1
    url = os.getenv(env_var, f"http://host.docker.internal:{default_port}").rstrip("/")
    if url.endswith("/v1"):
        return url
    return f"{url}/v1"

class IngestionService:
    def __init__(self, db_manager: "DatabaseManager", redis_manager: "RedisManager"):
        self.db = db_manager
        self.redis = redis_manager


        # --- 1. INITIALIZE EMBEDDINGS ---
        self.embeddings = OpenAIEmbeddings(
            model=os.getenv("OLLAMA_EMBEDDING_MODEL", "Qwen3-Embedding-4B-Q8_0"),
            # Uses 8090 as per your .env
            base_url=get_openai_url("OLLAMA_BASE_URL", 8090),
            api_key="sk-no-key-required"
        )
        logger.info(f"Initialized Embeddings with base_url: {self.embeddings.openai_api_base}")

        # --- 2. INITIALIZE LLM ---
        backend_type = os.getenv("LLM_BACKEND_TYPE", "openai").lower()
        
        if backend_type == "openai":
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=os.getenv("INGESTION_MODEL_NAME", "gpt-oss-120b"),
                temperature=float(os.getenv("INGESTION_MODEL_TEMPERATURE", "0")),
                base_url=get_openai_url("LLM_OPENAI_BASE_URL", 8089),
                api_key="sk-no-key-required"
            )
            logger.info(f"Initialized ChatOpenAI at {self.llm.openai_api_base}")
  
        else:
            # Only if you switch to a native Ollama instance
            # ChatOllama appends /api/chat, so we strip /v1 if present
            ollama_base = os.getenv("OLLAMA_BASE_URL", "http://172.24.77.77:8090")
            self.llm = ChatOllama(
                model=os.getenv("INGESTION_MODEL_NAME", "gpt-oss-120b"),
                temperature=float(os.getenv("INGESTION_MODEL_TEMPERATURE", "0")),
                base_url=ollama_base.replace("/v1", "").rstrip("/")
            )
            logger.info(f"Initialized ChatOllama at {self.llm.base_url}")

        # --- 3. INITIALIZE TEXT SPLITTER ---
        # Tune chunking to keep related numeric facts (e.g., fees) with their headings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=250,
            length_function=len,
        )

        # Updated metadata extraction prompt for ENBD
        self.metadata_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert AI assistant for the Emirates NBD bank. Your sole function is to analyze the provided document text and metadata to create a complete, structured JSON record.

Your response MUST be a single, clean JSON object with the following keys: category_id, title, document_source, publication_date, file_hash, file_name.

CRITICAL CATEGORIZATION RULES - READ CAREFULLY:

Analyze the document FIRST and THEN select the CORRECT category. DO NOT default to any category.

Category ID Mapping (CHOOSE EXACTLY ONE):
- 1 = Accounts & Savings: Document is about bank accounts, savings accounts, current accounts, deposit accounts. Keywords: account, savings, current, deposit
- 2 = Loans: Document is about loans, borrowing, lending, personal loans, home loans, car loans. Keywords: loan, credit, borrow, lending, mortgage
- 3 = Cards: Document is about credit cards, debit cards, payment cards. Keywords: card, credit, debit, payment
- 4 = Investments: Document is about investments, funds, stocks, bonds, mutual funds. Keywords: investment, fund, stock, bond, portfolio
- 5 = Business & Corporate Banking: Document is about business banking, corporate services. Keywords: business, corporate, commercial
- 6 = Insurance: Document is about insurance products. Keywords: insurance, protection, cover
- 7 = Digital & E-Banking: Document is about digital/mobile/online banking. Keywords: digital, online, mobile, app
- 8 = Payroll Services: Document is about payroll or salary. Keywords: payroll, salary, employee
- 9 = General Information: Document doesn't fit above categories.

CATEGORIZATION STEPS:
1. Read the document title and first 200 words carefully
2. Identify the MAIN topic
3. Match to the BEST fitting category
4. If document mentions "Accounts", it's category 1, NOT 4 (Investments)
5. If document mentions "Loans", it's category 2, NOT 4 (Investments)
6. Only use category 9 if truly no match

INSTRUCTIONS:
1. Classify the document's main topic using the rules above
2. Extract the title (use filename as fallback)
3. Extract document_source (Marketing Department, Annual Report, etc.) - use null if not found
4. Extract publication_date in YYYY-MM-DD format - use null if not found
5. Copy file_hash and file_name directly from metadata

Respond with ONLY valid JSON, no other text."""),
            ("human", "Text Content: {text}\n\nFile Hash: {file_hash}\nFile Name: {file_name}")
        ])

    async def process_document(self, content: bytes, filename: str, mime_type: str) -> "DocumentModel":
        """Process an uploaded ENBD document file"""
        try:
            if not validate_file_type(mime_type):
                raise ValueError(f"Unsupported file type: {mime_type}")

            file_hash = calculate_file_hash(content)

            if await self.db.check_document_exists(file_hash):
                raise ValueError("Document already exists in the system")

            text_content = await self._extract_text(content, filename, mime_type)
            metadata = await self._extract_metadata(text_content, file_hash, filename)

            # Insert document metadata into the main 'documents' table
            document_id = await self.db.insert_document({
                'category_id': metadata.category_id,
                'title': metadata.title,
                'document_source': metadata.document_source,
                'publication_date': metadata.publication_date,
                'file_hash': metadata.file_hash,
                'file_name': metadata.file_name
            })

            document = DocumentModel(
                id=document_id,
                category_id=metadata.category_id,
                title=metadata.title,
                document_source=metadata.document_source,
                publication_date=metadata.publication_date.isoformat() if metadata.publication_date else None,
                file_hash=metadata.file_hash,
                file_name=metadata.file_name,
                created_at=datetime.utcnow().isoformat()
            )

            # Split text and create vector store entries in the 'document_chunks' table
            try:
                # Split text into chunks
                split_docs = self.text_splitter.create_documents([text_content])
                await self._store_document_chunks(split_docs, document_id)
                logger.info(f"Successfully created vector embeddings for: {metadata.title}")
            except Exception as vector_error:
                # If embedding generation fails (e.g., Ollama unavailable), still store chunks
                # with NULL embeddings so text-based fallback search can work.
                logger.error(f"Failed to create vector embeddings for {metadata.title}: {vector_error}")
                logger.warning(f"Document {metadata.title} was saved, but vector embedding failed. Storing text chunks without embeddings.")
                try:
                    # Ensure split_docs exists; if not, create it now
                    if 'split_docs' not in locals() or not split_docs:
                        split_docs = self.text_splitter.create_documents([text_content])

                    chunk_data_to_insert = []
                    for doc in split_docs:
                        chunk_data_to_insert.append({
                            "document_id": document_id,
                            "content": doc.page_content,
                            "embedding": None,
                            "metadata": doc.metadata
                        })

                    await self.db.bulk_insert_chunks(chunk_data_to_insert)
                    logger.info(f"Stored {len(chunk_data_to_insert)} text-only chunks for document_id: {document_id}")
                except Exception as store_err:
                    logger.error(f"Failed to store text-only chunks for {metadata.title}: {store_err}")

            try:
                await self._cache_document(document)
            except Exception as cache_error:
                logger.warning(f"Failed to cache document data for {metadata.title}: {cache_error}")

            logger.info(f"Successfully processed document: {metadata.title}")
            return document

        except Exception as e:
            logger.error(f"Error processing document: {e}")
            raise

    async def _extract_text(self, content: bytes, filename: str, mime_type: str) -> str:
        """Extracts text from file content, supporting PDF and plain text, with normalization for numeric facts."""
        try:
            text = ""
            if mime_type == "application/pdf":
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                    temp_file.write(content)
                    temp_file_path = temp_file.name
                
                try:
                    loader = PyPDFLoader(temp_file_path)
                    documents = loader.load()
                    text = "\n".join([doc.page_content for doc in documents])
                finally:
                    os.unlink(temp_file_path) # Ensure cleanup
                    
            elif mime_type.startswith("text/"):
                text = content.decode('utf-8', errors='replace')
            else:
                raise ValueError(f"Unsupported MIME type for text extraction: {mime_type}")
            
            # Clean text to remove characters that can cause database issues
            cleaned_text = text.replace('\x00', '')

            # Normalize text to keep numbers close to their labels (e.g., "opening fee: EGP 1500")
            cleaned_text = self._normalize_text(cleaned_text)

            logger.info(f"Extracted {len(cleaned_text)} characters from {filename}")
            return cleaned_text
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {e}")
            raise ValueError(f"Failed to extract text from file: {e}")

    async def _extract_metadata(self, text: str, file_hash: str, filename: str) -> "DocumentMetadata":
        """Extract metadata using the LLM, with a robust fallback."""
        llm_response_str = ""
        try:
            chain = self.metadata_prompt | self.llm | StrOutputParser()
            text_for_llm = text[:8000] # Use the first 8000 characters for efficiency
            
            # Add timeout of 10 seconds to prevent long-running LLM calls
            try:
                llm_response_str = await asyncio.wait_for(
                    chain.ainvoke({
                        "text": text_for_llm,
                        "file_hash": file_hash,
                        "file_name": filename
                    }),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning("LLM metadata extraction timed out after 10 seconds. Using fallback.")
                raise ValueError("LLM call timed out")

            # Clean and parse the JSON response
            clean_response = llm_response_str.strip().replace("```json", "").replace("```", "")
            metadata_dict = json.loads(clean_response)

            # Validate required fields
            required_fields = ['category_id', 'title', 'file_hash', 'file_name']
            if not all(field in metadata_dict for field in required_fields):
                raise ValueError("LLM response missing required fields.")

            metadata = DocumentMetadata(
                category_id=metadata_dict['category_id'],
                title=metadata_dict['title'],
                document_source=metadata_dict.get('document_source'),
                publication_date=datetime.strptime(metadata_dict['publication_date'], '%Y-%m-%d').date() if metadata_dict.get('publication_date') else None,
                file_hash=metadata_dict['file_hash'],
                file_name=metadata_dict['file_name']
            )
            logger.info(f"Successfully extracted metadata for: {metadata.title}")
            return metadata

        except Exception as e:
            logger.error(f"Could not extract metadata via LLM: {e}. Raw response: '{llm_response_str}'")
            logger.warning("Using fallback metadata generation.")
            
            # Fallback to basic metadata
            return DocumentMetadata(
                category_id=9,  # Default to 'General Information' instead of Investments
                title=os.path.splitext(filename)[0].replace('_', ' ').title(),
                document_source=None,
                publication_date=None,
                file_hash=file_hash,
                file_name=filename
            )

    async def _store_document_chunks(self, split_docs: List[Document], document_id: int):
        """Generates embeddings and stores document chunks in the database."""
        try:
            texts = [doc.page_content for doc in split_docs]
            if not texts:
                logger.warning(f"No text content found to embed for document_id: {document_id}")
                return

            embeddings_list = await self.embeddings.aembed_documents(texts)
            
            chunk_data_to_insert = []
            for doc, embedding in zip(split_docs, embeddings_list):
                chunk_data_to_insert.append({
                    "document_id": document_id,
                    "content": doc.page_content,
                    "embedding": embedding,
                    "metadata": doc.metadata
                })

            # Use the database manager to perform a bulk insert for efficiency
            await self.db.bulk_insert_chunks(chunk_data_to_insert)
            
            logger.info(f"Stored {len(split_docs)} chunks for document_id: {document_id}")

        except Exception as e:
            logger.error(f"Error creating vector embeddings for document_id {document_id}: {e}")
            raise
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text to preserve numeric facts near their labels.
        - Join soft line breaks around colons and currency.
        - Normalize bullet lines continuation.
        - Normalize currency spacing (EGP/LE/جنيه)."""
        import re
        # Fix hyphenated line breaks: word-\nword -> wordword
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        # Join linebreaks after colon and before numbers/currency
        text = re.sub(r":\s*\n\s+", ": ", text)
        text = re.sub(r"\b(EGP|LE|جنيه)\s*\n\s*(\d)", r" \1 \2", text)
        # Bullet continuation: merge lines that are clearly continuation of a bullet
        lines = text.splitlines()
        out = []
        for i, line in enumerate(lines):
            if out and out[-1].lstrip().startswith(('-', '•', '·')) and line and not line.lstrip().startswith(('-', '•', '·')):
                out[-1] = out[-1].rstrip() + " " + line.strip()
            else:
                out.append(line)
        text = "\n".join(out)
        # Normalize currency spacing
        text = re.sub(r"\b(EGP|LE)\s*(\d)", r"\1 \2", text)
        text = re.sub(r"\s+جنيه\s*", " جنيه ", text)
        # Collapse 3+ newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    async def _cache_document(self, document: "DocumentModel"):
        """Cache document data in Redis for fast access."""
        try:
            cache_key = f"document:{document.id}"
            document_data = document.dict()
            # No need to convert - created_at and publication_date are already strings
            
            self.redis.set_cache(cache_key, document_data, expire_seconds=3600)
            logger.info(f"Cached data for document_id: {document.id}")
        except Exception as e:
            logger.warning(f"Failed to cache document data: {e}")

    async def list_documents(self, category_id: Optional[int] = None) -> List[DocumentModel]:
        """Lists all documents, optionally filtered by category ID."""
        try:
            if category_id:
                documents = await self.db.get_documents_by_category(category_id)
            else:
                documents = await self.db.execute_query("""
                    MATCH (d:Document)
                    RETURN d.id as id, d.category_id as category_id, d.title as title, 
                           d.document_source as document_source, d.publication_date as publication_date,
                           d.file_hash as file_hash, d.file_name as file_name, d.created_at as created_at
                    ORDER BY d.title
                """)
            
            # Convert Neo4j DateTime objects to ISO format strings
            result = []
            for doc in documents:
                doc_copy = dict(doc)
                # Convert created_at if it's a Neo4j DateTime object
                if hasattr(doc_copy.get('created_at'), 'to_native'):
                    doc_copy['created_at'] = doc_copy['created_at'].to_native().isoformat()
                # Convert publication_date if it's a Neo4j DateTime object
                if hasattr(doc_copy.get('publication_date'), 'to_native'):
                    doc_copy['publication_date'] = doc_copy['publication_date'].to_native().isoformat()
                result.append(DocumentModel(**doc_copy))
            
            return result
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            raise

    async def list_service_categories(self) -> List[ServiceCategoryModel]:
        """Lists all available service categories."""
        try:
            categories = await self.db.get_service_categories()
            # Convert Neo4j DateTime objects to Python datetime
            result = []
            for cat in categories:
                cat_copy = dict(cat)
                # Convert created_at if it's a Neo4j DateTime object
                if hasattr(cat_copy.get('created_at'), 'to_native'):
                    cat_copy['created_at'] = cat_copy['created_at'].to_native()
                result.append(ServiceCategoryModel(**cat_copy))
            return result
        except Exception as e:
            logger.error(f"Error listing service categories: {e}")
            raise

    async def get_document_by_hash(self, file_hash: str) -> Optional[DocumentModel]:
        """Gets a document by its file hash."""
        try:
            document = await self.db.fetch_one("""
                MATCH (d:Document {file_hash: $file_hash})
                RETURN d.id as id, d.category_id as category_id, d.title as title, 
                       d.document_source as document_source, d.publication_date as publication_date,
                       d.file_hash as file_hash, d.file_name as file_name, d.created_at as created_at
            """, {"file_hash": file_hash})
            
            if not document:
                return None
            
            # Convert Neo4j DateTime objects to strings
            doc_copy = dict(document)
            if hasattr(doc_copy.get('created_at'), 'to_native'):
                doc_copy['created_at'] = doc_copy['created_at'].to_native().isoformat()
            if hasattr(doc_copy.get('publication_date'), 'to_native'):
                doc_copy['publication_date'] = doc_copy['publication_date'].to_native().isoformat()
            
            return DocumentModel(**doc_copy)
        except Exception as e:
            logger.error(f"Error getting document by hash: {e}")
            raise

    async def get_document_by_id(self, document_id: str) -> Optional[DocumentModel]:
        """Gets a document by its ID."""
        try:
            document = await self.db.fetch_one("""
                MATCH (d:Document {id: $document_id})
                RETURN d.id as id, d.category_id as category_id, d.title as title, 
                       d.document_source as document_source, d.publication_date as publication_date,
                       d.file_hash as file_hash, d.file_name as file_name, d.created_at as created_at
            """, {"document_id": document_id})
            
            if not document:
                return None
            
            # Convert Neo4j DateTime objects to strings
            doc_copy = dict(document)
            if hasattr(doc_copy.get('created_at'), 'to_native'):
                doc_copy['created_at'] = doc_copy['created_at'].to_native().isoformat()
            if hasattr(doc_copy.get('publication_date'), 'to_native'):
                doc_copy['publication_date'] = doc_copy['publication_date'].to_native().isoformat()
            
            return DocumentModel(**doc_copy)
        except Exception as e:
            logger.error(f"Error getting document by ID: {e}")
            raise

    async def delete_document(self, document_id: str) -> bool:
        """Deletes a document from the database. Cascade delete will handle chunks and sessions."""
        try:
            # Delete the document node - relationships will be handled by Neo4j
            await self.db.execute_write("""
                MATCH (d:Document {id: $document_id})
                DETACH DELETE d
            """, {"document_id": document_id})
            
            # Remove from cache
            cache_key = f"document:{document_id}"
            self.redis.delete_cache(cache_key)
            
            logger.info(f"Successfully deleted document_id: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            raise
