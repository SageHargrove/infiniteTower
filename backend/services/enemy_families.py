"""
Per-floor-range enemy families — floors 1-100 grouped into themed blocks,
each with a Normal tier (already in combat_service.py's ENEMY_TYPES/
ENEMY_ABILITY_OVERRIDES), and a dedicated Mini-Boss (the range's %5 floor)
and Boss (the range's %10 floor). Looked up by exact floor number from
tower.py; floors with no entry here just fall back to make_boss()'s
existing generic LLM-flavored naming — nothing breaks for ranges not yet
built out. Building this out is intentionally staged one floor-range block
at a time (see PLAN_floor_workshop_enemies.md) — floors 1-10 first.

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

# floor_number -> family_override dict (see make_boss's family_override
# param in combat_service.py). Keyed by exact floor since each range only
# has one mini-boss floor and one boss floor right now.
MINIBOSS_OVERRIDES = {
    5: GOBLIN_KING,
}
BOSS_OVERRIDES = {
    10: WARREN_TYRANT,
}

# Marker only — not yet content-complete. See module docstring.
SPECIAL_BOSS_FLOORS = {50, 100}


def get_miniboss_override(floor_number: int) -> dict | None:
    return MINIBOSS_OVERRIDES.get(floor_number)


def get_boss_override(floor_number: int) -> dict | None:
    return BOSS_OVERRIDES.get(floor_number)
