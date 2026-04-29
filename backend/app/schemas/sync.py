from pydantic import BaseModel
from datetime import datetime

class CheckHashRequest(BaseModel):
    app_name: str
    sha256_checksum: str

class SyncRequest(BaseModel):
    app_name: str
    checksum: str
    file_size: int

class SyncResponse(BaseModel):
    message: str
    cloud_path: str
    updated_at: datetime
