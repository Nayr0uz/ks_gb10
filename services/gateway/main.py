from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response as FastAPIResponse
import uvicorn
import httpx
import os
import sys
import json
import logging
from contextlib import asynccontextmanager
from shared.utils import setup_logging, get_redis

# Add shared modules to path
sys.path.append('/app/shared')

# Import the correct, refactored models
from shared.models import (
    User,
    ServiceCategory,
    Document,
    DocumentChunk,
    ChatSession,
    ChatMessage,
    Presentation,
)

# Setup logging
setup_logging("api-gateway")
logger = logging.getLogger(__name__)


# --- Simple Rate Limiter ---
class RateLimiter:
    def __init__(self, redis_manager, max_requests: int = 100, window_seconds: int = 60):
        self.redis = redis_manager
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def is_allowed(self, client_id: str) -> bool:
        try:
            if not self.redis.client:
                return True
            key = f"rate_limit:{client_id}"
            current = self.redis.client.get(key)
            if current is None:
                self.redis.client.setex(key, self.window_seconds, 1)
                return True
            if int(current) >= self.max_requests:
                return False
            self.redis.client.incr(key)
            return True
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ENBD API Gateway...")
    redis_manager = get_redis()
    app.state.redis = redis_manager
    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(600.0))
    app.state.rate_limiter = RateLimiter(app.state.redis)
    yield
    logger.info("Shutting down ENBD API Gateway...")
    await app.state.http_client.aclose()
    redis_manager.disconnect()


app = FastAPI(
    title="ENBD API Gateway",
    description="Main entry point for the ENBD Document Chat microservices.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://ingestion-service:8000")
CHAT_SERVICE_URL = os.getenv("CHAT_SERVICE_URL", "http://chat-service:8001")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8002")
PRESENTATION_SERVICE_URL = os.getenv("PRESENTATION_SERVICE_URL", "http://presentation-service:8003")


# --- Rate limit dependency ---
async def check_rate_limit(request: Request):
    if not await request.app.state.rate_limiter.is_allowed(request.client.host):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")


# --- Forward requests to microservices ---
async def forward_request(request: Request, service_url: str, endpoint: str):
    client = request.app.state.http_client
    url = f"{service_url}{endpoint}"
    headers = {key: value for key, value in request.headers.items() if key.lower() not in ["host", "content-length"]}
    try:
        req = client.build_request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.query_params,
            content=await request.body(),
        )
        resp = await client.send(req)
        
        # Determine if we should attempt to parse as JSON
        # Most of our microservices return application/json
        content_type = resp.headers.get("content-type", "")
        is_json = "application/json" in content_type

        try:
            body = await resp.aread()
            if is_json:
                try:
                    return JSONResponse(content=json.loads(body), status_code=resp.status_code)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode JSON from {url} despite content-type. Returning raw.")
                    return Response(content=body, status_code=resp.status_code, media_type=content_type)
            else:
                return Response(content=body, status_code=resp.status_code, media_type=content_type)
        except Exception as e:
            logger.error(f"Error reading response from {url}: {e}")
            raise HTTPException(status_code=500, detail="Error reading service response.")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error forwarding to {url}: {e}")
        try:
            body = await e.response.aread()
            content_type = e.response.headers.get("content-type", "")
            if "application/json" in content_type:
                return JSONResponse(content=json.loads(body), status_code=e.response.status_code)
            else:
                return Response(content=body, status_code=e.response.status_code, media_type=content_type)
        except Exception:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service Error: {e.response.text}")

    except Exception as e:
        logger.error(f"Gateway error forwarding to {url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="API Gateway internal error.")



@app.get("/api/v1/presentation/{presentation_id}/download/ppt")
async def download_presentation_ppt_gateway(request: Request, presentation_id: str):
    """Proxy the PPT download from the presentation service and stream it back to the client.

    This ensures CORS headers come from the gateway and binary data is forwarded correctly.
    """
    client: httpx.AsyncClient = request.app.state.http_client
    url = f"{PRESENTATION_SERVICE_URL}/api/v1/presentation/{presentation_id}/download/ppt"
    try:
        resp = await client.get(url, headers={k: v for k, v in request.headers.items() if k.lower() != 'host'})
        # If presentation service returned an error, try to propagate JSON error
        if resp.status_code >= 400:
            try:
                return JSONResponse(content=resp.json(), status_code=resp.status_code)
            except Exception:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

        content_type = resp.headers.get('content-type', 'application/octet-stream')
        disp = resp.headers.get('content-disposition')

        return StreamingResponse(resp.aiter_bytes(), media_type=content_type, headers={k: v for k, v in resp.headers.items() if k.lower() in ['content-disposition']})
    except httpx.HTTPStatusError as e:
        logger.error(f"Error proxying PPT download: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch PPT from presentation service")


# =========================
# Health (local to gateway)
# =========================
@app.get("/health")
async def health():
    return {"status": "ok"}


# =========================
# Ingestion Service
# =========================
@app.post("/api/v1/documents", dependencies=[Depends(check_rate_limit)])
async def upload_document_gateway(request: Request):
    return await forward_request(request, INGESTION_SERVICE_URL, "/upload")


@app.get("/api/v1/documents", dependencies=[Depends(check_rate_limit)])
async def list_documents_gateway(request: Request):
    return await forward_request(request, INGESTION_SERVICE_URL, "/documents")


@app.get("/api/v1/documents/{document_id}", dependencies=[Depends(check_rate_limit)])
async def get_document_gateway(request: Request, document_id: int):
    return await forward_request(request, INGESTION_SERVICE_URL, f"/documents/{document_id}")


@app.delete("/api/v1/documents/{document_id}", dependencies=[Depends(check_rate_limit)])
async def delete_document_gateway(request: Request, document_id: int):
    return await forward_request(request, INGESTION_SERVICE_URL, f"/documents/{document_id}")


@app.get("/api/v1/service-categories", dependencies=[Depends(check_rate_limit)])
async def list_service_categories_gateway(request: Request):
    return await forward_request(request, INGESTION_SERVICE_URL, "/service-categories")


# =========================
# Chat Service
# =========================
@app.post("/api/v1/chat", dependencies=[Depends(check_rate_limit)])
async def chat_gateway(request: Request):
    return await forward_request(request, CHAT_SERVICE_URL, "/chat")


@app.post("/api/v1/sessions", dependencies=[Depends(check_rate_limit)])
async def create_session_gateway(request: Request):
    return await forward_request(request, CHAT_SERVICE_URL, "/sessions")


@app.get("/api/v1/sessions", dependencies=[Depends(check_rate_limit)])
async def get_user_sessions_gateway(request: Request):
    """Fetch all chat sessions for a user by user_id query parameter."""
    return await forward_request(request, CHAT_SERVICE_URL, "/sessions")


@app.get("/api/v1/sessions/{session_id}/history", dependencies=[Depends(check_rate_limit)])
async def get_chat_history_gateway(request: Request, session_id: str):
    return await forward_request(request, CHAT_SERVICE_URL, f"/sessions/{session_id}/history")


# =========================
# Auth Service
# =========================
@app.post("/api/v1/auth/signup")
async def signup_gateway(request: Request):
    return await forward_request(request, AUTH_SERVICE_URL, "/signup")


@app.post("/api/v1/auth/login")
async def login_gateway(request: Request):
    return await forward_request(request, AUTH_SERVICE_URL, "/login")


@app.get("/api/v1/auth/me", dependencies=[Depends(check_rate_limit)])
async def get_current_user_gateway(request: Request):
    return await forward_request(request, AUTH_SERVICE_URL, "/me")


# =========================
# Presentation Service
# =========================

# create / generate
@app.post("/api/v1/presentation/generate-presentation/", dependencies=[Depends(check_rate_limit)])
async def generate_presentation_gateway(request: Request):
    # forward to the exact path defined in presentation service
    return await forward_request(
        request,
        PRESENTATION_SERVICE_URL,
        "/api/v1/presentation/generate-presentation/",
    )


# get single presentation
@app.get("/api/v1/presentation/{presentation_id}", dependencies=[Depends(check_rate_limit)])
async def get_presentation_status_gateway(request: Request, presentation_id: str):
    # presentation service exposes /presentations/{id} as an alias
    return await forward_request(request, PRESENTATION_SERVICE_URL, f"/presentations/{presentation_id}")


# NEW: list presentations for the frontend
@app.get("/api/v1/presentation/presentations/", dependencies=[Depends(check_rate_limit)])
async def list_presentations_gateway(request: Request):
    # presentation service exposes /presentations
    return await forward_request(request, PRESENTATION_SERVICE_URL, "/presentations")


@app.get("/api/v1/presentation/health")
async def presentation_health_gateway(request: Request):
    return await forward_request(request, PRESENTATION_SERVICE_URL, "/health")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
