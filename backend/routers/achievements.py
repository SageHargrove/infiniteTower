from fastapi import APIRouter, HTTPException
from database import db
from services.achievement_service import get_achievements_with_progress, claim_achievement
from pydantic import BaseModel

router = APIRouter()


@router.get("/")
def list_achievements():
    with db() as conn:
        return {"achievements": get_achievements_with_progress(conn)}


class ClaimRequest(BaseModel):
    achievement_id: str


@router.post("/claim")
def claim(req: ClaimRequest):
    with db() as conn:
        result = claim_achievement(conn, req.achievement_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
