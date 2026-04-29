import os
from datetime import datetime, timezone
import aiofiles

async def log_audit(user_id: int, action: str, details: str):
    """
    Append an audit log event to the user's isolated text file.
    Does not block the main thread and silently fails if directory doesn't exist yet.
    """
    storage_dir = f"storage/{user_id}"
    log_path = os.path.join(storage_dir, "audit_log.txt")
    
    if not os.path.exists(storage_dir):
        return
        
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    log_line = f"[{now}] [{action}] {details}\n"
    
    try:
        # We use aiofiles to append asynchronously to avoid blocking
        async with aiofiles.open(log_path, mode='a', encoding='utf-8') as f:
            await f.write(log_line)
    except Exception as e:
        print(f"Failed to write audit log: {e}")
