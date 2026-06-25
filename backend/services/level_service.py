"""
Level System
============
Level is earned through combat experience — floors survived and kills.
It is NOT a separate grind resource, it emerges from play.

Formula:
  level = 1 + (floors_survived // 3) + (kills // 5)
  capped by STAR level cap (birth_star or current_star)

Star-gated level caps (from Pick Me Up):
  1★ → max level 10
  2★ → max level 20
  3★ → max level 40
  4★ → max level 60
  5★ → max level 80
  6★ → max level 99
  7★ → max level 100+ (transcendent)

Ascension stars add +5 levels per ascension within the star cap.

Stat scaling per level:
  +2% to ATK, DEF, SPD per level above 1
  +3% to Health per level above 1

Every 5 levels: one hidden aptitude is revealed
"""

# Star rank determines primary level cap
STAR_LEVEL_CAPS = {
    1: 10,
    2: 20,
    3: 40,
    4: 60,
    5: 80,
    6: 99,
    7: 120,  # Transcendent
}


def level_cap(hero_star: int, ascension_star: int = 0) -> int:
    """
    Get the level cap for a hero based on their star rank and ascension.
    hero_star = current_star if promoted, else birth_star.
    """
    base_cap = STAR_LEVEL_CAPS.get(hero_star, 10)
    ascension_bonus = ascension_star * 5
    return base_cap + ascension_bonus


def get_hero_star(hero: dict) -> int:
    """Get the effective star rank (current_star if promoted, else birth_star)."""
    return hero.get("current_star") or hero.get("birth_star", 1)


def calculate_level(floors_survived: int, kills: int, hero_star: int, ascension_star: int = 0, xp: int = 0) -> int:
    raw = 1 + (floors_survived // 3) + (kills // 5) + (xp // 100)
    cap = level_cap(hero_star, ascension_star)
    return min(raw, cap)

APTITUDE_KEYS = ["apt_combat", "apt_tactical", "apt_survival", "apt_mental", "apt_leadership"]

def talent_score(hero: dict) -> float:
    """
    Average of the 5 hidden aptitudes, normalized to 0.0-1.0. This drives
    growth RATE per level, not base stats — birth_star still sets a hero's
    starting floor (see generate_base_stats), talent decides how steep
    their climb is from there. A high-aptitude 1-star promoted all the way
    to 7-star ends up growing at roughly the same rate a natural 7-star
    does; a low-aptitude 1-star never catches up even fully promoted.
    """
    apts = [hero.get(k, 50) for k in APTITUDE_KEYS]
    return sum(apts) / len(apts) / 100.0

def growth_multiplier(hero: dict) -> float:
    """0.7x (untalented) to 1.3x (max talent) — applied to per-level stat gain."""
    return 0.7 + talent_score(hero) * 0.6

# Base skill capacity mirrors the old birth-time skill counts (1/4★+ gets a
# 2nd, 6★+ gets a 3rd) — talent adds up to 3 more slots on top, so a highly
# talented hero can out-learn a less-talented hero of the same rarity.
MAX_SKILLS_BASE = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 3}

def max_skill_slots(hero_star: int, talent: float) -> int:
    base = MAX_SKILLS_BASE.get(hero_star, 1)
    return base + int(talent * 3)

def stat_multiplier(level: int, growth_mult: float = 1.0) -> float:
    """Overall stat multiplier for a given level."""
    return 1.0 + (level - 1) * 0.02 * growth_mult

def hp_multiplier(level: int, growth_mult: float = 1.0) -> float:
    """Endurance's own per-level rate — it inherited Health's growth weight
    when Health stopped being independently rolled, so it grows at the
    faster rate Health used to use (3%/level), not flat Defense's old 2%."""
    return 1.0 + (level - 1) * 0.03 * growth_mult

def apply_level_to_stats(hero: dict) -> dict:
    """
    Apply level scaling to a hero's stats.
    Returns modified copy — does NOT write to DB.
    """
    h = hero.copy()
    level = h.get("level", 1)
    if level <= 1:
        return h

    gm = growth_multiplier(h)
    sm = stat_multiplier(level, gm)
    hm = hp_multiplier(level, gm)

    from services.gacha_service import health_from_endurance

    h["strength"]  = int(h["strength"]  * sm)
    h["intelligence"] = int(h["intelligence"] * sm)
    h["agility"]   = int(h["agility"]   * sm)
    h["willpower"] = int(h.get("willpower", 6) * sm)
    # Luck deliberately does NOT scale with level — it already grows gently
    # across star rank (see generate_base_stats), and a level-scaled Luck on
    # top of that risks snowballing combat/exploration drop rates at high
    # level. It stays at whatever was rolled at creation.
    h["endurance"] = int(h.get("endurance", h.get("defense", 5)) * hm)
    h["defense"] = h["endurance"]  # legacy mirror, see database.py migration notes
    h["max_health"] = health_from_endurance(h["endurance"])
    # Current Health scales proportionally
    hp_ratio = h["health"] / max(1, hero["max_health"])
    h["health"] = int(h["max_health"] * hp_ratio)

    return h

def recalculate_hero_level(hero: dict) -> int:
    """Given a hero dict, return their current level."""
    hero_star = get_hero_star(hero)
    return calculate_level(
        hero.get("floors_survived", 0),
        hero.get("kills", 0),
        hero_star,
        hero.get("ascension_star", 0),
        hero.get("xp", 0)
    )

def get_aptitude_reveals(level: int, archive_level: int = 0) -> int:
    """How many aptitudes should be revealed at this level. Base rate is one
    per 5 levels; the Archive base-upgrade ("Reveal hero aptitudes faster")
    shortens that interval by one level per Archive level, down to a floor
    of revealing one per level at Archive's max (3)."""
    interval = max(1, 5 - archive_level)
    return min(5, level // interval)

def level_up_summary(old_level: int, new_level: int, hero_name: str) -> list[str]:
    """Generate log messages for level ups."""
    messages = []
    for lvl in range(old_level + 1, new_level + 1):
        messages.append(f"{hero_name} reached level {lvl}.")
        if lvl % 5 == 0:
            messages.append(f"  → A hidden quality in {hero_name} becomes apparent.")
    return messages

APTITUDE_REVEAL_ORDER = ["apt_combat", "apt_survival", "apt_tactical", "apt_mental", "apt_leadership"]

def get_revealed_aptitudes(hero: dict, archive_level: int = 0) -> dict:
    level = hero.get("level", 1)
    reveals = get_aptitude_reveals(level, archive_level)
    result = {}
    for i, apt_key in enumerate(APTITUDE_REVEAL_ORDER):
        if i < reveals:
            result[apt_key] = hero.get(apt_key, 50)
        else:
            result[apt_key] = None
    return result
