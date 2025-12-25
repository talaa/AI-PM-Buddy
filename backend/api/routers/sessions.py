"""
Session management endpoints for chat sessions and message history.
"""
import logging
from fastapi import APIRouter, HTTPException

from database import supabase
from config import MAX_SESSIONS_LIMIT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/projects/{project_id}/sessions")
async def get_project_sessions(project_id: str):
    """List chat sessions for a project"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        response = supabase.table("chat_sessions").select("*").eq(
            "project_id", project_id
        ).order("updated_at", desc=True).limit(MAX_SESSIONS_LIMIT).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages")
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
