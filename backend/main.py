import os
import shutil
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username == "ken" and password == "1":
        return {"access_token": "mock_jwt_token_for_ken"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    if token == "mock_jwt_token_for_ken":
        return "ken"
    raise HTTPException(status_code=401, detail="Invalid auth credentials")

STORAGE_DIR = "storage"

@app.get("/api/sync/list")
def list_cloud_saves(current_user: str = Depends(get_current_user)):
    folder_id = "5" if current_user == "ken" else str(current_user)
    user_dir = f"{STORAGE_DIR}/{folder_id}"
    
    apps = []
    if os.path.exists(user_dir):
        for f in os.listdir(user_dir):
            if f.endswith(".zip"):
                apps.append(f[:-4])
                
    return {"cloud_apps": apps}

@app.post("/upload")
async def upload_file(
    user_id: str = Form(...),
    app_name: str = Form(...),
    file: UploadFile = File(...)
):
    user_dir = f"{STORAGE_DIR}/{user_id}"
    os.makedirs(user_dir, exist_ok=True)
    
    saved_path = f"{user_dir}/{app_name}.zip"
    
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"message": "Upload successful", "path": saved_path}

@app.get("/download")
def download_save(user_id: str, app_name: str):
    # Construct the path
    # "ken" maps to "5" in the database, so we handle that hardcoded ID here in the mock
    folder_id = "5" if user_id == "ken" else str(user_id)
    file_path = os.path.join(STORAGE_DIR, folder_id, f"{app_name}.zip")
    
    # DEBUG PRINTS - VERY IMPORTANT
    print(f"--- DEBUG DOWNLOAD REQUEST ---")
    print(f"Requested user_id: '{user_id}'")
    print(f"Requested app_name: '{app_name}'")
    print(f"Looking for file at EXACT path: '{file_path}'")
    print(f"Does it exist? {os.path.exists(file_path)}")
    print(f"------------------------------")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(file_path)
