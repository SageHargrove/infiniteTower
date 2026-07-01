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
every %10 floor (floor 50's lives in RAID_BOSS_OVERRIDES instead of
BOSS_OVERRIDES — see below). The multi-team Raid Boss merge used to only
trigger on floors that are multiples of 20 (20/40/60/80/100) — floor 50
(the halfway point) is now also included, given how significant a
milestone it is despite not landing on a multiple of 20.
"""

# ─── Floors 1-10: Shadow Wisp / Goblin / Giant Spider / Wolf ────────────

GOBLIN_KING = {
    "name": "Goblin King",
    "abilities": ["summon_add", "cleave"],
    "spawn_template": "Goblin",
    "stat_mod": {"atk": 1.0, "def": 1.0, "spd": 1.0, "health": 1.1},
}

WARREN_TYRANT = {
    "name": "The Warren Tyrant",
    "abilities": ["summon_add", "crushing_blow", "last_stand"],
    "spawn_template": "Giant Spider",
    "stat_mod": {"atk": 1.1, "def": 1.0, "spd": 0.9, "health": 1.2},
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

BOSS_OVERRIDES = {
    10: WARREN_TYRANT,
    20: TROLL_KING,
    30: HOBGOBLIN_WARLORD,
    40: GRAVE_SOVEREIGN,
    60: OBSIDIAN_TYRANT,
    70: UNDEAD_MONARCH,
    80: HYDRA_SOVEREIGN,
    90: MASKED_HORROR_BOSS,
    # A third, brand-new pick alongside the two preserved-art bosses — floor
    # 100 is the final floor and asked for something extra, but Lich King/
    # Nightwing Devourer are explicitly preserved-favorite art, not to be
    # displaced, so this adds variety rather than replacing either.
    100: [LICH_KING, NIGHTWING_DEVOURER, AETHERION_END_OF_ALL_THINGS],
}

# Floor 50 (the tower's halfway point) now also triggers the Raid Boss
# merge (see RAID_BOSS_OVERRIDES below, extended this pass to cover it).
# Floor 100 (the final floor) gets a third random pick added above instead
# — content-complete either way, no longer just a marker.
SPECIAL_BOSS_FLOORS = {50, 100}


def get_miniboss_override(floor_number: int) -> dict | None:
    return MINIBOSS_OVERRIDES.get(floor_number)


def get_boss_override(floor_number: int) -> dict | None:
    entry = BOSS_OVERRIDES.get(floor_number)
    if isinstance(entry, list):
        import random
        return random.choice(entry)
    return entry


# ─── Raid Bosses (every 20th floor, multi-team merge) ──────────────────────
#
# The original roster-overhaul plan named four tiers — elite/miniboss/boss/
# raid_boss — but raid_boss was never built; floor 20/40/60/80 just reused
# that floor's regular %10 boss scaled up for the combined team size. These
# give floors 20/40/60/80 their own unique, tougher-than-the-regular-boss
# identity, themed as the culmination of the two decades feeding into them.
# Floor 100 keeps its existing Lich King/Nightwing Devourer treatment —
# already has dedicated raid-scale specialness, doesn't need a 5th entry.

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

# Floor 50 (the halfway point) gets a second pick alongside Ashen Colossus,
# same random-variety treatment as floor 100 gets below in BOSS_OVERRIDES.
STORMCALLER_SKY_TYRANT = {
    "name": "The Stormcaller, Sky-Tyrant",
    "abilities": ["cleave", "enrage", "crushing_blow", "last_stand"],
    "spawn_template": "Manticore",
    "stat_mod": {"atk": 1.3, "def": 1.1, "spd": 1.1, "health": 1.5},
}

RAID_BOSS_OVERRIDES = {
    20: GORRATH_BONEBREAKER,
    40: ROTCALLER_FESTER_HOST,
    50: [ASHEN_COLOSSUS, STORMCALLER_SKY_TYRANT],
    60: EARTHSHAKER_TITAN,
    80: MORDANE_HOLLOW_KING,
}


def get_raid_boss_override(floor_number: int) -> dict | None:
    entry = RAID_BOSS_OVERRIDES.get(floor_number)
    if isinstance(entry, list):
        import random
        return random.choice(entry)
    return entry
