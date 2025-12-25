"""
Chat endpoints for individual agent interactions (Refactored to use Deep Agent).
"""
import logging
from fastapi import APIRouter, HTTPException
from schemas import ChatRequest, TeamChatRequest
from database import supabase
from agent_service import get_agent_config_by_id
from config import DEFAULT_MODEL
from deepagents import create_deep_agent
from agent_tools import internet_search, query_data, get_data_schema, search_text_documents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """
    Main chat endpoint using Deep Agent architecture.
    """
    
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        # Fetch Agent Details
        agent_config = get_agent_config_by_id(request.agent_id)
        
        if not agent_config:
            logger.error(f"Agent with ID {request.agent_id} could not be found.")
            raise HTTPException(status_code=404, detail="Agent not found.")
        
        logger.info(f"Creating Deep Agent for: {agent_config.name} ({agent_config.model})")
        
        # Prepare System Prompt
        system_prompt = f"""You are {agent_config.name}.
Description: {agent_config.description}

Instructions:
{agent_config.instructions}

Relevant Knowledge:
{agent_config.knowledge or 'None'}
"""
        # Create Deep Agent with standard tools
        # (We give standard tools to all agents for now, or we could customize based on config)
        tools = [internet_search, query_data, get_data_schema, search_text_documents]
        
        agent = create_deep_agent(
            tools=tools,
            system_prompt=system_prompt,
            model=agent_config.model
        )
        
        # Invoke Agent
        from dependencies import get_langfuse_callback
        callbacks = get_langfuse_callback(session_id=request.session_id)
        
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": request.message}]},
            config={"callbacks": callbacks} if callbacks else {}
        )
        
        # Extract Response
        final_message = result["messages"][-1]
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
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.post("/a2a/chat")
async def team_chat(request: TeamChatRequest):
    """
    Agent-to-Agent Team Chat.
    Routes to the new 'collaborate' endpoint.
    """
    from api.routers.collaboration import collaborate, CollaborateRequest
    
    # Adapt TeamChatRequest to CollaborateRequest if necessary, or just forward if compatible
    # TeamChatRequest likely has similar fields.
    # Let's assume we can map it or call collaborate directly if types match.
    # For now, we'll try to convert manually to be safe.
    
    try:
        collab_req = CollaborateRequest(
            project_id=request.project_id,
            agent_ids=request.agent_ids,
            document_ids=request.document_ids,
            message=request.message,
            knowledge_files=[]
        )
        # Note: collaborate returns a dict, not a standard response object sometimes.
        # But wait, collaborate is an endpoint function, calling it directly might bypass validation
        # or return the response body. 
        # Actually it's better to just return the result of collaborate logic if possible.
        # But since collaborate is an async def, we can await it.
        return await collaborate(collab_req)
    except Exception as e:
        logger.error(f"Error in team_chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Team chat failed: {str(e)}")
