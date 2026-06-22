import random
from database import db

def get_vault_capacity(conn) -> int:
    """Base storage of 20, +16 per Vault facility slot unlocked (matches
    the frontend's display formula in InventoryPage.jsx)."""
    vault = conn.execute("SELECT slots_unlocked FROM facilities WHERE base_id = 1 AND type = 'Vault'").fetchone()
    if not vault:
        return 20
    return 20 + (vault["slots_unlocked"] * 16)

def get_equipment_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) AS c FROM equipment").fetchone()["c"]

RARITY_TIERS = [
    "F-", "F", "F+",
    "E-", "E", "E+",
    "D-", "D", "D+",
    "C-", "C", "C+",
    "B-", "B", "B+",
    "A-", "A", "A+",
    "S-", "S", "S+",
    "SS", "SSS", "Z"
]

RARITY_MULTS = {
    "F-": 0.5, "F": 0.7, "F+": 0.9,
    "E-": 1.1, "E": 1.3, "E+": 1.5,
    "D-": 1.8, "D": 2.2, "D+": 2.6,
    "C-": 3.0, "C": 3.5, "C+": 4.0,
    "B-": 4.6, "B": 5.3, "B+": 6.0,
    "A-": 7.0, "A": 8.5, "A+": 10.0,
    "S-": 12.0, "S": 15.0, "S+": 18.0,
    "SS": 25.0,
    "SSS": 40.0,
    "Z": 100.0,
}

TYPES = ["Weapon", "Armor", "Accessory"]

EQUIPMENT_ADJECTIVES = {
    "F-": "Broken", "F": "Rusted", "F+": "Chipped", "E-": "Poor", "E": "Basic", "E+": "Sturdy",
    "D-": "Standard", "D": "Polished", "D+": "Heavy", "C-": "Fine", "C": "Refined", "C+": "Balanced",
    "B-": "Masterwork", "B": "Exceptional", "B+": "Flawless", "A-": "Epic", "A": "Legendary", "A+": "Mythic",
    "S-": "Divine", "S": "Godly", "S+": "Transcendent", "SS": "Omnipotent", "SSS": "Absolute", "Z": "Eldritch",
}

def _rarity_from_score(score: float) -> str:
    if score < 30: return "F-"
    if score < 50: return "F"
    if score < 70: return "F+"
    if score < 90: return "E-"
    if score < 110: return "E"
    if score < 130: return "E+"
    if score < 150: return "D-"
    if score < 170: return "D"
    if score < 190: return "D+"
    if score < 210: return "C-"
    if score < 230: return "C"
    if score < 250: return "C+"
    if score < 270: return "B-"
    if score < 290: return "B"
    if score < 310: return "B+"
    if score < 330: return "A-"
    if score < 350: return "A"
    if score < 370: return "A+"
    if score < 390: return "S-"
    if score < 420: return "S"
    if score < 450: return "S+"
    if score < 500: return "SS"
    return "SSS"

def _roll_equipment_stats(eq_type: str, mult: float) -> dict:
    """Roll base stats for a piece of gear at a given rarity multiplier.

    The primary stat (base_atk for weapons, base_def/base_hp for armor) is
    rolled in a tight +/-4% band around a fixed center, NOT a wide range
    like the old random.randint(1, 3) — that 3x in-tier spread overlapped
    with the ~13-25% gap between adjacent rarity multipliers, so a
    lucky-rolled C could out-stat an unlucky B. The tight band keeps every
    tier strictly ahead of the one below it (worst B+ > best B, etc.) while
    still leaving a little roll variety. Secondary/bonus stats (crit, dodge,
    armor pen, % stats) keep their wider existing randomness since they're
    itemization flavor, not the stat that defines the tier.
    """
    scale = int(10 * mult)
    base_atk = base_def = base_hp = base_spd = 0
    crit = dodge = armor_pen = 0.0
    atk_pct = def_pct = hp_pct = spd_pct = 0.0

    if eq_type == "Weapon":
        base_atk = int(scale * random.uniform(1.92, 2.08))
        base_spd = int(scale * random.uniform(0, 0.5))
        if random.random() < 0.3: crit = random.uniform(0.01, 0.05) * mult
        if random.random() < 0.2: armor_pen = random.uniform(0.01, 0.05) * mult
    elif eq_type == "Armor":
        base_def = int(scale * random.uniform(1.92, 2.08))
        base_hp = int(scale * random.uniform(5.28, 5.72))
    else:
        if random.random() < 0.7: dodge = random.uniform(0.02, 0.08) * mult
        if random.random() < 0.7: crit = random.uniform(0.02, 0.08) * mult
        if random.random() < 0.7: armor_pen = random.uniform(0.02, 0.08) * mult
        if random.random() < 0.5: atk_pct = random.uniform(0.02, 0.06) * mult
        if random.random() < 0.5: def_pct = random.uniform(0.02, 0.06) * mult
        if random.random() < 0.5: hp_pct = random.uniform(0.02, 0.06) * mult
        if random.random() < 0.5: spd_pct = random.uniform(0.02, 0.06) * mult

    return {
        "base_atk": base_atk, "base_def": base_def, "base_hp": base_hp, "base_spd": base_spd,
        "atk_pct": atk_pct, "def_pct": def_pct, "hp_pct": hp_pct, "spd_pct": spd_pct,
        "crit_chance": crit, "dodge_chance": dodge, "armor_pen": armor_pen,
    }

def save_equipment(equip: dict, conn=None) -> int:
    """Insert an already-built equipment dict (name/type/rarity/stats) that
    hasn't been persisted yet, and return its new row id.

    Pass `conn` if the caller is already inside a `with db() as conn:` block —
    opening a second connection while the first is still uncommitted raises
    'database is locked' on SQLite."""
    sql = "INSERT INTO equipment (name, type, rarity, level, base_atk, base_def, base_hp, base_spd, atk_pct, def_pct, hp_pct, spd_pct, crit_chance, dodge_chance, armor_pen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    params = (
        equip["name"], equip["type"], equip["rarity"], equip.get("level", 1),
        equip.get("base_atk", 0), equip.get("base_def", 0), equip.get("base_hp", 0), equip.get("base_spd", 0),
        equip.get("atk_pct", 0.0), equip.get("def_pct", 0.0), equip.get("hp_pct", 0.0), equip.get("spd_pct", 0.0),
        equip.get("crit_chance", 0.0), equip.get("dodge_chance", 0.0), equip.get("armor_pen", 0.0),
    )
    if conn is not None:
        return conn.execute(sql, params).lastrowid
    with db() as conn:
        return conn.execute(sql, params).lastrowid

def craft_equipment_for_slot(slot: str, level: int, apt: int) -> dict:
    """Build (but don't yet save) equipment for a specific Forge slot, using
    explicit crafting power (level/apt — already includes any Blacksmith
    bonus from forge_craft) instead of re-deriving it from a crafter_id."""
    eq_type = {"weapon": "Weapon", "armor": "Armor"}.get(slot, "Accessory")

    score = level + apt + random.randint(-20, 100)
    rarity = _rarity_from_score(score)
    mult = RARITY_MULTS[rarity]
    stats = _roll_equipment_stats(eq_type, mult)
    name = f"{EQUIPMENT_ADJECTIVES.get(rarity, rarity)} {eq_type}"

    return {
        "name": name, "type": eq_type, "rarity": rarity, "level": max(1, level),
        **stats,
    }

def get_all_equipment():
    with db() as conn:
        rows = conn.execute("SELECT * FROM equipment ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def get_hero_equipment(hero_id: int):
    with db() as conn:
        rows = conn.execute("SELECT * FROM equipment WHERE is_equipped_to = ?", (hero_id,)).fetchall()
        return [dict(r) for r in rows]

def get_unequipped():
    with db() as conn:
        rows = conn.execute("SELECT * FROM equipment WHERE is_equipped_to IS NULL ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

def equip_item(hero_id: int, equipment_id: int):
    with db() as conn:
        item = conn.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,)).fetchone()
        if not item:
            raise ValueError("Equipment not found")
        
        # Un-equip whatever is in that slot for the hero
        conn.execute("UPDATE equipment SET is_equipped_to = NULL WHERE is_equipped_to = ? AND type = ?", (hero_id, item["type"]))
        
        # Equip the new item
        conn.execute("UPDATE equipment SET is_equipped_to = ? WHERE id = ?", (hero_id, equipment_id))
        return {"success": True}

def unequip_item(equipment_id: int):
    with db() as conn:
        conn.execute("UPDATE equipment SET is_equipped_to = NULL WHERE id = ?", (equipment_id,))
        return {"success": True}

def scrap_equipment(equipment_id: int) -> dict:
    """Break down an unwanted piece of gear into crafting materials, scaled
    by rarity — a way to clean up the Vault without just deleting value."""
    import json
    import random
    from services.floor_templates import CRAFTING_MATERIALS

    with db() as conn:
        item = conn.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,)).fetchone()
        if not item:
            raise ValueError("Equipment not found.")
        item = dict(item)
        if item.get("is_equipped_to"):
            raise ValueError("Unequip this item before scrapping it.")

        mult = RARITY_MULTS.get(item["rarity"], 1.0)
        mat_name = random.choice(CRAFTING_MATERIALS)
        amount = max(1, int(random.randint(2, 4) * mult / 2))

        base_row = conn.execute("SELECT materials FROM base WHERE id = 1").fetchone()
        current_mats = json.loads(base_row["materials"]) if base_row["materials"] else {}
        current_mats[mat_name] = current_mats.get(mat_name, 0) + amount
        conn.execute("UPDATE base SET materials = ? WHERE id = 1", (json.dumps(current_mats),))

        conn.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))

    return {"ok": True, "material": mat_name, "amount": amount, "scrapped": item["name"]}

def apply_equipment_stats(hero: dict, equipment_list: list = None) -> dict:
    """Add equipped gear's stat bonuses on top of a hero's (already
    level-scaled, if the caller did that first) attack/defense/speed/hp.
    Pass equipment_list if the caller already has it (e.g. a bulk-fetched
    list for a whole roster) to avoid a redundant per-hero query."""
    hero_eq = equipment_list if equipment_list is not None else get_hero_equipment(hero["id"])

    atk_pct = def_pct = hp_pct = spd_pct = 0.0
    
    for eq in hero_eq:
        hero["attack"] += eq["base_atk"]
        hero["defense"] += eq["base_def"]
        hero["max_hp"] += eq["base_hp"]
        hero["hp"] += eq["base_hp"]
        hero["speed"] += eq["base_spd"]
        
        atk_pct += eq.get("atk_pct", 0.0)
        def_pct += eq.get("def_pct", 0.0)
        hp_pct += eq.get("hp_pct", 0.0)
        spd_pct += eq.get("spd_pct", 0.0)
        
        if "crit_chance" in hero:
            hero["crit_chance"] += eq.get("crit_chance", 0)
        if "dodge_chance" in hero:
            hero["dodge_chance"] += eq.get("dodge_chance", 0)
        if "armor_pen" in hero:
            hero["armor_pen"] += eq.get("armor_pen", 0)

    # Apply percentage buffs after flat buffs are added
    if atk_pct > 0: hero["attack"] = int(hero["attack"] * (1 + atk_pct))
    if def_pct > 0: hero["defense"] = int(hero["defense"] * (1 + def_pct))
    if spd_pct > 0: hero["speed"] = int(hero["speed"] * (1 + spd_pct))
    if hp_pct > 0:
        old_max = hero["max_hp"]
        hero["max_hp"] = int(hero["max_hp"] * (1 + hp_pct))
        hero["hp"] += (hero["max_hp"] - old_max)

            
    hero["equipment"] = hero_eq
    return hero

def craft_equipment(crafter_id: int):
    with db() as conn:
        crafter = conn.execute("SELECT level, apt_tactical, hero_class FROM heroes WHERE id = ?", (crafter_id,)).fetchone()
        if not crafter:
            raise ValueError("Crafter not found")
            
        base = conn.execute("SELECT gold FROM base WHERE id = 1").fetchone()
        cost = 500
        if base["gold"] < cost:
            raise ValueError("Not enough gold to craft.")
            
        conn.execute("UPDATE base SET gold = gold - ? WHERE id = 1", (cost,))

        level = crafter["level"]
        apt = crafter["apt_tactical"]
        hero_class = crafter["hero_class"]
        
        score = (level) + (apt)
        
        if hero_class in ("Forge Lord", "Runesmith"):
            score *= 2.5
        elif hero_class == "Master Smith":
            score *= 1.8
        elif hero_class == "Blacksmith":
            score *= 1.3
            
        score += random.randint(-20, 100)
        rarity = _rarity_from_score(score)

        eq_type = random.choice(TYPES)
        mult = RARITY_MULTS[rarity]
        stats = _roll_equipment_stats(eq_type, mult)

        adj = EQUIPMENT_ADJECTIVES.get(rarity, rarity)
        name = f"{adj} {eq_type}"

        cursor = conn.execute(
            "INSERT INTO equipment (name, type, rarity, level, base_atk, base_def, base_hp, base_spd, atk_pct, def_pct, hp_pct, spd_pct, crit_chance, dodge_chance, armor_pen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, eq_type, rarity, level, stats["base_atk"], stats["base_def"], stats["base_hp"], stats["base_spd"],
             stats["atk_pct"], stats["def_pct"], stats["hp_pct"], stats["spd_pct"],
             stats["crit_chance"], stats["dodge_chance"], stats["armor_pen"])
        )
        return {"id": cursor.lastrowid, "name": name, "type": eq_type, "rarity": rarity}

def generate_equipment_drop(floor_number: int, is_boss: bool = False, drop_bonus: float = 0.0) -> dict | None:
    # Base chance: 10% on normal floors, 100% on bosses
    base_chance = 1.0 if is_boss else 0.10
    total_chance = min(1.0, base_chance + drop_bonus)
    
    if random.random() > total_chance:
        return None
        
    score = floor_number * 3 + random.randint(0, 50)
    if is_boss:
        score += 100
        
    if score < 30: rarity = "F-"
    elif score < 50: rarity = "F"
    elif score < 70: rarity = "F+"
    elif score < 90: rarity = "E-"
    elif score < 110: rarity = "E"
    elif score < 130: rarity = "E+"
    elif score < 150: rarity = "D-"
    elif score < 170: rarity = "D"
    elif score < 190: rarity = "D+"
    elif score < 210: rarity = "C-"
    elif score < 230: rarity = "C"
    elif score < 250: rarity = "C+"
    elif score < 270: rarity = "B-"
    elif score < 290: rarity = "B"
    elif score < 310: rarity = "B+"
    elif score < 330: rarity = "A-"
    elif score < 350: rarity = "A"
    elif score < 370: rarity = "A+"
    elif score < 390: rarity = "S-"
    elif score < 420: rarity = "S"
    elif score < 450: rarity = "S+"
    elif score < 500: rarity = "SS"
    elif score < 600: rarity = "SSS"
    else: rarity = "Z" # Z can only drop on extreme floors from bosses
    
    eq_type = random.choice(TYPES)
    mult = RARITY_MULTS[rarity]
    
    base_atk = base_def = base_hp = base_spd = 0
    crit = dodge = armor_pen = 0.0
    atk_pct = def_pct = hp_pct = spd_pct = 0.0
    scale = int(10 * mult)
    
    if eq_type == "Weapon":
        base_atk = scale * random.randint(1, 3)
        base_spd = int(scale * random.uniform(0, 0.5))
        if random.random() < 0.3: crit = random.uniform(0.01, 0.05) * mult
        if random.random() < 0.2: armor_pen = random.uniform(0.01, 0.05) * mult
    elif eq_type == "Armor":
        base_def = scale * random.randint(1, 3)
        base_hp = scale * random.randint(3, 8)
    else:
        if random.random() < 0.7: dodge = random.uniform(0.02, 0.08) * mult
        if random.random() < 0.7: crit = random.uniform(0.02, 0.08) * mult
        if random.random() < 0.7: armor_pen = random.uniform(0.02, 0.08) * mult
        if random.random() < 0.5: atk_pct = random.uniform(0.02, 0.06) * mult
        if random.random() < 0.5: def_pct = random.uniform(0.02, 0.06) * mult
        if random.random() < 0.5: hp_pct = random.uniform(0.02, 0.06) * mult
        if random.random() < 0.5: spd_pct = random.uniform(0.02, 0.06) * mult
        
    adjectives = {"F-": "Broken", "F": "Rusted", "F+": "Chipped", "E-": "Poor", "E": "Basic", "E+": "Sturdy", "D-": "Standard", "D": "Polished", "D+": "Heavy", "C-": "Fine", "C": "Refined", "C+": "Balanced", "B-": "Masterwork", "B": "Exceptional", "B+": "Flawless", "A-": "Epic", "A": "Legendary", "A+": "Mythic", "S-": "Divine", "S": "Godly", "S+": "Transcendent", "SS": "Omnipotent", "SSS": "Absolute", "Z": "Eldritch"}
    adj = adjectives.get(rarity, rarity)
    name = f"{adj} {eq_type}"

    with db() as conn:
        if get_equipment_count(conn) >= get_vault_capacity(conn):
            return None
        cursor = conn.execute(
            "INSERT INTO equipment (name, type, rarity, level, base_atk, base_def, base_hp, base_spd, atk_pct, def_pct, hp_pct, spd_pct, crit_chance, dodge_chance, armor_pen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, eq_type, rarity, max(1, floor_number // 5), base_atk, base_def, base_hp, base_spd, atk_pct, def_pct, hp_pct, spd_pct, crit, dodge, armor_pen)
        )
        return {"id": cursor.lastrowid, "name": name, "type": eq_type, "rarity": rarity}
