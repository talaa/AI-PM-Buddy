from pydantic import BaseModel, Field
from typing import List
import uuid

class WorkflowSpec(BaseModel):
    """Specification for a dynamically generated collaboration workflow.
    
    The `agent_ids` list defines the order of agents – the first one is treated as the leader.
    `document_ids` are optional IDs of project documents whose content will be loaded as context.
    `user_message` is the original user request.
    `graph_json` can store a serialised LangGraph for debugging/persistence.
    """
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    agent_ids: List[str]
    document_ids: List[str] = []
    user_message: str
    graph_json: str | None = None
