"""
Level System
============
Level is earned through combat experience — floors survived and kills.
It is NOT a separate grind resource, it emerges from play.

Formula:
  level = 1 + (floors_survived // 3) + (kills // 5)
  capped by ascension_star

Level caps by ascension:
  0★ asc → max level 10
  1★ asc → max level 20
  2★ asc → max level 30
  3★ asc → max level 40
  4★ asc → max level 50
  5★ asc → max level 60
  6★ asc → max level 75
  7★ asc → max level 100

Stat scaling per level:
  +2% to ATK, DEF, SPD per level above 1
  +3% to HP per level above 1

Every 5 levels: one hidden aptitude is revealed
"""

def level_cap(ascension_star: int) -> int:
    caps = {0: 10, 1: 20, 2: 30, 3: 40, 4: 50, 5: 60, 6: 75, 7: 100}
    return caps.get(ascension_star, 10)

def calculate_level(floors_survived: int, kills: int, ascension_star: int) -> int:
    raw = 1 + (floors_survived // 3) + (kills // 5)
    cap = level_cap(ascension_star)
    return min(raw, cap)

def stat_multiplier(level: int) -> float:
    """Overall stat multiplier for a given level."""
    return 1.0 + (level - 1) * 0.02

def hp_multiplier(level: int) -> float:
    return 1.0 + (level - 1) * 0.03

def apply_level_to_stats(hero: dict) -> dict:
    """
    Apply level scaling to a hero's stats.
    Returns modified copy — does NOT write to DB.
    """
    h = hero.copy()
    level = h.get("level", 1)
    if level <= 1:
        return h

    sm = stat_multiplier(level)
    hm = hp_multiplier(level)

    h["attack"]  = int(h["attack"]  * sm)
    h["defense"] = int(h["defense"] * sm)
    h["speed"]   = int(h["speed"]   * sm)
    h["max_hp"]  = int(h["max_hp"]  * hm)
    # Current HP scales proportionally
    hp_ratio = h["hp"] / max(1, hero["max_hp"])
    h["hp"] = int(h["max_hp"] * hp_ratio)

    return h

def recalculate_hero_level(hero: dict) -> int:
    """Given a hero dict, return their current level."""
    return calculate_level(
        hero.get("floors_survived", 0),
        hero.get("kills", 0),
        hero.get("ascension_star", 0),
    )

def get_aptitude_reveals(level: int) -> int:
    """How many aptitudes should be revealed at this level."""
    return min(5, level // 5)  # one reveal per 5 levels, max 5

def level_up_summary(old_level: int, new_level: int, hero_name: str) -> list[str]:
    """Generate log messages for level ups."""
    messages = []
    for lvl in range(old_level + 1, new_level + 1):
        messages.append(f"{hero_name} reached level {lvl}.")
        if lvl % 5 == 0:
            messages.append(f"  → A hidden quality in {hero_name} becomes apparent.")
    return messages
