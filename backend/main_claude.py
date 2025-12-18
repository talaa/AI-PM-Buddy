import shutil
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from datetime import datetime
import os
from typing import Optional, List
from schemas import UpdateAgent, FolderCreationRequest, ChatRequest
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.chat_models import ChatOllama
from pydantic import BaseModel
from typing import Dict, Any
from database import supabase
from agent_service import (
    create_langchain_agent,
    convert_history_to_messages,
    get_agent_config_by_id,
    active_chains,
    send_message_to_agent,
    get_messages_for_agent,
    process_agent_collaboration
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
        "version": "2.1",
        "features": ["RAG-ready", "Tool calling", "Memory management", "A2A Communication"]
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
        # Fetch Agent Details from Supabase
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
        
        # Invoke the chain with correct variable names
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

# ============================================================================
# A2A (Agent-to-Agent) Communication Endpoints
# ============================================================================

class A2AMessageRequest(BaseModel):
    from_agent_id: str
    to_agent_id: str
    message: str
    context: Optional[Dict[str, Any]] = None

@app.post("/api/a2a/send")
async def send_a2a_message(request: A2AMessageRequest):
    """Send a message from one agent to another"""
    try:
        result = send_message_to_agent(
            from_agent_id=request.from_agent_id,
            to_agent_id=request.to_agent_id,
            message=request.message,
            context=request.context
        )
        return result
    except Exception as e:
        logger.error(f"Error sending A2A message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@app.get("/api/a2a/messages/{agent_id}")
async def get_agent_messages(agent_id: str):
    """Get all pending messages for an agent"""
    try:
        messages = get_messages_for_agent(agent_id)
        return {
            "agent_id": agent_id,
            "message_count": len(messages),
            "messages": messages
        }
    except Exception as e:
        logger.error(f"Error retrieving messages for {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve messages: {str(e)}")

class CollaborativeRequest(BaseModel):
    agent_id: str
    message: str
    history: Optional[List[Dict[str, str]]] = []
    collaborating_agents: Optional[List[str]] = None

@app.post("/api/a2a/collaborate")
async def collaborate(request: CollaborativeRequest):
    """Process a request with agent collaboration enabled"""
    try:
        result = process_agent_collaboration(
            agent_id=request.agent_id,
            message=request.message,
            history=request.history or [],
            other_agent_ids=request.collaborating_agents
        )
        return result
    except Exception as e:
        logger.error(f"Error in collaboration: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Collaboration failed: {str(e)}")

# ============================================================================
# Existing Endpoints (unchanged)
# ============================================================================

@app.patch("/api/agents/{agent_id}")
async def update_agent_endpoint(agent_id: str, update: UpdateAgent):
    """Update agent details"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    data = update.dict(exclude_unset=True)
    data["modified_at"] = datetime.utcnow().isoformat()
    try:
        response = supabase.table("agents").update(data).eq("id", agent_id).execute()
    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to update agent")
    return {"message": "Agent updated", "data": response.data}

@app.post("/api/folders/create")
async def create_folders_endpoint(request: FolderCreationRequest):
    """Create standard project subfolders locally"""
    base_path = request.path
    
    if not base_path:
        raise HTTPException(status_code=400, detail="Path is required")

    subfolders = ["Contracts", "Financials", "Technical Specs", "Correspondance", "Safety & Compliance"]
    
    results = []
    errors = []

    try:
        if not os.path.exists(base_path):
            os.makedirs(base_path, exist_ok=True)
            results.append(f"Created base folder: {base_path}")

        for folder in subfolders:
            folder_path = os.path.join(base_path, folder)
            try:
                os.makedirs(folder_path, exist_ok=True)
                results.append(f"Created: {folder}")
            except Exception as e:
                errors.append(f"Failed to create {folder}: {str(e)}")
                logger.error(f"Error creating folder {folder_path}: {e}")

        if errors:
            return {"status": "partial_success", "created": results, "errors": errors}
        
        return {"status": "success", "created": results}

    except Exception as e:
        logger.error(f"Error in folder creation: {e}")
        raise HTTPException(status_code=500, detail=f"System error: {str(e)}")

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    user_id: str = Form(...),
    category: str = Form(...),
    status: str = Form(...),
    tags: str = Form(None)
):
    """Handle document upload"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        response = supabase.table("projects").select("sharepoint_folder_path").eq("id", project_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        base_path = response.data.get("sharepoint_folder_path")
        if not base_path:
            raise HTTPException(status_code=400, detail="Project has no configured local folder path")

        folder_name = category
        target_dir = os.path.join(base_path, folder_name)
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        file_path = os.path.join(target_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size = os.path.getsize(file_path)
        tag_list = [t.strip() for t in tags.split(",")] if tags else []

        doc_entry = {
            "project_id": project_id,
            "user_id": user_id,
            "filename": file.filename,
            "file_path": file_path,
            "category": category,
            "status": status,
            "tags": tag_list,
            "file_size": file_size,
            "content_type": file.content_type
        }

        db_response = supabase.table("project_documents").insert(doc_entry).execute()

        return {
            "message": "File uploaded and logged successfully", 
            "data": db_response.data[0] if db_response.data else {},
            "saved_path": file_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        response = supabase.table("project_documents").select("*").eq("id", document_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = response.data
        file_path = doc.get("file_path")

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted local file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete local file {file_path}: {e}")

        supabase.table("project_documents").delete().eq("id", document_id).execute()
        
        return {"status": "success", "message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    from pydantic import BaseModel
    from typing import Dict, Any
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")