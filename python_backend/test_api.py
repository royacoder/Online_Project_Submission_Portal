import requests

API_URL = "http://127.0.0.1:5000/api"

def test_login():
    session = requests.Session()
    data = {
        'email': 'admin@ortal.com',
        'password': 'admin23'
    }
    
    # Login
    print("Attempting login...")
    r = session.post(f"{API_URL}?action=login", data=data)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    
    if r.status_code == 200 and r.json().get('success'):
        # Check session
        print("\nChecking session...")
        r2 = session.get(f"{API_URL}?action=getSession")
        print(f"Session Response: {r2.text}")

if __name__ == "__main__":
    test_login()
