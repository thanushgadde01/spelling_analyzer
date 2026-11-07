"""Quick test of the analyze-and-save endpoint"""
import requests
import json

# Test data
test_data = {
    "name": "Test User",
    "age": "25",
    "study": "Computer Science",
    "graduated": "no",
    "occupation": "",
    "hobbies": "",
    "goal": "",
    "self_intro": "",
    "text": "I havv a drream to becme a softwre enginear"
}

try:
    response = requests.post(
        'http://localhost:8000/analyze-and-save',
        json=test_data,
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to http://localhost:8000")
    print("Make sure the backend server is running!")
except Exception as e:
    print(f"ERROR: {e}")
