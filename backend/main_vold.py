import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import ollama
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from the project root (.env located one level up)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

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

# Supabase Setup
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: SUPABASE_URL or SUPABASE_ANON_KEY not found in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

class ChatRequest(BaseModel):
    agent_id: str
    message: str
    history: Optional[List[Dict[str, str]]] = []

@app.get("/")
async def root():
    return {"status": "ok", "message": "AI PM Buddy Backend (Ollama) is running"}

@app.post("/api/chat")
async def chat_with_agent(request: ChatRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        # Fetch Agent Details
        agent_response = supabase.table("agents").select("*").eq("id", request.agent_id).execute()
        
        if not agent_response.data:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent = agent_response.data[0]
        
        # Construct System Prompt
        system_instruction = f"""
        You are an AI assistant named '{agent.get('name')}'.
        Description: {agent.get('description')}
        
        Instructions:
        {agent.get('instructions')}
        
        Knowledge Base / Context:
        {agent.get('knowledge') or 'No specific knowledge base provided.'}
        
        Tools Available: {', '.join(agent.get('tools') or [])}
        """

        # Prepare messages for Ollama
        messages = [
            {'role': 'system', 'content': system_instruction}
        ]
        
        # Add history if provided
        if request.history:
            # Basic history conversion - ensuring roles are valid for Ollama
            for msg in request.history:
                messages.append(msg)
                
        # Add current user message
        messages.append({'role': 'user', 'content': request.message})

        # Use the model specified in agent, default to qwen3:latest
        model_name = agent.get('model', 'qwen3:latest')

        # Call Ollama
        response = ollama.chat(model=model_name, messages=messages)
        
        return {
            "response": response['message']['content'],
            "agent_name": agent.get('name'),
            "model_used": model_name
        }

    except Exception as e:
        print(f"Error processing chat: {str(e)}")
        # Determine model name safely – if agent was not fetched, fall back to default
        model_name = agent.get('model') if 'agent' in locals() else 'qwen3:latest'
        # Check if error is related to model not found
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=500,
                detail=f"Model '{model_name}' not found. Please run 'ollama pull {model_name}'"
                
            )
        model_name='qwen3:latest'
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
