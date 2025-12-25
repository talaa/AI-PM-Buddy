"""
Agent management endpoints for agent configuration and cache management.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException

from schemas import UpdateAgent
from database import supabase
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["agents"])


@router.delete("/chat/cache/{agent_id}")
async def clear_agent_cache(agent_id: str):
    """
    Clear cached chain for an agent.
    Deprecated: Deep Agent architecture is stateless per request or handles caching differently.
    Kept for API compatibility.
    """
    logger.info(f"Clear cache requested for {agent_id} (No-op in Deep Agent architecture)")
    return {
        "message": "Cache clear not required for Deep Agent",
        "cleared_keys": []
    }


@router.patch("/agents/{agent_id}")
async def update_agent_endpoint(agent_id: str, update: UpdateAgent):
    """Update agent details"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        # Log incoming data for debugging
        data = update.dict(exclude_unset=True)
        logger.info(f"Updating agent {agent_id} with data: {data}")
        
        # Check if agent exists
        check_response = supabase.table("agents").select("id").eq("id", agent_id).execute()
        if not check_response.data:
            logger.error(f"Agent {agent_id} not found")
            raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")
        
        # Map frontend field names to database column names
        if 'knowledge' in data:
            data['knowledge_path'] = data.pop('knowledge')
            logger.info(f"Mapped 'knowledge' to 'knowledge_path': {data.get('knowledge_path')}")
        
        # Add timestamp
        data["modified_at"] = datetime.utcnow().isoformat()
        
        # Perform update
        response = supabase.table("agents").update(data).eq("id", agent_id).execute()
        
        if not response.data:
            logger.error(f"Update returned no data for agent {agent_id}")
            raise HTTPException(status_code=500, detail="Update operation failed - no data returned")
        
        logger.info(f"Successfully updated agent {agent_id}")
        return {"message": "Agent updated successfully", "data": response.data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {str(e)}", exc_info=True)
        # Return the actual error message for debugging
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")
