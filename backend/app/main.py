from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, sync
from app.models import User, AppData

app = FastAPI(
    title="Cloud Save System API",
    description="Centralized Cloud Solution for Managing Application Data API",
    version="2.0.0"
)

# Allow CORS for the desktop client and any frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure routing explicitly
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(sync.router, prefix="/api/sync", tags=["Synchronization"])

@app.get("/")
async def root():
    """Simple root health check endpoint."""
    return {"message": "Welcome to Cloud Save API v2"}
