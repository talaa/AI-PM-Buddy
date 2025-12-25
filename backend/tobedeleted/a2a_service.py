import operator
from typing import Annotated, List, Sequence, Tuple, Union, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, FunctionMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_community.chat_models import ChatOllama
from langgraph.graph import StateGraph, END
from schemas import AgentConfig
from agent_service import get_agent_config_by_id, create_langchain_agent
import logging
import functools

logger = logging.getLogger(__name__)

# The state of the graph
class AgentState(Dict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str

def create_team_graph(agent_ids: List[str], context_files: List[str] = [], supervisor_model: str = "llama3"):
    """
    Create a LangGraph team with the specified agents and context.
    
    Args:
        agent_ids: List of agent IDs (from Supabase) to include in the team.
        context_files: List of file contents (strings) to provide as context.
        supervisor_model: The model to use for the Supervisor agent.
    """
    
    # 1. Fetch Agent Configurations
    members = []
    agent_nodes = {}
    
    for agent_id in agent_ids:
        config = get_agent_config_by_id(agent_id)
        if config:
            # Create the agent runnable
            agent_runnable = create_langchain_agent(config)
            
            # Define the node function for this agent
            # This function invokes the agent and formats the output
            async def agent_node(state, agent_name=config.name, runnable=agent_runnable):
                logger.info(f"--- Agent {agent_name} Node Executing ---")
                # Adapter: Convert LangGraph state to what the chain expects (history, input)
                # The chain expects 'history' (list of messages) and 'input' (string)
                
                messages = state.get("messages", [])
                
                # Separate history and input
                # In this multi-agent loop, the whole conversation so far is essentially history
                # But the prompt template has {input} at the end. 
                # We can treat the very last message as 'input' and everything before as 'history'
                
                history = messages[:-1] if len(messages) > 0 else []
                input_text = messages[-1].content if len(messages) > 0 else ""
                
                # However, if this is an AI agent, it usually responds to the *user* or *previous agent*.
                # If the last message was from ITSELF, we might have a loop, but LangGraph handles that. 
                
                result = await runnable.ainvoke({
                    "history": history,
                    "input": input_text
                })
                
                return {"messages": [AIMessage(content=result, name=agent_name)]}
                
            agent_nodes[config.name] = agent_node
            members.append(config.name)
        else:
            logger.warning(f"Could not find config for agent ID: {agent_id}")

    if not members:
        raise ValueError("No valid agents found for the team.")

    # 2. Create the Supervisor
    # The supervisor decides who speaks next or if we are done.
    
    system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        f" following workers: {members}. Given the following user request,"
        " respond with the worker to act next. Each worker will perform a"
        " task and respond with their results and status.\n"
        "RULES:\n"
        "1. You MUST select a worker to act if the user asks a question or gives a task.\n"
        "2. Do NOT answer the question yourself.\n"
        "3. Do NOT select FINISH unless a worker has already successfully answered the user's question in the history.\n"
        "4. If the user asks 'who are you?' or similar generic questions, route it to the most relevant worker or just pick the first one.\n"
        "5. Respond with FINISH only when the conversation is complete."
    )
    
    if context_files:
        system_prompt += "\n\nCONTEXT FROM DOCUMENTS:\n"
        for i, content in enumerate(context_files):
            system_prompt += f"\n--- DOCUMENT {i+1} ---\n{content}\n"

    # We use function calling / standard output parsing to determine the next step
    # Since Ollama json mode can be tricky, we'll use a robust text prompt approach.
    
    supervisor_llm = ChatOllama(model=supervisor_model, temperature=0, timeout=120.0)
    
    options = ["FINISH"] + members
    
    supervisor_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
            (
                "system",
                "Given the conversation above, who should act next?"
                " Or should we FINISH? Select one of: {options}."
                " Return ONLY the name of the selected option, with no punctuation or explanation."
            ),
        ]
    ).partial(options=str(options), members=", ".join(members))

    supervisor_chain = (
        supervisor_prompt
        | supervisor_llm
        | (lambda x: x.content)
    )

    def parse_supervisor_output(output):
        cleaned = output.strip().replace('"', '').replace("'", "")
        # Fuzzy match or exact match
        for member in members:
            if member.lower() in cleaned.lower():
                return {"next": member}
        if "finish" in cleaned.lower():
            return {"next": "FINISH"}
            
        # Default to first member if unsure, or FINISH?
        # Let's default to FINISH to avoid loops, but log it.
        logger.warning(f"Supervisor unexpected output: {output}. Defaulting to FINISH.")
        return {"next": "FINISH"}

    async def supervisor_node(state):
        logger.info(f"Supervisor executing with state messages count: {len(state['messages'])}")
        result = await supervisor_chain.ainvoke(state)
        logger.info(f"Supervisor LLM raw output: {result}")
        parsed = parse_supervisor_output(result)
        logger.info(f"Supervisor parsed decision: {parsed}")
        
        # FALLBACK: If Supervisor says FINISH but we only have the User's initial message,
        # FORCE delegation to the first agent. The Supervisor is being lazy.
        if parsed.get("next") == "FINISH" and len(state["messages"]) == 1:
            forced_agent = members[0]
            logger.warning(f"Supervisor tried to FINISH immediately. Forcing delegation to: {forced_agent}")
            return {"next": forced_agent}
            
        return parsed


    # 3. Build the Graph
    workflow = StateGraph(AgentState)
    
    workflow.add_node("Supervisor", supervisor_node)
    
    for name, node_func in agent_nodes.items():
        workflow.add_node(name, node_func)

    for member in members:
        # The supervisor delegates to the member
        # The member always returns to the supervisor
        workflow.add_edge(member, "Supervisor")

    # The supervisor decides the next node
    workflow.add_conditional_edges(
        "Supervisor",
        lambda x: x["next"],
        {**{n: n for n in members}, "FINISH": END}
    )
    
    workflow.set_entry_point("Supervisor")
    
    return workflow.compile()
