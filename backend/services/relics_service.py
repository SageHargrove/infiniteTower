"""
Relics — Seals and Runes
========================
Unlike Skills (born with some, can learn/upgrade more over time), Relics
are dropped loot, like Equipment: found from bosses and events, then
equipped onto an eligible hero. Eligibility is gated on a hero's CURRENT
star (current_star if promoted, else birth_star) — a 1-star promoted up
to 4-star can equip a Seal just as well as a hero born at 4-star.

Each hero can have at most one Seal and one Rune equipped at a time.
"""
import random
import json
from database import db

SEAL_CATALOG = [
    {"id": "seal_strength", "name": "Seal of Strength", "rarity": "epic", "type": "passive",
     "desc": "+25% ATK, -5% SPD", "effect": {"atk_pct": 0.25, "spd_pct": -0.05}, "min_star": 4},
    {"id": "seal_protection", "name": "Seal of Protection", "rarity": "epic", "type": "passive",
     "desc": "+25% DEF, +10% max HP", "effect": {"def_pct": 0.25, "hp_pct": 0.10}, "min_star": 4},
    {"id": "seal_agility", "name": "Seal of Agility", "rarity": "epic", "type": "passive",
     "desc": "+15% SPD, +15% dodge chance", "effect": {"spd_pct": 0.15, "dodge_pct": 0.15}, "min_star": 4},
]

RUNE_CATALOG = [
    {"id": "rune_destruction", "name": "Ancient Rune of Destruction", "rarity": "legendary", "type": "passive",
     "desc": "+40% ATK, attacks ignore 20% DEF", "effect": {"atk_pct": 0.40, "armor_pen": 0.20}, "min_star": 5},
    {"id": "rune_eternity", "name": "Ancient Rune of Eternity", "rarity": "legendary", "type": "passive",
     "desc": "+50% max HP, regenerate 5% HP per round", "effect": {"hp_pct": 0.50, "regen_pct": 0.05}, "min_star": 5},
    {"id": "rune_void", "name": "Ancient Rune of the Void", "rarity": "legendary", "type": "passive",
     "desc": "+30% all stats, immune to fear", "effect": {"all_pct": 0.30, "fear_immune": True}, "min_star": 5},
]

CATALOGS = {"seal": SEAL_CATALOG, "rune": RUNE_CATALOG}


def roll_relic_drop(is_boss: bool, is_miniboss: bool, floor_number: int, conn=None) -> dict | None:
    """
    Chance to drop a relic on a boss/miniboss victory. Runes are rarer and
    gated to deeper floors than seals, matching their higher min_star.
    Returns the saved relic row (already in the DB, unequipped) or None.
    """
    if not (is_boss or is_miniboss):
        return None

    drop_chance = 0.25 if is_boss else 0.15
    if random.random() >= drop_chance:
        return None

    can_drop_rune = floor_number >= 30
    if can_drop_rune and random.random() < 0.3:
        relic_type, catalog = "rune", RUNE_CATALOG
    else:
        relic_type, catalog = "seal", SEAL_CATALOG

    template = random.choice(catalog)
    return save_relic(relic_type, template, conn=conn)


def save_relic(relic_type: str, template: dict, conn=None) -> dict:
    row = {
        "relic_type": relic_type,
        "name": template["name"],
        "rarity": template["rarity"],
        "desc": template["desc"],
        "effect": json.dumps(template["effect"]),
        "min_star": template["min_star"],
    }

    def _insert(c):
        cur = c.execute(
            "INSERT INTO hero_relics (relic_type, name, rarity, desc, effect, min_star) VALUES (?, ?, ?, ?, ?, ?)",
            (row["relic_type"], row["name"], row["rarity"], row["desc"], row["effect"], row["min_star"]),
        )
        row["id"] = cur.lastrowid
        return row

    if conn is not None:
        return _insert(conn)
    with db() as c:
        return _insert(c)


def get_all_relics() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM hero_relics ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_hero_relics(hero_id: int) -> list[dict]:
    """Returns the equipped relics for a hero with effect already parsed to a dict."""
    with db() as conn:
        rows = conn.execute("SELECT * FROM hero_relics WHERE is_equipped_to = ?", (hero_id,)).fetchall()
    relics = [dict(r) for r in rows]
    for r in relics:
        r["effect"] = json.loads(r["effect"])
    return relics


def equip_relic(hero_id: int, relic_id: int) -> dict:
    from services.level_service import get_hero_star
    with db() as conn:
        relic = conn.execute("SELECT * FROM hero_relics WHERE id = ?", (relic_id,)).fetchone()
        if not relic:
            raise ValueError("Relic not found")
        hero = conn.execute("SELECT * FROM heroes WHERE id = ?", (hero_id,)).fetchone()
        if not hero:
            raise ValueError("Hero not found")

        hero_star = get_hero_star(dict(hero))
        if hero_star < relic["min_star"]:
            raise ValueError(f"Hero must be {relic['min_star']}★ or higher to equip this (currently {hero_star}★)")

        # Un-equip whatever this hero already has of the same relic type
        conn.execute(
            "UPDATE hero_relics SET is_equipped_to = NULL WHERE is_equipped_to = ? AND relic_type = ?",
            (hero_id, relic["relic_type"]),
        )
        conn.execute("UPDATE hero_relics SET is_equipped_to = ? WHERE id = ?", (hero_id, relic_id))
        return {"success": True}


def unequip_relic(relic_id: int):
    with db() as conn:
        conn.execute("UPDATE hero_relics SET is_equipped_to = NULL WHERE id = ?", (relic_id,))
        return {"success": True}
