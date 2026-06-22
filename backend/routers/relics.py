from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.relics_service import get_all_relics, equip_relic, unequip_relic
from database import db

router = APIRouter()

class EquipReq(BaseModel):
    hero_id: int
    relic_id: int

class UnequipReq(BaseModel):
    relic_id: int

@router.get("/")
def list_relics():
    all_relics = get_all_relics()
    equipped = [r for r in all_relics if r["is_equipped_to"]]
    unequipped = [r for r in all_relics if not r["is_equipped_to"]]
    return {"equipped": equipped, "unequipped": unequipped}

@router.post("/equip")
def do_equip(req: EquipReq):
    try:
        return equip_relic(req.hero_id, req.relic_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/unequip")
def do_unequip(req: UnequipReq):
    try:
        return unequip_relic(req.relic_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
