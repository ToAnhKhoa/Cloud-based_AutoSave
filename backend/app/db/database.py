from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Create the declarative base for models
Base = declarative_base()

# Create the Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for debugging SQL queries
    future=True,
    connect_args={"check_same_thread": False} # Needed for SQLite
)

# Create a sessionmaker for async sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

async def get_db():
    """
    Dependency to provide a database session to FastAPI routes.
    Yields an AsyncSession and ensures it's closed after use.
    """
    async with AsyncSessionLocal() as session:
        yield session
