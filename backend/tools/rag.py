from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_ollama import OllamaEmbeddings
from database import supabase
import logging

logger = logging.getLogger(__name__)

# Re-use the same embedding model
embeddings_model = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

class KnowledgeBaseInput(BaseModel):
    query: str = Field(description="The question or topic to search for in the knowledge base.")

class KnowledgeBaseTool(BaseTool):
    name: str = "retrieve_knowledge"
    description: str = (
        "Useful for retrieving specific information, documents, or context from the project's knowledge base. "
        "Use this whenever the user asks a question about the project, specifications, contracts, or uploaded files. "
        "Do not use this for general knowledge questions (e.g. 'what is the capital of France')."
    )
    args_schema: Type[BaseModel] = KnowledgeBaseInput

    def _run(self, query: str) -> str:
        """Execute the search."""
        logger.info(f"RAG Tool invoked with query: {query}")
        
        try:
            # 1. Embed the query
            query_vector = embeddings_model.embed_query(query)
            
            # 2. Call Supabase RPC
            response = supabase.rpc(
                "match_documents",
                {
                    "query_embedding": query_vector,
                    "match_threshold": 0.5, # Adjust based on testing
                    "match_count": 5
                }
            ).execute()
            
            if not response.data:
                return "No relevant documents found in the knowledge base."
                
            # 3. Format result
            results = []
            for item in response.data:
                source = item['metadata'].get('source', 'Unknown File')
                content = item['content']
                similarity = item.get('similarity', 0)
                results.append(f"--- Source: {source} (Confidence: {similarity:.2f}) ---\n{content}\n")
                
            return "\n".join(results)
            
        except Exception as e:
            logger.error(f"Error in KnowledgeBaseTool: {e}")
            return f"Error retrieving information: {str(e)}"

    async def _arun(self, query: str) -> str:
        """Async implementation (optional but good practice)."""
        # For simplicity, calling sync implementation if asyncio complications arise, 
        # but supabase client is sync by default unless configured otherwise.
        # Ideally we'd use run_in_executor or async supabase client.
        return self._run(query)
