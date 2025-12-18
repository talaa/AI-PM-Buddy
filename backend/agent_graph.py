from typing import TypedDict, Annotated, Sequence, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from tools.rag import KnowledgeBaseTool
from schemas import AgentConfig
import logging

logger = logging.getLogger(__name__)

# Define the State
class AgentState(TypedDict):
    messages: Sequence[BaseMessage]

def create_agent_graph(agent_config: AgentConfig):
    """
    Creates a LangGraph StateGraph for the agent.
    """
    
    # 1. Initialize Tools
    # In the future, we can add more tools here based on agent_config.tools
    tools = [KnowledgeBaseTool()] 
    
    # 2. Initialize Model
    llm = ChatOllama(
        model=agent_config.model,
        base_url="http://localhost:11434",
        # temperature=agent_config.temperature
    )
    
    # Bind tools to the model
    llm_with_tools = llm.bind_tools(tools)
    
    # 3. Define the Agent Node
    async def agent_node(state: AgentState):
        messages = state["messages"]
        
        # Construct System Prompt if it's the first message? 
        # Actually LangChain handles SystemMessages in the list nicely.
        # But we need to ensure the system prompt is always there or injected.
        
        # If the first message isn't system, we might want to prepend it, 
        # but `agent_service.py` handles history conversion.
        # Let's check if we need to enforce the system instruction here.
        
        # We can create a simple runner
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # 4. Define the Graph
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    
    workflow.set_entry_point("agent")
    
    # Conditional edge: If agent calls a tool, go to 'tools', else END
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
    )
    
    # Edge: After tools, go back to agent to synthesize answer
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()
