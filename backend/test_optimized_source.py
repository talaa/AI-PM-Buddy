import requests
import json
import time

def test_selected_source():
    url = "http://127.0.0.1:8000/api/a2a/collaborate" # Assuming default port
    
    # Test Data (replace with actual IDs from the DB if needed)
    project_id = "44ab080f-be87-4b03-b6d5-63ec55e61836"
    doc_id = "d3ddd643-4ec2-4b7f-a728-e58a72ad7f93"
    
    payload = {
        "project_id": project_id,
        "agent_ids": [],
        "document_ids": [doc_id],
        "message": "What is the content of this specific document?",
        "selected_source_id": doc_id
    }
    
    headers = {"Content-Type": "application/json"}
    
    print(f"Sending request with selected_source_id: {doc_id}")
    try:
        start = time.time()
        response = requests.post(url, json=payload, headers=headers, timeout=180)
        end = time.time()
        
        print(f"Status: {response.status_code}")
        print(f"Time: {end-start:.2f}s")
        if response.status_code == 200:
            print("Successfully received response.")
            # print(response.json().get("output"))
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_selected_source()
