import os
import hashlib
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.models.app_data import AppData

async def process_file_upload(db: AsyncSession, user: User, app_name: str, file: UploadFile) -> AppData:
    """Save physical file and create/update AppData metadata record."""
    # Ensure a directory exists at backend/storage/{user.id}/
    storage_dir = os.path.join("storage", str(user.id))
    os.makedirs(storage_dir, exist_ok=True)
    
    # Save the physical file
    cloud_path = os.path.join(storage_dir, f"{app_name}.zip")
    
    md5_hash = hashlib.md5()
    file_size = 0
    
    # Write file and calculate hash in chunks
    # Note: Replace with AIOFiles in a high-concurrency production env
    with open(cloud_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)
            md5_hash.update(chunk)
            file_size += len(chunk)
            
    checksum = md5_hash.hexdigest()
    
    # Query AppData for this user.id and app_name
    stmt = select(AppData).where(AppData.user_id == user.id, AppData.app_name == app_name)
    result = await db.execute(stmt)
    app_data = result.scalars().first()
    
    if app_data:
        # Update existing record
        app_data.checksum = checksum
        app_data.file_size = file_size
        # updated_at will auto-update in DB
    else:
        # Create new record
        app_data = AppData(
            user_id=user.id,
            app_name=app_name,
            cloud_path=cloud_path,
            checksum=checksum,
            file_size=file_size
        )
        db.add(app_data)
        
    await db.commit()
    await db.refresh(app_data)
    
    return app_data
