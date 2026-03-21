from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """Create a new user with a hashed password after ensuring uniqueness."""
    # Check if a user with this username already exists
    stmt = select(User).where(User.username == user_in.username)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Hash the password and create new User instance
    hashed_pass = get_password_hash(user_in.password)
    new_user = User(
        username=user_in.username,
        hashed_password=hashed_pass
    )
    
    # Add, commit, and refresh to get assigned DB ID
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """Check credentials matching a stored user."""
    # Fetch user by username
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        return None
    
    # Verify the provided password matches the hash
    if not verify_password(password, user.hashed_password):
        return None
        
    return user
