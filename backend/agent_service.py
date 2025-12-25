import logging
from typing import Dict, Any, List, Optional
from schemas import AgentConfig
from database import supabase
from functools import lru_cache

logger = logging.getLogger(__name__)

# active_chains removed as we are moving to Deep Agents


from functools import lru_cache

@lru_cache(maxsize=32)
def get_agent_config_by_id(agent_id: str) -> Optional[AgentConfig]:
    """Fetch agent details from Supabase and return AgentConfig"""
    if not supabase:
        logger.error("Supabase client is not initialized.")
        return None
    
    logger.info(f"Fetching agent from Supabase with ID: {agent_id}")
    
    try:
        # Debugging: Log the query we are about to make
        logger.debug(f"Executing query: supabase.table('agents').select('*').eq('id', '{agent_id}').execute()")
        
        response = supabase.table("agents").select("*").eq("id", agent_id).execute()
        
        # Debugging: Log the raw response
        logger.info(f"Supabase response: {response}")
        
        if not response.data:
            logger.warning(f"No agent found with ID: {agent_id}")
            # Try to fetch all agents to see if the ID is formatted differently or just missing
            all_agents = supabase.table("agents").select("id, name").execute()
            logger.info(f"Available agents: {all_agents.data}")
            return None
            
        agent_data = response.data[0]
        logger.info(f"Agent found: {agent_data.get('name')}")
        
        return AgentConfig(
            name=agent_data.get('name', 'Assistant'),
            description=agent_data.get('description', 'AI Assistant'),
            instructions=agent_data.get('instructions', 'Provide helpful responses'),
            knowledge=agent_data.get('knowledge_path'), # Map DB 'knowledge_path' to config 'knowledge'
            tools=agent_data.get('tools', []),
            model=agent_data.get('model', 'qwen3:latest'),
            #temperature=agent_data.get('temperature', 0.7),
            #max_tokens=agent_data.get('max_tokens', 2000)
        )
            
    except Exception as e:
        logger.error(f"Error fetching agent from Supabase: {str(e)}", exc_info=True)
        return None
