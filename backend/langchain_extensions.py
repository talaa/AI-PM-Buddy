# langchain_extensions.py
# Advanced LangChain features for your AI PM Buddy

from typing import List, Dict, Any, Optional
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.tools import Tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain.memory.buffer import ConversationBufferMemory
from langchain.memory.summary import ConversationSummaryMemory
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# 1. RAG (Retrieval Augmented Generation)
# ============================================================================

class RAGManager:
    """Manage RAG functionality for knowledge bases"""
    
    def __init__(self, model_name: str = "qwen3:latest", embedding_model: str = "nomic-embed-text"):
        self.llm = ChatOllama(model=model_name, temperature=0.3)
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.vectorstores: Dict[str, Chroma] = {}
    
    def create_knowledge_base(self, agent_id: str, documents: List[str], metadata: List[Dict] = None):
        """Create a vector store from documents"""
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        chunks = text_splitter.create_documents(
            documents,
            metadatas=metadata if metadata else [{"source": f"doc_{i}"} for i in range(len(documents))]
        )
        
        # Create vector store
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            collection_name=f"agent_{agent_id}"
        )
        
        self.vectorstores[agent_id] = vectorstore
        logger.info(f"Created knowledge base for agent {agent_id} with {len(chunks)} chunks")
        
        return vectorstore
    
    def get_rag_chain(self, agent_id: str, system_prompt: str = None):
        """Create a RAG chain for an agent"""
        
        if agent_id not in self.vectorstores:
            raise ValueError(f"No knowledge base found for agent {agent_id}")
        
        vectorstore = self.vectorstores[agent_id]
        
        # Create retrieval QA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(
                search_kwargs={"k": 3}  # Return top 3 relevant chunks
            ),
            return_source_documents=True
        )
        
        return qa_chain
    
    def query_knowledge_base(self, agent_id: str, query: str) -> Dict[str, Any]:
        """Query the knowledge base"""
        
        if agent_id not in self.vectorstores:
            return {"answer": "No knowledge base available", "sources": []}
        
        chain = self.get_rag_chain(agent_id)
        result = chain.invoke({"query": query})
        
        return {
            "answer": result["result"],
            "sources": [doc.metadata for doc in result["source_documents"]]
        }


# ============================================================================
# 2. Tools & Function Calling
# ============================================================================

class ToolManager:
    """Manage custom tools for agents"""
    
    @staticmethod
    def create_pm_tools() -> List[Tool]:
        """Create PM-specific tools"""
        
        def estimate_story_points(description: str) -> str:
            """Estimate story points based on description"""
            word_count = len(description.split())
            if word_count < 50:
                return "Estimated: 1-2 story points (Simple task)"
            elif word_count < 150:
                return "Estimated: 3-5 story points (Medium complexity)"
            else:
                return "Estimated: 8-13 story points (Complex task)"
        
        def calculate_sprint_velocity(completed_points: str) -> str:
            """Calculate average sprint velocity"""
            try:
                points = [int(x.strip()) for x in completed_points.split(",")]
                avg = sum(points) / len(points)
                return f"Average velocity: {avg:.1f} points per sprint"
            except:
                return "Please provide points as comma-separated numbers"
        
        def prioritize_tasks(tasks: str) -> str:
            """Prioritize tasks using MoSCoW method"""
            return """MoSCoW Prioritization Framework:
            
Must Have: Critical features/fixes blocking release
Should Have: Important but not critical
Could Have: Desirable but not necessary
Won't Have: Lowest priority or future consideration

Analyze each task against business value, urgency, and dependencies."""
        
        return [
            Tool(
                name="estimate_story_points",
                func=estimate_story_points,
                description="Estimate story points for a user story based on its description. Input should be the story description."
            ),
            Tool(
                name="calculate_sprint_velocity",
                func=calculate_sprint_velocity,
                description="Calculate average sprint velocity. Input should be comma-separated story points from recent sprints (e.g., '21,19,23,20')."
            ),
            Tool(
                name="prioritize_tasks",
                func=prioritize_tasks,
                description="Get guidance on prioritizing tasks using the MoSCoW method. Input should be 'prioritize' or a list of tasks."
            )
        ]
    
    @staticmethod
    def create_agent_with_tools(llm: ChatOllama, tools: List[Tool], system_prompt: str) -> AgentExecutor:
        """Create an agent with tools"""
        
        prompt = PromptTemplate.from_template(
            f"""{system_prompt}

You have access to the following tools:

{{tools}}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{{tool_names}}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {{input}}
Thought: {{agent_scratchpad}}"""
        )
        
        agent = create_react_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )
        
        return agent_executor


# ============================================================================
# 3. Advanced Memory Management
# ============================================================================

class MemoryManager:
    """Manage conversation memory for agents"""
    
    def __init__(self):
        self.memories: Dict[str, Any] = {}
    
    def get_buffer_memory(self, session_id: str) -> ConversationBufferMemory:
        """Get or create buffer memory for a session"""
        
        key = f"buffer_{session_id}"
        if key not in self.memories:
            self.memories[key] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        
        return self.memories[key]
    
    def get_summary_memory(self, session_id: str, llm: ChatOllama) -> ConversationSummaryMemory:
        """Get or create summary memory for a session"""
        
        key = f"summary_{session_id}"
        if key not in self.memories:
            self.memories[key] = ConversationSummaryMemory(
                llm=llm,
                memory_key="chat_history",
                return_messages=True
            )
        
        return self.memories[key]
    
    def clear_memory(self, session_id: str):
        """Clear memory for a session"""
        keys_to_remove = [k for k in self.memories.keys() if session_id in k]
        for key in keys_to_remove:
            del self.memories[key]
        
        logger.info(f"Cleared {len(keys_to_remove)} memory instances for session {session_id}")


# ============================================================================
# 4. Chain Orchestration
# ============================================================================

class ChainOrchestrator:
    """Orchestrate complex multi-step chains"""
    
    def __init__(self, llm: ChatOllama):
        self.llm = llm
    
    def create_sequential_chain(self, steps: List[Dict[str, str]]) -> Any:
        """Create a sequential chain with multiple steps"""
        # This is a simplified example
        # In production, use LangChain's SequentialChain or custom logic
        
        from langchain.chains import LLMChain
        
        chains = []
        for step in steps:
            prompt = PromptTemplate(
                input_variables=step.get("input_variables", ["input"]),
                template=step["template"]
            )
            chains.append(LLMChain(llm=self.llm, prompt=prompt))
        
        return chains
    
    def create_routing_chain(self, routes: Dict[str, str]) -> Any:
        """Create a chain that routes to different sub-chains based on input"""
        # Example: Route to different PM workflows based on query type
        
        routing_prompt = f"""Given the following user query, determine which workflow to use:

Workflows available:
{chr(10).join([f"- {k}: {v}" for k, v in routes.items()])}

Query: {{query}}

Respond with only the workflow name."""
        
        return PromptTemplate(template=routing_prompt, input_variables=["query"])


# ============================================================================
# Example Usage
# ============================================================================

def example_usage():
    """Example of how to use these extensions"""
    
    # 1. RAG Example
    rag_manager = RAGManager()
    documents = [
        "Agile methodology emphasizes iterative development...",
        "Sprint planning involves the entire team...",
        "User stories should follow the INVEST criteria..."
    ]
    rag_manager.create_knowledge_base("agent_123", documents)
    result = rag_manager.query_knowledge_base("agent_123", "What is agile?")
    print(result)
    
    # 2. Tools Example
    llm = ChatOllama(model="qwen3:latest")
    tools = ToolManager.create_pm_tools()
    agent = ToolManager.create_agent_with_tools(
        llm, 
        tools, 
        "You are a PM assistant with access to project management tools."
    )
    
    # 3. Memory Example
    memory_manager = MemoryManager()
    memory = memory_manager.get_buffer_memory("session_456")
    
    print("Extensions ready to use!")


if __name__ == "__main__":
    example_usage()