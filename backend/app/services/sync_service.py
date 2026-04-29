import os
import hashlib
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.models.app_data import AppData

import shutil
from datetime import datetime, timezone

async def process_file_upload(db: AsyncSession, user: User, app_name: str, device_name: str, file: UploadFile, sha256_checksum: str = None) -> AppData:
    """Save physical file and create/update AppData metadata record with rolling backup."""
    storage_dir = f"storage/{user.id}"
    os.makedirs(storage_dir, exist_ok=True)
    
    # Use forward slashes explicitly — os.path.join uses backslashes on Windows,
    # which breaks on the Linux server if the path gets stored in the DB.
    cloud_path = f"storage/{user.id}/{app_name}.zip"
    backup_path = f"storage/{user.id}/{app_name}_backup.zip"

    # Query AppData to get the existing record and its timestamp
    stmt = select(AppData).where(AppData.user_id == user.id, AppData.app_name == app_name)
    result = await db.execute(stmt)
    app_data = result.scalars().first()
    
    today = datetime.utcnow().date()
    
    if app_data and os.path.exists(cloud_path):
        if app_data.backup_date != today:
            shutil.copy(cloud_path, backup_path)
            app_data.backup_date = today
    
    server_hash = hashlib.sha256()
    file_size = 0
    
    with open(cloud_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
            server_hash.update(chunk)
            file_size += len(chunk)
            
    computed_checksum = server_hash.hexdigest()
    
    if sha256_checksum and computed_checksum != sha256_checksum:
        # If client provided a hash, ensure it matches the uploaded file
        if os.path.exists(cloud_path):
            os.remove(cloud_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checksum verification failed. The uploaded file may be corrupted."
        )
    
    if app_data:
        app_data.checksum = computed_checksum
        app_data.file_size = file_size
        app_data.updated_at = datetime.now(timezone.utc)
        app_data.last_synced_device = device_name
    else:
        app_data = AppData(
            user_id=user.id,
            app_name=app_name,
            cloud_path=cloud_path,
            checksum=computed_checksum,
            file_size=file_size,
            updated_at=datetime.now(timezone.utc),
            last_synced_device=device_name
        )
        db.add(app_data)
        
    await db.commit()
    await db.refresh(app_data)
    
    return app_data
