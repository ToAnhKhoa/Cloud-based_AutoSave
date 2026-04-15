from fastapi import APIRouter, APIRouter, Depends, HTTPException, status
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.app_data import AppData

router = APIRouter()

@router.delete("/{app_name}")
async def delete_app(
    app_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AppData).where(AppData.user_id == current_user.id, AppData.app_name == app_name)
    result = await db.execute(stmt)
    app = result.scalars().first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App data not found"
        )
        
    cloud_path = app.cloud_path
    
    if cloud_path and os.path.exists(cloud_path):
        os.remove(cloud_path)
        
    await db.delete(app)
    await db.commit()
    
    return {"status": "success", "message": f"Deleted {app_name} and its cloud backup."}

@router.post("/{app_name}/rollback")
async def rollback_app(
    app_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(AppData).where(AppData.user_id == current_user.id, AppData.app_name == app_name)
        result = await db.execute(stmt)
        app_data = result.scalars().first()

        if not app_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="App data not found"
            )

        storage_dir = os.path.join("storage", str(current_user.id))
        cloud_path = os.path.join(storage_dir, f"{app_name}.zip")
        backup_path = os.path.join(storage_dir, f"{app_name}_backup.zip")

        if not os.path.exists(backup_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No backup found to rollback to"
            )

        if os.path.exists(cloud_path):
            os.remove(cloud_path)
        
        os.rename(backup_path, cloud_path)

        app_data.backup_date = None
        
        await db.commit()
        
        return {"status": "success", "message": f"Successfully rolled back {app_name} to previous version."}
    except Exception as e:
        import traceback
        err_str = traceback.format_exc()
        raise HTTPException(status_code=500, detail=err_str)
