"""Collaboration endpoint based on the Deep Agent reasoning strategy.

The endpoint accepts a request describing the project, agents, documents, a user
message and optionally a list of knowledge files to include.
"""

import os
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

# Backend imports
from deep_agent_manager import run_deep_agent_workflow
from knowledge_loader import load_knowledge_files, build_knowledge_context
from config import DEFAULT_MODEL
from database import supabase

router = APIRouter(prefix="/api", tags=["collaboration"])

logger = logging.getLogger(__name__)

class CollaborateRequest(BaseModel):
    project_id: str
    session_id: Optional[str] = None
    agent_ids: List[str] = [] # Optional, treated as specialists
    document_ids: List[str]
    message: str
    knowledge_files: Optional[List[str]] = None  # e.g., ["skills", "processes"]
    selected_source_id: Optional[str] = None

def _load_documents(document_ids: List[str], selected_source_id: Optional[str] = None) -> (str, Optional[str]):
    import pandas as pd
    contents = []
    selected_filename = None
    # If a specific source is selected, only load that one
    ids_to_load = [selected_source_id] if selected_source_id else document_ids
    for doc_id in ids_to_load:
        resp = supabase.table("project_documents").select("file_path, filename").eq("id", doc_id).execute()
        if not resp.data:
            continue
        file_path = resp.data[0]["file_path"]
        document_name = resp.data[0].get("filename") or os.path.basename(file_path)
        
        if doc_id == selected_source_id:
            selected_filename = document_name
        
        # Adjust file path if needed (handle OneDrive space or absolute paths)
        # Assuming the files are accessible on the local system at this path.
        if not os.path.exists(file_path):
             logger.warning(f"File not found: {file_path}")
             continue
             
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".xlsx":
                df = pd.read_excel(file_path)
                contents.append(f"Document ID: {doc_id}\nContent:\n{df.to_csv(index=False)}")
            elif ext == ".csv":
                df = pd.read_csv(file_path)
                contents.append(f"Document ID: {doc_id}\nContent:\n{df.to_csv(index=False)}")
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    contents.append(f"Document ID: {doc_id}\nContent:\n{f.read()}")
        except Exception as e:
            logger.error(f"Failed to load document {doc_id}: {e}")
            # We continue instead of failing the whole request?
    return "\n---\n".join(contents), selected_filename

def _prepare_knowledge_context(request: CollaborateRequest) -> str:
    """Load requested knowledge markdown files and concatenate them."""
    if not request.knowledge_files:
        return ""
    knowledge_data = load_knowledge_files(request.knowledge_files)
    return build_knowledge_context(knowledge_data)

@router.post("/a2a/collaborate")
async def collaborate(request: CollaborateRequest = Body(...)):
    """
    Collaboration endpoint using the Deep Agent reasoning loop.
    """
    try:
        docs_context, selected_filename = _load_documents(request.document_ids, request.selected_source_id) if request.document_ids else ("", None)
        knowledge_context = _prepare_knowledge_context(request)
        
        combined_context = "\n".join(filter(None, [docs_context, knowledge_context]))
        
        # Ensure session exists
        session_id = request.session_id
        if not session_id:
            session_resp = supabase.table("chat_sessions").insert({
                "project_id": request.project_id,
                "title": request.message[:50] + "...",
                "agent_ids": request.agent_ids
            }).execute()
            if session_resp.data:
                session_id = session_resp.data[0]["id"]
            else:
                logger.error("Failed to create new chat session")
        
        # Pass specialist IDs (selected agents) to the Deep Agent workflow
        result = await run_deep_agent_workflow(
            user_message=request.message,
            project_id=request.project_id,
            session_id=session_id,
            knowledge_context=combined_context,
            specialist_ids=request.agent_ids,
            selected_source_id=request.selected_source_id,
            selected_filename=selected_filename
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))
            
        return result
        
    except Exception as e:
        logger.error(f"Collaboration Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
