"""
Level System
============
Level is earned through a real, accumulated XP economy now — kills, floor
clears, and Training Grounds all deposit into hero.xp, and level is derived
by walking an XP-cost-per-level curve up from there. This replaced an
earlier "level = 1 + floors_survived + kills//5" proxy that never actually
used the (previously dead, never-written-to) `xp` column at all —
confirmed real complaint that the old system was "weird" and didn't make
use of XP like a normal leveling system should.

XP curve (see xp_to_next_level/cumulative_xp_for_level):
  cost to go from level L to L+1 = 30 + 12*L (grows linearly each level)
  level is whatever level's cumulative threshold the hero's total xp clears,
  capped by STAR level cap (birth_star or current_star)

XP sources (see routers/tower.py combat resolution and
services/training_service.py's per-minute tick):
  - per enemy kill: scales with floor depth and boss/miniboss weight
  - per floor cleared: a flat bonus on top of kill XP, also floor-scaled
  - Training Grounds: a slow passive trickle for any hero assigned there,
    independent of (and much slower than) actually fighting

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


def xp_to_next_level(current_level: int) -> int:
    """XP needed to go from current_level to current_level+1. Grows by 12
    per level so the climb gets meaningfully steeper at high level without
    exploding — level 1->2 costs 42, level 50->51 costs 630."""
    return 30 + 12 * current_level


def cumulative_xp_for_level(level: int) -> int:
    """Total XP a hero needs to have ever earned to currently be at `level`
    (i.e. the threshold that was just cleared to reach it)."""
    if level <= 1:
        return 0
    n = level - 1
    return 30 * n + 6 * n * (n + 1)  # closed form of sum(30+12*i for i in 1..n)


def xp_progress(xp: int, level: int) -> tuple[int, int]:
    """(xp earned since hitting `level`, xp needed to reach `level`+1) — for
    a frontend progress bar."""
    floor_xp = cumulative_xp_for_level(level)
    next_xp = cumulative_xp_for_level(level + 1)
    return (max(0, xp - floor_xp), next_xp - floor_xp)


def calculate_level(xp: int, hero_star: int, ascension_star: int = 0) -> int:
    cap = level_cap(hero_star, ascension_star)
    level = 1
    while level < cap and xp >= cumulative_xp_for_level(level + 1):
        level += 1
    return level

APTITUDE_KEYS = ["apt_combat", "apt_tactical", "apt_survival", "apt_mental", "apt_leadership"]

# Raw apt_* values are unbounded (see gacha_service.generate_aptitudes —
# a true outlier can roll deep into the hundreds). TALENT_REFERENCE is
# where a "normal" 7★'s roll typically lands, not a hard cap — talent_score
# can and does exceed 1.0 for real prodigies. The 2.0 clamp below exists
# purely so combat math consuming talent downstream (panic resistance,
# skill-learn chance, etc. in combat_service.py) can't go nonsensical for
# an extreme roll — e.g. unclamped, panic resistance's "1.0 - talent*0.4"
# would go negative above talent=2.5. The raw apt_* numbers stored on the
# hero stay completely uncapped regardless; only this normalized,
# mechanically-consumed value is clamped.
TALENT_REFERENCE = 140.0
TALENT_SCORE_CLAMP = 2.0

def talent_score(hero: dict) -> float:
    """
    Average of the 5 hidden aptitudes, normalized against TALENT_REFERENCE.
    This drives growth RATE per level, not base stats — birth_star still
    sets a hero's starting floor (see generate_base_stats), talent decides
    how steep their climb is from there. A high-aptitude 1-star promoted
    all the way to 7-star ends up growing at roughly the same rate a
    natural 7-star does; a low-aptitude 1-star never catches up even fully
    promoted.
    """
    apts = [hero.get(k, 0) for k in APTITUDE_KEYS]
    raw = (sum(apts) / len(apts)) / TALENT_REFERENCE
    return min(TALENT_SCORE_CLAMP, raw)

def growth_multiplier(hero: dict) -> float:
    """0.5x (untalented) up to 3.0x (clamp-talent prodigy) — applied to
    per-level stat gain. The gap between these is deliberately wide now —
    talent is supposed to matter a lot, not just nudge growth by a little."""
    return 0.5 + talent_score(hero) * 1.25

# Base skill capacity mirrors the old birth-time skill counts (1/4★+ gets a
# 2nd, 6★+ gets a 3rd) — talent adds up to 3 more slots on top, so a highly
# talented hero can out-learn a less-talented hero of the same rarity.
MAX_SKILLS_BASE = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 3}
MAX_SKILLS_TALENT_BONUS_CAP = 5

def max_skill_slots(hero_star: int, talent: float) -> int:
    base = MAX_SKILLS_BASE.get(hero_star, 1)
    return base + min(MAX_SKILLS_TALENT_BONUS_CAP, int(talent * 3))

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
        hero.get("xp", 0),
        hero_star,
        hero.get("ascension_star", 0),
    )

def kill_xp_reward(floor_number: int, is_boss: bool = False, is_miniboss: bool = False) -> int:
    """XP for one enemy kill, scaled by how deep the floor is. Bosses count
    as a much bigger single kill (they're usually the only kill on that
    floor); minibosses are a smaller step up over a regular enemy."""
    base = 8 + floor_number
    if is_boss:
        return base * 4
    if is_miniboss:
        return int(base * 1.8)
    return base


def floor_clear_xp_reward(floor_number: int, is_boss: bool = False, is_miniboss: bool = False) -> int:
    """Flat bonus on top of kill XP for finishing the floor at all.
    Calibrated so floor 1's clear bonus ALONE (42 xp) already clears the
    level 1->2 threshold (also 42) — a level-1 hero clearing floor 1 always
    levels up even in a worst-case 0-kill clear, with actual kill XP
    stacking on top in the normal case."""
    base = 40 + floor_number * 2
    if is_boss:
        return base * 3
    if is_miniboss:
        return int(base * 1.5)
    return base


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

# Matches the manhwa trope this game is styled after — nobody just reads a
# "talent: 94%" stat off a character sheet, they piece it together from how
# fast someone grows and how much they can learn. Since this game DOES
# reveal raw aptitude numbers gradually (Archive upgrade speeds it up), the
# title below is the payoff for that reveal: an estimated rarity computed
# from whatever's visible so far, which sharpens as more gets revealed.
# Same powers-of-10 anchors as gacha_service.TALENT_FLOOR, so "One in a
# Million" here means the exact same rarity a natural 7★'s floor guarantees.
TALENT_TITLES = [
    (1_000_000, "One in a Million"),
    (100_000, "Prodigy"),
    (10_000, "Exceptional Talent"),
    (1_000, "Gifted"),
    (100, "Promising"),
    (10, "Adequate"),
]

def estimate_talent_rarity(hero: dict, archive_level: int = 0) -> float | None:
    """Inverts gacha_service's floor formula (rarity = e^(talent/SCALE)) to
    turn whatever aptitude average is currently visible into a "1 in X"
    estimate — the same number a hero's birth star floor is itself
    calibrated against, so a revealed-prodigy 1★ and a guaranteed-rare 7★
    converge on the same title at the same rarity. Returns None until at
    least one aptitude has been revealed."""
    import math
    from services.gacha_service import TALENT_TAIL_SCALE
    revealed = get_revealed_aptitudes(hero, archive_level)
    known = [v for v in revealed.values() if v is not None]
    if not known:
        return None
    avg = sum(known) / len(known)
    return max(1.0, math.exp(avg / TALENT_TAIL_SCALE))


# Talent Observatory — a SEPARATE, paid reveal path from Archive's passive
# per-level aptitude drip above. Archive gradually exposes the 5 individual
# aptitudes as a hero levels (free, automatic); the Observatory instead lets
# a player pay gold to immediately reveal the single overall talent_score
# (scaled to a friendlier 0-100 display range) for ANY hero regardless of
# level, with the level of detail (tier/range/exact) gated by the
# Observatory's own building level. The two systems don't share state.
MIRROR_OF_FATE_GOLD_PER_STAR = 500

MIRROR_OF_FATE_TIERS = [
    (25, "Poor"),
    (50, "Average"),
    (75, "Good"),
    (101, "Exceptional"),
]

def talent_display_value(hero: dict) -> int:
    """talent_score() is a 0.0-2.0 normalized float; scaled to 0-100 for a
    player-facing number that doesn't require explaining the raw formula."""
    return round(talent_score(hero) * 50)

def get_mirror_of_fate_cost(hero: dict) -> int:
    return get_hero_star(hero) * MIRROR_OF_FATE_GOLD_PER_STAR

def reveal_mirror_of_fate(hero: dict, mirror_level: int) -> str:
    """Returns the display string for the Mirror's current level —
    this is what gets persisted to heroes.talent_reveal, frozen at
    whatever detail the building offered at the moment of reveal."""
    value = talent_display_value(hero)
    if mirror_level >= 3:
        return f"Talent is {value}"
    if mirror_level >= 2:
        # ~15-wide window, gated to stay within [0, 100].
        low = max(0, (value // 15) * 15)
        high = min(100, low + 15)
        return f"Talent is between {low}-{high}"
    for threshold, label in MIRROR_OF_FATE_TIERS:
        if value < threshold:
            return label
    return MIRROR_OF_FATE_TIERS[-1][1]


def get_talent_title(hero: dict, archive_level: int = 0) -> str | None:
    """None below the 'Adequate' (1-in-10) threshold — most heroes simply
    don't have a talent title yet, which is the point; this is meant to
    read as a rare callout, not a stat every hero has filled in."""
    rarity = estimate_talent_rarity(hero, archive_level)
    if rarity is None:
        return None
    for threshold, title in TALENT_TITLES:
        if rarity >= threshold:
            return title
    return None
