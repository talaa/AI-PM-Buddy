"""
Pydantic request models for API endpoints.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict


class A2ASendRequest(BaseModel):
    """Request model for agent-to-agent message sending"""
    from_agent_id: str
    to_agent_id: str
    message: str
    context: Optional[Dict] = None


class CollaborationRequest(BaseModel):
    """Request model for collaborative agent processing"""
    agent_id: str  # The "Leader" agent
    message: str
    collaborating_agents: List[str]
    history: List[Dict] = []
    document_ids: List[str] = []  # Added to support RAG context
