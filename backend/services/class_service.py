"""
Class System
============
Handles class assignment, evolutions, class effects in combat, and base class passives.
"""

import random

# ---------------------------------------------------------------------------
# Class Evolution Trees
# ---------------------------------------------------------------------------

# { BaseClass: { 30: [Evo1, Evo2, Evo3], 60: { Evo1: [Evo1a, Evo1b], ... } } }
CLASS_EVOLUTIONS = {
    # COMBAT
    "Warrior": {
        30: ["Knight", "Berserker", "Paladin"],
        60: {
            "Knight": ["Aegis", "Templar"],
            "Berserker": ["Bloodrager", "Juggernaut"],
            "Paladin": ["Crusader", "Divine Sentinel"]
        }
    },
    "Spearman": {
        30: ["Lancer", "Halberdier", "Dragoon"],
        60: {
            "Lancer": ["Pikemaster", "Vanguard"],
            "Halberdier": ["Glaive Lord", "Warlord"],
            "Dragoon": ["Wyvern Rider", "Dragon Knight"]
        }
    },
    "Thief": {
        30: ["Assassin", "Rogue", "Ninja"],
        60: {
            "Assassin": ["Shadowblade", "Phantom"],
            "Rogue": ["Nightstalker", "Trickster"],
            "Ninja": ["Shinobi", "Shadowmaster"]
        }
    },
    "Archer": {
        30: ["Sniper", "Ranger", "Crossbowman"],
        60: {
            "Sniper": ["Marksman", "Deadeye"],
            "Ranger": ["Beastmaster", "Warden"],
            "Crossbowman": ["Arbalist", "Siege Master"]
        }
    },
    "Mage": {
        30: ["Sorcerer", "Warlock", "Necromancer", "Summoner"],
        60: {
            "Sorcerer": ["Archmage", "Elementalist"],
            "Warlock": ["Demonologist", "Voidwalker"],
            "Necromancer": ["Lich", "Deathcaller"],
            "Summoner": ["Grand Summoner", "Conjurer"]
        }
    },
    "Spellsword": {
        30: ["Eldritch Knight", "Rune Blade"],
        60: {
            "Eldritch Knight": ["Arcane Lord", "Mystic Vanguard"],
            "Rune Blade": ["Rune Master", "Spellweaver"]
        }
    },
    "Acolyte": {
        30: ["Cleric", "Bard", "Druid", "Monk"],
        60: {
            "Cleric": ["High Priest", "Bishop"],
            "Bard": ["Maestro", "Troubadour"],
            "Druid": ["Archdruid", "Hierophant"],
            "Monk": ["Grandmaster", "Zenith"]
        }
    },
    "Tactician": {
        30: ["Strategist"],
        60: {"Strategist": ["Grand Strategist", "War Master"]}
    },
    "Scout": {
        30: ["Pathfinder"],
        60: {"Pathfinder": ["Trailblazer", "Void Walker"]}
    },
    "Blacksmith": {
        30: ["Master Smith"],
        60: {"Master Smith": ["Forge Lord", "Runesmith"]}
    },
    "Chef": {
        30: ["Head Chef"],
        60: {"Head Chef": ["Culinary Master", "Brewmaster"]}
    },
    "Medic": {
        30: ["Field Medic"],
        60: {"Field Medic": ["Surgeon", "Miracle Worker"]}
    },
    "Quartermaster": {
        30: ["Logistics Officer"],
        60: {"Logistics Officer": ["Guild Treasurer", "Trade Baron"]}
    },
    "Farmer": {
        30: ["Master Farmer", "Beast Tamer"],
        60: {
            "Master Farmer": ["Harvest Lord", "Nature's Chosen"],
            "Beast Tamer": ["Apex Predator", "Wild Master"]
        }
    },
    "Merchant": {
        30: ["Trader", "Smuggler"],
        60: {
            "Trader": ["Guild Master", "Trade Prince"],
            "Smuggler": ["Black Market Baron", "Shadow Broker"]
        }
    },
    "Alchemist": {
        30: ["Master Alchemist"],
        60: {"Master Alchemist": ["Transmuter", "Philosopher"]}
    },
    "Classless": {
        30: ["Adventurer", "Mercenary", "Hero"],
        60: {
            "Adventurer": ["Veteran"],
            "Mercenary": ["Bounty Hunter"],
            "Hero": ["Champion"]
        }
    },
    "Magic Engineer": {
        30: [], 60: {} # Pinnacle class
    },
    
    # BASE / SUPPORT
    "Blacksmith": {
        30: ["Weaponsmith", "Armorer", "Artificer"],
        60: {
            "Weaponsmith": ["Master Smith"],
            "Armorer": ["Forge Lord"],
            "Artificer": ["Runesmith"]
        }
    },
    "Alchemist": {
        30: ["Apothecary", "Transmuter", "Poisoner"],
        60: {
            "Apothecary": ["Grand Alchemist"],
            "Transmuter": ["Philosopher"],
            "Poisoner": ["Brewmaster"]
        }
    },
    "Chef": {
        30: ["Sous Chef", "Forager", "Butcher"],
        60: {
            "Sous Chef": ["Master Chef"],
            "Forager": ["Gourmet"],
            "Butcher": ["Iron Chef"]
        }
    },
    "Medic": {
        30: ["Surgeon", "Herbalist", "Field Medic"],
        60: {
            "Surgeon": ["Chief Medical Officer"],
            "Herbalist": ["Miracle Worker"],
            "Field Medic": ["Plague Doctor"]
        }
    },
    "Quartermaster": {
        30: ["Merchant", "Logistics Officer", "Scavenger"],
        60: {
            "Merchant": ["Tycoon"],
            "Logistics Officer": ["Guildmaster"],
            "Scavenger": ["Hoarder"]
        }
    },
    "Tactician": {
        30: ["Strategist", "Commander", "Advisor"],
        60: {
            "Strategist": ["Grand Strategist"],
            "Commander": ["General"],
            "Advisor": ["Warlord"]
        }
    },
    "Scout": {
        30: ["Pathfinder", "Tracker", "Spy"],
        60: {
            "Pathfinder": ["Ranger"],
            "Tracker": ["Infiltrator"],
            "Spy": ["Spymaster"]
        }
    },
    "Priest": {
        30: ["Confessor", "Oracle", "Chaplain"],
        60: {
            "Confessor": ["High Confessor"],
            "Oracle": ["Prophet"],
            "Chaplain": ["Saint"]
        }
    }
}

COMBAT_BASE_CLASSES = ["Warrior", "Spearman", "Thief", "Archer", "Mage", "Acolyte", "Magic Engineer", "Spellsword"]
SUPPORT_BASE_CLASSES = ["Chef", "Medic", "Scout", "Blacksmith", "Quartermaster", "Tactician", "Priest", "Alchemist", "Merchant", "Farmer"]
BASE_CLASSES = SUPPORT_BASE_CLASSES # Legacy naming convention

# Weights within combat class pool (per star)
COMBAT_WEIGHTS_BY_STAR = {
    1: {},
    2: {},
    3: {"Warrior": 20, "Spearman": 20, "Thief": 20, "Archer": 20, "Mage": 4, "Acolyte": 16, "Magic Engineer": 0, "Spellsword": 0},
    4: {"Warrior": 18, "Spearman": 18, "Thief": 18, "Archer": 18, "Mage": 8, "Acolyte": 18, "Magic Engineer": 1, "Spellsword": 4},
    5: {"Warrior": 15, "Spearman": 15, "Thief": 15, "Archer": 15, "Mage": 15, "Acolyte": 15, "Magic Engineer": 2, "Spellsword": 6},
    6: {"Warrior": 15, "Spearman": 15, "Thief": 15, "Archer": 15, "Mage": 20, "Acolyte": 15, "Magic Engineer": 3, "Spellsword": 8},
    7: {"Warrior": 12, "Spearman": 12, "Thief": 12, "Archer": 12, "Mage": 25, "Acolyte": 15, "Magic Engineer": 4, "Spellsword": 10},
}

CLASS_CATEGORY_RATES = {
    1: (0,  15, 85),
    2: (0,  20, 80),
    3: (55, 20, 25),
    4: (65, 28,  7),
    5: (72, 28,  0),
    6: (96,  4,  0),
    7: (100, 0,  0),
}

# Recursively get all classes in tree
def _get_all_evolutions():
    all_evos = set()
    for base, evos in CLASS_EVOLUTIONS.items():
        all_evos.add(base)
        for e in evos.get(30, []): all_evos.add(e)
        for tier60 in evos.get(60, {}).values():
            for e in tier60: all_evos.add(e)
    return list(all_evos)

ALL_CLASSES = _get_all_evolutions()

def get_class_evolution_options(hero_class: str, level: int) -> list[str]:
    """Returns available evolution options for a given class at a specific level."""
    for base_cls, evos in CLASS_EVOLUTIONS.items():
        if level >= 30 and hero_class == base_cls:
            return evos.get(30, [])
        if level >= 60:
            if hero_class in evos.get(60, {}):
                return evos[60][hero_class]
    return []

# ---------------------------------------------------------------------------
# Class assignment
# ---------------------------------------------------------------------------

def assign_class(birth_star: int) -> tuple[str, str]:
    combat_pct, base_pct, classless_pct = CLASS_CATEGORY_RATES[birth_star]

    roll = random.uniform(0, 100)
    if roll < combat_pct:
        category = "combat"
    elif roll < combat_pct + base_pct:
        category = "base"
    else:
        category = "classless"

    if category == "classless":
        actual_class = "Classless"
    elif category == "base":
        if birth_star == 6:
            # 6-star base classes are exclusively Blacksmith due to combat scaling
            actual_class = "Blacksmith"
        else:
            actual_class = random.choice(SUPPORT_BASE_CLASSES)
    else:
        # Weighted roll for combat classes
        pool = COMBAT_WEIGHTS_BY_STAR.get(birth_star, {})
        weights = {k: v for k, v in pool.items() if v > 0}
        if not weights:
            actual_class = "Classless"
        else:
            classes = list(weights.keys())
            wts = list(weights.values())
            actual_class = random.choices(classes, weights=wts, k=1)[0]
            
    if birth_star <= 2 and actual_class != "Classless":
        return ("Classless", actual_class)
    return (actual_class, None)

def is_combat_class(hero_class: str) -> bool:
    # A support class can still be deployed, but typically combat classes have stats
    # For now, anything that isn't explicitly a base support class is combat capable.
    # Scout and Tactician are deployed classes too now.
    return hero_class not in ["Chef", "Blacksmith", "Quartermaster", "Alchemist", "Priest"]

def is_base_class(hero_class: str) -> bool:
    return hero_class in SUPPORT_BASE_CLASSES

def can_pilot(hero_class: str) -> bool:
    return hero_class == "Magic Engineer"

# ---------------------------------------------------------------------------
# Combat stat modifiers by class
# ---------------------------------------------------------------------------
# Using a dict to cleanly apply stats. Supports flat boosts, multipliers, and flags.
# Modifiers compound (e.g. Knight is applied ON TOP of Warrior if we wanted, but we replace the class entirely, so stats should be absolute for the tier)

CLASS_MODIFIERS = {
    # Tier 1 Combat
    "Warrior": {"def_mult": 1.20, "hp_mult": 1.15},
    "Spearman": {"atk_mult": 1.15, "spd_mult": 1.10},
    "Thief": {"spd_mult": 1.30, "crit_add": 0.15, "dodge_add": 0.10},
    "Archer": {"atk_mult": 1.10, "is_ranged": True},
    "Spellsword": {"atk_mult": 1.10, "def_mult": 0.90, "is_aoe": True, "power_stat": "intelligence"},
    "Mage": {"atk_mult": 0.85, "is_aoe": True, "power_stat": "intelligence"},
    "Acolyte": {"hp_mult": 1.10, "is_healer": True, "power_stat": "intelligence"},
    "Magic Engineer": {"atk_mult": 0.90, "has_construct": True, "power_stat": "intelligence"},
    "Classless": {"atk_mult": 0.75, "def_mult": 0.75, "spd_mult": 0.90},

    # Tier 2 Combat (Lv 30) - Massive Boosts
    "Knight": {"def_mult": 1.60, "hp_mult": 1.40, "has_taunt": True},
    "Berserker": {"atk_mult": 1.50, "def_mult": 0.70, "hp_mult": 1.20, "lifesteal": 0.1},
    "Paladin": {"def_mult": 1.30, "hp_mult": 1.30, "is_healer": True},
    "Lancer": {"atk_mult": 1.30, "spd_mult": 1.20, "armor_pen": 0.5},
    "Halberdier": {"atk_mult": 1.40, "is_cleave": True},
    "Dragoon": {"atk_mult": 1.40, "spd_mult": 1.30, "dodge_add": 0.15},
    "Assassin": {"atk_mult": 1.50, "spd_mult": 1.50, "crit_add": 0.30},
    "Rogue": {"spd_mult": 1.40, "dodge_add": 0.25, "crit_add": 0.20},
    "Ninja": {"spd_mult": 1.60, "dodge_add": 0.20, "multi_hit": 2},
    "Sniper": {"atk_mult": 1.40, "is_ranged": True, "crit_add": 0.25},
    "Ranger": {"atk_mult": 1.20, "is_ranged": True, "has_pet": True},
    "Crossbowman": {"atk_mult": 1.50, "spd_mult": 0.90, "is_ranged": True},
    "Sorcerer": {"atk_mult": 1.20, "is_aoe": True, "power_stat": "intelligence"},
    "Warlock": {"atk_mult": 1.10, "is_aoe": True, "lifesteal": 0.3, "power_stat": "intelligence"},
    "Necromancer": {"atk_mult": 1.0, "is_aoe": True, "summons_undead": True, "power_stat": "intelligence"},
    "Summoner": {"atk_mult": 0.9, "summons_beast": True, "has_construct": True, "hp_mult": 1.5, "power_stat": "intelligence"},
    "Cleric": {"def_mult": 1.20, "is_healer": True, "strong_heal": True, "power_stat": "intelligence"},
    "Bard": {"spd_mult": 1.30, "team_buff": True},
    "Druid": {"hp_mult": 1.40, "is_healer": True, "power_stat": "intelligence"},
    "Monk": {"atk_mult": 1.30, "spd_mult": 1.30, "dodge_add": 0.15},
    
    # Support Deployed (Lv 1)
    "Tactician": {"team_atk_mult": 1.10},
    "Scout": {"team_spd_mult": 1.10},
    
    # Tier 2 Support Deployed (Lv 30)
    "Strategist": {"team_end_mult": 1.20},
    "Commander": {"team_atk_mult": 1.25},
    "Advisor": {"team_xp_mult": 1.20},
    "Pathfinder": {"trap_immune": True},
    "Tracker": {"rare_find_mult": 1.5},
    "Spy": {"floor_reveal": 3},
}

def apply_class_combat_modifiers(hero: dict) -> dict:
    h = hero.copy()
    cls = h.get("hero_class", "Classless")
    
    mods = CLASS_MODIFIERS.get(cls, {})
    
    h["strength"] = int(h["strength"] * mods.get("atk_mult", 1.0))
    h["intelligence"] = int(h["intelligence"] * mods.get("atk_mult", 1.0) if mods.get("power_stat") == "intelligence" else h["intelligence"])
    h["defense"] = int(h.get("defense", 5) * mods.get("def_mult", 1.0))
    h["endurance"] = int(h.get("endurance", h.get("defense", 5)) * mods.get("def_mult", 1.0))
    h["agility"] = int(h["agility"] * mods.get("spd_mult", 1.0))
    h["max_health"] = int(h["max_health"] * mods.get("hp_mult", 1.0))
    h["health"] = int(h["health"] * mods.get("hp_mult", 1.0))
    h["power_stat"] = mods.get("power_stat", "strength")

    h["crit_chance"] = h.get("crit_chance", 0.05) + mods.get("crit_add", 0.0)
    h["dodge_chance"] = h.get("dodge_chance", 0.0) + mods.get("dodge_add", 0.0)

    for flag in ["is_ranged", "is_aoe", "has_construct", "has_taunt", "is_healer", "strong_heal", "is_cleave", "summons_undead", "summons_beast", "team_buff"]:
        if mods.get(flag):
            h[flag] = True

    if "lifesteal" in mods: h["lifesteal"] = mods["lifesteal"]
    if "armor_pen" in mods: h["armor_pen"] = mods["armor_pen"]
    if "multi_hit" in mods: h["multi_hit"] = mods["multi_hit"]
    leader_mult = 1.5 if h.get("is_team_leader") else 1.0
    if "team_atk_mult" in mods: h["team_atk_mult"] = 1.0 + ((mods["team_atk_mult"] - 1.0) * leader_mult)
    if "team_end_mult" in mods: h["team_end_mult"] = 1.0 + ((mods["team_end_mult"] - 1.0) * leader_mult)
    if "team_spd_mult" in mods: h["team_spd_mult"] = 1.0 + ((mods["team_spd_mult"] - 1.0) * leader_mult)
    
    return h

# ---------------------------------------------------------------------------
# Base class effects
# ---------------------------------------------------------------------------

def get_base_class_rest_bonus(hero_class: str, hero_level: int) -> dict:
    scale = 1.0 + (hero_level * 0.02)
    
    bonuses = {
        "Chef":          {"morale_bonus": int(8 * scale),  "stress_reduction": int(5 * scale)},
        "Master Chef":   {"morale_bonus": int(15 * scale), "stress_reduction": int(10 * scale)},
        "Medic":         {"hp_restore_pct": min(0.30, 0.15 * scale), "trauma_reduction": int(3 * scale)},
        "Chief Medical Officer": {"hp_restore_pct": min(0.60, 0.30 * scale), "trauma_reduction": int(8 * scale)},
        "Priest":        {"morale_bonus": int(5 * scale),  "trauma_reduction": int(6 * scale)},
        "High Priest":   {"morale_bonus": int(10 * scale), "trauma_reduction": int(12 * scale)},
        "Blacksmith":    {"team_def_bonus": int(2 * scale)},
        "Forge Lord":    {"team_def_bonus": int(8 * scale)},
        "Quartermaster": {"gold_bonus_pct": min(0.25, 0.10 * scale)},
        "Tycoon":        {"gold_bonus_pct": min(0.60, 0.25 * scale)},
        "Alchemist":     {"material_bonus": int(1 * scale)},
        "Grand Alchemist":{"material_bonus": int(3 * scale)},
    }
    return bonuses.get(hero_class, {})

# ---------------------------------------------------------------------------
# Forge crafting
# ---------------------------------------------------------------------------
# Blacksmith is the only Forge specialist. Crafting quality is capped by
# your single BEST Blacksmith present (a pile of weak ones can't out-craft
# one great one) — but multiple Blacksmiths of that same evolution tier
# add a smaller bonus on top, since a crew of comparably-skilled smiths
# really does work better together than just one.
BLACKSMITH_LINE = ["Blacksmith", "Weaponsmith", "Armorer", "Artificer", "Master Smith", "Forge Lord", "Runesmith"]

# Evolution tier rank — higher tier smiths set a meaningfully higher
# quality ceiling, not just a flat bonus regardless of how evolved they are.
SMITH_TIER_RANK = {
    "Blacksmith": 1, "Weaponsmith": 1, "Armorer": 1, "Artificer": 1,
    "Master Smith": 2,
    "Forge Lord": 3, "Runesmith": 3,
}
# tier -> (apt_bonus, level_bonus) for the best smith present.
SMITH_TIER_BONUS = {1: (30, 5), 2: (60, 10), 3: (100, 18)}
# tier -> (apt_bonus, level_bonus) added per *additional* smith sharing
# that same tier — the peak is still set by the best smith's tier alone.
SMITH_TIER_TEAMWORK_BONUS = {1: (15, 2), 2: (25, 4), 3: (40, 6)}

def forge_smith_bonus(hero_classes: list[str]) -> tuple[int, int, str | None]:
    """Returns (apt_bonus, level_bonus, best_smith_class) for a Forge craft.
    None present -> (0, 0, None). The bonus is anchored to the single best
    (highest-tier) Blacksmith-line class present, plus a smaller bonus per
    additional smith of that exact same tier."""
    smith_classes = [c for c in hero_classes if c in BLACKSMITH_LINE]
    if not smith_classes:
        return (0, 0, None)
    best = max(smith_classes, key=lambda c: SMITH_TIER_RANK.get(c, 1))
    best_tier = SMITH_TIER_RANK.get(best, 1)
    apt, level = SMITH_TIER_BONUS[best_tier]
    # Remove exactly one occurrence of `best` (the best smith themself)
    # before counting same-tier teammates — otherwise two heroes sharing
    # the identical class name would wrongly cancel each other out.
    remaining = smith_classes.copy()
    remaining.remove(best)
    same_tier_extra = sum(1 for c in remaining if SMITH_TIER_RANK.get(c, 1) == best_tier)
    extra_apt, extra_level = SMITH_TIER_TEAMWORK_BONUS[best_tier]
    apt += extra_apt * same_tier_extra
    level += extra_level * same_tier_extra
    return (apt, level, best)

# ---------------------------------------------------------------------------
# Class display helpers
# ---------------------------------------------------------------------------

CLASS_ICONS = {
    "Warrior": "⚔️", "Knight": "🛡️", "Berserker": "🩸", "Paladin": "✨",
    "Spearman": "🔱", "Lancer": "🐎", "Halberdier": "🪓", "Dragoon": "🐉",
    "Thief": "🗡️", "Assassin": "☠️", "Rogue": "🥷", "Ninja": "💨",
    "Archer": "🏹", "Sniper": "🎯", "Ranger": "🐺", "Crossbowman": "⚙️",
    "Spellsword": "⚔️✨",
    "Mage": "🪄", "Sorcerer": "🔮", "Warlock": "👁️‍🗨️", "Necromancer": "💀", "Summoner": "🐉",
    "Acolyte": "✝️", "Cleric": "🩹", "Bard": "🎵", "Druid": "🌿", "Monk": "👊",
    "Magic Engineer": "🤖",
    "Chef": "🍳", "Medic": "🩺", "Scout": "🔭", "Blacksmith": "⚒️",
    "Quartermaster": "💰", "Tactician": "📜", "Priest": "⛪", "Alchemist": "🧪",
    "Classless": "❓"
}

def get_class_icon(hero_class: str) -> str:
    return CLASS_ICONS.get(hero_class, "💠")
CLASS_DESCRIPTIONS = { k: 'A powerful hero.' for k in ALL_CLASSES }
