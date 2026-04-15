from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from fastapi.responses import FileResponse
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.app_data import AppData
from app.schemas.sync import SyncResponse
from app.services import sync_service

router = APIRouter()

@router.get("/status")
async def sync_status(current_user: User = Depends(get_current_user)):
    """Simple protected endpoint to verify the sync service and active user."""
    return {"message": f"Sync service is active for user: {current_user.username}"}

@router.post("/upload", response_model=SyncResponse)
async def upload_sync_data(
    app_name: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload physical app data and update metadata."""
    app_data = await sync_service.process_file_upload(db, current_user, app_name, file)
    
    return SyncResponse(
        message="Successfully synchronized file",
        cloud_path=app_data.cloud_path,
        updated_at=app_data.updated_at
    )

@router.get("/download/{app_name}")
async def download_sync_data(
    app_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download physical app data enforcing ownership."""
    stmt = select(AppData).where(AppData.user_id == current_user.id, AppData.app_name == app_name)
    result = await db.execute(stmt)
    app_data = result.scalars().first()
    
    if not app_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="App data not found for the requested application"
        )
        
    # the frontend client will download the literal .zip file representation
    return FileResponse(path=app_data.cloud_path, filename=f"{app_name}.zip")

@router.get("/info/{app_name}")
async def get_sync_info(
    app_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get metadata about a cloud save."""
    stmt = select(AppData).where(AppData.user_id == current_user.id, AppData.app_name == app_name)
    result = await db.execute(stmt)
    app_data = result.scalars().first()
    
    if not app_data:
        return {"exists": False}
        
    has_backup = app_data.backup_date.isoformat() if app_data.backup_date else None
        
    file_path = app_data.cloud_path
    if os.path.exists(file_path):
        mtime = os.path.getmtime(file_path)
        timestamp_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        size = os.path.getsize(file_path)
        return {"exists": True, "last_modified": timestamp_str, "size_bytes": size, "has_backup": has_backup}
    else:
        return {"exists": False}

@router.get("/list")
async def list_sync_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve a list of all application names bound to the cloud context."""
    stmt = select(AppData.app_name).where(AppData.user_id == current_user.id)
    result = await db.execute(stmt)
    apps = result.scalars().all()
    
    return {"cloud_apps": list(apps)}
