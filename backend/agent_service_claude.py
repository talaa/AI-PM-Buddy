import logging
from typing import Dict, Any, List, Optional
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from schemas import AgentConfig
from database import supabase

logger = logging.getLogger(__name__)

# Store active chains per agent
active_chains: Dict[str, Any] = {}

# A2A Communication State - for agent-to-agent messaging
a2a_message_buffer: Dict[str, List[Dict[str, Any]]] = {}

def create_langchain_agent(agent_config: AgentConfig):
    """Create a LangChain agent with the given configuration"""
    
    logger.info(f"Creating LangChain agent with model: {agent_config.model}")

    # Initialize Ollama LLM
    llm = ChatOllama(
        model=agent_config.model,
        base_url="http://localhost:11434"
    )
    
    # Create system prompt template
    system_template = f"""You are an AI assistant named '{agent_config.name}'.

Description: {agent_config.description}

Instructions:
{agent_config.instructions}

Knowledge Base / Context:
{agent_config.knowledge or 'No specific knowledge base provided.'}

Tools Available: {', '.join(agent_config.tools or [])}

Remember to:
- Follow the instructions carefully
- Use the knowledge base when relevant
- Be helpful, accurate, and concise
- Maintain conversation context
"""
    
    # Create prompt template with message history
    # Using MessagesPlaceholder to handle message objects directly
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])
    
    # Create the chain
    chain = prompt | llm | StrOutputParser()
    
    return chain


def convert_history_to_messages(history: List[Dict[str, str]]) -> List[BaseMessage]:
    """Convert history dict to LangChain message objects"""
    messages = []
    if not history:
        return messages
        
    for msg in history:
        role = msg.get('role', 'user').lower()
        content = msg.get('content', '')
        
        if role == 'user':
            messages.append(HumanMessage(content=content))
        elif role == 'assistant':
            messages.append(AIMessage(content=content))
        elif role == 'system':
            messages.append(SystemMessage(content=content))
        else:
            # Default to human message for unknown roles
            messages.append(HumanMessage(content=content))
    
    return messages


def get_agent_config_by_id(agent_id: str) -> Optional[AgentConfig]:
    """Fetch agent details from Supabase and return AgentConfig"""
    if not supabase:
        logger.error("Supabase client is not initialized.")
        return None
    
    logger.info(f"Fetching agent from Supabase with ID: {agent_id}")
    
    try:
        response = supabase.table("agents").select("*").eq("id", agent_id).execute()
        
        if not response.data:
            logger.warning(f"No agent found with ID: {agent_id}")
            all_agents = supabase.table("agents").select("id, name").execute()
            logger.info(f"Available agents: {all_agents.data}")
            return None
            
        agent_data = response.data[0]
        logger.info(f"Agent found: {agent_data.get('name')}")
        
        return AgentConfig(
            name=agent_data.get('name', 'Assistant'),
            description=agent_data.get('description', 'AI Assistant'),
            instructions=agent_data.get('instructions', 'Provide helpful responses'),
            knowledge=agent_data.get('knowledge'),
            tools=agent_data.get('tools', []),
            model=agent_data.get('model', 'qwen3:latest'),
        )
            
    except Exception as e:
        logger.error(f"Error fetching agent from Supabase: {str(e)}", exc_info=True)
        return None


# ============================================================================
# A2A (Agent-to-Agent) Communication Functions
# ============================================================================

def send_message_to_agent(
    from_agent_id: str,
    to_agent_id: str,
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send a message from one agent to another.
    Implements proper message routing with context preservation.
    """
    logger.info(f"A2A: {from_agent_id} -> {to_agent_id}: {message[:50]}...")
    
    # Initialize buffer for target agent if needed
    if to_agent_id not in a2a_message_buffer:
        a2a_message_buffer[to_agent_id] = []
    
    # Create message envelope with metadata
    message_envelope = {
        "from_agent_id": from_agent_id,
        "to_agent_id": to_agent_id,
        "content": message,
        "context": context or {},
        "timestamp": str(datetime.now()),
        "message_id": str(uuid.uuid4())
    }
    
    # Add to buffer
    a2a_message_buffer[to_agent_id].append(message_envelope)
    
    logger.info(f"Message queued for {to_agent_id}. Buffer size: {len(a2a_message_buffer[to_agent_id])}")
    
    return {
        "status": "queued",
        "message_id": message_envelope["message_id"],
        "recipient": to_agent_id
    }


def get_messages_for_agent(agent_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all pending messages for an agent.
    Messages are cleared after retrieval.
    """
    messages = a2a_message_buffer.get(agent_id, [])
    
    if messages:
        logger.info(f"Retrieved {len(messages)} messages for {agent_id}")
        # Clear the buffer after retrieval
        a2a_message_buffer[agent_id] = []
    
    return messages


def process_agent_collaboration(
    agent_id: str,
    message: str,
    history: List[Dict[str, str]],
    other_agent_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Process a message for an agent, including collaboration with other agents.
    
    Args:
        agent_id: The primary agent processing the request
        message: The input message
        history: Conversation history
        other_agent_ids: Other agents to potentially collaborate with
    
    Returns:
        Response with agent output and any collaboration metadata
    """
    logger.info(f"Processing collaborative request for agent: {agent_id}")
    
    # Get agent configuration
    agent_config = get_agent_config_by_id(agent_id)
    if not agent_config:
        raise ValueError(f"Agent {agent_id} not found")
    
    # Get or create chain
    cache_key = f"{agent_id}_{agent_config.model}"
    if cache_key not in active_chains:
        active_chains[cache_key] = create_langchain_agent(agent_config)
    
    chain = active_chains[cache_key]
    
    # Convert history
    history_messages = convert_history_to_messages(history)
    
    # Invoke chain
    logger.info(f"Invoking {agent_config.name} with model: {agent_config.model}")
    response = chain.invoke({
        "input": message,
        "history": history_messages
    })
    
    # Get pending messages from other agents
    pending_messages = get_messages_for_agent(agent_id)
    
    return {
        "response": response,
        "agent_name": agent_config.name,
        "agent_id": agent_id,
        "model_used": agent_config.model,
        "pending_messages": pending_messages,
        "collaboration_enabled": bool(other_agent_ids)
    }


# Import datetime and uuid at top if not already present
from datetime import datetime
import uuid