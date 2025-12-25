"""
Enhanced agent tools for internet search, RAG, and data analysis.
"""

from typing import TypedDict, Annotated, Sequence, Union, Optional
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from rag_manager import RAGDocumentManager
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable verbose LangChain logs (Compatibility Fix)
try:
    from langchain.globals import set_debug
    set_debug(True)
except ImportError:
    import langchain
    langchain.debug = True

@tool
def internet_search(query: str) -> str:
    """Perform a simple web search and return top result snippets.

    This implementation uses DuckDuckGo's HTML search page to fetch results
    without requiring an API key. It parses the titles and URLs of the first
    few results and returns a formatted string.
    """
    import requests
    from bs4 import BeautifulSoup
    try:
        resp = requests.get("https://duckduckgo.com/html/", params={"q": query}, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.select("a.result__a")[:5]:
            title = a.get_text(strip=True)
            url = a.get("href")
            results.append(f"- {title}: {url}")
        if not results:
            return "No results found for the query."
        return "Top search results:\n" + "\n".join(results)
    except Exception as e:
        logger.error(f"Internet search failed: {e}")
        return f"Error performing internet search: {e}"

# Initialize RAG manager lazily
rag_manager = None

def get_rag_manager():
    global rag_manager
    if rag_manager is None:
        rag_manager = RAGDocumentManager()
    return rag_manager

@tool
def search_text_documents(query: str, target_document_id: Optional[str] = None, target_filename: Optional[str] = None) -> str:
    """
    Search through text documents (PDFs, Word docs) using semantic search.
    If 'target_document_id' or 'target_filename' is provided, it ONLY searches that specific file. Use this if the user has selected a specific source.
    """
    try:
        # Generate embedding for the query
        mgr = get_rag_manager()
        embedding = mgr.processor.embeddings.embed_query(query)
        
        # Search
        results = mgr.search_documents(
            query_embedding=embedding,
            match_count=5,
            target_document_id=target_document_id,
            target_filename=target_filename
        )
        
        if not results:
            return "No relevant text documents found."
        
        # Format results
        formatted_results = "Found the following relevant information:\n\n"
        for i, result in enumerate(results, 1):
            formatted_results += f"{i}. {result.get('content', '')}\n"
            formatted_results += f"   Source: {result.get('metadata', {}).get('source', 'Unknown')}\n\n"
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return f"Error searching documents: {str(e)}"

@tool
def query_data(sql_query: str) -> str:
    """
    Execute SQL queries against structured data (Excel/CSV files).
    Use this when you need to:
    - Analyze data from Excel spreadsheets or CSV files
    - Perform aggregations, filtering, or sorting
    - Join data from multiple sheets/files
    
    Example queries:
    - SELECT * FROM sales_data WHERE amount > 1000;
    - SELECT product, SUM(quantity) FROM inventory GROUP BY product;
    - SELECT * FROM employees WHERE department = 'Engineering';
    """
    try:
        mgr = get_rag_manager()
        results, success, error = mgr.query_structured_data(sql_query)
        
        if not success:
            return f"Query failed: {error}"
        
        if not results:
            return (
                "Query executed successfully but returned 0 rows.\n"
                "SUGGESTION: The data might not match your exact filter.\n"
                "- Try checking the schema again with `get_data_schema` to verify column names and example values.\n"
                "- Try a broader query (e.g., using `LIKE` or removing WHERE clauses) to explore the data.\n"
                "- Check for case sensitivity or extra whitespace in string comparisons."
            )
        
        # Format results as readable text
        formatted = "Query Results:\n"
        formatted += json.dumps(results, indent=2, default=str)
        
        logger.info("\n" + "="*50)
        logger.info(f"⚡ [AGENT SQL] Executed Query: {sql_query}")
        logger.info(f"📊 [AGENT SQL] Result: {formatted}")
        logger.info("="*50 + "\n")
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error querying data: {str(e)}")
        return f"Error querying data: {str(e)}"

@tool
def get_data_schema() -> str:
    """
    Get information about available structured data tables (from Excel/CSV files).
    Shows table names, columns, row counts, and data types.
    Use this first to understand what data is available before writing SQL queries.
    """
    try:
        mgr = get_rag_manager()
        schema = mgr.get_data_context()
        
        logger.info("\n" + "="*50)
        logger.info("📋 [AGENT SCHEMA] Schema Requested")
        logger.info(f"content: {schema[:500]}..." if schema else "No schema found")
        logger.info("="*50 + "\n")
        
        return schema if schema else "No structured data tables are currently loaded."
    except Exception as e:
        logger.error(f"Error getting schema: {str(e)}")
        return f"Error retrieving schema: {str(e)}"

@tool
async def consult_specialist(agent_name: str, question: str) -> str:
    """
    Consult a specialist agent for expert advice on a specific topic.
    Use this when you need expertise in a specific domain (e.g., "Legal Expert", "Financial Analyst").
    You must provide the exact name of the agent and the specific question you want to ask.
    """
    from agent_service import get_agent_config_by_id
    from deepagents import create_deep_agent
    from database import supabase # To look up ID by name if needed

    try:
        logger.info(f"Consulting specialist: {agent_name} with question: {question}")
        
        # 1. Resolve Agent ID from Name (if name is passed)
        # We try to match name to an agent in the DB
        agent_config = None
        
        # Try fetching all agents to find a match
        # ( optimization: we could cache this map)
        res = supabase.table("agents").select("id, name").execute()
        target_id = None
        if res.data:
            for ag in res.data:
                if ag["name"].lower().strip() == agent_name.lower().strip():
                    target_id = ag["id"]
                    break
        
        if not target_id:
            # Fallback: maybe the user passed the ID directly?
             agent_config = get_agent_config_by_id(agent_name)
             if not agent_config:
                return f"Error: Specialist '{agent_name}' not found. Please verify the agent name."
        else:
            agent_config = get_agent_config_by_id(target_id)

        if not agent_config:
             return f"Error: Configuration for specialist '{agent_name}' could not be loaded."

        # 2. Create the Specialist Agent
        # Give the specialist standard tools + RAG (but not recursive consult_specialist to avoid loops for now)
        specialist_tools = [internet_search, query_data, get_data_schema, search_text_documents]
        
        # We add a specific instruction to the system prompt
        specialist_prompt = f"""You are {agent_config.name}, a specialist AI assistant.
Description: {agent_config.description}

{agent_config.instructions}

You are being consulted by the Project Manager to answer a specific question.
Answer concisely and professionally. Focus ONLY on your domain expertise.
"""
        
        agent = create_deep_agent(
            tools=specialist_tools,
            system_prompt=specialist_prompt,
            model=agent_config.model
        )
        
        # 3. Ask the question
        # We invoke the agent
        logger.info(f"Invoking specialist {agent_config.name}...")
        
        # Add tracing for specialist
        from dependencies import get_langfuse_callback
        callbacks = get_langfuse_callback() # Specialist call inherits trace? Or new trace? Let's generic for now.
        
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]},
            config={"callbacks": callbacks} if callbacks else {}
        )
        
        # 4. Extract Answer
        messages = result.get("messages", [])
        if messages:
             last_msg = messages[-1]
             if hasattr(last_msg, 'content'):
                 return f"Response from {agent_config.name}:\n{last_msg.content}"
        
        return f"Specialist {agent_config.name} did not provide a clear response."

    except Exception as e:
        logger.error(f"Error consulting specialist: {str(e)}", exc_info=True)
        return f"Error gathering advice from specialist: {str(e)}"
