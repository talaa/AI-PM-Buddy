"""
AI Project Manager Deep Agent Module

This module implements a Deep Agent pattern using LangGraph's StateGraph to dynamically
construct and execute multi-agent workflows based on WorkflowSpec.
"""
import logging
from typing import Dict, List, TypedDict, Any
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Annotated

def merge_dict(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    return {**left, **right}

def merge_list(left: List[Any], right: List[Any]) -> List[Any]:
    return left + right # Simple concat for now, or we could handle by ID


from workflows.spec import WorkflowSpec
from agent_service import get_agent_config_by_id
from config import OLLAMA_BASE_URL, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)


class AIProjectManagerState(TypedDict):
    """State schema for the AI PM Deep Agent workflow"""
    messages: Annotated[List[BaseMessage], merge_list]
    task_breakdown: List[Dict[str, Any]]  # Keeping list for now, PM updates it
    current_step: str
    context: Dict[str, Any]
    results: Dict[str, Any]
    agent_outputs: Annotated[Dict[str, str], merge_dict]  # agent_id -> output


def build_dynamic_graph(spec: WorkflowSpec):
    """
    Build a dynamic StateGraph based on the WorkflowSpec.
    
    Args:
        spec: WorkflowSpec containing project_id, agent_ids, document_ids, user_message
        
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info(f"Building dynamic graph for {len(spec.agent_ids)} agents")
    
    # Create the graph
    workflow = StateGraph(AIProjectManagerState)
    
    # --- Node 1: Task Planner ---
    async def task_planner_node(state: AIProjectManagerState) -> AIProjectManagerState:
        """AI PM analyzes request and creates task breakdown"""
        logger.info("Task Planner: Analyzing user request")
        
        # Get AI PM configuration (use first agent as the PM for now)
        pm_agent = get_agent_config_by_id(spec.agent_ids[0])
        if not pm_agent:
            raise ValueError(f"AI PM agent {spec.agent_ids[0]} not found")
        
        llm = ChatOllama(model=pm_agent.model, base_url=OLLAMA_BASE_URL, timeout=OLLAMA_TIMEOUT)
        
        # Create planning prompt
        planning_prompt = f"""You are an AI Project Manager. Analyze this request and create a task breakdown.

User Request: {spec.user_message}

Available Agents:
{chr(10).join([f"- {get_agent_config_by_id(aid).name}: {get_agent_config_by_id(aid).description}" for aid in spec.agent_ids if get_agent_config_by_id(aid)])}

Create a numbered task breakdown. For each task, specify:
1. Task description
2. Which agent should handle it
3. Expected output

Format as:
Task 1: [Description] - Assigned to: [Agent Name]
Task 2: [Description] - Assigned to: [Agent Name]
"""
        
        try:
            response = await llm.ainvoke([HumanMessage(content=planning_prompt)])
            
            # Parse task breakdown (simple parsing for now)
            tasks = []
            for i, agent_id in enumerate(spec.agent_ids):
                agent_config = get_agent_config_by_id(agent_id)
                if agent_config:
                    tasks.append({
                        "id": f"task_{i+1}",
                        "description": f"Analyze request using {agent_config.name}",
                        "status": "pending",
                        "assigned_to": agent_id,
                        "agent_name": agent_config.name
                    })
            
            return {
                "task_breakdown": tasks,
                "current_step": "execution",
                "messages": [AIMessage(content=f"Task Planning Complete:\n{response.content}")]
            }
        except Exception as e:
            logger.error(f"Task Planner Error: {str(e)}", exc_info=True)
            raise e
    
    # --- Node 2: Agent Execution Nodes (Dynamic) ---
    def create_agent_node(agent_id: str):
        """Factory function to create agent execution nodes"""
        async def agent_node(state: AIProjectManagerState) -> AIProjectManagerState:
            agent_config = get_agent_config_by_id(agent_id)
            if not agent_config:
                logger.warning(f"Agent {agent_id} not found, skipping")
                return state
            
            logger.info(f"Executing agent: {agent_config.name}")
            
            llm = ChatOllama(model=agent_config.model, base_url=OLLAMA_BASE_URL, timeout=OLLAMA_TIMEOUT)
            
            # Build agent prompt with context
            context = state["context"].get("document_context", "")
            agent_prompt = f"""You are {agent_config.name}. {agent_config.instructions}

Context:
{context}

User Request: {spec.user_message}

Provide your analysis or response."""
            
            try:
                response = await llm.ainvoke([SystemMessage(content=agent_prompt)])
                
                # Update task status locally in a copy
                new_tasks = []
                for task in state["task_breakdown"]:
                    t = task.copy()
                    if t["assigned_to"] == agent_id:
                        t["status"] = "completed"
                    new_tasks.append(t)
                
                logger.info(f"Agent {agent_config.name} completed")
                return {
                    "agent_outputs": {agent_id: response.content},
                    "task_breakdown": new_tasks
                }
            except Exception as e:
                logger.error(f"Error during agent execution ({node_name}): {str(e)}", exc_info=True)
                raise e
        
        return agent_node
    
    # --- Node 3: Synthesis Node ---
    async def synthesis_node(state: AIProjectManagerState) -> AIProjectManagerState:
        """AI PM combines all agent outputs into final response"""
        logger.info("Synthesis: Combining agent outputs")
        
        pm_agent = get_agent_config_by_id(spec.agent_ids[0])
        llm = ChatOllama(model=pm_agent.model, base_url=OLLAMA_BASE_URL, timeout=OLLAMA_TIMEOUT)
        
        # Collect all agent outputs
        agent_outputs_text = "\n\n".join([
            f"=== {get_agent_config_by_id(aid).name if get_agent_config_by_id(aid) else aid} ===\n{output}"
            for aid, output in state.get("agent_outputs", {}).items()
        ])
        
        synthesis_prompt = f"""You are an AI Project Manager. Synthesize the following agent outputs into a comprehensive response.

User Request: {spec.user_message}

Agent Outputs:
{agent_outputs_text}

Provide a clear, comprehensive answer that combines insights from all agents."""
        
        response = await llm.ainvoke([HumanMessage(content=synthesis_prompt)])
        
        return {
            "messages": [AIMessage(content=response.content)],
            "current_step": "completed"
        }
    
    # --- Build the graph ---
    workflow.add_node("task_planner", task_planner_node)
    
    # Add agent nodes dynamically
    for agent_id in spec.agent_ids:
        node_name = f"agent_{agent_id}"
        workflow.add_node(node_name, create_agent_node(agent_id))
    
    workflow.add_node("synthesis", synthesis_node)
    
    # --- Define edges ---
    workflow.set_entry_point("task_planner")
    
    # Connect task_planner to all agents
    for agent_id in spec.agent_ids:
        workflow.add_edge("task_planner", f"agent_{agent_id}")
    
    # Connect all agents to synthesis
    for agent_id in spec.agent_ids:
        workflow.add_edge(f"agent_{agent_id}", "synthesis")
    
    # Synthesis → END
    workflow.add_edge("synthesis", END)
    
    # Compile with memory
    memory = MemorySaver()
    compiled = workflow.compile(checkpointer=memory)
    
    logger.info("Dynamic graph built successfully")
    return compiled


async def run_dynamic_workflow(graph, initial_state: AIProjectManagerState) -> Dict[str, Any]:
    """
    Execute the compiled graph with the initial state.
    
    Args:
        graph: Compiled StateGraph
        initial_state: Initial state dictionary
        
    Returns:
        Final state after workflow execution
    """
    logger.info("Starting dynamic workflow execution")
    
    # Execute the graph
    config = {"configurable": {"thread_id": "1"}}
    
    # Use ainvoke to get the full final state
    final_state = await graph.ainvoke(initial_state, config)
    
    logger.info("Dynamic workflow execution complete")
    return final_state
