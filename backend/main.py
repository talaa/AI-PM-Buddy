"""
AI PM Buddy Backend - FastAPI Application Entry Point

This file serves as the minimal entry point for the FastAPI application.
Business logic is organized in routers under api/routers/.
"""
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_ollama import ChatOllama

from config import (
    DEFAULT_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_BASE_URL,
    CORS_ORIGINS,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
)
from database import supabase

# Import routers
from api.routers import chat, collaboration, sessions, agents, documents, projects

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize FastAPI app
app = FastAPI(
    title="AI PM Buddy Backend",
    description="FastAPI backend for AI-powered project management with LangChain + Ollama",
    version="2.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

# Register routers
app.include_router(chat.router)
app.include_router(collaboration.router)
app.include_router(sessions.router)
app.include_router(agents.router)
app.include_router(documents.router)
app.include_router(projects.router)


@app.on_event("startup")
async def startup_event():
    """Verify connections on startup"""
    logger.info("🚀 Starting AI PM Buddy Backend with LangChain + Ollama")
    
    try:
        test_llm = ChatOllama(
            model=DEFAULT_MODEL, 
            base_url=OLLAMA_BASE_URL,
            timeout=OLLAMA_TIMEOUT
        )
        # Use a more direct check or just a very short prompt
        await test_llm.ainvoke("hi")
        logger.info("✅ Ollama connection successful")
    except Exception as e:
        logger.error(f"⚠️ Ollama connection failed: {str(e)}")
        logger.error(f"Host: {OLLAMA_BASE_URL}, Model: {DEFAULT_MODEL}")
        logger.error("Please ensure Ollama is running: ollama serve")
    
    if supabase:
        logger.info("✅ Supabase configured")
    else:
        logger.warning("⚠️ Supabase not configured")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "ok", 
        "message": "AI PM Buddy Backend with LangChain + Ollama",
        "version": "2.0",
        "features": ["RAG-ready", "Tool calling", "Memory management", "Complex chains"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    ollama_status = False
    try:
        test_llm = ChatOllama(
            model=DEFAULT_MODEL, 
            base_url=OLLAMA_BASE_URL,
            timeout=OLLAMA_TIMEOUT
        )
        await test_llm.ainvoke("hi")
        ollama_status = True
    except Exception:
        pass
    
    return {
        "ollama": "connected" if ollama_status else "disconnected",
        "supabase": "configured" if supabase else "not configured",
        "langchain": "enabled"
    }


# Application entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True, 
        log_level="info",
        access_log=True
    )