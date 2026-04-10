import requests
import shutil
import tempfile
import os

class SessionExpiredError(Exception):
    """Raised when the backend returns a 401 Unauthorized, indicating JWT expiration."""
    pass

class APIClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token = None

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        response = requests.request(method, url, headers=headers, **kwargs)
        
        if response.status_code == 401:
            self.token = None # Clear invalid token immediately
            raise SessionExpiredError("Session has expired.")
            
        return response

    def login(self, username, password) -> bool:
        """
        Authenticate with the backend and retrieve a JWT access token.
        Expects a FastAPI OAuth2 Password flow endpoint (form-data).
        
        Returns:
            bool: Success status
        """
        # FastAPI's OAuth2PasswordRequestForm expects form data, not JSON
        data = {
            "username": username,
            "password": password
        }
        
        try:
            # We explicitly bypass _make_request here because login triggers initial auth creation natively
            response = requests.post(f"{self.base_url}/api/auth/login", data=data, timeout=5)
            
            if response.status_code == 200:
                json_data = response.json()
                self.token = json_data.get("access_token")
                return True
            else:
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            return False

    def register(self, username, password) -> tuple[bool, str]:
        """Register a new user account."""
        json_data = {
            "username": username,
            "password": password
        }
        try:
            response = requests.post(f"{self.base_url}/api/auth/register", json=json_data, timeout=5)
            if response.status_code in (200, 201):
                return True, "Registration successful! You can now log in."
            else:
                try:
                    error_msg = response.json().get("detail", "Registration failed.")
                except ValueError:
                    error_msg = f"HTTP {response.status_code}"
                return False, error_msg
        except requests.exceptions.RequestException as e:
            print(f"Registration connection error: {e}")
            return False, "Connection error to server."

    def upload_save(self, app_name: str, zip_file_path: str):
        if not self.token:
            return False
            
        data = {"app_name": app_name}
        try:
            with open(zip_file_path, "rb") as f:
                files = {"file": f}
                response = self._make_request("POST", "/api/sync/upload", data=data, files=files)
            
            if response.status_code == 200:
                return True
            else:
                print(f"Upload failed: HTTP {response.status_code} - {response.text}")
                return False
        except SessionExpiredError:
            raise
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False

    def download_save(self, app_name: str, extract_to_path: str) -> bool:
        if not self.token:
            return False

        try:
            response = self._make_request("GET", f"/api/sync/download/{app_name}", stream=True)
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
        except SessionExpiredError:
            raise
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False

    def get_save_info(self, app_name: str) -> dict:
        if not self.token:
            return {"exists": False, "error": "Not authenticated"}

        try:
            response = self._make_request("GET", f"/api/sync/info/{app_name}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"exists": False, "error": f"HTTP {response.status_code}"}
        except SessionExpiredError:
            raise
        except Exception as e:
            print(f"Error getting save info: {e}")
            return {"exists": False, "error": str(e)}

    def ask_ai_for_path(self, app_name: str) -> dict | None:
        if not self.token:
            return {"status": "error", "message": "Not authenticated"}
        try:
            response = self._make_request("POST", "/api/ai/find-path", json={"app_name": app_name, "os_platform": "Windows"}, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": f"HTTP {response.status_code} - {response.text}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_cloud_apps(self) -> list:
        if not self.token:
            return []
            
        try:
            response = self._make_request("GET", "/api/sync/list", timeout=5)
            if response.status_code == 200:
                return response.json().get("cloud_apps", [])
        except SessionExpiredError:
            raise
        except Exception as e:
            print(f"Error getting cloud apps: {e}")
        return []
