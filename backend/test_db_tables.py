from database import supabase
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_db():
    if not supabase:
        logger.error("Supabase client not initialized")
        return

    print("Testing 'chat_sessions' table...")
    try:
        # Try to insert a dummy session
        dummy_project_id = "00000000-0000-0000-0000-000000000000" # Invalid UUID might fail FK constraint if not careful.
        # Check if we can list first
        resp = supabase.table("chat_sessions").select("*").limit(1).execute()
        print(f"Select 'chat_sessions' success. Count: {len(resp.data)}")
        
    except Exception as e:
        print(f"Error accessing 'chat_sessions': {e}")

    print("\nTesting 'chat_messages' table...")
    try:
        resp = supabase.table("chat_messages").select("*").limit(1).execute()
        print(f"Select 'chat_messages' success. Count: {len(resp.data)}")
    except Exception as e:
        print(f"Error accessing 'chat_messages': {e}")

if __name__ == "__main__":
    test_db()
