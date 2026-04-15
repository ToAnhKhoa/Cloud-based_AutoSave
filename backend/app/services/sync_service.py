import os
import hashlib
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.models.app_data import AppData

import shutil
from datetime import datetime, timezone

async def process_file_upload(db: AsyncSession, user: User, app_name: str, file: UploadFile) -> AppData:
    """Save physical file and create/update AppData metadata record with rolling backup."""
    storage_dir = os.path.join("storage", str(user.id))
    os.makedirs(storage_dir, exist_ok=True)
    
    cloud_path = os.path.join(storage_dir, f"{app_name}.zip")
    backup_path = os.path.join(storage_dir, f"{app_name}_backup.zip")

    # Query AppData to get the existing record and its timestamp
    stmt = select(AppData).where(AppData.user_id == user.id, AppData.app_name == app_name)
    result = await db.execute(stmt)
    app_data = result.scalars().first()
    
    today = datetime.utcnow().date()
    
    if app_data and os.path.exists(cloud_path):
        if app_data.backup_date != today:
            shutil.copy(cloud_path, backup_path)
            app_data.backup_date = today
    
    md5_hash = hashlib.md5()
    file_size = 0
    
    with open(cloud_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
            md5_hash.update(chunk)
            file_size += len(chunk)
            
    checksum = md5_hash.hexdigest()
    
    if app_data:
        app_data.checksum = checksum
        app_data.file_size = file_size
        app_data.updated_at = datetime.now(timezone.utc)
    else:
        app_data = AppData(
            user_id=user.id,
            app_name=app_name,
            cloud_path=cloud_path,
            checksum=checksum,
            file_size=file_size,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(app_data)
        
    await db.commit()
    await db.refresh(app_data)
    
    return app_data
