# test_env.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import uuid
# Load from specific path
#load_dotenv(dotenv_path='.env')
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Supabase Setup
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
print("=== Environment Variables Check ===")
print(f"VITE_SUPABASE_URL: {os.getenv('VITE_SUPABASE_URL')}")
print(f"VITE_SUPABASE_ANON_KEY: {os.getenv('VITE_SUPABASE_ANON_KEY')[:20]}..." if os.getenv('VITE_SUPABASE_ANON_KEY') else "Not found")
print("===================================")

agent_id_str='d1312606-b152-4eb2-9330-546f6258e0d8'
agent_id = uuid.UUID(agent_id_str)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) 

response = supabase.table("agents").select("*").eq("id", agent_id).execute()

#response = supabase.rpc("get_agent_by_id", {"agent_id": agent_id_str}).execute()
print(response)