from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.equipment_service import get_all_equipment, craft_equipment, equip_item, unequip_item, unequip_all, auto_equip_hero, scrap_equipment
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
    from services.equipment_service import get_all_equipment
    all_eq = get_all_equipment()
    equipped = [e for e in all_eq if e["is_equipped_to"]]

    with db() as conn:
        rows = conn.execute("SELECT * FROM equipment WHERE is_equipped_to IS NULL ORDER BY created_at DESC").fetchall()
        unequipped = [dict(r) for r in rows]

    # "F" rarity is never droppable/craftable/persisted — heroes don't get
    # a real starting weapon row anymore at all (see hero creation in
    # routers/gacha.py). ensure_hero_has_weapon (equipment_service.py)
    # injects a purely in-memory placeholder for stat math at combat time
    # only, never written to this table. This filter just guards against
    # any leftover F-grade rows from before that change, on existing save
    # files — nothing new should ever produce one. Unconditionally
    # hidden, no show_all override; there's nothing here worth revealing.
    equipped = [e for e in equipped if e.get("rarity") != "F"]
    unequipped = [e for e in unequipped if e.get("rarity") != "F"]

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

class AutoEquipReq(BaseModel):
    hero_id: int

@router.post("/auto-equip")
def do_auto_equip(req: AutoEquipReq):
    try:
        return auto_equip_hero(req.hero_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/unequip-all")
def do_unequip_all(req: AutoEquipReq):
    try:
        return unequip_all(req.hero_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
