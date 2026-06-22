from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from database import db
from pydantic import BaseModel
import json

router = APIRouter()

class ChatGenerateRequest(BaseModel):
    location: str = "The Lobby"

@router.get("/")
def get_chat_logs(limit: int = 5):
    with db() as conn:
        rows = conn.execute(
            "SELECT id, location, message, participants, created_at FROM hero_chat_logs ORDER BY created_at DESC LIMIT ?", 
            (limit,)
        ).fetchall()
        
    logs = []
    for r in rows:
        try:
            msg_data = json.loads(r["message"])
        except:
            msg_data = []
        logs.append({
            "id": r["id"],
            "location": r["location"],
            "participants": r["participants"],
            "messages": msg_data,
            "created_at": r["created_at"]
        })
    return logs

@router.post("/generate")
def generate_chat(req: ChatGenerateRequest, background_tasks: BackgroundTasks):
    from services.chat_service import generate_hero_chat
    # We could run this in background or synchronously
    res = generate_hero_chat(req.location)
    if res.get("status") == "error":
        raise HTTPException(status_code=500, detail=res.get("message"))
    return {"status": "success", "chat": res}
