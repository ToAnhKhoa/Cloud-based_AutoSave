from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Application core settings using Pydantic v2 BaseSettings.
    Values can be overridden by a .env file or environment variables.
    """
    PROJECT_NAME: str = "Cloud Save System API"
    
    # Security / Auth
    SECRET_KEY: str = Field(..., description="Secret key for JWT generation")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instantiate settings to be used throughout the application
settings = Settings()
