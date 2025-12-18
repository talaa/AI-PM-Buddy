from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class ChatRequest(BaseModel):
    agent_id: str
    message: str
    history: Optional[List[Dict[str, str]]] = []
    session_id: Optional[str] = None  # For memory management

class TeamChatRequest(BaseModel):
    agent_ids: List[str]
    project_id: str # Required for session grouping
    document_ids: List[str] = []
    message: str
    session_id: Optional[str] = None    

class AgentConfig(BaseModel):
    name: str
    description: str
    instructions: str
    knowledge: Optional[str] = None
    tools: Optional[List[str]] = []
    model: str = "qwen3:latest"
    #temperature: float = 0.7
    #max_tokens: int = 2000
    modified_at: Optional[datetime] = None

# Schema for partial updates
class UpdateAgent(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    knowledge: Optional[str] = None
    tools: Optional[List[str]] = None
    model: Optional[str] = None
    #temperature: Optional[float] = None
    #max_tokens: Optional[int] = None

class FolderCreationRequest(BaseModel):
    path: str
