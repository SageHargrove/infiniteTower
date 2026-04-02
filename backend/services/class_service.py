"""
Class System
============
Handles class assignment, class effects in combat, and base class passives.

Combat Classes (tower):
  Warrior, Spearman, Thief, Archer, Mage, Magic Engineer

Base Classes (home):
  Chef, Medic, Scout, Blacksmith, Quartermaster, Tactician, Priest, Alchemist

Classless: weak in tower, inefficient at base tasks
"""

import random

# ---------------------------------------------------------------------------
# Class definitions
# ---------------------------------------------------------------------------

COMBAT_CLASSES = ["Warrior", "Spearman", "Thief", "Archer", "Mage", "Magic Engineer"]
BASE_CLASSES   = ["Chef", "Medic", "Scout", "Blacksmith", "Quartermaster", "Tactician", "Priest", "Alchemist"]
ALL_CLASSES    = COMBAT_CLASSES + BASE_CLASSES + ["Classless"]

# Weights within combat class pool (per star)
# Format: {class: weight}
COMBAT_WEIGHTS_BY_STAR = {
    1: {},  # no combat classes
    2: {},
    3: {"Warrior": 25, "Spearman": 25, "Thief": 25, "Archer": 25, "Mage": 4,  "Magic Engineer": 0},
    4: {"Warrior": 22, "Spearman": 22, "Thief": 22, "Archer": 22, "Mage": 8,  "Magic Engineer": 1},
    5: {"Warrior": 20, "Spearman": 20, "Thief": 20, "Archer": 20, "Mage": 12, "Magic Engineer": 2},
    6: {"Warrior": 18, "Spearman": 18, "Thief": 18, "Archer": 18, "Mage": 16, "Magic Engineer": 3},
    7: {"Warrior": 16, "Spearman": 16, "Thief": 16, "Archer": 16, "Mage": 20, "Magic Engineer": 4},
}

BASE_CLASSES_EQUAL = {c: 1 for c in BASE_CLASSES}

# Probability of each category by star
# (combat_pct, base_pct, classless_pct) — must sum to 100
CLASS_CATEGORY_RATES = {
    1: (0,  15, 85),
    2: (0,  20, 80),
    3: (55, 20, 25),
    4: (65, 28,  7),
    5: (72, 28,  0),
    6: (74, 26,  0),
    7: (76, 24,  0),
}

# ---------------------------------------------------------------------------
# Class assignment
# ---------------------------------------------------------------------------

def assign_class(birth_star: int) -> str:
    """Roll a class for a hero based on birth star."""
    combat_pct, base_pct, classless_pct = CLASS_CATEGORY_RATES[birth_star]

    roll = random.uniform(0, 100)
    if roll < combat_pct:
        category = "combat"
    elif roll < combat_pct + base_pct:
        category = "base"
    else:
        category = "classless"

    if category == "classless":
        return "Classless"

    if category == "base":
        return random.choice(BASE_CLASSES)

    # Combat class — weighted by star
    weights = COMBAT_WEIGHTS_BY_STAR.get(birth_star, {})
    weights = {k: v for k, v in weights.items() if v > 0}
    if not weights:
        return "Classless"

    classes = list(weights.keys())
    wts = list(weights.values())
    return random.choices(classes, weights=wts, k=1)[0]

def is_combat_class(hero_class: str) -> bool:
    return hero_class in COMBAT_CLASSES

def is_base_class(hero_class: str) -> bool:
    return hero_class in BASE_CLASSES

def can_pilot(hero_class: str) -> bool:
    return hero_class == "Magic Engineer"

# ---------------------------------------------------------------------------
# Combat stat modifiers by class
# ---------------------------------------------------------------------------

def apply_class_combat_modifiers(hero: dict) -> dict:
    """
    Apply class-based stat modifiers to a hero dict before combat.
    Returns modified copy — does NOT write to DB.
    """
    h = hero.copy()
    cls = h.get("hero_class", "Classless")

    if cls == "Warrior":
        h["defense"] = int(h["defense"] * 1.20)
        h["hp"] = int(h["hp"] * 1.15)
        h["max_hp"] = int(h["max_hp"] * 1.15)

    elif cls == "Spearman":
        h["attack"] = int(h["attack"] * 1.15)
        h["speed"] = int(h["speed"] * 1.10)  # reach bonus

    elif cls == "Thief":
        h["speed"] = int(h["speed"] * 1.30)
        h["crit_chance"] = h.get("crit_chance", 0.05) + 0.15
        h["dodge_chance"] = h.get("dodge_chance", 0.0) + 0.10

    elif cls == "Archer":
        h["attack"] = int(h["attack"] * 1.10)
        h["is_ranged"] = True  # backline protection

    elif cls == "Mage":
        h["is_aoe"] = True   # hits all enemies
        h["attack"] = int(h["attack"] * 0.85)  # lower per-hit, but AoE

    elif cls == "Magic Engineer":
        h["has_construct"] = True  # deploys construct that tanks one hit
        h["attack"] = int(h["attack"] * 0.90)

    elif cls == "Classless":
        # Significant penalty — classless heroes are genuinely weak
        h["attack"]  = int(h["attack"]  * 0.75)
        h["defense"] = int(h["defense"] * 0.75)
        h["speed"]   = int(h["speed"]   * 0.90)

    return h

# ---------------------------------------------------------------------------
# Base class effects
# ---------------------------------------------------------------------------

def get_base_class_rest_bonus(hero_class: str, hero_level: int) -> dict:
    """
    Returns rest bonuses granted by base class heroes.
    Called during base rest. Scales slightly with hero level.
    """
    scale = 1.0 + (hero_level * 0.02)  # 2% better per level

    bonuses = {
        "Chef":          {"morale_bonus": int(8 * scale),  "stress_reduction": int(5 * scale)},
        "Medic":         {"hp_restore_pct": min(0.30, 0.15 * scale), "trauma_reduction": int(3 * scale)},
        "Priest":        {"morale_bonus": int(5 * scale),  "trauma_reduction": int(6 * scale)},
        "Tactician":     {"team_atk_bonus": int(2 * scale)},
        "Blacksmith":    {"team_def_bonus": int(2 * scale)},
        "Quartermaster": {"gold_bonus_pct": min(0.25, 0.10 * scale)},
        "Scout":         {},  # Scout effect is on floor entry, not rest
        "Alchemist":     {"material_bonus": int(1 * scale)},
    }
    return bonuses.get(hero_class, {})

def get_scout_floor_info(floor_number: int) -> str:
    """Scout reveals next floor type. Called before floor entry."""
    from services.tower_service import get_floor_type
    next_type = get_floor_type(floor_number + 1)
    return f"Scout reports: Floor {floor_number + 1} is a {next_type} encounter."

# ---------------------------------------------------------------------------
# Class display helpers
# ---------------------------------------------------------------------------

CLASS_ICONS = {
    "Warrior":        "⚔",
    "Spearman":       "🗡",
    "Thief":          "🗝",
    "Archer":         "🏹",
    "Mage":           "✦",
    "Magic Engineer": "⚙",
    "Chef":           "🍖",
    "Medic":          "✚",
    "Scout":          "👁",
    "Blacksmith":     "🔨",
    "Quartermaster":  "💰",
    "Tactician":      "♟",
    "Priest":         "☽",
    "Alchemist":      "⚗",
    "Classless":      "—",
}

CLASS_DESCRIPTIONS = {
    "Warrior":        "Frontline fighter. High DEF and HP.",
    "Spearman":       "Reach attacker. Strikes fast with bonus ATK.",
    "Thief":          "Lightning fast. High crit and dodge chance.",
    "Archer":         "Backline ranged. Protected until frontline falls.",
    "Mage":           "Hits all enemies each turn. Rare and powerful.",
    "Magic Engineer": "Combat utility. Deploys construct, can pilot vessels.",
    "Chef":           "Boosts morale recovery and stress relief at base.",
    "Medic":          "Restores HP and reduces trauma between floors.",
    "Scout":          "Reveals the next floor type before entry.",
    "Blacksmith":     "Improves team DEF through equipment upkeep.",
    "Quartermaster":  "Increases gold found on resource floors.",
    "Tactician":      "Boosts team ATK through strategic planning.",
    "Priest":         "Slowly heals trauma. Keeps spirits from breaking.",
    "Alchemist":      "Crafts useful items from tower materials.",
    "Classless":      "No formal training. Weaker in all areas.",
}
