import os
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import google.generativeai as genai
from app.api.dependencies import get_current_user
from app.models.user import User
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.models.game_cache import GamePathCache, GameAlias
router = APIRouter()

# Configure the Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview')

class AILookupRequest(BaseModel):
    app_name: str
    os_platform: str = "Windows"

@router.post("/find-path")
async def find_path(
    request: AILookupRequest, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail={"error": "API Key Missing", "message": "Please add your GEMINI_API_KEY to the backend/.env file and restart the server!"}
        )

    user_input_lower = request.app_name.lower().strip()
    
    # --- Cache Hit Strategy ---
    alias_query = await db.execute(select(GameAlias).where(GameAlias.user_input == user_input_lower))
    alias = alias_query.scalars().first()
    
    if alias:
        game_query = await db.execute(select(GamePathCache).where(GamePathCache.id == alias.game_id))
        game = game_query.scalars().first()
        if game:
            return {
                "status": "success",
                "official_name": game.official_name,
                "path": game.default_path,
                "cached": True # optional debug flag
            }

    # --- Cache Miss Fallback (Gemini) ---
    prompt = f"""You are a PC gaming database expert. The user is looking for the default '{request.os_platform}' save game path for the input: '{request.app_name}'.
Task 1: Normalize the input to the official game name (fix typos, expand abbreviations like 'pvz' to 'Plants vs. Zombies'). If the input is complete gibberish, set status to 'error'.
Task 2: Find the default save directory. You MUST use standard Windows environment variables (e.g., %USERPROFILE%, %APPDATA%, %LOCALAPPDATA%, %PUBLIC%). Escape backslashes as \\\\.
Respond ONLY with a raw JSON object (NO markdown tags like ```json). Format:
Success: {{"status": "success", "official_name": "...", "path": "..."}}
Error: {{"status": "error", "message": "Could not recognize the game."}}"""

    try:
        response = await model.generate_content_async(prompt)
        text = response.text
        
        # Clean the response.text by stripping any ```json and ``` markers
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        parsed_data = json.loads(text)
        
        # --- Save to Cache ---
        if parsed_data.get("status") == "success":
            official_name = parsed_data.get("official_name")
            path = parsed_data.get("path")
            
            if official_name and path:
                # 1. Ensure GamePathCache exists
                game_query = await db.execute(select(GamePathCache).where(GamePathCache.official_name == official_name))
                game = game_query.scalars().first()
                
                if not game:
                    game = GamePathCache(official_name=official_name, default_path=path)
                    db.add(game)
                    await db.flush() # Get the new ID
                
                # 2. Add GameAlias
                alias_query = await db.execute(select(GameAlias).where(GameAlias.user_input == user_input_lower))
                existing_alias = alias_query.scalars().first()
                
                if not existing_alias:
                    new_alias = GameAlias(user_input=user_input_lower, game_id=game.id)
                    db.add(new_alias)
                
                await db.commit()
                
        return parsed_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "JSON parse error or API failure", "message": str(e)}
        )
