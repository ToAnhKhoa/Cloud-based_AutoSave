import asyncio
from app.db.database import AsyncSessionLocal
from app.schemas.user import UserCreate
from app.services.auth_service import create_user

async def seed():
    async with AsyncSessionLocal() as db:
        user_in = UserCreate(username="ken", password="1")
        try:
            await create_user(db, user_in)
            print("User 'ken' with password '1' created successfully!")
        except Exception as e:
            print(f"Error (maybe already exists): {e}")

if __name__ == "__main__":
    asyncio.run(seed())
