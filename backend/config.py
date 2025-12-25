"""
Configuration and constants for the AI PM Buddy backend.
"""

# LLM Configuration
DEFAULT_MODEL = "qwen3:latest"
OLLAMA_TIMEOUT = 120.0
OLLAMA_BASE_URL = "http://localhost:11434"

# Context and History Limits
MAX_CONTEXT_LENGTH = 2000
MAX_HISTORY_MESSAGES = 10
MAX_SESSIONS_LIMIT = 50

# File Operations
MAX_FILE_DELETE_RETRIES = 3
FILE_DELETE_RETRY_DELAY = 0.5

# CORS Configuration
CORS_ORIGINS = ["*"]  # Relaxed for debugging, tighten for production
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]
