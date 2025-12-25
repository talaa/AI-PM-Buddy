"""
Shared dependencies and utilities used across routers.
"""
import logging
from typing import Optional, List, Dict
from langfuse import get_client
from langfuse.langchain import CallbackHandler

# Configure logging
logger = logging.getLogger(__name__)

# Initialize LangFuse
try:
    langfuse = get_client()
    langfuse_handler = CallbackHandler()
    logger.info("✅ LangFuse handler initialized")
except Exception as e:
    logger.warning(f"⚠️ LangFuse not initialized: {e}")
    langfuse_handler = None


def get_langfuse_callback(session_id: Optional[str] = None) -> List[CallbackHandler]:
    """
    Get LangFuse callback handlers for tracing.
    Creates session-specific handlers for collaborative mode to ensure proper trace grouping.
    
    Args:
        session_id: Optional session ID for trace grouping
        
    Returns:
        List of callback handlers (empty if LangFuse not initialized)
    """
    if not langfuse_handler:
        return []
    
    if session_id:
        try:
            # Create session-specific handler for proper trace grouping in multi-agent scenarios
            return [CallbackHandler(session_id=session_id)]
        except Exception as e:
            logger.warning(f"Failed to create session-specific LangFuse handler: {e}")
            return [langfuse_handler]
    
    return [langfuse_handler]


# In-memory message queue for A2A communication (upgradeable to Redis)
# Structure: { to_agent_id: [ {from, message, timestamp, ...} ] }
a2a_message_buffer: Dict[str, List[Dict]] = {}
