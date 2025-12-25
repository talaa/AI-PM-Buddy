# backend/deep_agent_manager.py
"""Deep Agent manager module.
Implements a reasoning loop (Deep Agent) for the AI PM Buddy.
"""

import logging
import json
from typing import Any, Dict, List, Optional

from deepagents import create_deep_agent
from agent_tools import internet_search, query_data, get_data_schema, search_text_documents, consult_specialist
from config import DEFAULT_MODEL
from agent_service import get_agent_config_by_id
from database import supabase

logger = logging.getLogger(__name__)

def _build_system_prompt() -> str:
    """Return a system prompt that steers the Deep Agent as an AI PM."""
    return (
        """
        You are an expert AI Project Manager (AI PM). Your job is to fulfill the user's project management request autonomously, professionally, and comprehensively by coordinating with specialist agents when needed and leveraging all available context, tools, and knowledge.

CRITICAL OPERATIONAL RULES:
1. You are the leader of a multi-agent team. Think step-by-step before acting.
2. **DELEGATE DATA EXTRACTION:** Do not perform technical tasks like data analysis or SQL querying yourself. FOR ANY ENTITY like "ARDA", "PO", "Cost Item", or precise financial figures, you MUST delegate the search to the "Senior Data Analyst" specialist via the `consult_specialist` tool.
3. **MULTI-SOURCE VERIFICATION (THOROUGHNESS):** Never assume the first source provides the complete picture. If you find qualitative info in text documents (using `search_text_documents`), you MUST proactively check if related quantitative/structured data exists in the Excel files by consulting the "Senior Data Analyst".
4. **PERSISTENCE:** If a search returns incomplete results, try different angles or specialists. Do not settle for "no results" until all tools (Internet, Documents, Specialists) have been exhausted.
5. DO NOT answer everything yourself. Use your specialist consultation tools when the request requires domain-specific expertise (Technical, Legal, Financial, Data Analysis).
6. You MAY call multiple specialists in sequence or parallel if the task benefits from diverse inputs. (Use `consult_specialist` tool).
7. ALWAYS incorporate relevant document context and shared team knowledge when reasoning.
8. Structure your reasoning clearly:
   - First, analyze the request and identify key aspects (Technical, Data, Project).
   - Second, decide which sources and specialists cover these aspects.
   - Third, execute tool calls (e.g., Search Text + Consult Senior Data Analyst).
   - Fourth, synthesize ALL inputs into a professional, actionable response.
9. NEVER stop after calling a tool. Always continue reasoning with the observation and move toward the final answer.
10. Provide responses in a clear, professional project management style (Bullet points, Tables, Executive Summary).
11. NEVER ask for permission or confirmation to proceed. Execute the full reasoning chain.
12. NEVER hallucinate processes, templates, or data.
13. If the request is unclear, ask clarifying questions ONLY as a last resort.
14. **PROGRESS TRACKING:** For every new complex task, start your FIRST response with a section titled `[PLAN]:` followed by a markdown checklist of the high-level steps you intend to take.

You lead a capable team. Use them wisely to deliver the best possible project management outcome for the user.
        """
    )

async def run_deep_agent_workflow(
    user_message: str,
    project_id: str,
    session_id: Optional[str] = None,
    knowledge_context: str | None = None,
    specialist_ids: List[str] = [],
    model: str = DEFAULT_MODEL,
    selected_source_id: Optional[str] = None,
    selected_filename: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a Deep Agent reasoning loop.

    Parameters
    ----------
    user_message: str
        The raw user request.
    knowledge_context: str, optional
        Additional context (documents, knowledge base).
    specialist_ids: List[str], optional
        List of agent IDs available as specialists.

    Returns
    -------
    dict
        Response with status, messages, and results.
    """
    system_prompt = _build_system_prompt()
    
    # If a specific source is selected, inject focus instruction
    if selected_source_id:
        focus_msg = f"\n\n### MANDATORY FOCUS SOURCE:\n"
        focus_msg += f"The user has explicitly selected ONE document to use for this request: {selected_filename or selected_source_id}\n"
        focus_msg += "1. You MUST prioritize information from this source above all others.\n"
        
        # Add table name hint for structured data
        if selected_filename and any(selected_filename.lower().endswith(ext) for ext in ['.xlsx', '.xls', '.csv']):
            import os
            table_name = os.path.splitext(selected_filename)[0]
            table_name = "".join([c if c.isalnum() else "_" for c in table_name])
            focus_msg += f"2. This is structured data. The TABLE NAME in SQLite is likely: `{table_name}`. Use this in your SQL queries.\n"
            focus_msg += "3. Only search other documents or the internet if the information is explicitly missing from this selected source."
        else:
            focus_msg += "2. Only search other documents or the internet if the information is explicitly missing from this selected source."
            
        system_prompt += focus_msg
    
    # Inject Specialist Context
    if specialist_ids:
        specialist_info = []
        for ag_id in specialist_ids:
            conf = get_agent_config_by_id(ag_id)
            if conf:
                specialist_info.append(f"- Name: {conf.name} | Role/Desc: {conf.description[:100]}...")
        
        if specialist_info:
            system_prompt += "\n\n### AVAILABLE SPECIALISTS:\n" + "\n".join(specialist_info)
            system_prompt += "\nUse the `consult_specialist` tool with the EXACT Name above to ask them questions."

    if knowledge_context:
        # We append context but warn the agent to prefer tools for large data
        system_prompt += (
            "\n\n### ADDITIONAL CONTEXT / DOCUMENTS:\n"
            "Note: Use the tools to query this data if it refers to structured tables.\n"
            + knowledge_context
        )

    # Create the deep agent - REMOVED direct data tools to enforce delegation
    tools = [ search_text_documents,get_data_schema,query_data, internet_search,consult_specialist,consult_specialist]
    agent = create_deep_agent(
        tools=tools,
        system_prompt=system_prompt,
        model=model
    )

    logger.info(f"Running Refined Deep Agent for message: {user_message[:150]}...")
    
    # Load existing history if session_id is provided
    chat_history = []
    if session_id:
        try:
            resp = supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at").execute()
            if resp.data:
                for row in resp.data:
                    role = row.get("role")
                    content = row.get("content")
                    if role == "user":
                        chat_history.append({"role": "user", "content": content})
                    elif role == "assistant":
                        chat_history.append({"role": "assistant", "content": content})
                    elif role == "function":
                        chat_history.append({"role": "tool", "content": content, "tool_call_id": row.get("name") or "unknown"})
        except Exception as e:
            logger.error(f"Failed to load chat history for session {session_id}: {e}")

    # Prepare input messages
    input_messages = chat_history + [{"role": "user", "content": user_message}]
    try:
        # We use a higher recursion limit if possible, though create_react_agent default is 25.
        # The result is the final state.
        
        # Add LangFuse config
        from dependencies import get_langfuse_callback
        callbacks = get_langfuse_callback()
        
        result = await agent.ainvoke(
            {"messages": input_messages},
            config={"callbacks": callbacks} if callbacks else {}
        )
        
        # Extract the final answer from the last message
        messages = result.get("messages", [])
        final_answer = ""
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, 'content'):
                final_answer = last_msg.content
            elif isinstance(last_msg, dict):
                final_answer = last_msg.get('content', '')

        # Standardize response format with safe serialization
        serialized_messages = []
        for msg in messages:
            try:
                # Helper to extract content
                content = msg.content
                if isinstance(content, list):
                    # Handle complex content (e.g., text + image)
                    content = " ".join([c.get("text", "") for c in content if c.get("type") == "text"])
                
                # Default role mapping
                role = "assistant"
                if msg.type == "human":
                    role = "user"
                elif msg.type == "system":
                    role = "system"
                elif msg.type == "tool":
                    role = "function" # Shows in grey bubble
                
                # Check for tool_calls in AIMessage to show them?
                # Using 'function' role for tool calls output is standard in this UI.
                
                serialized_messages.append({
                    "role": role,
                    "content": content,
                    "name": msg.name or ("You" if role == "user" else "Agent"),
                    "type": msg.type
                })
            except Exception as e:
                logger.warning(f"Failed to serialize message {msg}: {e}")
                serialized_messages.append({"role": "system", "content": str(msg)})

        # Parse plan if present in final answer
        parsed_plan = []
        if final_answer:
            import re
            plan_match = re.search(r'\[PLAN\]:(.*?)(?:\n\n|\n[A-Z]|$)', final_answer, re.DOTALL)
            if plan_match:
                plan_text = plan_match.group(1).strip()
                for line in plan_text.split('\n'):
                    line = line.strip()
                    if line.startswith('- [ ]') or line.startswith('- [x]'):
                        parsed_plan.append({
                            "text": line.replace('- [ ] ', '').replace('- [x] ', '').strip(),
                            "completed": line.startswith('- [x]')
                        })

        # Persistence logic
        logger.info(f"[PERSISTENCE] Starting persistence for project_id={project_id}, session_id={session_id}")
        if project_id and session_id:
            try:
                logger.info(f"[PERSISTENCE] Attempting to save user message: {user_message[:100]}...")
                # 1. Save the user message first
                user_insert_result = supabase.table("chat_messages").insert({
                    "session_id": session_id,
                    "role": "user",
                    "content": user_message,
                    "name": "You"
                }).execute()
                logger.info(f"[PERSISTENCE] User message saved successfully: {user_insert_result.data}")
                
                # 2. Save new messages generated by the agent
                # input_messages includes history + user message
                # messages includes history + user message + agent responses
                # So new messages start at index len(input_messages)
                new_messages = messages[len(input_messages):]
                logger.info(f"[PERSISTENCE] Found {len(new_messages)} new messages to save")
                
                for idx, msg in enumerate(new_messages):
                    role = "assistant"
                    if msg.type == "human": 
                        role = "user"
                    elif msg.type == "tool": 
                        role = "function"
                    
                    content = msg.content
                    if isinstance(content, list):
                        content = " ".join([c.get("text", "") for c in content if c.get("type") == "text"])
                    
                    logger.info(f"[PERSISTENCE] Saving message {idx+1}/{len(new_messages)}: role={role}, content_length={len(str(content))}")
                    msg_insert_result = supabase.table("chat_messages").insert({
                        "session_id": session_id,
                        "role": role,
                        "content": str(content),
                        "name": getattr(msg, "name", None) or getattr(msg, "tool_call_id", None)
                    }).execute()
                    logger.info(f"[PERSISTENCE] Message {idx+1} saved: {msg_insert_result.data}")
                
                # 3. Update session timestamp and plan
                from datetime import datetime
                update_data = {"updated_at": datetime.utcnow().isoformat()}
                if parsed_plan:
                    update_data["plan"] = parsed_plan
                    logger.info(f"[PERSISTENCE] Plan to save: {len(parsed_plan)} items")
                
                logger.info(f"[PERSISTENCE] Updating session with data: {update_data}")
                session_update_result = supabase.table("chat_sessions").update(update_data).eq("id", session_id).execute()
                logger.info(f"[PERSISTENCE] Session updated: {session_update_result.data}")
                
                logger.info(f"[PERSISTENCE] ✅ SUCCESS: Saved {len(new_messages) + 1} messages to session {session_id}")
                    
            except Exception as e:
                logger.error(f"[PERSISTENCE] ❌ FAILED: {e}", exc_info=True)

        return {
            "status": "success",
            "output": final_answer,
            "messages": serialized_messages,
            "plan": parsed_plan,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Deep Agent Workflow Error: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }
