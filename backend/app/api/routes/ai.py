import os
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.api.dependencies import get_current_user
from app.models.user import User
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.models.game_cache import GamePathCache, GameAlias

router = APIRouter()

# Use Cloudflare Worker proxy URL if set, otherwise call Gemini directly.
# The Worker forwards requests to generativelanguage.googleapis.com from a
# non-geo-restricted IP, bypassing the East Asia block on the Azure VM.
_raw_endpoint = os.environ.get("GEMINI_API_ENDPOINT", "").strip()
if _raw_endpoint:
    # Ensure it has a scheme
    if not _raw_endpoint.startswith("http"):
        _raw_endpoint = f"https://{_raw_endpoint}"
    GEMINI_BASE_URL = _raw_endpoint.rstrip("/")
else:
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"

GEMINI_MODEL = "gemini-2.5-flash"

async def call_gemini_api(prompt: str) -> str:
    """Make a direct HTTP call to Gemini (or the Cloudflare Worker proxy)."""
    url = f"{GEMINI_BASE_URL}/v1beta/models/{GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


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
                "cached": True
            }

    # --- Cache Miss Fallback (Gemini via proxy) ---
    prompt = f"""You are a PC gaming database expert. The user is looking for the default '{request.os_platform}' save game path for the input: '{request.app_name}'.
Task 1: Normalize the input to the official game name (fix typos, expand abbreviations like 'pvz' to 'Plants vs. Zombies'). If the input is complete gibberish, set status to 'error'.
Task 2: Find the default save directory. You MUST use standard Windows environment variables (e.g., %USERPROFILE%, %APPDATA%, %LOCALAPPDATA%, %PUBLIC%). Escape backslashes as \\\\.
Respond ONLY with a raw JSON object (NO markdown tags like ```json). Format:
Success: {{"status": "success", "official_name": "...", "path": "..."}}
Error: {{"status": "error", "message": "Could not recognize the game."}}"""

    try:
        text = await call_gemini_api(prompt)

        # Strip any accidental markdown code fences
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
                game_query = await db.execute(select(GamePathCache).where(GamePathCache.official_name == official_name))
                game = game_query.scalars().first()

                if not game:
                    game = GamePathCache(official_name=official_name, default_path=path)
                    db.add(game)
                    await db.flush()

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
            detail={"error": "Gemini API call failed", "message": str(e)}
        )
