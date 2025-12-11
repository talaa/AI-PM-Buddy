import logging
from typing import Dict, Any, List, Optional
#from langchain_community.chat_models import ChatOllama
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from schemas import AgentConfig
from database import supabase

logger = logging.getLogger(__name__)

# Store active chains per agent
active_chains: Dict[str, Any] = {}

def create_langchain_agent(agent_config: AgentConfig):
    """Create a LangChain agent with the given configuration"""
    
    logger.info(f"Creating LangChain agent with model: {agent_config.model}")

    # Initialize Ollama LLM
    llm = ChatOllama(
        model=agent_config.model,
        #temperature=agent_config.temperature,
        #num_predict=agent_config.max_tokens,
        base_url="http://localhost:11434"  # Default Ollama URL
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
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])
    
    # Create the chain
    chain = prompt | llm | StrOutputParser()
    
    return chain

def convert_history_to_messages(history: List[Dict[str, str]]) -> List:
    """Convert history dict to LangChain message objects"""
    messages = []
    if not history:
        return messages
        
    for msg in history:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        
        if role == 'user':
            messages.append(HumanMessage(content=content))
        elif role == 'assistant':
            messages.append(AIMessage(content=content))
        elif role == 'system':
            messages.append(SystemMessage(content=content))
    
    return messages

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
            knowledge=agent_data.get('knowledge'),
            tools=agent_data.get('tools', []),
            model=agent_data.get('model', 'qwen3:latest'),
            #temperature=agent_data.get('temperature', 0.7),
            #max_tokens=agent_data.get('max_tokens', 2000)
        )
            
    except Exception as e:
        logger.error(f"Error fetching agent from Supabase: {str(e)}", exc_info=True)
        return None
