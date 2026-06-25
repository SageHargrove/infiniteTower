from fastapi import APIRouter, HTTPException
from database import db
from pydantic import BaseModel
import json
import random

router = APIRouter()

@router.get("/")
def get_base():
    from services.time_service import process_fatigue_decay, process_passive_generation
    from services.training_service import process_training_xp
    from services.research_service import process_mage_research
    from services.alchemist_service import process_alchemist_lab
    from services.restaurant_service import process_restaurant
    from services.infirmary_service import process_infirmary
    from routers.gacha import maybe_reconcile_pending_profiles
    maybe_reconcile_pending_profiles()
    with db() as conn:
        process_fatigue_decay(conn)
        process_passive_generation(conn)
        process_training_xp(conn)
        process_mage_research(conn)
        process_alchemist_lab(conn)
        process_restaurant(conn)
        process_infirmary(conn)
        row = conn.execute("SELECT * FROM base WHERE id = 1").fetchone()
        result = dict(row)
        # Locked once per profile on first load — a 50/50 roll that then
        # persists for the lifetime of this save, rather than re-rolling
        # randomly on every page load.
        if not result.get("fairy_gender"):
            result["fairy_gender"] = random.choice(["male", "female"])
            conn.execute("UPDATE base SET fairy_gender = ? WHERE id = 1", (result["fairy_gender"],))
    return result

@router.post("/upgrade")
def upgrade_base():
    """Upgrades the base level and increases max heroes."""
    from database import db
    from fastapi import HTTPException
    with db() as conn:
        base = conn.execute("SELECT level, gold, max_roster_size FROM base WHERE id = 1").fetchone()
        lvl = base["level"]
        cost = 5000 * lvl
        if base["gold"] < cost:
            raise HTTPException(status_code=400, detail=f"Not enough gold. Need {cost}.")
        conn.execute("UPDATE base SET gold = gold - ?, level = level + 1, max_roster_size = max_roster_size + 10 WHERE id = 1", (cost,))
    return {"ok": True}

class RenameRequest(BaseModel):
    name: str

@router.post("/rename")
def rename_base(req: RenameRequest):
    if not req.name or len(req.name.strip()) == 0:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")
    with db() as conn:
        conn.execute("UPDATE base SET name = ? WHERE id = 1", (req.name.strip()[:30],))
    return {"ok": True, "name": req.name.strip()[:30]}

class MasterNameRequest(BaseModel):
    name: str

@router.post("/master-name")
def set_master_name(req: MasterNameRequest):
    """The player's own chosen name — distinct from base.name (the tower's
    name). Heroes refer to the player generically as 'the Master' in flavor
    text until this is set, after which that text uses the real name."""
    if not req.name or len(req.name.strip()) == 0:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")
    with db() as conn:
        conn.execute("UPDATE base SET master_name = ? WHERE id = 1", (req.name.strip()[:24],))
    return {"ok": True, "master_name": req.name.strip()[:24]}

TUTORIAL_COMPLETION_GEMS = 500

@router.post("/tutorial/complete")
def complete_tutorial():
    """Marks the tutorial as seen (so it never shows again on this profile)
    and grants the starter-gem bonus — awarded whether the player finished
    every step or hit Skip, since the point is getting them into their first
    summon either way, not gating the reward on sitting through the whole thing."""
    with db() as conn:
        already = conn.execute("SELECT tutorial_complete FROM base WHERE id = 1").fetchone()
        if already and already["tutorial_complete"]:
            return {"ok": True, "already_complete": True, "gems_granted": 0}
        conn.execute(
            "UPDATE base SET tutorial_complete = 1, gems = gems + ? WHERE id = 1",
            (TUTORIAL_COMPLETION_GEMS,),
        )
        row = conn.execute("SELECT gems FROM base WHERE id = 1").fetchone()
    return {"ok": True, "already_complete": False, "gems_granted": TUTORIAL_COMPLETION_GEMS, "gems": row["gems"]}

class GrantResourcesRequest(BaseModel):
    gold: int = 0
    gems: int = 0
    supplies: int = 0

@router.post("/dev/grant")
def grant_resources(req: GrantResourcesRequest):
    """
    Dev/testing helper — adds resources to the currently active profile.
    Intended for use on a dedicated test save, not your main progress.
    """
    import database
    with db() as conn:
        conn.execute(
            "UPDATE base SET gold = gold + ?, gems = gems + ?, supplies = supplies + ? WHERE id = 1",
            (max(0, req.gold), max(0, req.gems), max(0, req.supplies))
        )
        row = conn.execute("SELECT gold, gems, supplies FROM base WHERE id = 1").fetchone()
    return {"ok": True, "profile": database.ACTIVE_PROFILE, "gold": row["gold"], "gems": row["gems"], "supplies": row["supplies"]}

@router.post("/dev/clear-inventory")
def dev_clear_inventory():
    """Dev/testing helper — wipes equipment, materials, potions, and scrolls.
    Refuses to run outside a profile named 'test*' since this is destructive."""
    import database
    if not database.ACTIVE_PROFILE or not database.ACTIVE_PROFILE.lower().startswith("test"):
        raise HTTPException(status_code=400, detail="Refused: this only runs on a 'test' profile.")
    with db() as conn:
        conn.execute("DELETE FROM equipment")
        conn.execute("DELETE FROM inventory")
        conn.execute("UPDATE base SET materials = '{}' WHERE id = 1")
    return {"ok": True}

class DevSetLevelRequest(BaseModel):
    hero_id: int
    level: int

@router.post("/dev/set-level")
def dev_set_level(req: DevSetLevelRequest):
    """Dev/testing helper — force a hero to a target level by backfilling
    just enough XP to satisfy the normal level formula, so it doesn't get
    silently recalculated back down on the next floor/synthesis."""
    import database
    if not database.ACTIVE_PROFILE or not database.ACTIVE_PROFILE.lower().startswith("test"):
        raise HTTPException(status_code=400, detail="Refused: this only runs on a 'test' profile.")

    from services.level_service import level_cap, get_hero_star
    with db() as conn:
        hero = conn.execute("SELECT * FROM heroes WHERE id = ?", (req.hero_id,)).fetchone()
        if not hero:
            raise HTTPException(status_code=404, detail="Hero not found.")
        hero = dict(hero)

        cap = level_cap(get_hero_star(hero), hero.get("ascension_star", 0))
        target = max(1, min(req.level, cap))

        needed = (target - 1) - (hero.get("floors_survived", 0) // 3) - (hero.get("kills", 0) // 5)
        new_xp = max(hero.get("xp", 0), needed * 100) if needed > 0 else hero.get("xp", 0)

        conn.execute("UPDATE heroes SET level = ?, xp = ? WHERE id = ?", (target, new_xp, req.hero_id))
    return {"ok": True, "level": target, "capped": target < req.level}

@router.post("/rest")
def rest_heroes():
    """Rest all active heroes at base. Costs 50 supplies, 5 min cooldown."""
    import time
    from services.morale_service import rest_at_base_recovery
    with db() as conn:
        # Get base info
        base = conn.execute("SELECT supplies, last_rest_time FROM base WHERE id = 1").fetchone()
        
        now = time.time()
        cooldown = 300 # 5 minutes
        last_rest = base["last_rest_time"] or 0
        if now - last_rest < cooldown:
            rem = int(cooldown - (now - last_rest))
            raise HTTPException(status_code=400, detail=f"Resting is on cooldown for {rem} more seconds.")
            
        supply_cost = 50
        
        if base["supplies"] < supply_cost:
            raise HTTPException(status_code=400, detail=f"Not enough supplies to rest. Need {supply_cost}, have {base['supplies']}.")
            
        conn.execute("UPDATE base SET supplies = supplies - ?, last_rest_time = ? WHERE id = 1", (supply_cost, now))

        # Button says "Rest All Heroes" — rest the whole living roster, not just deployed ones
        heroes = conn.execute("SELECT * FROM heroes WHERE is_alive = 1").fetchall()
        for hero in heroes:
            recovery = rest_at_base_recovery(dict(hero))
            # Psych-only — HP is handled by lobby-return full heal, not Rest.
            conn.execute("""
                UPDATE heroes SET morale = ?, stress = ?, trauma = ?, morale_state = ?, fatigue = 0
                WHERE id = ?
            """, (recovery["morale"], recovery["stress"], recovery["trauma"],
                  recovery["morale_state"], hero["id"]))
    return {"ok": True, "rested": len(heroes), "cost": supply_cost}

@router.get("/market/catalog")
def market_catalog():
    from services.market_service import get_shop_catalog
    return get_shop_catalog()

class MarketPurchaseRequest(BaseModel):
    item_id: str

@router.post("/market/purchase")
def market_purchase(req: MarketPurchaseRequest):
    from services.market_service import purchase_item
    with db() as conn:
        try:
            return purchase_item(conn, req.item_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

class CraftBandagesRequest(BaseModel):
    crafter_id: int
    quantity: int = 1

@router.post("/infirmary/craft-bandages")
def craft_bandages_endpoint(req: CraftBandagesRequest):
    from services.infirmary_service import craft_bandages
    with db() as conn:
        try:
            return craft_bandages(conn, req.crafter_id, req.quantity)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

# ─── Base Floors ────────────────────────────────────────────────

class AssignFloorRequest(BaseModel):
    hero_id: int
    floor: int # 0 means unassigned

@router.get("/floors")
def get_base_floors():
    """Get the calculated LP and stats for all base floors"""
    with db() as conn:
        base = conn.execute("SELECT highest_floor FROM base WHERE id = 1").fetchone()
        highest_tower_floor = base["highest_floor"]
        unlocked_floors = max(1, highest_tower_floor // 10)
        
        # Calculate LP pool for each floor
        # e.g., floor 1 = 100 LP, floor 5 = 500 LP
        floors = {}
        for f in range(1, unlocked_floors + 1):
            floors[f] = {
                "floor_number": f,
                "total_lp": f * 100,
                "heroes": [],
                "lp_per_hero": 0,
                "stat_bonus_pct": 0
            }
            
        # Get hero assignments (all alive heroes)
        heroes = conn.execute("SELECT id, name, base_floor, hero_class, portrait_path, is_alive, level, birth_star, current_star FROM heroes WHERE is_alive = 1").fetchall()
        
        base_heroes = []
        for h in heroes:
            f = h["base_floor"]
            if f == 0:
                base_heroes.append(dict(h))
                continue
            if f not in floors:
                # If they are on a floor that is no longer unlocked or invalid, move them to unassigned (0)
                conn.execute("UPDATE heroes SET base_floor = 0 WHERE id = ?", (h["id"],))
                f = 0
                base_heroes.append(dict(h))
                continue
            floors[f]["heroes"].append(dict(h))
            
        # Calculate math
        for f in floors.values():
            if len(f["heroes"]) > 0:
                f["lp_per_hero"] = round(f["total_lp"] / len(f["heroes"]))
                f["stat_bonus_pct"] = round(f["lp_per_hero"] / 10)
            else:
                f["lp_per_hero"] = f["total_lp"]
                f["stat_bonus_pct"] = round(f["total_lp"] / 10)
                
    return {"floors": list(floors.values()), "unlocked": unlocked_floors, "base_heroes": base_heroes}

@router.post("/floors/assign")
def assign_base_floor(req: AssignFloorRequest):
    with db() as conn:
        base = conn.execute("SELECT highest_floor FROM base WHERE id = 1").fetchone()
        highest_tower_floor = base["highest_floor"]
        unlocked_floors = max(1, highest_tower_floor // 10)
        
        if req.floor > unlocked_floors or req.floor < 0:
            raise HTTPException(status_code=400, detail=f"Floor {req.floor} is invalid.")
            
        conn.execute("UPDATE heroes SET base_floor = ? WHERE id = ?", (req.floor, req.hero_id))
    return {"ok": True}

# ─── Daily Dungeon endpoints ────────────────────────────────────────

@router.post("/daily_dungeon/{dungeon_type}")
def run_daily_dungeon(dungeon_type: str):
    """
    Run a daily dungeon for Gold or Materials.
    Rewards scale with the highest floor reached in the tower.
    """
    if dungeon_type not in ["gold", "materials", "supplies"]:
        raise HTTPException(status_code=400, detail="Invalid dungeon type. Must be 'gold', 'materials', or 'supplies'.")

    with db() as conn:
        # Check team
        team = conn.execute("SELECT * FROM heroes WHERE is_on_team = 1 AND is_alive = 1").fetchall()
        if not team:
            raise HTTPException(status_code=400, detail="No team assigned. Set a team first.")

        # Get highest floor
        run = conn.execute("SELECT MAX(highest_floor) as max_floor FROM runs").fetchone()
        highest = run["max_floor"] if run and run["max_floor"] else 0
        scale = 1 + (highest // 10)

        # Base info
        base_row = conn.execute("SELECT gold, materials, supplies FROM base WHERE id = 1").fetchone()
        
        if dungeon_type == "gold":
            gold_reward = 1000 + (scale * 800)
            conn.execute("UPDATE base SET gold = gold + ? WHERE id = 1", (gold_reward,))
            return {"ok": True, "type": "gold", "reward": gold_reward, "message": f"Dungeon cleared! Gained {gold_reward} Gold."}
            
        elif dungeon_type == "materials":
            mats = ["iron_shard", "dark_crystal", "worn_leather", "spirit_dust", "ancient_bone", "elemental_stone"]
            import random
            drops = {}
            for _ in range(random.randint(2, 4 + (scale // 2))):
                mat = random.choice(mats)
                drops[mat] = drops.get(mat, 0) + random.randint(1, 3 + (scale // 3))
            
            current_mats = json.loads(base_row["materials"]) if base_row["materials"] else {}
            for mat, qty in drops.items():
                current_mats[mat] = current_mats.get(mat, 0) + qty
            
            conn.execute("UPDATE base SET materials = ? WHERE id = 1", (json.dumps(current_mats),))
            return {"ok": True, "type": "materials", "reward": drops, "message": "Dungeon cleared! Gathered materials."}

        elif dungeon_type == "supplies":
            supplies_earned = 20 + max(0, highest * 5)
            conn.execute("UPDATE base SET supplies = supplies + ? WHERE id = 1", (supplies_earned,))
            return {"ok": True, "type": "supplies", "reward": supplies_earned, "message": f"Dungeon cleared! Gathered {supplies_earned} Supplies 🍖."}
# ─── Inventory endpoints ────────────────────────────────────────────

@router.get("/inventory")
def get_inventory():
    """Return all items in the base inventory."""
    with db() as conn:
        rows = conn.execute("SELECT * FROM inventory WHERE quantity > 0 ORDER BY item_type, item_name").fetchall()
    return [dict(r) for r in rows]


@router.post("/inventory/add")
def add_inventory_item(item_name: str, item_type: str, quantity: int = 1, description: str = ""):
    """Add an item to inventory (or increment quantity if it exists)."""
    with db() as conn:
        existing = conn.execute(
            "SELECT * FROM inventory WHERE item_name = ? AND item_type = ?",
            (item_name, item_type)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE inventory SET quantity = quantity + ? WHERE id = ?",
                (quantity, existing["id"])
            )
            return {"ok": True, "item": item_name, "new_quantity": existing["quantity"] + quantity}
        else:
            conn.execute(
                "INSERT INTO inventory (item_name, item_type, quantity, description) VALUES (?,?,?,?)",
                (item_name, item_type, quantity, description)
            )
            return {"ok": True, "item": item_name, "new_quantity": quantity}


class UseItemRequest(BaseModel):
    item_name: str
    hero_id: int
    target_skill_id: str = None

@router.post("/inventory/use")
def use_item(req: UseItemRequest):
    """Consume a potion or scroll on a target hero."""
    from services.alchemist_service import POTION_CATALOG
    from services.research_service import SCROLL_CATALOG
    catalog = {p["name"]: p["effect"] for p in POTION_CATALOG}
    catalog.update({s["name"]: s["effect"] for s in SCROLL_CATALOG})

    effect = catalog.get(req.item_name)
    if not effect:
        raise HTTPException(status_code=400, detail="Unknown or unusable item.")

    with db() as conn:
        item = conn.execute(
            "SELECT * FROM inventory WHERE item_name = ? AND quantity > 0", (req.item_name,)
        ).fetchone()
        if not item:
            raise HTTPException(status_code=400, detail="You don't have any of that item.")

        hero = conn.execute("SELECT * FROM heroes WHERE id = ? AND is_alive = 1", (req.hero_id,)).fetchone()
        if not hero:
            raise HTTPException(status_code=400, detail="Hero not available.")
        hero = dict(hero)

        applied = {}
        if "heal_pct" in effect:
            heal = int(hero["max_health"] * effect["heal_pct"])
            new_hp = min(hero["max_health"], hero["health"] + heal)
            conn.execute("UPDATE heroes SET health = ? WHERE id = ?", (new_hp, hero["id"]))
            applied["health"] = new_hp

        if "stress_delta" in effect:
            new_stress = max(0, hero["stress"] + effect["stress_delta"])
            conn.execute("UPDATE heroes SET stress = ? WHERE id = ?", (new_stress, hero["id"]))
            applied["stress"] = new_stress

        if "trauma_delta" in effect:
            new_trauma = max(0, hero["trauma"] + effect["trauma_delta"])
            conn.execute("UPDATE heroes SET trauma = ? WHERE id = ?", (new_trauma, hero["id"]))
            applied["trauma"] = new_trauma

        if "skill_xp" in effect:
            skills = json.loads(hero.get("skills") or "[]")
            target = None
            if req.target_skill_id:
                target = next((s for s in skills if s["id"] == req.target_skill_id), None)
            elif skills:
                target = skills[0]
            if target:
                target["xp"] = target.get("xp", 0) + effect["skill_xp"]
                max_xp = target.get("max_xp", 100)
                if target["xp"] >= max_xp:
                    target["xp"] -= max_xp
                    target["level"] = target.get("level", 1) + 1
                    target["max_xp"] = int(max_xp * 1.5)
                conn.execute("UPDATE heroes SET skills = ? WHERE id = ?", (json.dumps(skills), hero["id"]))
                applied["skill"] = target["name"]

        new_qty = item["quantity"] - 1
        if new_qty <= 0:
            conn.execute("DELETE FROM inventory WHERE id = ?", (item["id"],))
        else:
            conn.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_qty, item["id"]))

    return {"ok": True, "item": req.item_name, "applied": applied, "remaining": max(0, new_qty)}


# ─── Base upgrades endpoints ────────────────────────────────────────

DEFAULT_UPGRADES = [
    {"id": "barracks", "name": "Barracks", "description": "Increase max team size.", "max_level": 5},
    {"id": "infirmary", "name": "Infirmary", "description": "Improve rest recovery rates.", "max_level": 5},
    {"id": "forge", "name": "Forge", "description": "Improves the quality of crafted equipment.", "max_level": 5},
    {"id": "watchtower", "name": "Watchtower", "description": "Reveal floor types in advance.", "max_level": 3},
    {"id": "archive", "name": "Archive", "description": "Reveal hero aptitudes faster.", "max_level": 3},
    {"id": "chapel", "name": "Chapel", "description": "Reduce trauma buildup.", "max_level": 5},
]

UPGRADE_GOLD_COST = {
    1: 500,
    2: 1200,
    3: 2500,
    4: 5000,
    5: 10000,
}

@router.get("/upgrades")
def get_upgrades():
    """Return all base upgrades and their current levels."""
    with db() as conn:
        # Ensure defaults exist, and keep name/description/max_level in sync
        # for rows created before a wording change (e.g. Forge's "unlock
        # crafting" claim, which never matched reality since crafting
        # already worked without it — see forge_craft's real effect now).
        for u in DEFAULT_UPGRADES:
            conn.execute(
                "INSERT OR IGNORE INTO base_upgrades (id, name, description, max_level) VALUES (?,?,?,?)",
                (u["id"], u["name"], u["description"], u["max_level"])
            )
            conn.execute(
                "UPDATE base_upgrades SET name = ?, description = ?, max_level = ? WHERE id = ?",
                (u["name"], u["description"], u["max_level"], u["id"])
            )
        rows = conn.execute("SELECT * FROM base_upgrades ORDER BY name").fetchall()
        
    results = []
    for r in rows:
        upgrade = dict(r)
        current_level = upgrade.get("level", 0)
        max_level = upgrade.get("max_level", 5)
        next_level = current_level + 1
        upgrade["is_maxed"] = current_level >= max_level
        upgrade["next_cost"] = UPGRADE_GOLD_COST.get(next_level, 10000)
        results.append(upgrade)
    return results


class UpgradeRequest(BaseModel):
    upgrade_id: str

@router.post("/upgrades/purchase")
def buy_upgrade(data: UpgradeRequest):
    """Purchase the next level of a base upgrade."""
    with db() as conn:
        upgrade = conn.execute("SELECT * FROM base_upgrades WHERE id = ?", (data.upgrade_id,)).fetchone()
        if not upgrade:
            raise HTTPException(status_code=404, detail="Upgrade not found.")
        upgrade = dict(upgrade)

        current_level = upgrade.get("level", 0)
        max_level = upgrade.get("max_level", 5)
        if current_level >= max_level:
            raise HTTPException(status_code=400, detail="Upgrade already at max level.")

        next_level = current_level + 1
        cost = UPGRADE_GOLD_COST.get(next_level, 10000)

        base = conn.execute("SELECT gold FROM base WHERE id = 1").fetchone()
        if base["gold"] < cost:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough gold. Need {cost}, have {base['gold']}."
            )

        conn.execute("UPDATE base SET gold = gold - ? WHERE id = 1", (cost,))
        conn.execute(
            "UPDATE base_upgrades SET level = ?, unlocked = 1 WHERE id = ?",
            (next_level, data.upgrade_id)
        )

    return {
        "ok": True,
        "upgrade_id": data.upgrade_id,
        "new_level": next_level,
        "gold_spent": cost,
        "message": f"{upgrade['name']} upgraded to level {next_level}!"
    }


# ─── Equipment endpoints ────────────────────────────────────────────

@router.get("/equipment")
def list_equipment():
    """List all equipment, grouped by equipped/unequipped."""
    from services.equipment_service import get_unequipped
    with db() as conn:
        all_equip = conn.execute("SELECT * FROM equipment").fetchall()
    equipped = [dict(e) for e in all_equip if e["is_equipped_to"]]
    unequipped = get_unequipped()
    return {"equipped": equipped, "unequipped": unequipped}


class EquipRequest(BaseModel):
    equipment_id: int
    hero_id: int

@router.post("/equipment/equip")
def equip_item_endpoint(data: EquipRequest):
    from services.equipment_service import equip_item
    result = equip_item(data.equipment_id, data.hero_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class UnequipRequest(BaseModel):
    equipment_id: int

@router.post("/equipment/unequip")
def unequip_item_endpoint(data: UnequipRequest):
    from services.equipment_service import unequip_item
    return unequip_item(data.equipment_id)


@router.get("/equipment/hero/{hero_id}")
def hero_equipment(hero_id: int):
    from services.equipment_service import get_hero_equipment
    return get_hero_equipment(hero_id)
class CraftRequest(BaseModel):
    slot: str

@router.post("/forge/craft")
def forge_craft(req: CraftRequest):
    from services.equipment_service import craft_equipment_for_slot, save_equipment, get_vault_capacity, get_equipment_count
    with db() as conn:
        if get_equipment_count(conn) >= get_vault_capacity(conn):
            raise HTTPException(status_code=400, detail="The Vault is full. Upgrade it or clear out some equipment first.")

        # Check base gold and materials
        base = conn.execute("SELECT gold, materials FROM base WHERE id = 1").fetchone()

        mats = json.loads(base["materials"]) if base["materials"] else {}
        recipe = {}
        if req.slot == "weapon":
            recipe = {"Iron Ore": 3, "Monster Bone": 1}
        elif req.slot == "armor":
            recipe = {"Slime Core": 2, "Iron Ore": 2}
        else:
            recipe = {"Mystic Dust": 3, "Goblin Ear": 1}
            
        from services.materials_service import get_material_total, consume_material
        for m, q in recipe.items():
            if get_material_total(mats, m) < q:
                raise HTTPException(status_code=400, detail=f"Not enough {m}. Need {q} for {req.slot}.")

        if base["gold"] < 100:
            raise HTTPException(status_code=400, detail="Not enough gold (costs 100).")

        for m, q in recipe.items():
            consume_material(mats, m, q)

        # Find Forge facility
        forge = conn.execute("SELECT id FROM facilities WHERE type = 'Forge'").fetchone()
        if not forge:
            raise HTTPException(status_code=400, detail="You must build the Forge first!")
            
        # Get assigned heroes
        assigned = conn.execute("""
            SELECT h.* FROM facility_assignments fa
            JOIN heroes h ON fa.hero_id = h.id
            WHERE fa.facility_id = ? AND h.is_alive = 1
        """, (forge["id"],)).fetchall()
        
        # Calculate crafting power
        level = 1
        apt = 10
        crafter_name = "Nobody"

        if assigned:
            from services.class_service import forge_smith_bonus

            # Average level and apt
            level = sum(h["level"] for h in assigned) // len(assigned)
            apt = sum(h["apt_tactical"] + h["apt_survival"] for h in assigned) // (2 * len(assigned))

            assigned_classes = [h["hero_class"] for h in assigned]

            # Quality is capped by your single best Blacksmith present —
            # more of them at the same tier adds a smaller bonus on top,
            # but a pile of weak smiths can't out-craft one great one.
            smith_apt, smith_level, best_smith_cls = forge_smith_bonus(assigned_classes)
            apt += smith_apt
            level += smith_level
            if best_smith_cls:
                crafter_name = next(h["name"] for h in assigned if h["hero_class"] == best_smith_cls)
            else:
                crafter_name = assigned[0]["name"] + " (Unskilled)"

        # Forge base-upgrade (DEFAULT_UPGRADES "forge") used to claim it
        # "unlocks equipment crafting" — but crafting already works without
        # it, so that description never matched reality. Repurposed: a flat
        # quality nudge on top of whichever Blacksmith crafted it, same
        # scale as one smith-tier step (see SMITH_TIER_BONUS).
        from services.base_service import get_base_upgrade_level
        apt += get_base_upgrade_level(conn, "forge") * 10

        conn.execute("UPDATE base SET gold = gold - 100, materials = ? WHERE id = 1", (json.dumps(mats),))

        # Craft
        equip = craft_equipment_for_slot(req.slot, level, apt)
        equip_id = save_equipment(equip, conn=conn)
        equip["id"] = equip_id
        
        # Grant XP to assigned heroes
        if assigned:
            for h in assigned:
                conn.execute("UPDATE heroes SET xp = COALESCE(xp, 0) + 500 WHERE id = ?", (h["id"],))
        
        return {"ok": True, "equipment": equip, "crafter_used": crafter_name}

@router.get("/inventory/equipment")
def get_equipment_inventory():
    from services.equipment_service import get_unequipped
    return get_unequipped()

class EquipRequest(BaseModel):
    equipment_id: int
    hero_id: int

@router.post("/inventory/equip")
def equip_item_endpoint(req: EquipRequest):
    from services.equipment_service import equip_item
    res = equip_item(req.equipment_id, req.hero_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

class UnequipRequest(BaseModel):
    equipment_id: int

@router.post("/inventory/unequip")
def unequip_item_endpoint(req: UnequipRequest):
    from services.equipment_service import unequip_item
    res = unequip_item(req.equipment_id)
    return res

# Facilities
from pydantic import BaseModel

class BuildFacilityReq(BaseModel):
    facility_type: str

@router.get("/facilities")
def get_base_facilities():
    from services.facility_service import get_facilities
    return get_facilities()

@router.post("/facilities/build")
def build_new_facility(req: BuildFacilityReq):
    from services.facility_service import build_facility
    try:
        return build_facility(req.facility_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class UpgradeFacilityReq(BaseModel):
    facility_id: int

@router.post("/facilities/upgrade")
def upgrade_existing_facility(req: UpgradeFacilityReq):
    from services.facility_service import upgrade_facility
    try:
        return upgrade_facility(req.facility_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class AssignFacilityReq(BaseModel):
    facility_id: int
    hero_id: int
    role: str = None
    target_hero_id: int = None
    target_skill_id: str = None

@router.post("/facilities/assign")
def assign_hero_facility(req: AssignFacilityReq):
    from services.facility_service import assign_hero_to_facility
    try:
        return assign_hero_to_facility(req.facility_id, req.hero_id, req.role, req.target_hero_id, req.target_skill_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class RemoveFacilityReq(BaseModel):
    hero_id: int

@router.post("/facilities/remove")
def remove_hero_facility(req: RemoveFacilityReq):
    from services.facility_service import remove_hero_from_facility
    return remove_hero_from_facility(req.hero_id)

class TrainingConfigReq(BaseModel):
    facility_id: int
    hero_id: int
    role: str
    target_skill_id: str = None
    target_hero_id: int = None

@router.post("/facilities/training-config")
def config_training(req: TrainingConfigReq):
    from services.training_service import assign_training
    try:
        return assign_training(req.facility_id, req.hero_id, req.role, req.target_skill_id, req.target_hero_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class TrainSkillReq(BaseModel):
    hero_id: int
    skill_id: str
    sparring_partner_id: int = None

@router.post("/facilities/training-grounds/train")
def train_skill(req: TrainSkillReq):
    with db() as conn:
        # Verify they are in training grounds
        assigned = conn.execute("""
            SELECT fa.facility_id FROM facility_assignments fa
            JOIN facilities f ON fa.facility_id = f.id
            WHERE fa.hero_id = ? AND f.type = 'Training Grounds'
        """, (req.hero_id,)).fetchone()
        
        if not assigned:
            raise HTTPException(status_code=400, detail="Hero must be assigned to Training Grounds to train.")
            
        hero = conn.execute("SELECT skills, level, fatigue FROM heroes WHERE id = ?", (req.hero_id,)).fetchone()
        skills = json.loads(hero["skills"]) if hero["skills"] else []
        
        target_skill = next((s for s in skills if s["id"] == req.skill_id), None)
        if not target_skill:
            raise HTTPException(status_code=400, detail="Skill not found.")
            
        if target_skill.get("level", 1) >= 10:
            raise HTTPException(status_code=400, detail="Skill is max level for this tier. Advance tier in the tower.")
            
        xp_gain = 20
        # If there's a sparring partner, verify they are also in training grounds
        if req.sparring_partner_id:
            partner_assigned = conn.execute("""
                SELECT fa.facility_id FROM facility_assignments fa
                JOIN facilities f ON fa.facility_id = f.id
                WHERE fa.hero_id = ? AND f.type = 'Training Grounds'
            """, (req.sparring_partner_id,)).fetchone()
            if not partner_assigned:
                raise HTTPException(status_code=400, detail="Sparring partner must also be in Training Grounds.")
            xp_gain += 30 # Teacher/Sparring bonus!
            
        target_skill["xp"] = target_skill.get("xp", 0) + xp_gain
        leveled_up = False
        if target_skill["xp"] >= target_skill.get("max_xp", 100):
            target_skill["level"] = target_skill.get("level", 1) + 1
            target_skill["xp"] -= target_skill.get("max_xp", 100)
            target_skill["max_xp"] = int(target_skill.get("max_xp", 100) * 1.5)
            leveled_up = True
            
        # Training causes fatigue
        conn.execute("UPDATE heroes SET skills = ?, fatigue = fatigue + 10 WHERE id = ?", (json.dumps(skills), req.hero_id))
        
        return {"ok": True, "xp_gained": xp_gain, "leveled_up": leveled_up, "new_level": target_skill["level"]}

RESEARCH_UPGRADES = {
    "gold_boost": {"name": "Alchemical Transmutation", "desc": "+5% Gold from Tower", "max_level": 5, "base_cost": 100},
    "xp_boost": {"name": "Arcane Insight", "desc": "+10% Skill XP Gain", "max_level": 5, "base_cost": 150},
    "drop_boost": {"name": "Treasure Finding", "desc": "+5% Equipment Drop Rate", "max_level": 5, "base_cost": 200},
}

@router.get("/facilities/mage-tower/upgrades")
def get_research_upgrades():
    with db() as conn:
        base = conn.execute("SELECT research_points, global_buffs FROM base WHERE id = 1").fetchone()
        buffs = json.loads(base["global_buffs"] or "{}")
        
    res = []
    for uid, info in RESEARCH_UPGRADES.items():
        lvl = buffs.get(uid, 0)
        res.append({
            "id": uid,
            "name": info["name"],
            "desc": info["desc"],
            "level": lvl,
            "max_level": info["max_level"],
            "cost": info["base_cost"] * (lvl + 1)
        })
    return {"points": base["research_points"], "upgrades": res}

class BuyResearchReq(BaseModel):
    upgrade_id: str

@router.post("/facilities/mage-tower/buy")
def buy_research_upgrade(req: BuyResearchReq):
    with db() as conn:
        base = conn.execute("SELECT research_points, global_buffs FROM base WHERE id = 1").fetchone()
        buffs = json.loads(base["global_buffs"] or "{}")
        
        info = RESEARCH_UPGRADES.get(req.upgrade_id)
        if not info:
            raise HTTPException(status_code=400, detail="Invalid upgrade.")
            
        lvl = buffs.get(req.upgrade_id, 0)
        if lvl >= info["max_level"]:
            raise HTTPException(status_code=400, detail="Max level reached.")
            
        cost = info["base_cost"] * (lvl + 1)
        if base["research_points"] < cost:
            raise HTTPException(status_code=400, detail=f"Requires {cost} Research Points.")
            
        buffs[req.upgrade_id] = lvl + 1
        conn.execute("UPDATE base SET research_points = research_points - ?, global_buffs = ? WHERE id = 1", 
                     (cost, json.dumps(buffs)))
                     
    return {"ok": True}
