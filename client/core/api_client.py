import requests

class APIClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.jwt_token = None

    def login(self, username, password):
        """
        Authenticate with the backend and retrieve a JWT access token.
        Expects a FastAPI OAuth2 Password flow endpoint (form-data).
        
        Returns:
            Tuple[bool, str]: (Success status, Error message if any)
        """
        url = f"{self.base_url}/api/auth/login"
        
        # FastAPI's OAuth2PasswordRequestForm expects form data, not JSON
        data = {
            "username": username,
            "password": password
        }
        
        try:
            # Set a reasonable timeout so the GUI doesn't hang forever
            response = requests.post(url, data=data, timeout=5)
            
            if response.status_code == 200:
                json_data = response.json()
                self.jwt_token = json_data.get("access_token")
                return True, ""
            elif response.status_code == 401:
                return False, "Invalid username or password"
            else:
                return False, f"Login failed: HTTP {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {e}"
