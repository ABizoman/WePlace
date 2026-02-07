import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_update():
    place_id = 1
    
    print(f"--- 1. Testing Valid Update for Place ID {place_id} ---")
    payload = {
        "name": "Updated Valid Name",
        "description": "This is a new description for the place."
    }
    
    try:
        response = requests.post(f"{BASE_URL}/places/{place_id}/update", json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response:", json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")

    print("\n--- 2. Testing Invalid Update (LLM Rejection Simulation) ---")
    bad_payload = {
        "name": "Fake Scam Business",
        "description": "Trying to trick the system."
    }
    
    try:
        response = requests.post(f"{BASE_URL}/places/{place_id}/update", json=bad_payload)
        print(f"Status Code: {response.status_code}")
        print("Response:", json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_update()
