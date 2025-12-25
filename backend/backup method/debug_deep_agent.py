import asyncio
import logging
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from deep_agent_manager import run_deep_agent_workflow

async def main():
    logging.basicConfig(level=logging.INFO)
    user_message = "extract the Total Qty of ARDA that is needed in 2026"
    # For testing, we might need some context or mock it
    knowledge_context = "This is a test context."
    
    print("Starting Deep Agent Workflow...")
    try:
        result = await run_deep_agent_workflow(user_message, knowledge_context)
        print("\n--- FINAL OUTPUT ---")
        print(result.get("output", "No output found"))
        print("---------------------")
    except Exception as e:
        print(f"\nCaught Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
