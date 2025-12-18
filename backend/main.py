import shutil
import logging
# Force reload

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from datetime import datetime
import os
from typing import Optional, List
from schemas import UpdateAgent, FolderCreationRequest
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.chat_models import ChatOllama

from schemas import ChatRequest
from database import supabase
from agent_service import (
    create_langchain_agent,
    convert_history_to_messages,
    get_agent_config_by_id,
    active_chains,
)
from a2a_service import create_team_graph
from schemas import ChatRequest, TeamChatRequest
from langchain_core.messages import HumanMessage, SystemMessage


# Configure logging
from pydantic import BaseModel
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Solution 2: A2A Architecture Components ---

# In-memory message queue (upgradeable to Redis)
# Structure: { to_agent_id: [ {from, message, timestamp, ...} ] }
a2a_message_buffer: Dict[str, List[Dict]] = {}

class A2ASendRequest(BaseModel):
    from_agent_id: str
    to_agent_id: str
    message: str
    context: Optional[Dict] = None

class CollaborationRequest(BaseModel):
    agent_id: str  # The "Leader" agent
    message: str
    collaborating_agents: List[str]
    history: List[Dict] = []
    document_ids: List[str] = [] # Added to support RAG context

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
        
        # Prepare System Message
        system_msg = SystemMessage(content=f"""You are {agent_config.name}. 
Description: {agent_config.description}
Instructions: {agent_config.instructions}
Relevant Knowledge: {agent_config.knowledge or ''}
""")
        
        # Construct input state
        # We need to prepend system message if it's not in history (usually it isn't)
        # And append the current user input
        messages = [system_msg] + history_messages + [HumanMessage(content=request.message)]
        
        # Invoke the graph
        logger.info(f"Invoking agent graph with model: {agent_config.model}")
        
        # Async invoke is preferred but synchronous 'invoke' works too on CompiledGraph
        result_state = await chain.ainvoke({"messages": messages})
        
        # Extract the final response (last message)
        final_message = result_state["messages"][-1]
        response_content = final_message.content
        
        return {
            "response": response_content,
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

@app.post("/api/a2a/chat")
async def team_chat(request: TeamChatRequest):
    """
    Agent-to-Agent Team Chat (Solution 2 Implementation)
    Routes to the new specific 'collaborate' logic but keeps endpoint for frontend compatibility.
    """
    # Simply delegate to the new architecture
    return await collaborate(request)

# --- Solution 2: New A2A Endpoints ---

@app.post("/api/a2a/send")
async def send_a2a_message(request: A2ASendRequest):
    """Send a message from one agent to another (Async)"""
    try:
        if request.to_agent_id not in a2a_message_buffer:
            a2a_message_buffer[request.to_agent_id] = []
            
        a2a_message_buffer[request.to_agent_id].append({
            "from_agent_id": request.from_agent_id,
            "message": request.message,
            "timestamp": datetime.now().isoformat(),
            "context": request.context or {}
        })
        logger.info(f"A2A Message Queued: {request.from_agent_id} -> {request.to_agent_id}")
        return {"status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/a2a/messages/{agent_id}")
async def get_a2a_messages(agent_id: str):
    """Retrieve pending messages for an agent"""
    messages = a2a_message_buffer.get(agent_id, [])
    # Clear buffer after retrieval (or use acknowledgement in future)
    a2a_message_buffer[agent_id] = []
    return {"messages": messages}

@app.post("/api/a2a/collaborate")
async def collaborate(request: TeamChatRequest): 
    # NOTE: Reusing TeamChatRequest for frontend compatibility, but implementing "Collaborative Processing" logic
    # Request: agent_ids (list), document_ids, message
    
    # --- 1. Session Management ---
    session_id = request.session_id
    
    # If no session_id, create a new session
    if not session_id:
        try:
            # Create new session
            # Try with title first
            try:
                sess_resp = supabase.table("chat_sessions").insert({
                    "project_id": request.project_id,
                    "title": f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}" 
                }).execute()
            except Exception as e:
                # Fallback: Maybe 'title' column is missing from schema cache or table
                logger.warning(f"Failed to insert with title, trying without. Error: {e}")
                sess_resp = supabase.table("chat_sessions").insert({
                    "project_id": request.project_id
                }).execute()

            if sess_resp.data:
                session_id = sess_resp.data[0]["id"]
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            # Debugging: Return this error to frontend
            return {
                "status": "error",
                "message": f"Database Error: {str(e)}. Tip: Go to Supabase Dashboard > Settings > API > 'Reload Schema Cache'."
            }

    # Save User Message
    if session_id:
        try:
            supabase.table("chat_messages").insert({
                "session_id": session_id,
                "sender_id": "user",
                "role": "user",
                "content": request.message
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save user message: {e}")

    # --- 2. Load History ---
    # Fetch recent messages for context
    history_context = []
    if session_id:
        try:
            # Get last 10 messages for context
            h_resp = supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=True).limit(10).execute()
            if h_resp.data:
                # Reverse to get chronological order
                msgs = h_resp.data[::-1]
                for m in msgs:
                    history_context.append(f"{m['role'].upper()}: {m['content']}")
        except Exception as e:
            logger.error(f"Failed to load history: {e}")

    # 1. Select a "Leader" agent (first one selected) and "Workers" (rest)
    if not request.agent_ids:
        raise HTTPException(status_code=400, detail="At least one agent must be selected")
        
    leader_id = request.agent_ids[0]
    worker_ids = request.agent_ids[1:]
    
    # 2. Setup Context (RAG)
    context_str = ""
    for doc_id in request.document_ids:
        resp = supabase.table("project_documents").select("file_path").eq("id", doc_id).single().execute()
        if resp.data and os.path.exists(resp.data.get("file_path")):
            try:
                with open(resp.data.get("file_path"), "r", encoding="utf-8", errors="ignore") as f:
                    context_str += f"\nDocument Context:\n{f.read()[:2000]}...\n" # Limit for now
            except: pass

    # 3. Create the Plan/Task
    # We ask the Leader to analyze the request and delegate if needed
    leader_config = get_agent_config_by_id(leader_id)
    if not leader_config:
        raise HTTPException(status_code=404, detail=f"Leader agent {leader_id} not found")
        
    # Construct the Leader's chain
    # We manually inject the collaboration prompt
    llm = ChatOllama(model=leader_config.model, base_url="http://localhost:11434")
    
    # If there are workers, we tell the leader they can ask them questions
    collaboration_prompt = ""
    if worker_ids:
        worker_details = []
        for wid in worker_ids:
            wc = get_agent_config_by_id(wid)
            if wc:
                worker_details.append(f"{wc.name} ({wc.description})")
        collaboration_prompt = f"\nYou have the following team members available to help: {', '.join(worker_details)}. "
    
    # Add history to system prompt context
    history_str = "\n".join(history_context)
    
    full_system_prompt = f"""You are {leader_config.name}. {leader_config.instructions}
    {context_str}
    {collaboration_prompt}
    
    Recent Conversation History:
    {history_str}
    
    User Request: {request.message}
    
    If you need help from your team, describe what you need. If you can answer directly, do so.
    For this 'Lite' collaboration, simply provide your best answer, incorporating your own knowledge.
    """
    
    # In a full impl, we would loop: Leader -> sends msg -> Worker -> sends reply -> Leader -> Final Answer.
    # For MVP of Solution 2, we will do a simple "Consultation":
    # 1. Leader thinks about the plan.
    # 2. We (the code) query the workers in parallel with the user request.
    # 3. We feed worker responses back to the leader as "Context".
    # 4. Leader gives final answer.
    
    internal_logs = []
    
    # Step 1: Consult Workers (Parallel)
    worker_responses = []
    for wid in worker_ids:
        w_config = get_agent_config_by_id(wid)
        if w_config:
            w_llm = ChatOllama(model=w_config.model)
            w_prompt = f"You are {w_config.name}. Context: {context_str}\n\nUser Question: {request.message}\n\nProvide your input/analysis."
            w_resp = w_llm.invoke(w_prompt)
            worker_responses.append(f"Input from {w_config.name}:\n{w_resp.content}")
            
            # Save Agent Internal Thought
            if session_id:
                try:
                    supabase.table("chat_messages").insert({
                        "session_id": session_id,
                        "sender_id": wid,
                        "sender_name": w_config.name,
                        "role": "function",
                        "content": w_resp.content
                    }).execute()
                except: pass

            internal_logs.append({
                "role": "function", 
                "name": w_config.name, 
                "content": w_resp.content
            })
            
    # Step 2: Leader Synthesis
    final_inputs = f"""User Request: {request.message}
    
    Team Inputs:
    {chr(10).join(worker_responses)}
    
    Based on the above, provide a comprehensive response to the user.
    """
    
    leader_resp = llm.invoke([
        SystemMessage(content=full_system_prompt),
        HumanMessage(content=final_inputs)
    ])
    
    # Save Leader Response
    if session_id:
        try:
            supabase.table("chat_messages").insert({
                "session_id": session_id,
                "sender_id": leader_id,
                "sender_name": leader_config.name,
                "role": "assistant",
                "content": leader_resp.content
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save leader response: {e}")

    
    # Construct partial history to return to frontend
    # Filter out internal logs if detailed view not desired, but user wanted visibility.
    # We will return: [User Msg] -> [Worker Thoughts] -> [Leader Final Answer]
    
    messages_to_return = []
    # messages_to_return.append({"role": "user", "content": request.message}) # Frontend already has this
    
    for log in internal_logs:
        messages_to_return.append(log)
        
    messages_to_return.append({
        "role": "assistant",
        "name": leader_config.name,
        "content": leader_resp.content
    })

    return {
        "status": "success",
        "messages": messages_to_return,
        "session_id": session_id # Return the ID so frontend can update URL or state
    }


@app.get("/api/projects/{project_id}/sessions")
async def get_project_sessions(project_id: str):
    """List chat sessions for a project"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        response = supabase.table("chat_sessions").select("*").eq("project_id", project_id).order("updated_at", desc=True).limit(50).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get full message history for a session"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        response = supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=False).execute()
        
        # Format for frontend
        formatted = []
        for msg in response.data:
            formatted.append({
                "role": msg["role"],
                "content": msg["content"],
                "name": msg.get("sender_name", msg["role"])
            })
        return formatted
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.post("/api/folders/create")
async def create_folders_endpoint(request: FolderCreationRequest):
    """Create standard project subfolders locally"""
    base_path = request.path
    
    if not base_path:
        raise HTTPException(status_code=400, detail="Path is required")

    subfolders = [
        "Contracts",
        "Financials",
        "Technical Specs",
        "Correspondance",
        "Safety & Compliance"
    ]
    
    results = []
    errors = []

    try:
        # Create base folder (if it doesn't exist)
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

from fastapi import BackgroundTasks
from ingest_service import process_and_store_document

@app.post("/api/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = Form(...),
    user_id: str = Form(...),
    category: str = Form(...),
    status: str = Form(...),
    tags: str = Form(None)
):
    """
    Handle document upload:
    1. Fetch project path from Supabase.
    2. Save file to category subfolder.
    3. Log entry to project_documents table.
    4. Trigger RAG Ingestion (Async).
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        # 1. Fetch Project Path
        response = supabase.table("projects").select("sharepoint_folder_path").eq("id", project_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        base_path = response.data.get("sharepoint_folder_path")
        if not base_path:
            raise HTTPException(status_code=400, detail="Project has no configured local folder path")

        # 2. Determine Save Path
        # Map category names to folder names if they differ slightly, or use direct match
        # Assuming category matches folder definitions in create_folders_endpoint
        folder_name = category
        target_dir = os.path.join(base_path, folder_name)
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True) # Create if missing

        file_path = os.path.join(target_dir, file.filename)
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size = os.path.getsize(file_path)

        # 3. Log to Supabase
        # Parse tags (comma separated string) -> list
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
        new_doc = db_response.data[0] if db_response.data else {}

        # 4. Trigger Ingestion (Background)
        if new_doc and new_doc.get("id"):
            background_tasks.add_task(
                process_and_store_document, 
                document_id=new_doc.get("id"), 
                file_path=file_path,
                metadata={"category": category}
            )

        return {
            "message": "File uploaded and logged successfully. RAG ingestion started.", 
            "data": new_doc,
            "saved_path": file_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document:
    1. Fetch file path from Supabase
    2. Delete local file
    3. Delete database record
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        # 1. Fetch document details to get the path
        response = supabase.table("project_documents").select("*").eq("id", document_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = response.data
        file_path = doc.get("file_path")

        # 2. Delete local file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted local file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete local file {file_path}: {e}")
                # We continue to delete from DB even if file delete fails (or maybe it was already gone)
        else:
            logger.warning(f"File not found locally: {file_path}")

        # 3. Delete from Supabase
        supabase.table("project_documents").delete().eq("id", document_id).execute()
        
        return {"status": "success", "message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")