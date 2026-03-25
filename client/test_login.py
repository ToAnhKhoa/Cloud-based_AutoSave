import asyncio
import os
import sys

# Ensure the parent directory is in the path so we can import client
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client.core.api_client import APIClient
import requests

def test_backend_running():
    try:
        r = requests.get("http://127.0.0.1:8000/")
        print("Backend is running:", r.status_code)
        return True
    except:
        print("Backend is NOT running.")
        return False

def test_login():
    if not test_backend_running():
        return
    client = APIClient()
    print("Testing with wrong credentials...")
    success, msg = client.login("wronguser", "wrongpassword")
    print(f"Result: success={success}, msg='{msg}'")
    
    print("Testing with valid credentials (if any known)...")
    # We don't have a known user right now, maybe register one?
    try:
        res = requests.post("http://127.0.0.1:8000/api/auth/register", json={
            "username": "testuser",
            "email": "test@test.com",
            "password": "testpassword"
        })
        print("Register result:", res.status_code, res.text)
    except Exception as e:
        print("Could not register user:", e)
        
    print("Testing with correct credentials...")
    success, msg = client.login("testuser", "testpassword")
    print(f"Result: success={success}, msg='{msg}'")

if __name__ == "__main__":
    test_login()
