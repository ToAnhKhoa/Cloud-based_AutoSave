from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt, JWTError

from app.db.database import AsyncSessionLocal
from app.models.user import User
from app.core.config import settings

# Define the OAuth2 scheme (where the client can obtain the token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_db():
    """
    Dependency to provide a database session to FastAPI routes.
    Yields an AsyncSession and ensures it's closed in a finally block.
    """
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    """
    Dependency to get the currently authenticated user from the JWT token.
    Raises a 401 error if the token is invalid or the user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str | None = payload.get("sub")
        
        if username is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
        
    # Fetch the user from the database
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
        
    return user
