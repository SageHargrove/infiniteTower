"""
Legacy Service
==============
When a hero dies, their sacrifice echoes through the roster forever.

Legacy bonuses are permanent passive buffs based on the fallen hero's
accomplishments: floors survived, kills, star rank, trauma endured.

The LLM generates a legacy title and flavor text based on the hero's story.
"""

import random
import json
from database import db


def calculate_legacy_bonus(hero: dict) -> dict:
    """
    Calculate the legacy bonus a dead hero leaves behind.
    Higher accomplishments = stronger legacy.
    """
    floors = hero.get("floors_survived", 0)
    kills = hero.get("kills", 0)
    star = hero.get("birth_star", 1)
    trauma = hero.get("trauma", 0)
    level = hero.get("level", 1)

    # Score determines legacy power
    score = (floors * 2) + (kills * 3) + (star * 10) + (trauma // 5) + (level * 2)

    # Determine bonus type based on hero's strongest trait
    bonus_types = [
        ("atk_pct", "ATK", hero.get("attack", 0)),
        ("def_pct", "DEF", hero.get("defense", 0)),
        ("hp_pct", "HP", hero.get("max_hp", 0) // 10),
        ("spd_pct", "SPD", hero.get("speed", 0)),
    ]

    # Pick the stat the hero was best at
    best_stat = max(bonus_types, key=lambda x: x[2])
    bonus_key = best_stat[0]
    bonus_label = best_stat[1]

    # Calculate bonus magnitude (1-5% based on score)
    magnitude = min(5, max(1, score // 30))

    # Special bonuses for exceptional heroes
    special = None
    if kills >= 20:
        special = {"id": "killer_instinct", "desc": f"+{magnitude}% crit chance to all heroes",
                   "effect": {"team_crit_pct": magnitude * 0.01}}
    elif floors >= 30:
        special = {"id": "veteran_wisdom", "desc": f"-{magnitude * 2}% stress gain for all heroes",
                   "effect": {"team_stress_reduce": magnitude * 0.02}}
    elif trauma >= 70:
        special = {"id": "iron_spirit", "desc": f"+{magnitude}% fear resistance to all heroes",
                   "effect": {"team_fear_resist": magnitude * 0.01}}

    return {
        "hero_id": hero["id"],
        "hero_name": hero.get("name", "Unknown"),
        "hero_star": star,
        "score": score,
        "primary_bonus": {
            "stat": bonus_key,
            "label": bonus_label,
            "value": magnitude * 0.01,  # percentage
            "desc": f"+{magnitude}% {bonus_label} to all heroes",
        },
        "special_bonus": special,
        "floors_survived": floors,
        "kills": kills,
        "level": level,
    }


def create_legacy(hero: dict, title: str = None, flavor: str = None, is_sacrifice: bool = False) -> dict:
    """Create and save a legacy record for a fallen hero.

    Portraits are only preserved for sacrificed heroes — sacrifice is a
    deliberate, memorialized death, so the team chooses to immortalize their
    face. An ordinary combat death is just gone; the legacy keeps their name
    and story, not their portrait.
    """
    bonus = calculate_legacy_bonus(hero)

    # Try LLM-generated title and flavor
    if not title or not flavor:
        try:
            from services.llm_service import generate_legacy_text
            llm_title, llm_flavor = generate_legacy_text(
                hero.get("name", "Unknown"),
                hero.get("birth_star", 1),
                hero.get("floors_survived", 0),
                hero.get("kills", 0),
                hero.get("backstory", ""),
            )
            title = title or llm_title
            flavor = flavor or llm_flavor
        except Exception:
            pass

    if not title:
        title = _generate_fallback_title(hero)
    if not flavor:
        flavor = f"They survived {bonus['floors_survived']} floors and slew {bonus['kills']} foes."

    portrait_path = hero.get("portrait_path") if is_sacrifice else None

    with db() as conn:
        conn.execute("""
            INSERT INTO legacies (hero_id, hero_name, hero_star, title, flavor_text,
                                  bonus_json, score, is_sacrifice, portrait_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            hero["id"], hero.get("name", "Unknown"), hero.get("birth_star", 1),
            title, flavor, json.dumps(bonus), bonus["score"],
            1 if is_sacrifice else 0, portrait_path,
        ))

    return {"title": title, "flavor": flavor, "is_sacrifice": is_sacrifice, "portrait_path": portrait_path, **bonus}


def get_all_legacies() -> list[dict]:
    """Return all legacy records."""
    with db() as conn:
        rows = conn.execute("""
            SELECT * FROM legacies ORDER BY score DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_active_legacy_bonuses() -> dict:
    """Calculate total legacy bonuses — only sacrificed/memorialized heroes
    contribute a stat bonus. An ordinary combat death is remembered (title,
    flavor, the legacy entry itself) but doesn't buff the team; that's
    reserved for the deliberate, rare act of sacrifice."""
    legacies = [l for l in get_all_legacies() if l.get("is_sacrifice")]
    total = {
        "atk_pct": 0, "def_pct": 0, "hp_pct": 0, "spd_pct": 0,
        "team_crit_pct": 0, "team_stress_reduce": 0, "team_fear_resist": 0,
    }

    for legacy in legacies:
        try:
            bonus = json.loads(legacy.get("bonus_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            continue

        primary = bonus.get("primary_bonus", {})
        stat = primary.get("stat", "")
        if stat in total:
            total[stat] += primary.get("value", 0)

        special = bonus.get("special_bonus")
        if special and isinstance(special, dict):
            for key, val in special.get("effect", {}).items():
                if key in total:
                    total[key] += val

    return total


def apply_legacy_bonuses(hero: dict) -> dict:
    """Apply legacy bonuses to hero stats before combat."""
    bonuses = get_active_legacy_bonuses()
    h = hero.copy()

    if bonuses["atk_pct"] > 0:
        h["attack"] = int(h["attack"] * (1 + bonuses["atk_pct"]))
    if bonuses["def_pct"] > 0:
        h["defense"] = int(h["defense"] * (1 + bonuses["def_pct"]))
    if bonuses["hp_pct"] > 0:
        h["max_hp"] = int(h["max_hp"] * (1 + bonuses["hp_pct"]))
        h["hp"] = int(h["hp"] * (1 + bonuses["hp_pct"]))
    if bonuses["spd_pct"] > 0:
        h["speed"] = int(h["speed"] * (1 + bonuses["spd_pct"]))
    if bonuses["team_crit_pct"] > 0:
        h["crit_chance"] = h.get("crit_chance", 0.05) + bonuses["team_crit_pct"]
    if bonuses["team_fear_resist"] > 0:
        h["fear_resist"] = h.get("fear_resist", 0) + bonuses["team_fear_resist"]

    return h


def _generate_fallback_title(hero: dict) -> str:
    """Fallback title if LLM is unavailable."""
    templates = [
        f"The Memory of {hero.get('name', 'the Fallen')}",
        f"{hero.get('name', 'Unknown')}'s Final Echo",
        f"Shadow of {hero.get('name', 'the Lost')}",
        f"The Weight {hero.get('name', 'They')} Carried",
    ]
    return random.choice(templates)
