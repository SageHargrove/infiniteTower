"""
Per-floor-range enemy families — floors 1-100 grouped into themed blocks,
each with a Normal tier (already in combat_service.py's ENEMY_TYPES/
ENEMY_ABILITY_OVERRIDES), and a dedicated Mini-Boss (the range's %5 floor)
and Boss (the range's %10 floor). Looked up by exact floor number from
tower.py; floors with no entry here just fall back to make_boss()'s
existing generic LLM-flavored naming — nothing breaks for ranges not yet
built out.

Floors 1-100 are now fully covered — a named miniboss at every %5 floor
(except 35, see comment above MINIBOSS_OVERRIDES) and a named boss at
every %10 floor. Raid Boss (multi-team merge) fires only on floors 50 and
100 — those are the two real milestone floors (halfway point and final
floor). All other x10 floors, including 20/40/60/80, are regular single-
team boss fights pulled from BOSS_OVERRIDES.
"""

# ─── Floors 1-10: Shadow Wisp / Goblin / Giant Spider / Wolf ────────────

GOBLIN_KING = {
    "name": "Goblin King",
    "abilities": ["summon_add", "cleave"],
    "spawn_template": "Goblin",
    "stat_mod": {"atk": 1.0, "def": 1.0, "spd": 1.0, "health": 1.1},
}

# ─── Floors 11-30: intermediate/veteran tiers' miniboss+boss ──────────────
#
# These two tiers (Dire Wolf/Orc/Harpy/Ogre/Troll at floor 15+, Hobgoblin/
# Lizardman at floor 21+) never had a named miniboss/boss of their own —
# floor 15/20/25/30 fell back to the old generic LLM-flavored naming.

ORC_WARCHIEF = {
    "name": "Orc Warchief",
    "abilities": ["cleave", "enrage"],
    "spawn_template": "Orc",
    "stat_mod": {"atk": 1.1, "def": 1.0, "spd": 1.0, "health": 1.1},
}

TROLL_KING = {
    "name": "The Troll King",
    "abilities": ["crushing_blow", "last_stand", "enrage"],
    "spawn_template": "Troll",
    "stat_mod": {"atk": 1.2, "def": 1.1, "spd": 0.8, "health": 1.3},
}

SKARN_LIZARD_CHIEFTAIN = {
    "name": "Skarn the Lizard Chieftain",
    "abilities": ["self_regen", "crushing_blow"],
    "spawn_template": "Lizardman",
    "stat_mod": {"atk": 1.1, "def": 1.0, "spd": 1.1, "health": 1.1},
}

HOBGOBLIN_WARLORD = {
    "name": "The Hobgoblin Warlord",
    "abilities": ["cleave", "summon_add", "last_stand"],
    "spawn_template": "Hobgoblin",
    "stat_mod": {"atk": 1.2, "def": 1.1, "spd": 0.9, "health": 1.3},
}

# ─── Floors 31-50: advanced/mighty tiers' miniboss+boss ───────────────────

GRAVE_SOVEREIGN = {
    "name": "The Grave Sovereign",
    "abilities": ["self_regen", "crushing_blow", "last_stand"],
    "spawn_template": "Rotting Ghoul",
    "stat_mod": {"atk": 1.2, "def": 1.1, "spd": 0.9, "health": 1.3},
}

BULLHORN_MINOTAUR_LORD = {
    "name": "Bullhorn the Minotaur Lord",
    "abilities": ["crushing_blow", "enrage"],
    "spawn_template": "Minotaur",
    "stat_mod": {"atk": 1.2, "def": 1.1, "spd": 0.9, "health": 1.2},
}

# Floor 50 — the tower's halfway point, flagged as wanting something
# extra-special (see SPECIAL_BOSS_FLOORS) — no preserved art fit this range
# so it never got a design until now.
ASHEN_COLOSSUS = {
    "name": "The Ashen Colossus",
    "abilities": ["crushing_blow", "enrage", "last_stand"],
    "spawn_template": "Minotaur",
    "stat_mod": {"atk": 1.3, "def": 1.2, "spd": 0.8, "health": 1.5},
}

# ─── Floors 51-70: ascendant/mythic tiers' miniboss+boss ──────────────────

STONEHEART_UNBROKEN = {
    "name": "Stoneheart the Unbroken",
    "abilities": ["crushing_blow", "last_stand"],
    "spawn_template": "Stone Sentinel",
    "stat_mod": {"atk": 1.1, "def": 1.3, "spd": 0.7, "health": 1.4},
}

OBSIDIAN_TYRANT = {
    "name": "The Obsidian Tyrant",
    "abilities": ["crushing_blow", "team_buff_aura", "last_stand"],
    "spawn_template": "Lesser Golem",
    "stat_mod": {"atk": 1.3, "def": 1.4, "spd": 0.6, "health": 1.5},
}

DROWNED_NAGA_QUEEN = {
    "name": "The Drowned Naga Queen",
    "abilities": ["team_buff_aura", "self_regen"],
    "spawn_template": "Naga",
    "stat_mod": {"atk": 1.2, "def": 1.0, "spd": 1.1, "health": 1.2},
}

# ─── Floors 71-90: apex/dread tiers' miniboss+boss ─────────────────────────

KNIGHT_CAPTAIN_MORDREK = {
    "name": "Knight-Captain Mordrek",
    "abilities": ["cleave", "enrage"],
    "spawn_template": "Death Knight",
    "stat_mod": {"atk": 1.2, "def": 1.2, "spd": 0.9, "health": 1.2},
}

HYDRA_SOVEREIGN = {
    "name": "The Hydra Sovereign",
    "abilities": ["summon_add", "self_regen", "last_stand"],
    "spawn_template": "Hydra Spawn",
    "stat_mod": {"atk": 1.3, "def": 1.1, "spd": 0.9, "health": 1.5},
}

PIT_FIEND_COMMANDER = {
    "name": "Pit Fiend Commander",
    "abilities": ["summon_add", "crushing_blow"],
    "spawn_template": "Imp",
    "stat_mod": {"atk": 1.3, "def": 1.2, "spd": 1.0, "health": 1.3},
}

# ─── Floors 91-100: ancient tier's miniboss ────────────────────────────────

DRACOLICH_HERALD = {
    "name": "The Dracolich Herald",
    "abilities": ["self_regen", "last_stand"],
    "spawn_template": "Young Dragon",
    "stat_mod": {"atk": 1.3, "def": 1.2, "spd": 0.9, "health": 1.4},
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
    "portrait_path": "static/portraits/enemies/boss/boss_undead_monarch.png",
    "stat_mod": {"atk": 1.1, "def": 1.1, "spd": 0.9, "health": 1.3},
}

MASKED_HORROR_BOSS = {
    "name": "The Masked Horror",
    "abilities": ["cleave", "crushing_blow", "enrage"],
    "portrait_path": "static/portraits/enemies/boss/boss_masked_horror.png",
    "stat_mod": {"atk": 1.2, "def": 1.15, "spd": 1.0, "health": 1.2},
}

LICH_KING = {
    "name": "The Lich King",
    "abilities": ["summon_add", "team_buff_aura", "last_stand"],
    "spawn_template": "Corpse Rat",
    "portrait_path": "static/portraits/enemies/boss/boss_lich_king.png",
    "stat_mod": {"atk": 1.1, "def": 1.0, "spd": 0.9, "health": 1.4},
}

NIGHTWING_DEVOURER = {
    "name": "The Nightwing Devourer",
    "abilities": ["cleave", "enrage", "crushing_blow", "last_stand"],
    "portrait_path": "static/portraits/enemies/boss/boss_nightwing_devourer.png",
    "stat_mod": {"atk": 1.3, "def": 1.0, "spd": 1.2, "health": 1.3},
}

# floor_number -> family_override dict (see make_boss's family_override
# param in combat_service.py), or a list of dicts for a floor that should
# randomly pick between more than one (floor 100). Keyed by exact floor
# since each range only has one mini-boss floor and one boss floor right now.
# Floor 35 has no miniboss entry — advanced tier's one named unique
# (Grave Sovereign) is reserved for floor 40's boss, so 35 stays on the old
# generic LLM-flavored naming rather than reusing the same unit twice.
MINIBOSS_OVERRIDES = {
    5: GOBLIN_KING,
    15: ORC_WARCHIEF,
    25: SKARN_LIZARD_CHIEFTAIN,
    45: BULLHORN_MINOTAUR_LORD,
    55: STONEHEART_UNBROKEN,
    65: DROWNED_NAGA_QUEEN,
    75: KNIGHT_CAPTAIN_MORDREK,
    85: PIT_FIEND_COMMANDER,
    95: DRACOLICH_HERALD,
}

AETHERION_END_OF_ALL_THINGS = {
    "name": "Aetherion, the End of All Things",
    "abilities": ["summon_add", "team_buff_aura", "crushing_blow", "enrage", "last_stand"],
    "spawn_template": "Archdemon",
    "stat_mod": {"atk": 1.4, "def": 1.2, "spd": 1.1, "health": 1.5},
}

def get_miniboss_override(floor_number: int) -> dict | None:
    return MINIBOSS_OVERRIDES.get(floor_number)


GORRATH_BONEBREAKER = {
    "name": "Gorrath the Bonebreaker",
    "abilities": ["cleave", "crushing_blow", "enrage", "last_stand"],
    "spawn_template": "Skeleton",
    "stat_mod": {"atk": 1.3, "def": 1.2, "spd": 0.9, "health": 1.5},
}

ROTCALLER_FESTER_HOST = {
    "name": "The Rotcaller, Warlord of the Fester Host",
    "abilities": ["self_regen", "summon_add", "crushing_blow", "last_stand"],
    "spawn_template": "Rotting Ghoul",
    "stat_mod": {"atk": 1.3, "def": 1.2, "spd": 0.9, "health": 1.6},
}

EARTHSHAKER_TITAN = {
    "name": "The Earthshaker Titan",
    "abilities": ["crushing_blow", "enrage", "last_stand"],
    "spawn_template": "Elemental",
    "stat_mod": {"atk": 1.4, "def": 1.4, "spd": 0.6, "health": 1.8},
}

MORDANE_HOLLOW_KING = {
    "name": "Mordane, the Hollow King",
    "abilities": ["self_regen", "cleave", "crushing_blow", "last_stand"],
    "spawn_template": "Vampire Spawn",
    "stat_mod": {"atk": 1.4, "def": 1.2, "spd": 1.0, "health": 1.6},
}

STORMCALLER_SKY_TYRANT = {
    "name": "The Stormcaller, Sky-Tyrant",
    "abilities": ["cleave", "enrage", "crushing_blow", "last_stand"],
    "spawn_template": "Manticore",
    "stat_mod": {"atk": 1.3, "def": 1.1, "spd": 1.1, "health": 1.5},
}

BOSS_OVERRIDES = {
    20: [TROLL_KING, GORRATH_BONEBREAKER],
    30: HOBGOBLIN_WARLORD,
    40: [GRAVE_SOVEREIGN, ROTCALLER_FESTER_HOST],
    60: [OBSIDIAN_TYRANT, EARTHSHAKER_TITAN],
    70: UNDEAD_MONARCH,
    80: [HYDRA_SOVEREIGN, ASHEN_COLOSSUS, STORMCALLER_SKY_TYRANT],
    90: MASKED_HORROR_BOSS,
    # Floor 100 is a Raid Boss (Aetherion) — this fallback is never reached
    # in normal play because get_raid_boss_override fires first.
    100: [LICH_KING, NIGHTWING_DEVOURER],
}

SPECIAL_BOSS_FLOORS = {50, 100}


def get_boss_override(floor_number: int) -> dict | None:
    entry = BOSS_OVERRIDES.get(floor_number)
    if isinstance(entry, list):
        import random
        return random.choice(entry)
    return entry


# Only two true Raid Boss floors — 50 (halfway) and 100 (final).
RAID_BOSS_OVERRIDES = {
    50: MORDANE_HOLLOW_KING,
    100: AETHERION_END_OF_ALL_THINGS,
}


def get_raid_boss_override(floor_number: int) -> dict | None:
    entry = RAID_BOSS_OVERRIDES.get(floor_number)
    if isinstance(entry, list):
        import random
        return random.choice(entry)
    return entry


# ─── Generic Boss Pool (no LLM fallback) ────────────────────────────────────
#
# Every boss floor without a named BOSS_OVERRIDES entry draws from this pool
# instead of calling the LLM. portrait_path is explicit because these use the
# "boss_<key>.png" naming convention that _enemy_portrait_path can't resolve
# from the display name alone.

GENERIC_BOSS_POOL = [
    {
        "name": "The Juggernaut",
        "portrait_path": "static/portraits/enemies/boss/boss_juggernaut.png",
        "abilities": ["crushing_blow", "enrage", "last_stand"],
        "stat_mod": {"atk": 1.2, "def": 1.4, "spd": 0.7, "health": 1.5},
    },
    {
        "name": "The Specter Tyrant",
        "portrait_path": "static/portraits/enemies/boss/boss_specter_tyrant.png",
        "abilities": ["team_buff_aura", "self_regen", "last_stand"],
        "stat_mod": {"atk": 1.1, "def": 0.9, "spd": 1.3, "health": 1.3},
    },
    {
        "name": "The Feral Titan",
        "portrait_path": "static/portraits/enemies/boss/boss_feral_titan.png",
        "abilities": ["cleave", "enrage", "last_stand"],
        "stat_mod": {"atk": 1.4, "def": 1.0, "spd": 1.1, "health": 1.4},
    },
    {
        "name": "The Stone Titan",
        "portrait_path": "static/portraits/enemies/boss/boss_stone_titan.png",
        "abilities": ["crushing_blow", "last_stand"],
        "stat_mod": {"atk": 1.1, "def": 1.6, "spd": 0.6, "health": 1.6},
    },
    {
        "name": "The Arcane Abomination",
        "portrait_path": "static/portraits/enemies/boss/boss_arcane_abomination.png",
        "abilities": ["team_buff_aura", "summon_add", "last_stand"],
        "stat_mod": {"atk": 1.3, "def": 1.1, "spd": 1.0, "health": 1.4},
    },
    {
        "name": "The Demon Overlord",
        "portrait_path": "static/portraits/enemies/boss/boss_demon_overlord.png",
        "abilities": ["cleave", "crushing_blow", "enrage", "last_stand"],
        "stat_mod": {"atk": 1.4, "def": 1.2, "spd": 1.0, "health": 1.5},
    },
    {
        "name": "Big Greg",
        "portrait_path": "static/portraits/enemies/boss/boss_big_greg.png",
        "abilities": ["crushing_blow", "last_stand"],
        "stat_mod": {"atk": 1.3, "def": 1.2, "spd": 0.9, "health": 1.5},
    },
    {
        "name": "The Dragon",
        "portrait_path": "static/portraits/enemies/boss/boss_dragon.png",
        "abilities": ["cleave", "enrage", "self_regen", "last_stand"],
        "stat_mod": {"atk": 1.4, "def": 1.2, "spd": 1.0, "health": 1.6},
    },
    {
        "name": "The Nightwing Devourer",
        "portrait_path": "static/portraits/enemies/boss/boss_nightwing_devourer.png",
        "abilities": ["cleave", "enrage", "crushing_blow", "last_stand"],
        "stat_mod": {"atk": 1.3, "def": 1.1, "spd": 1.2, "health": 1.4},
    },
]


def get_generic_boss() -> dict:
    import random
    return random.choice(GENERIC_BOSS_POOL)
