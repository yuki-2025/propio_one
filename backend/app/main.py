"""
FastAPI Backend Service for LangChain Agent
Using the modern Lifespan pattern for resource management
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import mlflow

from .config import settings
from .models import HealthResponse
from .routers import chat_router, set_agent
from .services import create_simple_agent
from .routers.websocket import websocket_endpoint

# ============ Logging Configuration ============
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============ Lifespan Context Manager ============
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Modern Lifespan pattern for FastAPI.
    - Code before `yield` runs on startup
    - Code after `yield` runs on shutdown
    """
    logger.info("🚀 Starting up LangChain Agent Service...")
    
    try:
        # Initialize MLflow
        logger.debug("Initializing MLflow...")
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
        mlflow.openai.autolog()
        mlflow.langchain.autolog()  # Auto-trace LangChain/LangGraph tool calls
        logger.info(f"✅ MLflow initialized: {settings.MLFLOW_TRACKING_URI}")
        
        # Create the agent
        logger.debug("Creating agent...")
        agent, checkpointer = create_simple_agent()
        logger.debug("Agent created successfully.")
        
        # Store in app state
        app.state.agent = agent
        app.state.checkpointer = checkpointer
        
        # Set agent reference in chat router
        set_agent(agent)
        
        logger.info("✅ LangChain Agent initialized successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent: {e}", exc_info=True)
        raise
    
    yield  # Application is running
    
    # Cleanup on shutdown
    logger.info("🛑 Shutting down LangChain Agent Service...")
    app.state.agent = None
    app.state.checkpointer = None
    logger.info("✅ Cleanup complete!")


# ============ FastAPI App ============
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Thread-ID"],  # Allow JS to read this header
)

# Include routers
app.include_router(chat_router)


# ============ Request Logging Middleware ============
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"➡️  Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.debug(f"⬅️  Response: {request.url.path} - Status: {response.status_code}")
    return response


# ============ Root Endpoints ============
@app.get("/")
async def root():
    """Root endpoint to check API status."""
    return {
        "status": "running",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        agent_initialized=app.state.agent is not None
    )


# ============ WebSocket Route ============
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice communication.

    This endpoint connects the frontend to OpenAI Realtime API,
    acting as a bidirectional proxy for audio and event streaming.

    Usage from frontend:
        const ws = new WebSocket('ws://localhost:8000/ws')

        // Send audio
        ws.send(JSON.stringify({
            type: 'audio',
            audio: 'base64_encoded_pcm16_audio'
        }))

        // Receive events
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            console.log('Received:', data.type)
        }
    """
    logger.info("WebSocket connection initiated")
    await websocket_endpoint(websocket)


# ============ Run Server ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
