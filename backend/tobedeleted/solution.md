# Fix Guide: ChatPromptTemplate Error & A2A Improvements

## Problem Analysis

### Root Cause
Your error: `"Input to ChatPromptTemplate is missing variables {'history', 'input'}. Expected: ['history', 'input'] Received: ['messages', 'next']"`

This indicates you have a **LangGraph workflow** somewhere that's passing `messages` and `next` variables, but your prompt template expects `history` and `input`. The traceback shows it's failing in `a2a_service.py` which wasn't provided, but the pattern is clear.

---

## Solution 1: Fix the Prompt Template Variables

### Option A: Match Your Graph's State (Recommended if using LangGraph)
```python
# If your LangGraph state uses 'messages' and 'next':
prompt = ChatPromptTemplate.from_messages([
    ("system", system_template),
    MessagesPlaceholder(variable_name="messages"),  # Changed from 'history'
    ("human", "{next}")  # Changed from 'input'
])
```

### Option B: Keep Current Approach (Fix State Instead)
Ensure your graph/workflow passes the correct variables:
```python
# When invoking, use:
response = chain.invoke({
    "input": request.message,        # NOT "next"
    "history": history_messages      # NOT "messages"
})
```

---

## Solution 2: Improved A2A Communication Architecture

The updated code provides three levels of agent communication:

### 1. **Simple Message Queue (Basic A2A)**
```python
# Agent 1 sends message to Agent 2
POST /api/a2a/send
{
    "from_agent_id": "agent-1",
    "to_agent_id": "agent-2", 
    "message": "Please analyze the risks",
    "context": {"project_id": "123"}
}

# Agent 2 retrieves pending messages
GET /api/a2a/messages/agent-2
```

**When to use:** Simple sequential collaboration, no immediate response needed.

### 2. **Collaborative Processing (Medium Complexity)**
```python
POST /api/a2a/collaborate
{
    "agent_id": "project-manager",
    "message": "Evaluate project feasibility",
    "collaborating_agents": ["risk-manager", "tech-lead"],
    "history": [...]
}
```

**When to use:** One agent needs input from multiple agents before responding.

### 3. **Full LangGraph Integration (Advanced)**
For complex multi-agent orchestration with:
- Conditional routing
- Parallel execution
- Dynamic agent selection

---

## Key Improvements Over Original Code

### 1. **Proper Message Conversion**
```python
# Old: Could miss message types
def convert_history_to_messages(history):
    # ...

# New: Handles edge cases
def convert_history_to_messages(history: List[Dict[str, str]]) -> List[BaseMessage]:
    messages = []
    for msg in history:
        role = msg.get('role', 'user').lower()  # Case-insensitive
        content = msg.get('content', '')
        
        if role == 'user':
            messages.append(HumanMessage(content=content))
        # ... handles all cases
    return messages
```

### 2. **Separation of Concerns**
- `agent_service.py`: Agent logic + LLM chains
- `main.py`: API routes + request handling
- A2A functions isolated for testability

### 3. **Message Metadata**
Each A2A message carries:
```python
{
    "from_agent_id": "...",
    "to_agent_id": "...", 
    "message_id": "uuid",           # For tracking
    "timestamp": "...",              # For ordering
    "context": {...}                 # Domain context
}
```

### 4. **Buffer Management**
```python
# In-memory message queue (upgradeable to Redis)
a2a_message_buffer: Dict[str, List[Dict]] = {}

# Clear after retrieval to prevent duplicates
messages = a2a_message_buffer[agent_id]
a2a_message_buffer[agent_id] = []  # Clear
```

---

## Implementation Checklist

- [ ] Add missing imports to `main.py`:
  ```python
  from pydantic import BaseModel
  from typing import Dict, Any
  ```

- [ ] Update `agent_service.py` with new functions
  
- [ ] Update `main.py` with A2A endpoints

- [ ] If you have `a2a_service.py`, replace it with the updated `agent_service.py`

- [ ] Test the basic endpoint:
  ```bash
  curl -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{
      "agent_id": "your-agent-id",
      "message": "Test message",
      "history": []
    }'
  ```

- [ ] Test A2A messaging:
  ```bash
  # Send message
  curl -X POST http://localhost:8000/api/a2a/send \
    -H "Content-Type: application/json" \
    -d '{
      "from_agent_id": "agent-1",
      "to_agent_id": "agent-2",
      "message": "Hello agent 2"
    }'
  
  # Retrieve messages
  curl http://localhost:8000/api/a2a/messages/agent-2
  ```

---

## Future Enhancements

### 1. **Upgrade Message Queue to Redis**
```python
import redis
from typing import Optional

class A2AQueue:
    def __init__(self, redis_url="redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
    
    def send(self, from_id, to_id, message):
        key = f"a2a:{to_id}:messages"
        self.redis.rpush(key, json.dumps({
            "from": from_id,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }))
    
    def get_all(self, agent_id):
        key = f"a2a:{agent_id}:messages"
        messages = self.redis.lrange(key, 0, -1)
        self.redis.delete(key)
        return [json.loads(m) for m in messages]
```

### 2. **Add Request/Response Pattern**
```python
def request_agent_response(from_id, to_id, message) -> str:
    """Synchronous agent-to-agent request"""
    # Send message and wait for response
    # Use Redis Streams or websockets for real-time
```

### 3. **Agent Discovery**
```python
@app.get("/api/a2a/agents")
async def list_available_agents():
    """Discover all agents and their capabilities"""
    response = supabase.table("agents").select("id, name, description, tools").execute()
    return response.data
```

### 4. **Conversation Threading**
```python
# Track related A2A messages
message_envelope = {
    "thread_id": "conv-123",  # Group related messages
    "parent_message_id": "msg-456",  # For replies
    # ...
}
```

---

## Testing A2A Communication

```python
# test_a2a.py
import requests
import json

BASE_URL = "http://localhost:8000"

def test_a2a_flow():
    # 1. Send from Risk Manager to Project Manager
    send_response = requests.post(
        f"{BASE_URL}/api/a2a/send",
        json={
            "from_agent_id": "risk-manager",
            "to_agent_id": "project-manager",
            "message": "Risk assessment complete. Critical issues found.",
            "context": {"severity": "high"}
        }
    )
    print("Send response:", send_response.json())
    
    # 2. Project Manager retrieves messages
    messages = requests.get(
        f"{BASE_URL}/api/a2a/messages/project-manager"
    )
    print("Messages:", messages.json())
    
    # 3. Project Manager processes with collaboration
    collaborate = requests.post(
        f"{BASE_URL}/api/a2a/collaborate",
        json={
            "agent_id": "project-manager",
            "message": "Based on risks, what's our mitigation strategy?",
            "collaborating_agents": ["risk-manager", "tech-lead"]
        }
    )
    print("Collaboration result:", collaborate.json())

if __name__ == "__main__":
    test_a2a_flow()
```

---

## Troubleshooting

### Error: "Variable name expected but got 'input'"
- Make sure you're using MessagesPlaceholder correctly
- Check that your chain invocation passes matching variable names

### A2A Messages Not Being Retrieved
- Verify `agent_id` matches exactly
- Check logs for buffer size: `Buffer size: X`
- Ensure messages aren't being cleared prematurely

### Memory Bloat from Message Buffer
- Upgrade to Redis-based queue
- Add message expiration (TTL)
- Implement periodic cleanup

---

## Architecture Diagram

```
Frontend
   ↓
/api/chat (Single agent)
   ↓
create_langchain_agent → ChatPromptTemplate
   ↓
chain.invoke({input, history})
   ↓
LLM Response

---

/api/a2a/send (Agent-to-Agent)
   ↓
send_message_to_agent()
   ↓
a2a_message_buffer[to_agent_id]
   ↓
/api/a2a/messages/{agent_id}
   ↓
Message Queue

---

/api/a2a/collaborate (Multi-Agent)
   ↓
process_agent_collaboration()
   ↓
[Agent 1 thinks] → [Checks messages from others] → [Response]
   ↓
Return with pending_messages + response
```