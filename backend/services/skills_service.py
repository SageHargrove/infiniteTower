"""
Skills Service
==============
Hero skills system with rarity tiers (Common → Legendary).
Heroes gain skills at creation and through progression.

Skills can be:
  - PASSIVE: Always active, modify stats or behavior
  - ACTIVE: Used in combat with cooldowns (AI-controlled)
  - BOSS_DROP: Extremely rare skills only from boss kills

Rarity tiers:
  Common (60%) → Uncommon (25%) → Rare (10%) → Epic (4%) → Legendary (1%)
"""

import random

SKILL_RARITY_WEIGHTS = {
    "common": 60,
    "uncommon": 25,
    "rare": 10,
    "epic": 4,
    "legendary": 1,
}

SKILL_RARITY_COLORS = {
    "common": "#888",
    "uncommon": "#4a9a6a",
    "rare": "#4a7aaa",
    "epic": "#8030c8",
    "legendary": "#c9a84c",
}

# ─── Skill Definitions ─────────────────────────────────────────────
# type: "passive" | "active" | "boss_drop"
# For active skills: cooldown = rounds between uses

SKILL_POOL = {
    "Warrior": {
        "common": [
            {"id": "iron_skin", "name": "Iron Skin", "type": "passive",
             "desc": "+10% DEF", "effect": {"def_pct": 0.10}},
            {"id": "heavy_strikes", "name": "Heavy Strikes", "type": "passive",
             "desc": "+8% ATK", "effect": {"atk_pct": 0.08}},
        ],
        "uncommon": [
            {"id": "shield_wall", "name": "Shield Wall", "type": "active",
             "desc": "Absorb 30% team damage for 2 rounds", "cooldown": 5,
             "effect": {"team_dmg_reduce": 0.30, "duration": 2}},
            {"id": "battle_cry", "name": "Battle Cry", "type": "passive",
             "desc": "+5% ATK to all frontline allies", "effect": {"team_atk_pct": 0.05}},
        ],
        "rare": [
            {"id": "last_stand", "name": "Last Stand", "type": "passive",
             "desc": "When below 20% HP, ATK doubles", "effect": {"low_hp_atk_mult": 2.0, "threshold": 0.20}},
            {"id": "taunt", "name": "Taunt", "type": "active",
             "desc": "Force all enemies to target you for 2 rounds", "cooldown": 4,
             "effect": {"taunt_duration": 2}},
        ],
        "epic": [
            {"id": "undying_will", "name": "Undying Will", "type": "passive",
             "desc": "Survive one killing blow with 1 HP (once per fight)",
             "effect": {"death_save": 1}},
        ],
        "legendary": [
            {"id": "berserker_rage", "name": "Berserker Rage", "type": "passive",
             "desc": "Each kill grants +15% ATK for the rest of combat",
             "effect": {"kill_atk_stack": 0.15}},
        ],
    },
    "Spearman": {
        "common": [
            {"id": "long_reach", "name": "Long Reach", "type": "passive",
             "desc": "+5% SPD, +5% ATK", "effect": {"spd_pct": 0.05, "atk_pct": 0.05}},
            {"id": "piercing_thrust", "name": "Piercing Thrust", "type": "passive",
             "desc": "Ignore 10% of enemy DEF", "effect": {"armor_pen": 0.10}},
        ],
        "uncommon": [
            {"id": "sweeping_strike", "name": "Sweeping Strike", "type": "active",
             "desc": "Hit 2 enemies for 80% ATK each", "cooldown": 3,
             "effect": {"multi_target": 2, "dmg_pct": 0.80}},
        ],
        "rare": [
            {"id": "impale", "name": "Impale", "type": "active",
             "desc": "300% ATK single target, ignore DEF", "cooldown": 5,
             "effect": {"dmg_pct": 3.0, "ignore_def": True}},
        ],
        "epic": [
            {"id": "phalanx", "name": "Phalanx Formation", "type": "passive",
             "desc": "If adjacent to another Spearman/Warrior, both get +20% DEF",
             "effect": {"adjacent_def_pct": 0.20}},
        ],
        "legendary": [
            {"id": "dragon_lance", "name": "Dragon Lance", "type": "passive",
             "desc": "First attack each combat deals 500% damage",
             "effect": {"first_strike_mult": 5.0}},
        ],
    },
    "Thief": {
        "common": [
            {"id": "nimble_feet", "name": "Nimble Feet", "type": "passive",
             "desc": "+10% dodge chance", "effect": {"dodge_pct": 0.10}},
            {"id": "quick_hands", "name": "Quick Hands", "type": "passive",
             "desc": "+10% SPD", "effect": {"spd_pct": 0.10}},
        ],
        "uncommon": [
            {"id": "backstab", "name": "Backstab", "type": "active",
             "desc": "200% ATK damage, guaranteed crit", "cooldown": 4,
             "effect": {"dmg_pct": 2.0, "guaranteed_crit": True}},
        ],
        "rare": [
            {"id": "shadow_step", "name": "Shadow Step", "type": "passive",
             "desc": "30% chance to attack twice per round",
             "effect": {"double_strike": 0.30}},
        ],
        "epic": [
            {"id": "poison_blade", "name": "Poison Blade", "type": "passive",
             "desc": "Attacks apply 3% max HP poison for 3 rounds",
             "effect": {"poison_pct": 0.03, "poison_duration": 3}},
        ],
        "legendary": [
            {"id": "phantom_assassin", "name": "Phantom Assassin", "type": "passive",
             "desc": "If you kill an enemy, become untargetable for 1 round",
             "effect": {"kill_stealth": 1}},
        ],
    },
    "Archer": {
        "common": [
            {"id": "steady_aim", "name": "Steady Aim", "type": "passive",
             "desc": "+10% ATK", "effect": {"atk_pct": 0.10}},
            {"id": "keen_eyes", "name": "Keen Eyes", "type": "passive",
             "desc": "+5% crit chance", "effect": {"crit_pct": 0.05}},
        ],
        "uncommon": [
            {"id": "volley", "name": "Volley", "type": "active",
             "desc": "Hit all enemies for 50% ATK", "cooldown": 4,
             "effect": {"aoe": True, "dmg_pct": 0.50}},
            {"id": "suppressing_fire", "name": "Suppressing Fire", "type": "active",
             "desc": "Reduce all enemy SPD by 30% for 2 rounds", "cooldown": 4,
             "effect": {"enemy_spd_debuff": 0.30, "duration": 2}},
        ],
        "rare": [
            {"id": "headshot", "name": "Headshot", "type": "passive",
             "desc": "Crits deal 250% damage instead of 180%",
             "effect": {"crit_mult": 2.5}},
        ],
        "epic": [
            {"id": "rain_of_arrows", "name": "Rain of Arrows", "type": "active",
             "desc": "Hit all enemies for 120% ATK, +fear check", "cooldown": 6,
             "effect": {"aoe": True, "dmg_pct": 1.2, "fear_check": True}},
        ],
        "legendary": [
            {"id": "one_shot_one_kill", "name": "One Shot, One Kill", "type": "passive",
             "desc": "20% chance to instantly kill non-boss enemies",
             "effect": {"instant_kill": 0.20}},
        ],
    },
    "Mage": {
        "common": [
            {"id": "mana_shield", "name": "Mana Shield", "type": "passive",
             "desc": "+15% max HP", "effect": {"hp_pct": 0.15}},
        ],
        "uncommon": [
            {"id": "arcane_blast", "name": "Arcane Blast", "type": "active",
             "desc": "200% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 2.0, "single_target": True}},
        ],
        "rare": [
            {"id": "chain_lightning", "name": "Chain Lightning", "type": "passive",
             "desc": "AoE damage increased by 25%", "effect": {"aoe_bonus": 0.25}},
        ],
        "epic": [
            {"id": "time_warp", "name": "Time Warp", "type": "active",
             "desc": "All allies act twice next round", "cooldown": 8,
             "effect": {"team_double_turn": True}},
        ],
        "legendary": [
            {"id": "meteor", "name": "Meteor", "type": "active",
             "desc": "400% ATK to all enemies, self-stun 1 round", "cooldown": 7,
             "effect": {"aoe": True, "dmg_pct": 4.0, "self_stun": 1}},
        ],
    },
    "Magic Engineer": {
        "common": [
            {"id": "reinforced_construct", "name": "Reinforced Construct", "type": "passive",
             "desc": "Construct absorbs 2 hits instead of 1", "effect": {"construct_hits": 2}},
        ],
        "uncommon": [
            {"id": "repair_drone", "name": "Repair Drone", "type": "active",
             "desc": "Restore 15% HP to lowest-HP ally", "cooldown": 4,
             "effect": {"heal_pct": 0.15}},
        ],
        "rare": [
            {"id": "emp_blast", "name": "EMP Blast", "type": "active",
             "desc": "Stun all enemies for 1 round", "cooldown": 6,
             "effect": {"enemy_stun": 1}},
        ],
        "epic": [
            {"id": "overcharge", "name": "Overcharge", "type": "passive",
             "desc": "Construct explodes on death dealing 200% ATK to all enemies",
             "effect": {"construct_explode_pct": 2.0}},
        ],
        "legendary": [
            {"id": "war_machine", "name": "War Machine", "type": "passive",
             "desc": "Construct attacks each round for 50% of your ATK",
             "effect": {"construct_attack_pct": 0.50}},
        ],
    },
}

# Generic skills for base/classless heroes
GENERIC_SKILLS = {
    "common": [
        {"id": "tough", "name": "Tough", "type": "passive",
         "desc": "+8% HP", "effect": {"hp_pct": 0.08}},
        {"id": "determined", "name": "Determined", "type": "passive",
         "desc": "+5% all stats", "effect": {"all_pct": 0.05}},
        {"id": "calm_mind", "name": "Calm Mind", "type": "passive",
         "desc": "-10% stress gain", "effect": {"stress_reduce": 0.10}},
    ],
    "uncommon": [
        {"id": "survivor", "name": "Survivor", "type": "passive",
         "desc": "+15% HP, -5% ATK", "effect": {"hp_pct": 0.15, "atk_pct": -0.05}},
        {"id": "field_medic", "name": "Field Medic", "type": "passive",
         "desc": "Restore 3% HP to self each round", "effect": {"regen_pct": 0.03}},
    ],
    "rare": [
        {"id": "iron_will", "name": "Iron Will", "type": "passive",
         "desc": "Immune to fear stun", "effect": {"fear_immune": True}},
    ],
    "epic": [
        {"id": "martyrdom", "name": "Martyrdom", "type": "passive",
         "desc": "On death, fully heal all allies", "effect": {"death_heal": True}},
    ],
    "legendary": [
        {"id": "chosen_one", "name": "Chosen One", "type": "passive",
         "desc": "+25% all stats, immune to fear", "effect": {"all_pct": 0.25, "fear_immune": True}},
    ],
}

# Seals and Runes used to be rolled here at birth — they're now Relics
# (services/relics_service.py): loot dropped from bosses/events, then
# equipped onto any hero whose CURRENT star meets the relic's min_star.
# Genius/Prodigy talent is retired entirely — the aptitude/talent growth
# system (level_service.talent_score) now covers that "secretly OP low
# rarity" narrative beat more thoroughly.

# Boss-drop exclusive skills — never rolled naturally
BOSS_DROP_SKILLS = [
    {"id": "boss_slayer", "name": "Boss Slayer", "rarity": "epic", "type": "passive",
     "desc": "+50% damage to bosses", "effect": {"boss_dmg_pct": 0.50}},
    {"id": "tower_sense", "name": "Tower Sense", "rarity": "legendary", "type": "passive",
     "desc": "Team takes 15% less damage on all floors", "effect": {"team_dmg_reduce": 0.15}},
    {"id": "deaths_embrace", "name": "Death's Embrace", "rarity": "legendary", "type": "passive",
     "desc": "When an ally dies, gain their ATK for the rest of combat",
     "effect": {"inherit_atk": True}},
    {"id": "floor_master", "name": "Floor Master", "rarity": "legendary", "type": "passive",
     "desc": "+2% all stats per 10 floors survived (permanent)",
     "effect": {"floor_scaling": 0.02}},
]


def roll_skill_rarity() -> str:
    """Roll a skill rarity using weighted RNG."""
    rarities = list(SKILL_RARITY_WEIGHTS.keys())
    weights = list(SKILL_RARITY_WEIGHTS.values())
    return random.choices(rarities, weights=weights, k=1)[0]


def get_skill_for_class(hero_class: str, rarity: str = None) -> dict | None:
    """Get a random skill for a class at a given rarity."""
    if rarity is None:
        rarity = roll_skill_rarity()

    # Get class-specific pool, fall back to generic
    pool = SKILL_POOL.get(hero_class, GENERIC_SKILLS)
    if isinstance(pool, dict):
        skills = pool.get(rarity, [])
    else:
        skills = []

    # If no class-specific skill at this rarity, try generic
    if not skills:
        skills = GENERIC_SKILLS.get(rarity, [])

    if not skills:
        return None

    skill = random.choice(skills).copy()
    skill["rarity"] = rarity
    skill["tier"] = "Beginner"
    skill["level"] = 1
    skill["xp"] = 0
    skill["max_xp"] = 100
    return skill


def assign_initial_skills(hero_class: str, birth_star: int) -> list[dict]:
    """Assign starting skills to a new hero. Higher star = better chance of rare skills."""
    skills = []

    # Everyone gets 1 skill at birth
    # Higher star heroes get a rarity bonus
    rarity_bonus = {1: 0, 2: 0, 3: 5, 4: 10, 5: 20, 6: 30, 7: 50}
    bonus = rarity_bonus.get(birth_star, 0)

    # Roll with bonus applied
    skill = get_skill_for_class(hero_class)
    if skill and bonus > 0:
        # Chance to upgrade rarity
        if random.randint(0, 100) < bonus:
            rarity_order = ["common", "uncommon", "rare", "epic", "legendary"]
            idx = rarity_order.index(skill["rarity"])
            if idx < len(rarity_order) - 1:
                upgraded = get_skill_for_class(hero_class, rarity_order[idx + 1])
                if upgraded:
                    skill = upgraded

    if skill:
        skills.append(skill)

    # 4★+ heroes get a second skill
    if birth_star >= 4:
        skill2 = get_skill_for_class(hero_class)
        if skill2 and skill2["id"] != skills[0]["id"]:
            skills.append(skill2)

    # 6★+ heroes get a third skill
    if birth_star >= 6 and len(skills) >= 2:
        skill3 = get_skill_for_class(hero_class)
        if skill3 and skill3["id"] not in [s["id"] for s in skills]:
            skills.append(skill3)

    for s in skills:
        if "tier" not in s:
            s["tier"] = "Beginner"
            s["level"] = 1
            s["xp"] = 0
            s["max_xp"] = 100

    return skills


def get_boss_drop_skill() -> dict | None:
    """Roll for a boss-drop exclusive skill. 15% chance on boss kill."""
    if random.random() < 0.15:
        skill = random.choice(BOSS_DROP_SKILLS).copy()
        return skill
    return None


def apply_passive_skills(hero: dict, skills: list[dict]) -> dict:
    """Apply passive skill effects to hero stats before combat."""
    h = hero.copy()
    for skill in skills:
        if skill.get("type") != "passive":
            continue
        eff = skill.get("effect", {})

        if "atk_pct" in eff:
            h["attack"] = int(h["attack"] * (1 + eff["atk_pct"]))
        if "def_pct" in eff:
            h["defense"] = int(h["defense"] * (1 + eff["def_pct"]))
        if "spd_pct" in eff:
            h["speed"] = int(h["speed"] * (1 + eff["spd_pct"]))
        if "hp_pct" in eff:
            h["max_hp"] = int(h["max_hp"] * (1 + eff["hp_pct"]))
            h["hp"] = int(h["hp"] * (1 + eff["hp_pct"]))
        if "all_pct" in eff:
            mult = 1 + eff["all_pct"]
            h["attack"] = int(h["attack"] * mult)
            h["defense"] = int(h["defense"] * mult)
            h["speed"] = int(h["speed"] * mult)
            h["max_hp"] = int(h["max_hp"] * mult)
            h["hp"] = int(h["hp"] * mult)
        if "crit_pct" in eff:
            h["crit_chance"] = h.get("crit_chance", 0.05) + eff["crit_pct"]
        if "dodge_pct" in eff:
            h["dodge_chance"] = h.get("dodge_chance", 0.0) + eff["dodge_pct"]
        if "armor_pen" in eff:
            h["armor_pen"] = h.get("armor_pen", 0) + eff["armor_pen"]
        if "fear_immune" in eff:
            h["fear_immune"] = True
        if "death_save" in eff:
            h["death_save"] = eff["death_save"]
        if "regen_pct" in eff:
            h["regen_pct"] = h.get("regen_pct", 0.0) + eff["regen_pct"]

    return h
