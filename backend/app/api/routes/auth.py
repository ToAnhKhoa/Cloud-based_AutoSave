from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db
from app.schemas.user import UserCreate, UserOut, Token
from app.services import auth_service
from app.core.security import create_access_token

router = APIRouter()

@router.post("/register", response_model=UserOut)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user in the system."""
    user = await auth_service.create_user(db, user_in)
    return user

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Obtain a JWT access token upon successful authentication."""
    user = await auth_service.authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Generate token data
    token = create_access_token(data={"sub": user.username})
    
    return {"access_token": token, "token_type": "bearer"}
