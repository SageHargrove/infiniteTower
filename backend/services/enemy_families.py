"""
Per-floor-range enemy families — floors 1-100 grouped into themed blocks,
each with a Normal tier (already in combat_service.py's ENEMY_TYPES/
ENEMY_ABILITY_OVERRIDES), and a dedicated Mini-Boss (the range's %5 floor)
and Boss (the range's %10 floor). Looked up by exact floor number from
tower.py; floors with no entry here just fall back to make_boss()'s
existing generic LLM-flavored naming — nothing breaks for ranges not yet
built out. Building this out is intentionally staged one floor-range block
at a time (see PLAN_floor_workshop_enemies.md) — floors 1-10 and 11-20 done
so far.

Floor 50 and 100 are flagged as wanting extra-special treatment (floor 50
is the tower's halfway point, floor 100 the final floor) but are NOT yet
content-complete — they're just a marker for later, once the families that
actually occupy those ranges (41-50, 91-100) are built out.
"""

# ─── Floors 1-10: Slime / Goblin / Rat / Wolf ──────────────────────────

GOBLIN_KING = {
    "name": "Goblin King",
    "abilities": ["summon_add", "cleave"],
    "spawn_template": "Goblin",
    "stat_mod": {"atk": 1.0, "def": 1.0, "spd": 1.0, "health": 1.1},
}

WARREN_TYRANT = {
    "name": "The Warren Tyrant",
    "abilities": ["summon_add", "crushing_blow", "last_stand"],
    "spawn_template": "Giant Rat",
    "stat_mod": {"atk": 1.1, "def": 1.0, "spd": 0.9, "health": 1.2},
}

# ─── Floors 11-20: Kobold / Skeleton / Orc / Giant Spider ──────────────────

SKELETON_CHAMPION = {
    # "revive_ally" needs a dead ally to actually do anything — a solo
    # family_override boss has none by default, so this also carries
    # summon_add (its own Skeleton reinforcements) to have something worth
    # bringing back once one of them falls.
    "name": "Skeleton Champion",
    "abilities": ["summon_add", "revive_ally", "cleave"],
    "spawn_template": "Skeleton",
    "stat_mod": {"atk": 1.1, "def": 1.1, "spd": 0.9, "health": 1.1},
}

GORRATH_THE_BONEBREAKER = {
    "name": "Gorrath the Bonebreaker",
    "abilities": ["summon_add", "crushing_blow", "last_stand"],
    "spawn_template": "Kobold",
    "stat_mod": {"atk": 1.2, "def": 1.1, "spd": 0.9, "health": 1.2},
}

# ─── Floors 51-100: bosses built from preserved hand-picked art ───────────
#
# These 4 portraits predate the floor-range family system — they were kept
# specifically because they were liked, not generated for any one range —
# so they're slotted into the family they best match by design rather than
# being tied to a built-out Normal/Elite roster for their range yet:
#   - Undead Monarch (vampire king) -> 51-70's "Vampire Spawn" range, floor 70 boss.
#   - Masked Horror (masked armored knight) -> 71-90's "Death Knights" range, floor 90 boss.
#   - Lich King / Nightwing Devourer -> 91-100's "Liches"/"Dragons" range. Floor
#     100 is the tower's final floor (also already triggers the every-20th-floor
#     Raid Boss merge) and asked for something extra-special, so rather than
#     picking just one of these two, floor 100 randomly fights either —
#     see get_boss_override below.

UNDEAD_MONARCH = {
    "name": "The Undead Monarch",
    "abilities": ["self_regen", "crushing_blow", "last_stand"],
    "portrait_path": "static/portraits/bosses/boss_undead_monarch.png",
    "stat_mod": {"atk": 1.1, "def": 1.1, "spd": 0.9, "health": 1.3},
}

MASKED_HORROR_BOSS = {
    "name": "The Masked Horror",
    "abilities": ["cleave", "crushing_blow", "enrage"],
    "portrait_path": "static/portraits/bosses/boss_masked_horror.png",
    "stat_mod": {"atk": 1.2, "def": 1.15, "spd": 1.0, "health": 1.2},
}

LICH_KING = {
    "name": "The Lich King",
    "abilities": ["summon_add", "team_buff_aura", "last_stand"],
    "spawn_template": "Corpse Rat",
    "portrait_path": "static/portraits/bosses/boss_lich_king.png",
    "stat_mod": {"atk": 1.1, "def": 1.0, "spd": 0.9, "health": 1.4},
}

NIGHTWING_DEVOURER = {
    "name": "The Nightwing Devourer",
    "abilities": ["cleave", "enrage", "crushing_blow", "last_stand"],
    "portrait_path": "static/portraits/bosses/boss_nightwing_devourer.png",
    "stat_mod": {"atk": 1.3, "def": 1.0, "spd": 1.2, "health": 1.3},
}

# floor_number -> family_override dict (see make_boss's family_override
# param in combat_service.py), or a list of dicts for a floor that should
# randomly pick between more than one (floor 100). Keyed by exact floor
# since each range only has one mini-boss floor and one boss floor right now.
MINIBOSS_OVERRIDES = {
    5: GOBLIN_KING,
    15: SKELETON_CHAMPION,
}
BOSS_OVERRIDES = {
    10: WARREN_TYRANT,
    20: GORRATH_THE_BONEBREAKER,
    70: UNDEAD_MONARCH,
    90: MASKED_HORROR_BOSS,
    100: [LICH_KING, NIGHTWING_DEVOURER],
}

# Marker only — not yet content-complete for the ranges that don't have a
# BOSS_OVERRIDES entry above. See module docstring.
SPECIAL_BOSS_FLOORS = {50, 100}


def get_miniboss_override(floor_number: int) -> dict | None:
    return MINIBOSS_OVERRIDES.get(floor_number)


def get_boss_override(floor_number: int) -> dict | None:
    entry = BOSS_OVERRIDES.get(floor_number)
    if isinstance(entry, list):
        import random
        return random.choice(entry)
    return entry
