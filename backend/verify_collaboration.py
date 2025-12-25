import requests
import json
import time

def test_collaboration():
    url = "http://127.0.0.1:8003/api/a2a/collaborate"
    payload = {
        "project_id": "44ab080f-be87-4b03-b6d5-63ec55e61836",
        "agent_ids": ["295aa262-4fb3-4928-9e4a-3e56ad5ad499"],
        "document_ids": ["d3ddd643-4ec2-4b7f-a728-e58a72ad7f93"],
        "message": "extract the Total Qty of ARDA that is needed in 2026",
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Sending request to {url}...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, headers=headers, timeout=180)
        end_time = time.time()
        
        print(f"Response Status: {response.status_code}")
        print(f"Time Taken: {end_time - start_time:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            print("\nFinal Output:")
            print(result.get("output"))
            
            output = result.get("output", "")
            if "583" in output:
                print("\n✅ VERIFICATION SUCCESSFUL: Found '583' in output.")
            else:
                print("\n❌ VERIFICATION FAILED: '583' not found in output.")
                
            # print("\nFull Result:")
            # print(json.dumps(result, indent=2))
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_collaboration()
