from typing import Any, Dict, List, Optional, Sequence, Union
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from config import OLLAMA_BASE_URL, DEFAULT_MODEL
import logging

logger = logging.getLogger(__name__)

def create_deep_agent(
    tools: List[BaseTool],
    system_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2
):
    """
    Creates a Deep Agent (reasoning loop) using LangGraph's create_react_agent.
    
    Args:
        tools: List of tools the agent can use.
        system_prompt: The system prompt for the agent.
        model: The Ollama model to use.
        temperature: Sampling temperature.
        
    Returns:
        A compiled LangGraph runnable.
    """
    llm = ChatOllama(
        model=model,
        base_url=OLLAMA_BASE_URL,
        temperature=temperature,
        timeout=120.0
    )
    
    # create_react_agent returns a compiled graph that implements the 
    # Thought -> Action -> Observation loop.
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt
    )
    
    return agent
