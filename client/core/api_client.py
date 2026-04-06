import requests
import shutil
import tempfile
import os

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

    def upload_save(self, app_name: str, zip_file_path: str):
        url = f"{self.base_url}/api/sync/upload"
        data = {"app_name": app_name}
        headers = {}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
            
        try:
            with open(zip_file_path, "rb") as f:
                files = {"file": f}
                response = requests.post(url, data=data, files=files, headers=headers)
            
            if response.status_code == 200:
                return True
            else:
                print(f"Upload failed: HTTP {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False

    def download_save(self, app_name: str, extract_to_path: str) -> bool:
        url = f"{self.base_url}/api/sync/download/{app_name}"
        headers = {}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"

        try:
            response = requests.get(url, headers=headers, stream=True)
            if response.status_code == 200:
                temp_zip_path = tempfile.mktemp(suffix=".zip")
                with open(temp_zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                shutil.unpack_archive(temp_zip_path, extract_to_path)
                if os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)
                return True
            else:
                print(f"Download failed: HTTP {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False

    def get_save_info(self, app_name: str) -> dict:
        url = f"{self.base_url}/api/sync/info/{app_name}"
        headers = {}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"exists": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            print(f"Error getting save info: {e}")
            return {"exists": False, "error": str(e)}
