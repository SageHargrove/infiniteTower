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
    "D-", "D", "D+",
    "C-", "C", "C+",
    "B-", "B", "B+",
    "A-", "A", "A+",
    "S-", "S", "S+",
    "SS", "SSS", "Z"
]

RARITY_MULTS = {
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
    # "F" is intentionally not part of RARITY_TIERS/RARITY_MULTS — it's never
    # droppable, only ever auto-generated as a hero's guaranteed starting
    # weapon (see generate_starting_weapon below) so nobody fights bare-handed.
    "F": "Worn",
    "D-": "Standard", "D": "Polished", "D+": "Heavy", "C-": "Fine", "C": "Refined", "C+": "Balanced",
    "B-": "Masterwork", "B": "Exceptional", "B+": "Flawless", "A-": "Epic", "A": "Legendary", "A+": "Mythic",
    "S-": "Divine", "S": "Godly", "S+": "Transcendent", "SS": "Omnipotent", "SSS": "Absolute", "Z": "Eldritch",
}

def generate_starting_weapon() -> dict:
    """Every hero starts with a guaranteed basic weapon instead of fighting
    unarmed — deliberately not part of the droppable rarity pool, and not
    worth being picky about (always a plain Sword)."""
    return {
        "name": "Worn Sword", "type": "Weapon", "rarity": "F", "level": 1,
        "base_str": 4, "base_int": 0, "base_hlt": 0, "base_agi": 0, "base_def": 0,
        "str_pct": 0.0, "int_pct": 0.0, "hlt_pct": 0.0, "agi_pct": 0.0,
        "crit_chance": 0.0, "dodge_chance": 0.0, "armor_pen": 0.0, "dmg_reduction_pct": 0.0,
    }

def _rarity_from_score(score: float) -> str:
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
    if score < 600: return "SSS"
    return "Z"

def _roll_equipment_stats(eq_type: str, mult: float) -> dict:
    """Roll base stats for a piece of gear at a given rarity multiplier.

    The primary stat (base_str for weapons, base_int/base_hlt for armor) is
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
    base_str = base_int = base_hlt = base_agi = base_def = base_end = base_wil = base_luck = 0
    crit = dodge = armor_pen = dmg_reduction_pct = 0.0
    str_pct = int_pct = hlt_pct = agi_pct = 0.0

    if eq_type == "Weapon":
        base_str = int(scale * random.uniform(1.92, 2.08))
        base_agi = int(scale * random.uniform(0, 0.5))
        if random.random() < 0.3: crit = random.uniform(0.01, 0.05) * mult
        if random.random() < 0.2: armor_pen = random.uniform(0.01, 0.05) * mult
    elif eq_type == "Armor":
        # Armor's primary stat is Endurance (was flat Defense, then base_int
        # before that — Defense/Endurance has always been the real combat
        # stat behind this slot, base_def kept in sync for legacy reads).
        base_end = int(scale * random.uniform(1.92, 2.08))
        base_def = base_end
        base_hlt = int(scale * random.uniform(5.28, 5.72))
        if random.random() < 0.4: dmg_reduction_pct = random.uniform(0.01, 0.04) * mult
    else:
        # Every stat below used to roll independently — rare bad luck across
        # all chances could leave an accessory with nothing useful on
        # it at all (confirmed: a real drop with only a 5% dmg_reduction_pct
        # and zero everything else). Force at least 2 of these to roll no
        # matter what, then let the rest stay probabilistic for variety on
        # top of that floor.
        rolls = {
            "dodge": (0.7, lambda: random.uniform(0.02, 0.08) * mult),
            "crit": (0.7, lambda: random.uniform(0.02, 0.08) * mult),
            "armor_pen": (0.7, lambda: random.uniform(0.02, 0.08) * mult),
            "str_pct": (0.5, lambda: random.uniform(0.02, 0.06) * mult),
            "int_pct": (0.5, lambda: random.uniform(0.02, 0.06) * mult),
            "hlt_pct": (0.5, lambda: random.uniform(0.02, 0.06) * mult),
            "agi_pct": (0.5, lambda: random.uniform(0.02, 0.06) * mult),
            "dmg_reduction_pct": (0.3, lambda: random.uniform(0.01, 0.03) * mult),
            "base_wil": (0.5, lambda: max(1, int(scale * random.uniform(0.5, 1.0)))),
            "base_luck": (0.5, lambda: max(1, int(scale * random.uniform(0.3, 0.7)))),
        }
        guaranteed = set(random.sample(list(rolls.keys()), 2))
        results = {}
        for key, (chance, roll_fn) in rolls.items():
            if key in guaranteed or random.random() < chance:
                results[key] = roll_fn()
        dodge = results.get("dodge", 0.0)
        crit = results.get("crit", 0.0)
        armor_pen = results.get("armor_pen", 0.0)
        str_pct = results.get("str_pct", 0.0)
        int_pct = results.get("int_pct", 0.0)
        hlt_pct = results.get("hlt_pct", 0.0)
        agi_pct = results.get("agi_pct", 0.0)
        dmg_reduction_pct = results.get("dmg_reduction_pct", 0.0)
        base_wil = results.get("base_wil", 0)
        base_luck = results.get("base_luck", 0)

    return {
        "base_str": base_str, "base_int": base_int, "base_hlt": base_hlt, "base_agi": base_agi, "base_def": base_def,
        "base_end": base_end, "base_wil": base_wil, "base_luck": base_luck,
        "str_pct": str_pct, "int_pct": int_pct, "hlt_pct": hlt_pct, "agi_pct": agi_pct,
        "crit_chance": crit, "dodge_chance": dodge, "armor_pen": armor_pen, "dmg_reduction_pct": dmg_reduction_pct,
    }

def save_equipment(equip: dict, conn=None) -> int:
    """Insert an already-built equipment dict (name/type/rarity/stats) that
    hasn't been persisted yet, and return its new row id.

    Pass `conn` if the caller is already inside a `with db() as conn:` block —
    opening a second connection while the first is still uncommitted raises
    'database is locked' on SQLite."""
    sql = "INSERT INTO equipment (name, type, rarity, level, base_str, base_int, base_hlt, base_agi, base_def, base_end, base_wil, base_luck, str_pct, int_pct, hlt_pct, agi_pct, crit_chance, dodge_chance, armor_pen, dmg_reduction_pct) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    params = (
        equip["name"], equip["type"], equip["rarity"], equip.get("level", 1),
        equip.get("base_str", 0), equip.get("base_int", 0), equip.get("base_hlt", 0), equip.get("base_agi", 0), equip.get("base_def", 0),
        equip.get("base_end", 0), equip.get("base_wil", 0), equip.get("base_luck", 0),
        equip.get("str_pct", 0.0), equip.get("int_pct", 0.0), equip.get("hlt_pct", 0.0), equip.get("agi_pct", 0.0),
        equip.get("crit_chance", 0.0), equip.get("dodge_chance", 0.0), equip.get("armor_pen", 0.0), equip.get("dmg_reduction_pct", 0.0),
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
    from services.materials_service import CRAFTING_MATERIALS, MATERIAL_TIERS, tiered_material_name

    with db() as conn:
        item = conn.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,)).fetchone()
        if not item:
            raise ValueError("Equipment not found.")
        item = dict(item)
        if item.get("is_equipped_to"):
            raise ValueError("Unequip this item before scrapping it.")

        mult = RARITY_MULTS.get(item["rarity"], 1.0)
        # Better gear scraps into a better material tier, not just more of it.
        tier_idx = min(len(MATERIAL_TIERS) - 1, int(mult / 4))
        mat_name = tiered_material_name(random.choice(CRAFTING_MATERIALS), MATERIAL_TIERS[tier_idx])
        amount = max(1, int(random.randint(2, 4) * mult / 2))

        base_row = conn.execute("SELECT materials FROM base WHERE id = 1").fetchone()
        current_mats = json.loads(base_row["materials"]) if base_row["materials"] else {}
        current_mats[mat_name] = current_mats.get(mat_name, 0) + amount
        conn.execute("UPDATE base SET materials = ? WHERE id = 1", (json.dumps(current_mats),))

        conn.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))

    return {"ok": True, "material": mat_name, "amount": amount, "scrapped": item["name"]}

def apply_equipment_stats(hero: dict, equipment_list: list = None) -> dict:
    """Add equipped gear's stat bonuses on top of a hero's (already
    level-scaled, if the caller did that first) strength/intelligence/agility/health.
    Pass equipment_list if the caller already has it (e.g. a bulk-fetched
    list for a whole roster) to avoid a redundant per-hero query."""
    hero_eq = equipment_list if equipment_list is not None else get_hero_equipment(hero["id"])

    str_pct = int_pct = hlt_pct = agi_pct = 0.0
    dmg_reduction_pct = hero.get("dmg_reduction_pct", 0.0)
    end_bonus = 0

    for eq in hero_eq:
        hero["strength"] += eq["base_str"]
        hero["intelligence"] += eq["base_int"]
        hero["max_health"] += eq["base_hlt"]
        hero["health"] += eq["base_hlt"]
        hero["agility"] += eq["base_agi"]
        hero["defense"] = hero.get("defense", 5) + eq.get("base_def", 0)
        # Endurance gear bonus adds to max_health too (HP_PER_ENDURANCE per
        # point), same relationship as hero creation/leveling — accumulated
        # and applied once below, alongside base_hlt/hlt_pct.
        end_bonus += eq.get("base_end", 0)
        hero["endurance"] = hero.get("endurance", hero.get("defense", 5)) + eq.get("base_end", 0)
        hero["willpower"] = hero.get("willpower", 6) + eq.get("base_wil", 0)
        hero["luck"] = hero.get("luck", 5) + eq.get("base_luck", 0)
        dmg_reduction_pct += eq.get("dmg_reduction_pct", 0.0)

        str_pct += eq.get("str_pct", 0.0)
        int_pct += eq.get("int_pct", 0.0)
        hlt_pct += eq.get("hlt_pct", 0.0)
        agi_pct += eq.get("agi_pct", 0.0)

        if "crit_chance" in hero:
            hero["crit_chance"] += eq.get("crit_chance", 0)
        if "dodge_chance" in hero:
            hero["dodge_chance"] += eq.get("dodge_chance", 0)
        if "armor_pen" in hero:
            hero["armor_pen"] += eq.get("armor_pen", 0)

    if end_bonus:
        from services.gacha_service import HP_PER_ENDURANCE
        hero["max_health"] += end_bonus * HP_PER_ENDURANCE
        hero["health"] += end_bonus * HP_PER_ENDURANCE

    # Apply percentage buffs after flat buffs are added
    if str_pct > 0: hero["strength"] = int(hero["strength"] * (1 + str_pct))
    if int_pct > 0: hero["intelligence"] = int(hero["intelligence"] * (1 + int_pct))
    if agi_pct > 0: hero["agility"] = int(hero["agility"] * (1 + agi_pct))
    if hlt_pct > 0:
        old_max = hero["max_health"]
        hero["max_health"] = int(hero["max_health"] * (1 + hlt_pct))
        hero["health"] += (hero["max_health"] - old_max)

    # Capped well short of 100% — %DR is meant to stack with the Defense
    # stat, not let stacked gear make a hero outright unhittable.
    hero["dmg_reduction_pct"] = min(0.6, dmg_reduction_pct)
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
            "INSERT INTO equipment (name, type, rarity, level, base_str, base_int, base_hlt, base_agi, str_pct, int_pct, hlt_pct, agi_pct, crit_chance, dodge_chance, armor_pen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, eq_type, rarity, level, stats["base_str"], stats["base_int"], stats["base_hlt"], stats["base_agi"],
             stats["str_pct"], stats["int_pct"], stats["hlt_pct"], stats["agi_pct"],
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
        
    rarity = _rarity_from_score(score)
    eq_type = random.choice(TYPES)
    mult = RARITY_MULTS[rarity]
    
    stats = _roll_equipment_stats(eq_type, mult)
        
    adjectives = {"F-": "Broken", "F": "Rusted", "F+": "Chipped", "E-": "Poor", "E": "Basic", "E+": "Sturdy", "D-": "Standard", "D": "Polished", "D+": "Heavy", "C-": "Fine", "C": "Refined", "C+": "Balanced", "B-": "Masterwork", "B": "Exceptional", "B+": "Flawless", "A-": "Epic", "A": "Legendary", "A+": "Mythic", "S-": "Divine", "S": "Godly", "S+": "Transcendent", "SS": "Omnipotent", "SSS": "Absolute", "Z": "Eldritch"}
    adj = adjectives.get(rarity, rarity)
    name = f"{adj} {eq_type}"

    result = {
        "name": name, "type": eq_type, "rarity": rarity,
        "level": max(1, floor_number // 5)
    }
    result.update(stats)
    return result
