"""
Floor Templates Service
=======================
Defines mechanical templates for all floor types beyond standard combat.
All outcomes are deterministic — the backend decides everything, LLM only narrates.

Floor types (all are real fights of roughly normal length — the point is
tactical variety, not "combat" as a single undifferentiated default):
  field_combat   — A looser, lower-stakes skirmish
  conquest       — A larger enemy wave to clear by force, no twist beyond the numbers
  war            — The hardest non-boss set-piece fight: biggest wave, toughened stats
  retrieve       — A fight guarding something worth taking; guaranteed bonus loot on a win
  ambush         — Enemies get a guaranteed first strike round 1, regardless of speed
  blitz          — Enemies gain a stacking +20% ATK/SPD every round — a pure burst race
  cursed_ground  — Team starts the fight already debuffed (poisoned + HP cap reduced)
  event          — Choice encounter (existing, handled by event_service)
  survival       — A real fight against a larger wave of enemies
  defend         — A real fight framed as holding a chokepoint
  explore        — Risk/reward discovery. Find loot, traps, or materials.
  escort         — Protect an NPC; a win also gives a small morale boost (the captive's gratitude)
  boss           — Every 10th floor. Powerful single enemy.
  miniboss_*     — Every 5th floor, one of 5 "gear/comp check" variants (see MINIBOSS_VARIANTS)

Rest floors were removed — health no longer carries between floor entries
(a full heal happens on every return to the Tower screen), so a dedicated
"safe, no combat" floor had nothing left to do. Plain undifferentiated
"combat" was removed too, same reasoning pushed further — every regular
floor should change the tactical priority somehow, not just be a generic
fight with a different name on the tin.
"""

import random

# ─── Floor Type Distribution ───────────────────────────────────────

# Miniboss (every 5th floor) rolls one of these instead of always being
# "a slightly beefier guy" — each is a deliberate comp check:
#   survival — endurance check (sustain through a real wave, see is_survival_swarm)
#   behemoth — DPS check (huge HP/DEF, tiny ATK — can you crack it before bleeding out)
#   assassin — tank check (huge speed/burst — no frontline means a one-shot squishy)
#   twins    — damage-type check (one physical-resistant, one magic-resistant elite)
#   mirror   — mirror-match (shadow clones of the deployed team's own classes/stats)
MINIBOSS_VARIANTS = ["survival", "behemoth", "assassin", "twins"]


def get_floor_type(floor_number: int) -> str:
    """Determine floor type based on floor number."""
    # Fixed floors
    if floor_number % 10 == 0:
        return "boss"
    if floor_number % 10 == 5:
        return f"miniboss_{random.choice(MINIBOSS_VARIANTS)}"

    # Weighted random for every other floor — every entry here is a real
    # fight, just with a different tactical hook. No plain "combat" anymore.
    weights = {
        "field_combat": 15,
        "conquest": 6,
        "war": 3,
        "retrieve": 6,
        "ambush": 10,
        "blitz": 8,
        "cursed_ground": 7,
        "event": 12,
        "explore": 15,
        "survival": 6,
        "defend": 6,
        "escort": 6,
    }

    types = list(weights.keys())
    wts = list(weights.values())
    return random.choices(types, weights=wts, k=1)[0]


def get_cached_floor_type(conn, floor_number: int) -> str:
    """Floor type is rolled once per floor number and cached — re-entering
    (rerun) or merely previewing a floor must always show the same type."""
    row = conn.execute("SELECT floor_type FROM floor_cache WHERE floor_number = ?", (floor_number,)).fetchone()
    if row:
        return row["floor_type"]
    floor_type = get_floor_type(floor_number)
    conn.execute("INSERT INTO floor_cache (floor_number, floor_type) VALUES (?, ?)", (floor_number, floor_type))
    return floor_type


# One-line flavor/intro text per floor type, shared by the pre-floor preview
# card (shown only for floors not yet visited) and the actual combat log
# framing — keeps what the player previews consistent with what they get.
FLOOR_FLAVOR_INTRO = {
    "miniboss": "A presence looms ahead, stronger than the rest.",
    "miniboss_survival": "Something enormous stirs. The walls themselves seem to be breathing.",
    "miniboss_behemoth": "The ground shakes with every step it takes. This will be a war of attrition.",
    "miniboss_assassin": "Silence. Too much silence — and then it's already moving.",
    "miniboss_twins": "Two shapes step out of the dark together, watching you with one mind.",
    "boss": "The floor's guardian awaits. There is no other way through.",
    "event": "Something unusual catches your attention.",
    "survival": "Waves of enemies pour from every corridor. There is no retreat — only endurance.",
    "defend": "A narrow passage. Behind you, something worth protecting. They're coming.",
    "explore": "The corridor opens into an unexplored chamber. Dust and silence.",
    "escort": "Someone nearby needs safe passage. Enemies aren't far.",
    "field_combat": "An open chamber. Footing is loose, but there's room to fight.",
    "conquest": "A war band holds this floor. Every last one of them stands between you and the stairs up.",
    "war": "Banners, fire, and steel — this floor is a battlefield in miniature, and you've just walked into it.",
    "retrieve": "Something valuable is held here, guarded. Take it from them.",
    "ambush": "The corridor is too quiet. Too late — they were waiting.",
    "blitz": "The air crackles with something that isn't yours. Whatever's here, it's getting stronger by the second.",
    "cursed_ground": "The air here is wrong — your team feels it the moment they step through.",
}


# ─── Explore Floor ─────────────────────────────────────────────────

def generate_explore_floor(floor_number: int) -> dict:
    """Generate an explore floor with risk/reward choices. Every choice still
    leads to a real fight (combat is mandatory on every floor type) — the
    choice decides how big/hard that fight is, and the loot odds that follow
    a win."""
    return {
        "floor_type": "explore",
        "theme": "The corridor opens into an unexplored chamber. Dust and silence.",
        "discovery_chance": min(0.80, 0.50 + floor_number * 0.005),
        "trap_chance": min(0.35, 0.10 + floor_number * 0.004),
        "choices": [
            {
                "id": "thorough",
                "label": "Search Thoroughly",
                "hint": "A genuinely harder fight, better loot odds",
                "difficulty_mult": 1.8,
                "discovery_bonus": 0.20,
                "trap_bonus": 0.15,
                "time_cost": 2,
            },
            {
                "id": "quick",
                "label": "Quick Sweep",
                "hint": "A normal fight, standard loot odds",
                "difficulty_mult": 1.0,
                "discovery_bonus": -0.10,
                "trap_bonus": -0.10,
                "time_cost": 1,
            },
            {
                "id": "leave",
                "label": "Fight Defensively",
                "hint": "The weakest fight possible — safest, worst loot odds",
                "difficulty_mult": 0.4,
                "discovery_bonus": -1.0,
                "trap_bonus": -1.0,
                "time_cost": 0,
            },
        ],
        "loot_table": _exploration_loot_table(floor_number),
    }


def get_explore_choice(template: dict, choice_id: str) -> dict:
    """Look up a choice by id, defaulting to Quick Sweep if unrecognized."""
    return next((c for c in template["choices"] if c["id"] == choice_id), template["choices"][1])


def resolve_explore_loot(template: dict, choice: dict, avg_luck: float = 5.0) -> dict:
    """Roll for bonus loot after a real fight has already been won — the
    fight itself (sized by enemy_count_mod) carries the actual danger now;
    this just decides what extra the choice's thoroughness turned up.
    avg_luck is the deployed team's average Luck stat (team-wide, not a
    single hero) nudging the discovery roll, same pattern as combat's
    equipment drop bonus."""
    log = []
    discovery = template["discovery_chance"] + choice["discovery_bonus"] + (avg_luck / 200)
    found_something = random.random() < discovery

    loot = {}
    if found_something:
        loot = random.choice(template["loot_table"])
        log.append(f"  Discovery! Found: {loot.get('desc', 'something useful')}")
    else:
        log.append("  Nothing more of value here.")

    return {
        "success": found_something,
        "loot": loot,
        "log": log,
        "summary": "Found treasure!" if found_something else "Nothing else of note.",
    }


from services.materials_service import roll_material_name, tiered_material_name

def _exploration_loot_table(floor_number: int) -> list[dict]:
    """Generate possible loot for this floor level."""
    base_gold = (30 + floor_number * 3) * 3
    mat_name = tiered_material_name(roll_material_name(floor_number))
    return [
        {"type": "gold", "amount": random.randint(base_gold, base_gold * 2), "desc": f"{base_gold}-{base_gold*2} gold"},
        {"type": "materials", "name": mat_name, "amount": random.randint(2, 4), "desc": f"{mat_name} ×{random.randint(2, 4)}"},
        {"type": "materials", "name": mat_name, "amount": random.randint(3, 5), "desc": f"{mat_name} ×{random.randint(3, 5)}"},
        {"type": "gold", "amount": random.randint(base_gold * 2, base_gold * 3), "desc": f"Large gold cache"},
    ]
    # Higher floors add rarer loot
    # (equipment drops would go here once equipment system exists)


# Escort floors are real turn-based combat now (an NPC CombatUnit the team
# protects — see combat_service.py's is_escort handling), not resolved
# here. This used to hold a standalone interception-math resolver
# (generate_escort_floor/resolve_escort_floor) that had zero callers —
# tower.py already routed floor_type=="escort" through the same real-combat
# path as every other combat floor type, just without an NPC or alternate
# win condition. Removed rather than left to mislead the next reader.

# Rest floors removed — see module docstring. generate_rest_floor/
# resolve_rest_floor used to live here (free healing, no combat); deleted
# rather than left dead, since health no longer persists between floors.
