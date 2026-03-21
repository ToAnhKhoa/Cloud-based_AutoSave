import asyncio
import os
from app.db.database import engine, Base

# CRITICAL: Import models to register them with Base.metadata
from app.models.user import User
from app.models.app_data import AppData

async def create_tables():
    """Create all tables stored in this metadata."""
    print("Initializing SQLite database and creating tables...")
    async with engine.begin() as conn:
        # Create all tables explicitly defined via Base
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialization complete! Tables created successfully.")

if __name__ == "__main__":
    # Ensure the directory exists if using relative SQLite paths
    # database_url is something like sqlite+aiosqlite:///./app.db
    # It creates app.db in the current working directory.
    
    # Run the asyncio event loop
    asyncio.run(create_tables())
