"""
Floor Templates Service
=======================
Defines mechanical templates for all floor types beyond standard combat.
All outcomes are deterministic — the backend decides everything, LLM only narrates.

Floor types:
  combat    — Standard fight (existing, handled by combat_service)
  event     — Choice encounter (existing, handled by event_service)
  survival  — A real fight against a larger wave of enemies (handled by tower.py via combat_service)
  defend    — A real fight framed as holding a chokepoint (handled by tower.py via combat_service)
  explore   — Risk/reward discovery. Find loot, traps, or materials.
  escort    — A real fight framed as protecting an NPC (handled by tower.py via combat_service)
  boss      — Every 10th floor. Powerful single enemy.
  rest      — Every floor after boss. Free healing, no combat.
"""

import random

# ─── Floor Type Distribution ───────────────────────────────────────

def get_floor_type(floor_number: int) -> str:
    """Determine floor type based on floor number."""
    # Fixed floors
    if floor_number % 10 == 0:
        return "boss"
    if floor_number % 10 == 5:
        return "miniboss"
    if floor_number % 10 == 1 and floor_number > 1:
        return "rest"

    # Weighted random for other floors — survival/defend/escort are all real
    # fights under a different frame, so combat still dominates the mix.
    weights = {
        "combat": 50,
        "event": 10,
        "explore": 15,
        "survival": 10,
        "defend": 10,
        "escort": 5,
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
    "combat": "The corridor stretches ahead. Something waits in the dark.",
    "miniboss": "A presence looms ahead, stronger than the rest.",
    "boss": "The floor's guardian awaits. There is no other way through.",
    "event": "Something unusual catches your attention.",
    "survival": "Waves of enemies pour from every corridor. There is no retreat — only endurance.",
    "defend": "A narrow passage. Behind you, something worth protecting. They're coming.",
    "explore": "The corridor opens into an unexplored chamber. Dust and silence.",
    "escort": "Someone nearby needs safe passage. Enemies aren't far.",
    "rest": "A safe chamber. Water flows from cracks in the stone.",
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


from services.materials_service import CRAFTING_MATERIALS, tiered_material_name

def _exploration_loot_table(floor_number: int) -> list[dict]:
    """Generate possible loot for this floor level."""
    base_gold = (30 + floor_number * 3) * 3
    mat_name = tiered_material_name(random.choice(CRAFTING_MATERIALS))
    return [
        {"type": "gold", "amount": random.randint(base_gold, base_gold * 2), "desc": f"{base_gold}-{base_gold*2} gold"},
        {"type": "materials", "name": mat_name, "amount": random.randint(2, 4), "desc": f"{mat_name} ×{random.randint(2, 4)}"},
        {"type": "materials", "name": mat_name, "amount": random.randint(3, 5), "desc": f"{mat_name} ×{random.randint(3, 5)}"},
        {"type": "gold", "amount": random.randint(base_gold * 2, base_gold * 3), "desc": f"Large gold cache"},
    ]
    # Higher floors add rarer loot
    # (equipment drops would go here once equipment system exists)


# ─── Escort Floor ──────────────────────────────────────────────────

def generate_escort_floor(floor_number: int) -> dict:
    """Generate an escort floor challenge."""
    npc_names = ["a wounded traveler", "a lost child", "a captured merchant", "a dying scholar"]

    return {
        "floor_type": "escort",
        "theme": f"You find {random.choice(npc_names)} who needs safe passage to the next floor.",
        "npc_hp": 80 + floor_number * 2,
        "ambush_count": min(5, 2 + floor_number // 15),
        "ambush_power": 1 + (floor_number * 0.05),
        "reward": {
            "gold": (random.randint(100, 200) + floor_number * 6) * 3,
            "morale": random.randint(5, 15),
            "materials": random.randint(1, 3),
        },
    }


def resolve_escort_floor(template: dict, heroes: list[dict]) -> dict:
    """Resolve an escort floor. Team ATK/DEF determines if NPC survives."""
    ambushes = template["ambush_count"]
    npc_hp = template["npc_hp"]
    log = []

    total_atk = sum(h.get("strength", 5) for h in heroes)
    total_def = sum(h.get("intelligence", 5) for h in heroes)

    for i in range(ambushes):
        # Heroes intercept damage based on their total ATK
        intercept_pct = min(0.90, total_atk / (total_atk + 50 * template["ambush_power"]))
        npc_damage = int(30 * template["ambush_power"] * (1 - intercept_pct))
        npc_hp -= npc_damage

        hero_damage_pct = random.uniform(0.03, 0.08)

        if npc_hp > 0:
            log.append(f"  Ambush {i+1}: Intercepted! NPC takes {npc_damage} damage. NPC Health: {npc_hp}")
        else:
            log.append(f"  Ambush {i+1}: The NPC fell. You failed to protect them.")
            break

    npc_survived = npc_hp > 0
    hero_results = []
    for hero in heroes:
        dmg = int(hero["max_health"] * random.uniform(0.03, 0.08) * ambushes)
        hero_results.append({
            "id": hero["id"],
            "health": max(1, hero["health"] - dmg),
            "morale_delta": template["reward"]["morale"] if npc_survived else -10,
        })

    return {
        "success": npc_survived,
        "npc_survived": npc_survived,
        "npc_hp": max(0, npc_hp),
        "hero_results": hero_results,
        "reward": template["reward"] if npc_survived else {"gold": template["reward"]["gold"] // 3},
        "log": [f"Escort — {ambushes} ambushes ahead."] + log,
        "summary": f"{'NPC delivered safely!' if npc_survived else 'The NPC was lost.'}",
    }


# ─── Rest Floor ────────────────────────────────────────────────────

def generate_rest_floor(floor_number: int) -> dict:
    """Generate a rest floor — free healing, no combat."""
    return {
        "floor_type": "rest",
        "theme": "A safe chamber. Water flows from cracks in the stone. Your team can rest.",
        "heal_pct": 0.50,  # 50% Health restored
        "stress_reduction": 20,
        "morale_boost": 15,
    }


def resolve_rest_floor(template: dict, heroes: list[dict]) -> dict:
    """Apply rest floor healing to all heroes."""
    hero_results = []
    for hero in heroes:
        heal = int(hero["max_health"] * template["heal_pct"])
        new_hp = min(hero["max_health"], hero["health"] + heal)
        hero_results.append({
            "id": hero["id"],
            "health": new_hp,
            "stress_gained": -template["stress_reduction"],
            "morale_delta": template["morale_boost"],
        })

    return {
        "success": True,
        "hero_results": hero_results,
        "reward": {"gold": 0},
        "log": [
            "Rest — the team finds a moment of peace.",
            "  Water is found. Wounds are tended. The silence is a gift.",
            f"  All heroes recover {int(template['heal_pct']*100)}% Health, -{template['stress_reduction']} stress, +{template['morale_boost']} morale.",
        ],
        "summary": "The team rests and recovers.",
    }
