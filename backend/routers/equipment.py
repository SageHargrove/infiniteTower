from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.equipment_service import get_all_equipment, craft_equipment, equip_item, unequip_item, scrap_equipment
from database import db

router = APIRouter()

class CraftReq(BaseModel):
    crafter_id: int

class EquipReq(BaseModel):
    hero_id: int
    equipment_id: int

class UnequipReq(BaseModel):
    equipment_id: int

class ScrapReq(BaseModel):
    equipment_id: int

@router.get("/")
def list_equipment():
    from services.equipment_service import get_all_equipment, get_hero_equipment
    all_eq = get_all_equipment()
    equipped = [e for e in all_eq if e["is_equipped_to"]]
    
    with db() as conn:
        rows = conn.execute("SELECT * FROM equipment WHERE is_equipped_to IS NULL ORDER BY created_at DESC").fetchall()
        unequipped = [dict(r) for r in rows]
        
    return {"equipped": equipped, "unequipped": unequipped}

@router.post("/craft")
def do_craft(req: CraftReq):
    try:
        return craft_equipment(req.crafter_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/equip")
def do_equip(req: EquipReq):
    try:
        return equip_item(req.hero_id, req.equipment_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/unequip")
def do_unequip(req: UnequipReq):
    try:
        return unequip_item(req.equipment_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/scrap")
def do_scrap(req: ScrapReq):
    try:
        return scrap_equipment(req.equipment_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
