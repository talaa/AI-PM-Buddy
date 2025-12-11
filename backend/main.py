import logging
from fastapi import FastAPI, HTTPException
from datetime import datetime
from schemas import UpdateAgent
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.chat_models import ChatOllama

from schemas import ChatRequest
from database import supabase
from agent_service import (
    create_langchain_agent,
    convert_history_to_messages,
    get_agent_config_by_id,
    active_chains
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS Configuration
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:5177",
    "http://localhost:5178",
    "http://localhost:5179",
    "http://localhost:5180",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Verify connections on startup"""
    logger.info("🚀 Starting AI PM Buddy Backend with LangChain + Ollama")
    
    try:
        test_llm = ChatOllama(model="qwen3:latest")
        test_llm.invoke("test")
        logger.info("✅ Ollama connection successful")
    except Exception as e:
        logger.error(f"⚠️ Ollama connection failed: {str(e)}")
        logger.error("Please ensure Ollama is running: ollama serve")
    
    if supabase:
        logger.info("✅ Supabase configured")
    else:
        logger.warning("⚠️ Supabase not configured")

@app.get("/")
async def root():
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
        test_llm = ChatOllama(model="qwen3:latest")
        test_llm.invoke("test")
        ollama_status = True
    except:
        pass
    
    return {
        "ollama": "connected" if ollama_status else "disconnected",
        "supabase": "configured" if supabase else "not configured",
        "langchain": "enabled"
    }

@app.post("/api/chat")
async def chat_with_agent(request: ChatRequest):
    """Main chat endpoint using LangChain"""
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        # Fetch Agent Details from Supabase (Delegated to service)
        agent_config = get_agent_config_by_id(request.agent_id)
        
        if not agent_config:
            logger.error(f"Agent with ID {request.agent_id} could not be found.")
            raise HTTPException(status_code=404, detail="Agent not found. Is the backend server running?")
        
        # Create or get cached chain
        cache_key = f"{request.agent_id}_{agent_config.model}"
        if cache_key not in active_chains:
            logger.info(f"Creating new LangChain agent for: {cache_key}")
            active_chains[cache_key] = create_langchain_agent(agent_config)
        
        chain = active_chains[cache_key]
        
        # Convert history to LangChain messages
        history_messages = convert_history_to_messages(request.history)
        
        # Invoke the chain
        logger.info(f"Invoking chain with model: {agent_config.model}")
        response = chain.invoke({
            "input": request.message,
            "history": history_messages
        })
        
        return {
            "response": response,
            "agent_name": agent_config.name,
            "model_used": agent_config.model,
            "session_id": request.session_id,
            "langchain_enabled": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}", exc_info=True)
        
        # Better error messages for common issues
        if "model" in str(e).lower() and "not found" in str(e).lower():
            model_name = agent_config.model if 'agent_config' in locals() else 'qwen3:latest'
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_name}' not found. Run: ollama pull {model_name}"
            )
        elif "connect" in str(e).lower() or "connection" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to Ollama. Please ensure it's running: ollama serve"
            )
        
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.delete("/api/chat/cache/{agent_id}")
async def clear_agent_cache(agent_id: str):
    """Clear cached chain for an agent (useful when agent config changes)"""
    cleared = []
    for key in list(active_chains.keys()):
        if key.startswith(agent_id):
            del active_chains[key]
            cleared.append(key)
    
    return {
        "message": f"Cleared {len(cleared)} cached chains",
        "cleared_keys": cleared
    }

@app.patch("/api/agents/{agent_id}")
async def update_agent_endpoint(agent_id: str, update: UpdateAgent):
    """Update agent details"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    # Prepare update data
    data = update.dict(exclude_unset=True)
    data["modified_at"] = datetime.utcnow().isoformat()
    try:
        response = supabase.table("agents").update(data).eq("id", agent_id).execute()
    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to update agent")
    return {"message": "Agent updated", "data": response.data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")