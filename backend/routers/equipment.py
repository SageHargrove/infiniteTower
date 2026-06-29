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
def list_equipment(show_all: bool = False):
    from services.equipment_service import get_all_equipment, get_hero_equipment
    all_eq = get_all_equipment()
    equipped = [e for e in all_eq if e["is_equipped_to"]]

    with db() as conn:
        rows = conn.execute("SELECT * FROM equipment WHERE is_equipped_to IS NULL ORDER BY created_at DESC").fetchall()
        unequipped = [dict(r) for r in rows]

    # "F" rarity is never droppable/craftable — it only exists as a hero's
    # guaranteed starting weapon (generate_starting_weapon). Once a hero
    # equips something better, the old F-grade item lands back here with
    # no slot, no artwork, and nothing a player would ever want — pure
    # clutter. Hidden by default; ?show_all=true reveals it.
    hidden_count = 0
    if not show_all:
        visible = [e for e in unequipped if e.get("rarity") != "F"]
        hidden_count = len(unequipped) - len(visible)
        unequipped = visible

    return {"equipped": equipped, "unequipped": unequipped, "hidden_count": hidden_count}

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
