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

Class coverage: every one of the 8 combat base classes (Warrior, Spearman,
Thief, Archer, Mage, Magic Engineer, Acolyte, Spellsword), every
support-combat base class that fights even unevolved (Medic, Scout,
Tactician — see class_service.SUPPORT_COMBAT_CLASSES), AND every pure
profession base class (Blacksmith, Alchemist, Chef, Priest, Quartermaster,
Merchant, Farmer) has its own full kit below — the last group never
fights at their literal base name, but every one of their evolutions
does, so the kit matters the moment they evolve. On top of that, every
class's FIRST evolution tier (e.g. Warrior -> Knight/Berserker/Paladin)
gets its own bespoke signature kit, since those are the evolutions
players see constantly.
Second-tier "pinnacle" evolutions (e.g. Knight -> Aegis/Templar) are
numerous (~80 names) and inherit their base lineage's kit via
_LINEAGE_MAP rather than each getting hand-tuned content — a real kit,
just shared with their tier-30 siblings under the same lineage, not the
bland classless GENERIC_SKILLS fallback every one of these used to get.
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
    # ═══════════════════════════════════════════════════════════════
    # BASE LINEAGE: WARRIOR (frontline tank/bruiser)
    # ═══════════════════════════════════════════════════════════════
    "Warrior": {
        "common": [
            {"id": "iron_skin", "name": "Iron Skin", "type": "passive",
             "desc": "+10% DEF", "effect": {"int_pct": 0.10}},
            {"id": "heavy_strikes", "name": "Heavy Strikes", "type": "passive",
             "desc": "+8% ATK", "effect": {"str_pct": 0.08}},
            {"id": "thick_hide", "name": "Thick Hide", "type": "passive",
             "desc": "+6% Health", "effect": {"hlt_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "shield_wall", "name": "Shield Wall", "type": "active",
             "desc": "Absorb 30% team damage for 2 rounds", "cooldown": 5,
             "effect": {"team_dmg_reduce": 0.30, "duration": 2, "mana_cost": 30}},
            {"id": "battle_cry", "name": "Battle Cry", "type": "passive",
             "desc": "+5% ATK to all frontline allies", "effect": {"team_atk_pct": 0.05}},
            {"id": "scarred_veteran", "name": "Scarred Veteran", "type": "passive",
             "desc": "+8% damage reduction", "effect": {"dmg_reduction_pct": 0.08}},
        ],
        "rare": [
            {"id": "last_stand", "name": "Last Stand", "type": "passive",
             "desc": "When below 20% Health, ATK doubles", "effect": {"low_hp_atk_mult": 2.0, "threshold": 0.20}},
            {"id": "taunt", "name": "Taunt", "type": "active",
             "desc": "Force all enemies to target you for 2 rounds", "cooldown": 4,
             "effect": {"taunt_duration": 2, "mana_cost": 25}},
            {"id": "reckless_swing", "name": "Reckless Swing", "type": "active",
             "desc": "220% ATK single target", "cooldown": 4,
             "effect": {"dmg_pct": 2.2, "single_target": True, "mana_cost": 30}},
            {"id": "adrenaline_rush", "name": "Adrenaline Rush", "type": "active",
             "desc": "Recover 20% of your own max Health", "cooldown": 5,
             "effect": {"self_heal_pct": 0.20, "mana_cost": 25}},
        ],
        "epic": [
            {"id": "undying_will", "name": "Undying Will", "type": "passive",
             "desc": "Survive one killing blow with 1 Health (once per fight)",
             "effect": {"death_save": 1}},
        ],
        "legendary": [
            {"id": "berserker_rage", "name": "Berserker Rage", "type": "passive",
             "desc": "Each kill grants +15% ATK for the rest of combat",
             "effect": {"kill_atk_stack": 0.15}},
        ],
    },
    # KNIGHT — disciplined defender, tier-30 Warrior signature
    "Knight": {
        "common": [
            {"id": "knight_drill", "name": "Drilled Stance", "type": "passive",
             "desc": "+10% DEF, +5% Health", "effect": {"int_pct": 0.10, "hlt_pct": 0.05}},
            {"id": "knight_polish", "name": "Polished Plate", "type": "passive",
             "desc": "+7% damage reduction", "effect": {"dmg_reduction_pct": 0.07}},
        ],
        "uncommon": [
            {"id": "shield_bash", "name": "Shield Bash", "type": "active",
             "desc": "150% ATK, stun the target 1 round", "cooldown": 4,
             "effect": {"dmg_pct": 1.5, "single_target": True, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "guardians_oath", "name": "Guardian's Oath", "type": "active",
             "desc": "Taunt all enemies and reduce team damage taken 25% for 2 rounds", "cooldown": 6,
             "effect": {"taunt_duration": 2, "team_dmg_reduce": 0.25, "mana_cost": 35}},
        ],
        "epic": [
            {"id": "bulwark", "name": "Bulwark", "type": "passive",
             "desc": "+12% damage reduction, +10% physical resist",
             "effect": {"dmg_reduction_pct": 0.12, "physical_resist_pct": 0.10}},
        ],
        "legendary": [
            {"id": "knights_vow", "name": "Knight's Vow", "type": "passive",
             "desc": "Survive one killing blow with 1 Health, then +20% ATK for the rest of the fight",
             "effect": {"death_save": 1, "kill_atk_stack": 0.0}},
        ],
    },
    # BERSERKER — all-in glass cannon, tier-30 Warrior signature
    "Berserker": {
        "common": [
            {"id": "bloodlust", "name": "Bloodlust", "type": "passive",
             "desc": "+12% ATK, -4% Health", "effect": {"str_pct": 0.12, "hlt_pct": -0.04}},
            {"id": "fury", "name": "Fury", "type": "passive",
             "desc": "+6% crit chance", "effect": {"crit_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "rampage", "name": "Rampage", "type": "active",
             "desc": "200% ATK to a single target, heal 15% of damage dealt", "cooldown": 4,
             "effect": {"dmg_pct": 2.0, "single_target": True, "lifesteal_pct": 0.15, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "blood_frenzy", "name": "Blood Frenzy", "type": "passive",
             "desc": "Below 50% Health, +20% ATK", "effect": {"low_hp_atk_mult": 1.2, "threshold": 0.50}},
        ],
        "epic": [
            {"id": "execute", "name": "Execute", "type": "active",
             "desc": "180% ATK, +100% damage if target is below 30% Health", "cooldown": 5,
             "effect": {"dmg_pct": 1.8, "single_target": True, "execute_bonus_pct": 1.0, "execute_threshold": 0.30, "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "unstoppable_rage", "name": "Unstoppable Rage", "type": "passive",
             "desc": "Each kill grants +20% ATK for the rest of combat",
             "effect": {"kill_atk_stack": 0.20}},
        ],
    },
    # PALADIN — holy bruiser/support hybrid, tier-30 Warrior signature
    "Paladin": {
        "common": [
            {"id": "blessed_armor", "name": "Blessed Armor", "type": "passive",
             "desc": "+8% DEF, +5% Health", "effect": {"int_pct": 0.08, "hlt_pct": 0.05}},
            {"id": "righteous_will", "name": "Righteous Will", "type": "passive",
             "desc": "-8% stress gain", "effect": {"stress_reduce": 0.08}},
        ],
        "uncommon": [
            {"id": "lay_on_hands", "name": "Lay on Hands", "type": "active",
             "desc": "Heal the lowest-Health ally for 25% of their max Health", "cooldown": 4,
             "effect": {"heal_pct": 0.25, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "consecration", "name": "Consecration", "type": "active",
             "desc": "Taunt all enemies for 2 rounds and cleanse your own afflictions", "cooldown": 6,
             "effect": {"taunt_duration": 2, "cleanse_self": True, "mana_cost": 35}},
        ],
        "epic": [
            {"id": "divine_shield", "name": "Divine Shield", "type": "active",
             "desc": "Shield the team for 30% damage reduction for 2 rounds", "cooldown": 6,
             "effect": {"team_dmg_reduce": 0.30, "duration": 2, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "last_rites", "name": "Last Rites", "type": "active",
             "desc": "Revive a fallen ally at 40% Health (once per fight)", "cooldown": 99,
             "effect": {"revive_pct": 0.40, "min_star": 6, "mana_cost": 50}},
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # BASE LINEAGE: SPEARMAN (reach/pierce DPS)
    # ═══════════════════════════════════════════════════════════════
    "Spearman": {
        "common": [
            {"id": "long_reach", "name": "Long Reach", "type": "passive",
             "desc": "+5% SPD, +5% ATK", "effect": {"agi_pct": 0.05, "str_pct": 0.05}},
            {"id": "piercing_thrust", "name": "Piercing Thrust", "type": "passive",
             "desc": "Ignore 10% of enemy DEF", "effect": {"armor_pen": 0.10}},
            {"id": "drilled_footing", "name": "Drilled Footing", "type": "passive",
             "desc": "+5% Health", "effect": {"hlt_pct": 0.05}},
        ],
        "uncommon": [
            {"id": "sweeping_strike", "name": "Sweeping Strike", "type": "active",
             "desc": "Hit 2 enemies for 80% ATK each", "cooldown": 3,
             "effect": {"multi_target": 2, "dmg_pct": 0.80, "mana_cost": 25}},
            {"id": "rally_the_line", "name": "Rally the Line", "type": "active",
             "desc": "Permanently boost team ATK 8% for the rest of the fight", "cooldown": 7,
             "effect": {"team_buff_pct": 0.08, "buff_stat": "strength", "mana_cost": 35}},
        ],
        "rare": [
            {"id": "impale", "name": "Impale", "type": "active",
             "desc": "300% ATK single target, ignore DEF", "cooldown": 5,
             "effect": {"dmg_pct": 3.0, "ignore_def": True, "mana_cost": 35}},
            {"id": "spear_wall", "name": "Spear Wall", "type": "active",
             "desc": "Reduce team damage taken 20% for 2 rounds", "cooldown": 5,
             "effect": {"team_dmg_reduce": 0.20, "duration": 2, "mana_cost": 30}},
        ],
        "epic": [
            {"id": "phalanx", "name": "Phalanx Formation", "type": "passive",
             "desc": "If adjacent to another Spearman/Warrior, both get +20% DEF",
             "effect": {"adjacent_def_pct": 0.20}},
        ],
        "legendary": [
            {"id": "dragon_lance", "name": "Dragon Lance", "type": "passive",
             "desc": "First strike each combat deals 500% damage",
             "effect": {"first_strike_mult": 5.0}},
        ],
    },
    # LANCER — mobile charger, tier-30 Spearman signature
    "Lancer": {
        "common": [
            {"id": "charge_step", "name": "Charge Step", "type": "passive",
             "desc": "+8% SPD", "effect": {"agi_pct": 0.08}},
            {"id": "lance_grip", "name": "Lance Grip", "type": "passive",
             "desc": "+6% ATK", "effect": {"str_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "charging_lance", "name": "Charging Lance", "type": "active",
             "desc": "180% ATK, ignore 15% DEF", "cooldown": 3,
             "effect": {"dmg_pct": 1.8, "single_target": True, "ignore_def": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "momentum", "name": "Momentum", "type": "passive",
             "desc": "+8% crit chance", "effect": {"crit_pct": 0.08}},
        ],
        "epic": [
            {"id": "skewer", "name": "Skewer", "type": "active",
             "desc": "Hit 3 enemies for 100% ATK each", "cooldown": 5,
             "effect": {"multi_target": 3, "dmg_pct": 1.0, "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "wind_lance", "name": "Wind Lance", "type": "passive",
             "desc": "First strike each combat deals 500% damage",
             "effect": {"first_strike_mult": 5.0}},
        ],
    },
    # HALBERDIER — line-control, tier-30 Spearman signature
    "Halberdier": {
        "common": [
            {"id": "wide_arc", "name": "Wide Arc", "type": "passive",
             "desc": "+8% ATK", "effect": {"str_pct": 0.08}},
            {"id": "braced_haft", "name": "Braced Haft", "type": "passive",
             "desc": "+6% damage reduction", "effect": {"dmg_reduction_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "cleaving_sweep", "name": "Cleaving Sweep", "type": "active",
             "desc": "Hit all enemies for 60% ATK", "cooldown": 4,
             "effect": {"aoe": True, "dmg_pct": 0.60, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "anchor_point", "name": "Anchor Point", "type": "active",
             "desc": "Taunt all enemies for 2 rounds", "cooldown": 5,
             "effect": {"taunt_duration": 2, "mana_cost": 25}},
        ],
        "epic": [
            {"id": "halberd_storm", "name": "Halberd Storm", "type": "active",
             "desc": "Hit all enemies for 120% ATK", "cooldown": 6,
             "effect": {"aoe": True, "dmg_pct": 1.2, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "warlines_end", "name": "Warline's End", "type": "passive",
             "desc": "+20% DEF, +10% physical resist",
             "effect": {"int_pct": 0.20, "physical_resist_pct": 0.10}},
        ],
    },
    # DRAGOON — heavy striker, tier-30 Spearman signature
    "Dragoon": {
        "common": [
            {"id": "heavy_lance", "name": "Heavy Lance", "type": "passive",
             "desc": "+10% ATK", "effect": {"str_pct": 0.10}},
            {"id": "drake_hide", "name": "Drake Hide", "type": "passive",
             "desc": "+8% Health", "effect": {"hlt_pct": 0.08}},
        ],
        "uncommon": [
            {"id": "diving_strike", "name": "Diving Strike", "type": "active",
             "desc": "220% ATK, guaranteed crit", "cooldown": 4,
             "effect": {"dmg_pct": 2.2, "single_target": True, "guaranteed_crit": True, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "wyvern_step", "name": "Wyvern Step", "type": "passive",
             "desc": "+8% dodge chance", "effect": {"dodge_pct": 0.08}},
        ],
        "epic": [
            {"id": "thunder_dive", "name": "Thunder Dive", "type": "active",
             "desc": "300% ATK single target, ignore DEF", "cooldown": 6,
             "effect": {"dmg_pct": 3.0, "ignore_def": True, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "dragons_descent", "name": "Dragon's Descent", "type": "passive",
             "desc": "Each kill grants +15% ATK for the rest of combat",
             "effect": {"kill_atk_stack": 0.15}},
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # BASE LINEAGE: THIEF (crit/evasion burst)
    # ═══════════════════════════════════════════════════════════════
    "Thief": {
        "common": [
            {"id": "nimble_feet", "name": "Nimble Feet", "type": "passive",
             "desc": "+10% dodge chance", "effect": {"dodge_pct": 0.10}},
            {"id": "quick_hands", "name": "Quick Hands", "type": "passive",
             "desc": "+10% SPD", "effect": {"agi_pct": 0.10}},
            {"id": "light_steps", "name": "Light Steps", "type": "passive",
             "desc": "+5% crit chance", "effect": {"crit_pct": 0.05}},
            {"id": "evasive_instinct", "name": "Evasive Instinct", "type": "passive",
             "desc": "+6% SPD, +4% dodge chance", "effect": {"agi_pct": 0.06, "dodge_pct": 0.04}},
        ],
        "uncommon": [
            {"id": "backstab", "name": "Backstab", "type": "active",
             "desc": "200% ATK damage, guaranteed crit", "cooldown": 4,
             "effect": {"dmg_pct": 2.0, "single_target": True, "guaranteed_crit": True, "mana_cost": 30}},
            {"id": "vital_strike", "name": "Vital Strike", "type": "active",
             "desc": "150% ATK, heal 25% of damage dealt", "cooldown": 4,
             "effect": {"dmg_pct": 1.5, "single_target": True, "lifesteal_pct": 0.25, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "shadow_step", "name": "Shadow Step", "type": "passive",
             "desc": "30% chance to strike twice per round",
             "effect": {"double_strike": 0.30}},
        ],
        "epic": [
            {"id": "poison_blade", "name": "Poison Blade", "type": "passive",
             "desc": "Attacks apply 3% max Health poison for 3 rounds",
             "effect": {"poison_pct": 0.03, "poison_duration": 3}},
        ],
        "legendary": [
            {"id": "phantom_assassin", "name": "Phantom Assassin", "type": "passive",
             "desc": "If you kill an enemy, become untargetable for 1 round",
             "effect": {"kill_stealth": 1}},
        ],
    },
    # ASSASSIN — single-target execution, tier-30 Thief signature
    "Assassin": {
        "common": [
            {"id": "killers_eye", "name": "Killer's Eye", "type": "passive",
             "desc": "+8% crit chance", "effect": {"crit_pct": 0.08}},
            {"id": "silent_step", "name": "Silent Step", "type": "passive",
             "desc": "+8% dodge chance", "effect": {"dodge_pct": 0.08}},
        ],
        "uncommon": [
            {"id": "garrote", "name": "Garrote", "type": "active",
             "desc": "180% ATK, guaranteed crit", "cooldown": 3,
             "effect": {"dmg_pct": 1.8, "single_target": True, "guaranteed_crit": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "mark_for_death", "name": "Mark for Death", "type": "active",
             "desc": "250% ATK, +80% damage if target is below 30% Health", "cooldown": 5,
             "effect": {"dmg_pct": 2.5, "single_target": True, "execute_bonus_pct": 0.80, "execute_threshold": 0.30, "mana_cost": 35}},
        ],
        "epic": [
            {"id": "vanish", "name": "Vanish", "type": "passive",
             "desc": "+15% dodge chance", "effect": {"dodge_pct": 0.15}},
        ],
        "legendary": [
            {"id": "one_inch_punch", "name": "Death's Door", "type": "passive",
             "desc": "If you kill an enemy, become untargetable for 1 round",
             "effect": {"kill_stealth": 1}},
        ],
    },
    # ROGUE — opportunistic skirmisher, tier-30 Thief signature
    "Rogue": {
        "common": [
            {"id": "cutpurse", "name": "Cutpurse Reflexes", "type": "passive",
             "desc": "+8% SPD", "effect": {"agi_pct": 0.08}},
            {"id": "rogue_grit", "name": "Rogue's Grit", "type": "passive",
             "desc": "+5% Health, +4% dodge chance", "effect": {"hlt_pct": 0.05, "dodge_pct": 0.04}},
        ],
        "uncommon": [
            {"id": "dirty_trick", "name": "Dirty Trick", "type": "active",
             "desc": "140% ATK, stun the target 1 round", "cooldown": 4,
             "effect": {"dmg_pct": 1.4, "single_target": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "quick_fingers", "name": "Quick Fingers", "type": "passive",
             "desc": "30% chance to strike twice per round",
             "effect": {"double_strike": 0.30}},
        ],
        "epic": [
            {"id": "smoke_bomb", "name": "Smoke Bomb", "type": "active",
             "desc": "Permanently boost own dodge 15% for the rest of the fight, cleanse self", "cooldown": 6,
             "effect": {"team_buff_pct": 0.0, "cleanse_self": True, "mana_cost": 30}},
        ],
        "legendary": [
            {"id": "perfect_getaway", "name": "Perfect Getaway", "type": "passive",
             "desc": "If you kill an enemy, become untargetable for 1 round",
             "effect": {"kill_stealth": 1}},
        ],
    },
    # NINJA — speed/poison hybrid, tier-30 Thief signature
    "Ninja": {
        "common": [
            {"id": "shadow_clone_step", "name": "Shadow Clone Step", "type": "passive",
             "desc": "+10% SPD", "effect": {"agi_pct": 0.10}},
            {"id": "blade_focus", "name": "Blade Focus", "type": "passive",
             "desc": "+6% crit chance", "effect": {"crit_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "kunai_throw", "name": "Kunai Throw", "type": "active",
             "desc": "Hit 2 enemies for 90% ATK each", "cooldown": 3,
             "effect": {"multi_target": 2, "dmg_pct": 0.90, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "venom_strike", "name": "Venom Strike", "type": "passive",
             "desc": "Attacks apply 3% max Health poison for 3 rounds",
             "effect": {"poison_pct": 0.03, "poison_duration": 3}},
        ],
        "epic": [
            {"id": "shadow_clone", "name": "Shadow Clone Jutsu", "type": "passive",
             "desc": "30% chance to strike twice per round",
             "effect": {"double_strike": 0.30}},
        ],
        "legendary": [
            {"id": "art_of_the_unseen", "name": "Art of the Unseen", "type": "passive",
             "desc": "If you kill an enemy, become untargetable for 1 round",
             "effect": {"kill_stealth": 1}},
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # BASE LINEAGE: ARCHER (ranged crit/AoE)
    # ═══════════════════════════════════════════════════════════════
    "Archer": {
        "common": [
            {"id": "steady_aim", "name": "Steady Aim", "type": "passive",
             "desc": "+10% ATK", "effect": {"str_pct": 0.10}},
            {"id": "keen_eyes", "name": "Keen Eyes", "type": "passive",
             "desc": "+5% crit chance", "effect": {"crit_pct": 0.05}},
            {"id": "fletchers_calm", "name": "Fletcher's Calm", "type": "passive",
             "desc": "+5% dodge chance", "effect": {"dodge_pct": 0.05}},
        ],
        "uncommon": [
            {"id": "volley", "name": "Volley", "type": "active",
             "desc": "Hit all enemies for 50% ATK", "cooldown": 4,
             "effect": {"aoe": True, "dmg_pct": 0.50, "mana_cost": 30}},
            {"id": "piercing_shot", "name": "Piercing Shot", "type": "active",
             "desc": "180% ATK, ignore 15% DEF", "cooldown": 3,
             "effect": {"dmg_pct": 1.8, "single_target": True, "ignore_def": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "headshot", "name": "Headshot", "type": "passive",
             "desc": "Crits deal 250% damage instead of 180%",
             "effect": {"crit_mult": 2.5}},
            {"id": "toxic_arrows", "name": "Toxic Arrows", "type": "passive",
             "desc": "Attacks apply 3% max Health poison for 3 rounds",
             "effect": {"poison_pct": 0.03, "poison_duration": 3}},
        ],
        "epic": [
            {"id": "rain_of_arrows", "name": "Rain of Arrows", "type": "active",
             "desc": "Hit all enemies for 120% ATK, +fear check", "cooldown": 6,
             "effect": {"aoe": True, "dmg_pct": 1.2, "fear_check": True, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "one_shot_one_kill", "name": "One Shot, One Kill", "type": "passive",
             "desc": "20% chance to instantly kill non-boss enemies",
             "effect": {"instant_kill": 0.20}},
        ],
    },
    # SNIPER — precision burst, tier-30 Archer signature
    "Sniper": {
        "common": [
            {"id": "scope_sight", "name": "Scope Sight", "type": "passive",
             "desc": "+8% crit chance", "effect": {"crit_pct": 0.08}},
            {"id": "patient_hand", "name": "Patient Hand", "type": "passive",
             "desc": "+8% ATK", "effect": {"str_pct": 0.08}},
        ],
        "uncommon": [
            {"id": "called_shot", "name": "Called Shot", "type": "active",
             "desc": "220% ATK, guaranteed crit", "cooldown": 4,
             "effect": {"dmg_pct": 2.2, "single_target": True, "guaranteed_crit": True, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "long_shot", "name": "Long Shot", "type": "active",
             "desc": "280% ATK, ignore DEF", "cooldown": 5,
             "effect": {"dmg_pct": 2.8, "single_target": True, "ignore_def": True, "mana_cost": 35}},
        ],
        "epic": [
            {"id": "kill_shot", "name": "Kill Shot", "type": "active",
             "desc": "180% ATK, +100% damage if target below 30% Health", "cooldown": 5,
             "effect": {"dmg_pct": 1.8, "single_target": True, "execute_bonus_pct": 1.0, "execute_threshold": 0.30, "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "headshot_legend", "name": "Dead Center", "type": "passive",
             "desc": "20% chance to instantly kill non-boss enemies",
             "effect": {"instant_kill": 0.20}},
        ],
    },
    # RANGER — wilderness skirmisher, tier-30 Archer signature
    "Ranger": {
        "common": [
            {"id": "tracker_eye", "name": "Tracker's Eye", "type": "passive",
             "desc": "+6% crit chance", "effect": {"crit_pct": 0.06}},
            {"id": "woodland_step", "name": "Woodland Step", "type": "passive",
             "desc": "+6% dodge chance", "effect": {"dodge_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "twin_shot", "name": "Twin Shot", "type": "active",
             "desc": "Hit 2 enemies for 100% ATK each", "cooldown": 3,
             "effect": {"multi_target": 2, "dmg_pct": 1.0, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "natures_grace", "name": "Nature's Grace", "type": "active",
             "desc": "Heal the lowest-Health ally for 20% of their max Health", "cooldown": 4,
             "effect": {"heal_pct": 0.20, "mana_cost": 30}},
        ],
        "epic": [
            {"id": "barrage", "name": "Barrage", "type": "active",
             "desc": "Hit all enemies for 100% ATK", "cooldown": 6,
             "effect": {"aoe": True, "dmg_pct": 1.0, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "apex_predator_shot", "name": "Apex Shot", "type": "passive",
             "desc": "20% chance to instantly kill non-boss enemies",
             "effect": {"instant_kill": 0.20}},
        ],
    },
    # CROSSBOWMAN — heavy ranged, tier-30 Archer signature
    "Crossbowman": {
        "common": [
            {"id": "loaded_bolt", "name": "Loaded Bolt", "type": "passive",
             "desc": "+10% ATK", "effect": {"str_pct": 0.10}},
            {"id": "steel_string", "name": "Steel String", "type": "passive",
             "desc": "+5% crit chance", "effect": {"crit_pct": 0.05}},
        ],
        "uncommon": [
            {"id": "heavy_bolt", "name": "Heavy Bolt", "type": "active",
             "desc": "200% ATK, ignore 15% DEF", "cooldown": 4,
             "effect": {"dmg_pct": 2.0, "single_target": True, "ignore_def": True, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "rapid_reload", "name": "Rapid Reload", "type": "passive",
             "desc": "30% chance to strike twice per round",
             "effect": {"double_strike": 0.30}},
        ],
        "epic": [
            {"id": "siege_bolt", "name": "Siege Bolt", "type": "active",
             "desc": "350% ATK single target, ignore DEF", "cooldown": 7,
             "effect": {"dmg_pct": 3.5, "single_target": True, "ignore_def": True, "mana_cost": 45}},
        ],
        "legendary": [
            {"id": "executioners_bolt", "name": "Executioner's Bolt", "type": "passive",
             "desc": "20% chance to instantly kill non-boss enemies",
             "effect": {"instant_kill": 0.20}},
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # BASE LINEAGE: MAGE (burst caster)
    # ═══════════════════════════════════════════════════════════════
    "Mage": {
        "common": [
            {"id": "mana_shield", "name": "Mana Shield", "type": "passive",
             "desc": "+15% max Health", "effect": {"hlt_pct": 0.15}},
            {"id": "spark", "name": "Spark", "type": "active",
             "desc": "130% ATK to a single target", "cooldown": 2,
             "effect": {"dmg_pct": 1.3, "single_target": True, "mana_cost": 20}},
        ],
        "uncommon": [
            {"id": "arcane_blast", "name": "Arcane Blast", "type": "active",
             "desc": "200% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 2.0, "single_target": True, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "chain_lightning", "name": "Chain Lightning", "type": "passive",
             "desc": "AoE damage increased by 25%", "effect": {"aoe_bonus": 0.25}},
            {"id": "mana_burn", "name": "Mana Burn", "type": "active",
             "desc": "180% ATK single target, ignore DEF", "cooldown": 3,
             "effect": {"dmg_pct": 1.8, "single_target": True, "ignore_def": True, "mana_cost": 30}},
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
    # SORCERER — raw damage caster, tier-30 Mage signature
    "Sorcerer": {
        "common": [
            {"id": "kindled_power", "name": "Kindled Power", "type": "passive",
             "desc": "+10% Health", "effect": {"hlt_pct": 0.10}},
            {"id": "spell_focus", "name": "Spell Focus", "type": "passive",
             "desc": "+5% crit chance", "effect": {"crit_pct": 0.05}},
        ],
        "uncommon": [
            {"id": "firebolt", "name": "Firebolt", "type": "active",
             "desc": "220% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 2.2, "single_target": True, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "scorching_ray", "name": "Scorching Ray", "type": "active",
             "desc": "Hit 2 enemies for 130% ATK each", "cooldown": 4,
             "effect": {"multi_target": 2, "dmg_pct": 1.3, "mana_cost": 35}},
        ],
        "epic": [
            {"id": "firestorm", "name": "Firestorm", "type": "active",
             "desc": "Hit all enemies for 150% ATK", "cooldown": 7,
             "effect": {"aoe": True, "dmg_pct": 1.5, "mana_cost": 45}},
        ],
        "legendary": [
            {"id": "archmagic", "name": "Archmagic Surge", "type": "active",
             "desc": "350% ATK to all enemies", "cooldown": 8,
             "effect": {"aoe": True, "dmg_pct": 3.5, "mana_cost": 55}},
        ],
    },
    # WARLOCK — dark pact damage/drain, tier-30 Mage signature
    "Warlock": {
        "common": [
            {"id": "dark_pact", "name": "Dark Pact", "type": "passive",
             "desc": "+10% ATK, -4% Health", "effect": {"str_pct": 0.0, "int_pct": 0.10, "hlt_pct": -0.04}},
            {"id": "shadow_focus", "name": "Shadow Focus", "type": "passive",
             "desc": "+5% crit chance", "effect": {"crit_pct": 0.05}},
        ],
        "uncommon": [
            {"id": "drain_life", "name": "Drain Life", "type": "active",
             "desc": "200% ATK, heal 30% of damage dealt", "cooldown": 4,
             "effect": {"dmg_pct": 2.0, "single_target": True, "lifesteal_pct": 0.30, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "curse", "name": "Curse", "type": "passive",
             "desc": "Attacks apply 3% max Health poison for 3 rounds",
             "effect": {"poison_pct": 0.03, "poison_duration": 3}},
        ],
        "epic": [
            {"id": "soul_burn", "name": "Soul Burn", "type": "active",
             "desc": "260% ATK, +60% damage if target below 30% Health", "cooldown": 6,
             "effect": {"dmg_pct": 2.6, "single_target": True, "execute_bonus_pct": 0.60, "execute_threshold": 0.30, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "demonic_pact", "name": "Demonic Pact", "type": "active",
             "desc": "300% ATK to all enemies, heal 20% of damage dealt", "cooldown": 8,
             "effect": {"aoe": True, "dmg_pct": 3.0, "lifesteal_pct": 0.20, "mana_cost": 55}},
        ],
    },
    # NECROMANCER — DoT/attrition, tier-30 Mage signature
    "Necromancer": {
        "common": [
            {"id": "death_chill", "name": "Death Chill", "type": "passive",
             "desc": "+8% Health", "effect": {"hlt_pct": 0.08}},
            {"id": "grim_focus", "name": "Grim Focus", "type": "passive",
             "desc": "+5% crit chance", "effect": {"crit_pct": 0.05}},
        ],
        "uncommon": [
            {"id": "withering_touch", "name": "Withering Touch", "type": "active",
             "desc": "160% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 1.6, "single_target": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "plague_curse", "name": "Plague Curse", "type": "passive",
             "desc": "Attacks apply 4% max Health poison for 3 rounds",
             "effect": {"poison_pct": 0.04, "poison_duration": 3}},
        ],
        "epic": [
            {"id": "raise_dead", "name": "Raise Dead", "type": "active",
             "desc": "Revive a fallen ally at 35% Health (once per fight)", "cooldown": 99,
             "effect": {"revive_pct": 0.35, "min_star": 6, "mana_cost": 45}},
        ],
        "legendary": [
            {"id": "soul_harvest", "name": "Soul Harvest", "type": "passive",
             "desc": "Each kill grants +20% ATK for the rest of combat",
             "effect": {"kill_atk_stack": 0.20}},
        ],
    },
    # SUMMONER — pet/utility, tier-30 Mage signature
    "Summoner": {
        "common": [
            {"id": "bound_familiar", "name": "Bound Familiar", "type": "passive",
             "desc": "+10% Health", "effect": {"hlt_pct": 0.10}},
            {"id": "summoners_focus", "name": "Summoner's Focus", "type": "passive",
             "desc": "+5% ATK", "effect": {"str_pct": 0.0, "int_pct": 0.05}},
        ],
        "uncommon": [
            {"id": "spirit_bolt", "name": "Spirit Bolt", "type": "active",
             "desc": "170% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 1.7, "single_target": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "guardian_spirit", "name": "Guardian Spirit", "type": "active",
             "desc": "Shield the team for 25% damage reduction for 2 rounds", "cooldown": 5,
             "effect": {"team_dmg_reduce": 0.25, "duration": 2, "mana_cost": 35}},
        ],
        "epic": [
            {"id": "summon_swarm", "name": "Summon Swarm", "type": "active",
             "desc": "Hit all enemies for 110% ATK", "cooldown": 6,
             "effect": {"aoe": True, "dmg_pct": 1.1, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "spirit_rebirth", "name": "Spirit Rebirth", "type": "active",
             "desc": "Revive a fallen ally at 45% Health (once per fight)", "cooldown": 99,
             "effect": {"revive_pct": 0.45, "min_star": 6, "mana_cost": 50}},
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # BASE LINEAGE: MAGIC ENGINEER (construct support, pinnacle class)
    # ═══════════════════════════════════════════════════════════════
    "Magic Engineer": {
        "common": [
            {"id": "reinforced_construct", "name": "Reinforced Construct", "type": "passive",
             "desc": "Construct absorbs 2 hits instead of 1", "effect": {"construct_hits": 2}},
            {"id": "tinkers_focus", "name": "Tinker's Focus", "type": "passive",
             "desc": "+6% ATK", "effect": {"str_pct": 0.0, "int_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "repair_drone", "name": "Repair Drone", "type": "active",
             "desc": "Restore 15% Health to lowest-Health ally", "cooldown": 4,
             "effect": {"heal_pct": 0.15, "mana_cost": 25}},
            {"id": "overclock_strike", "name": "Overclock Strike", "type": "active",
             "desc": "170% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 1.7, "single_target": True, "mana_cost": 28}},
        ],
        "rare": [
            {"id": "emp_blast", "name": "EMP Blast", "type": "active",
             "desc": "Stun all enemies for 1 round", "cooldown": 6,
             "effect": {"enemy_stun": 1, "mana_cost": 35}},
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

    # ═══════════════════════════════════════════════════════════════
    # BASE LINEAGE: ACOLYTE (healer/support caster)
    # ═══════════════════════════════════════════════════════════════
    "Acolyte": {
        "common": [
            {"id": "novice_prayer", "name": "Novice Prayer", "type": "passive",
             "desc": "+10% Health", "effect": {"hlt_pct": 0.10}},
            {"id": "ward", "name": "Ward", "type": "passive",
             "desc": "+5% damage reduction", "effect": {"dmg_reduction_pct": 0.05}},
            {"id": "mend", "name": "Mend", "type": "active",
             "desc": "Heal the lowest-Health ally for 15% of their max Health", "cooldown": 3,
             "effect": {"heal_pct": 0.15, "mana_cost": 20}},
        ],
        "uncommon": [
            {"id": "calming_chant", "name": "Calming Chant", "type": "passive",
             "desc": "-10% stress gain", "effect": {"stress_reduce": 0.10}},
            {"id": "smite", "name": "Smite", "type": "active",
             "desc": "150% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 1.5, "single_target": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "greater_heal", "name": "Greater Heal", "type": "active",
             "desc": "Heal the lowest-Health ally for 30% of their max Health", "cooldown": 5,
             "effect": {"heal_pct": 0.30, "mana_cost": 35}},
        ],
        "epic": [
            {"id": "purify", "name": "Purify", "type": "active",
             "desc": "Cleanse all your own afflictions and heal self 15%", "cooldown": 5,
             "effect": {"cleanse_self": True, "self_heal_pct": 0.15, "mana_cost": 30}},
        ],
        "legendary": [
            {"id": "resurrection", "name": "Resurrection", "type": "active",
             "desc": "Revive a fallen ally at 50% Health (once per fight)", "cooldown": 99,
             "effect": {"revive_pct": 0.50, "min_star": 6, "mana_cost": 50}},
        ],
    },
    # CLERIC — frontline healer, tier-30 Acolyte signature
    "Cleric": {
        "common": [
            {"id": "blessing", "name": "Blessing", "type": "passive",
             "desc": "+12% Health", "effect": {"hlt_pct": 0.12}},
            {"id": "faithful_heart", "name": "Faithful Heart", "type": "passive",
             "desc": "-8% stress gain", "effect": {"stress_reduce": 0.08}},
        ],
        "uncommon": [
            {"id": "heal", "name": "Heal", "type": "active",
             "desc": "Heal the lowest-Health ally for 20% of their max Health", "cooldown": 3,
             "effect": {"heal_pct": 0.20, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "holy_light", "name": "Holy Light", "type": "active",
             "desc": "180% ATK to single target", "cooldown": 4,
             "effect": {"dmg_pct": 1.8, "single_target": True, "mana_cost": 30}},
        ],
        "epic": [
            {"id": "sanctuary", "name": "Sanctuary", "type": "active",
             "desc": "Shield the team for 30% damage reduction for 2 rounds", "cooldown": 6,
             "effect": {"team_dmg_reduce": 0.30, "duration": 2, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "miracle", "name": "Miracle", "type": "active",
             "desc": "Revive a fallen ally at 55% Health (once per fight)", "cooldown": 99,
             "effect": {"revive_pct": 0.55, "min_star": 6, "mana_cost": 50}},
        ],
    },
    # BARD — buff/utility, tier-30 Acolyte signature
    "Bard": {
        "common": [
            {"id": "inspiring_tune", "name": "Inspiring Tune", "type": "passive",
             "desc": "+5% ATK to all frontline allies", "effect": {"team_atk_pct": 0.05}},
            {"id": "quick_fingers_bard", "name": "Quick Fingers", "type": "passive",
             "desc": "+6% SPD", "effect": {"agi_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "rousing_ballad", "name": "Rousing Ballad", "type": "active",
             "desc": "Permanently boost team ATK 8% for the rest of the fight", "cooldown": 6,
             "effect": {"team_buff_pct": 0.08, "buff_stat": "strength", "mana_cost": 30}},
        ],
        "rare": [
            {"id": "soothing_melody", "name": "Soothing Melody", "type": "active",
             "desc": "Heal the lowest-Health ally for 22% of their max Health", "cooldown": 4,
             "effect": {"heal_pct": 0.22, "mana_cost": 30}},
        ],
        "epic": [
            {"id": "warsong", "name": "Warsong", "type": "active",
             "desc": "Permanently boost team SPD 12% for the rest of the fight", "cooldown": 7,
             "effect": {"team_buff_pct": 0.12, "buff_stat": "agility", "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "ballad_of_heroes", "name": "Ballad of Heroes", "type": "passive",
             "desc": "+15% ATK to all frontline allies", "effect": {"team_atk_pct": 0.15}},
        ],
    },
    # DRUID — nature hybrid damage/heal, tier-30 Acolyte signature
    "Druid": {
        "common": [
            {"id": "wild_growth", "name": "Wild Growth", "type": "passive",
             "desc": "+3% Health regen per round", "effect": {"regen_pct": 0.03}},
            {"id": "natures_touch", "name": "Nature's Touch", "type": "passive",
             "desc": "+8% Health", "effect": {"hlt_pct": 0.08}},
        ],
        "uncommon": [
            {"id": "thorn_whip", "name": "Thorn Whip", "type": "active",
             "desc": "150% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 1.5, "single_target": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "rejuvenation", "name": "Rejuvenation", "type": "active",
             "desc": "Heal the lowest-Health ally for 25% of their max Health", "cooldown": 4,
             "effect": {"heal_pct": 0.25, "mana_cost": 30}},
        ],
        "epic": [
            {"id": "entangling_roots", "name": "Entangling Roots", "type": "active",
             "desc": "Stun all enemies for 1 round", "cooldown": 6,
             "effect": {"enemy_stun": 1, "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "natures_wrath", "name": "Nature's Wrath", "type": "active",
             "desc": "Hit all enemies for 150% ATK", "cooldown": 8,
             "effect": {"aoe": True, "dmg_pct": 1.5, "mana_cost": 45}},
        ],
    },
    # MONK — melee/self-sustain hybrid, tier-30 Acolyte signature
    "Monk": {
        "common": [
            {"id": "iron_body", "name": "Iron Body", "type": "passive",
             "desc": "+8% Health, +5% damage reduction", "effect": {"hlt_pct": 0.08, "dmg_reduction_pct": 0.05}},
            {"id": "focused_breath", "name": "Focused Breath", "type": "passive",
             "desc": "+2% Health regen per round", "effect": {"regen_pct": 0.02}},
        ],
        "uncommon": [
            {"id": "palm_strike", "name": "Palm Strike", "type": "active",
             "desc": "170% ATK, heal self 10% of damage dealt", "cooldown": 3,
             "effect": {"dmg_pct": 1.7, "single_target": True, "lifesteal_pct": 0.10, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "meditation", "name": "Meditation", "type": "active",
             "desc": "Heal self for 25% of max Health", "cooldown": 4,
             "effect": {"self_heal_pct": 0.25, "mana_cost": 25}},
        ],
        "epic": [
            {"id": "iron_fist_flurry", "name": "Iron Fist Flurry", "type": "active",
             "desc": "Hit 3 enemies for 100% ATK each", "cooldown": 5,
             "effect": {"multi_target": 3, "dmg_pct": 1.0, "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "enlightenment", "name": "Enlightenment", "type": "passive",
             "desc": "+15% all stats", "effect": {"all_pct": 0.15}},
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # BASE LINEAGE: SPELLSWORD (hybrid melee/caster)
    # ═══════════════════════════════════════════════════════════════
    "Spellsword": {
        "common": [
            {"id": "enchanted_edge", "name": "Enchanted Edge", "type": "passive",
             "desc": "+8% ATK", "effect": {"str_pct": 0.0, "int_pct": 0.08}},
            {"id": "spell_armor", "name": "Spell Armor", "type": "passive",
             "desc": "+6% magic resist", "effect": {"magic_resist_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "rune_slash", "name": "Rune Slash", "type": "active",
             "desc": "180% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 1.8, "single_target": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "arcane_parry", "name": "Arcane Parry", "type": "passive",
             "desc": "+8% damage reduction", "effect": {"dmg_reduction_pct": 0.08}},
            {"id": "elemental_edge", "name": "Elemental Edge", "type": "active",
             "desc": "190% ATK single target, ignore 15% DEF", "cooldown": 4,
             "effect": {"dmg_pct": 1.9, "single_target": True, "ignore_def": True, "mana_cost": 32}},
        ],
        "epic": [
            {"id": "spellblade_flurry", "name": "Spellblade Flurry", "type": "active",
             "desc": "Hit 2 enemies for 140% ATK each, heal self 10% of damage dealt", "cooldown": 5,
             "effect": {"multi_target": 2, "dmg_pct": 1.4, "lifesteal_pct": 0.10, "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "rune_ascendance", "name": "Rune Ascendance", "type": "passive",
             "desc": "+15% ATK, +10% magic resist",
             "effect": {"int_pct": 0.15, "magic_resist_pct": 0.10}},
        ],
    },
    # ELDRITCH KNIGHT — battlemage tank, tier-30 Spellsword signature
    "Eldritch Knight": {
        "common": [
            {"id": "warded_blade", "name": "Warded Blade", "type": "passive",
             "desc": "+8% DEF, +5% magic resist", "effect": {"int_pct": 0.08, "magic_resist_pct": 0.05}},
            {"id": "battle_focus", "name": "Battle Focus", "type": "passive",
             "desc": "+6% ATK", "effect": {"str_pct": 0.0, "int_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "spellsteel_strike", "name": "Spellsteel Strike", "type": "active",
             "desc": "200% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 2.0, "single_target": True, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "arcane_ward", "name": "Arcane Ward", "type": "active",
             "desc": "Shield the team for 25% damage reduction for 2 rounds", "cooldown": 5,
             "effect": {"team_dmg_reduce": 0.25, "duration": 2, "mana_cost": 35}},
        ],
        "epic": [
            {"id": "runic_bulwark", "name": "Runic Bulwark", "type": "passive",
             "desc": "+10% damage reduction, +10% magic resist",
             "effect": {"dmg_reduction_pct": 0.10, "magic_resist_pct": 0.10}},
        ],
        "legendary": [
            {"id": "spellblade_ascendant", "name": "Spellblade Ascendant", "type": "passive",
             "desc": "Each kill grants +15% ATK for the rest of combat",
             "effect": {"kill_atk_stack": 0.15}},
        ],
    },
    # RUNE BLADE — rune-empowered striker, tier-30 Spellsword signature
    "Rune Blade": {
        "common": [
            {"id": "etched_runes", "name": "Etched Runes", "type": "passive",
             "desc": "+10% ATK", "effect": {"str_pct": 0.0, "int_pct": 0.10}},
            {"id": "rune_ward", "name": "Rune Ward", "type": "passive",
             "desc": "+5% physical resist", "effect": {"physical_resist_pct": 0.05}},
        ],
        "uncommon": [
            {"id": "rune_burst", "name": "Rune Burst", "type": "active",
             "desc": "210% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 2.1, "single_target": True, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "rune_chain", "name": "Rune Chain", "type": "active",
             "desc": "Hit 2 enemies for 130% ATK each", "cooldown": 4,
             "effect": {"multi_target": 2, "dmg_pct": 1.3, "mana_cost": 35}},
        ],
        "epic": [
            {"id": "rune_overload", "name": "Rune Overload", "type": "active",
             "desc": "320% ATK single target, ignore DEF", "cooldown": 6,
             "effect": {"dmg_pct": 3.2, "ignore_def": True, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "runeblade_apex", "name": "Runeblade Apex", "type": "passive",
             "desc": "+15% ATK, +10% physical resist",
             "effect": {"int_pct": 0.15, "physical_resist_pct": 0.10}},
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # SUPPORT-NAMED BUT COMBAT-CAPABLE BASE LINEAGES
    # ═══════════════════════════════════════════════════════════════
    "Medic": {
        "common": [
            {"id": "field_dressing", "name": "Field Dressing", "type": "active",
             "desc": "Heal the lowest-Health ally for 18% of their max Health", "cooldown": 3,
             "effect": {"heal_pct": 0.18, "mana_cost": 20}},
            {"id": "steady_hands_medic", "name": "Steady Hands", "type": "passive",
             "desc": "+8% Health", "effect": {"hlt_pct": 0.08}},
        ],
        "uncommon": [
            {"id": "triage", "name": "Triage", "type": "active",
             "desc": "Heal the lowest-Health ally for 28% of their max Health", "cooldown": 4,
             "effect": {"heal_pct": 0.28, "mana_cost": 30}},
        ],
        "rare": [
            {"id": "stabilize", "name": "Stabilize", "type": "active",
             "desc": "Cleanse own afflictions and heal self 15%", "cooldown": 4,
             "effect": {"cleanse_self": True, "self_heal_pct": 0.15, "mana_cost": 25}},
        ],
        "epic": [
            {"id": "emergency_surgery", "name": "Emergency Surgery", "type": "active",
             "desc": "Revive a fallen ally at 30% Health (once per fight)", "cooldown": 99,
             "effect": {"revive_pct": 0.30, "min_star": 6, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "miracle_worker_medic", "name": "Against All Odds", "type": "active",
             "desc": "Revive a fallen ally at 50% Health (once per fight)", "cooldown": 99,
             "effect": {"revive_pct": 0.50, "min_star": 6, "mana_cost": 50}},
        ],
    },
    "Scout": {
        "common": [
            {"id": "keen_senses", "name": "Keen Senses", "type": "passive",
             "desc": "+8% dodge chance", "effect": {"dodge_pct": 0.08}},
            {"id": "fleet_footed", "name": "Fleet-Footed", "type": "passive",
             "desc": "+8% SPD", "effect": {"agi_pct": 0.08}},
        ],
        "uncommon": [
            {"id": "snap_shot", "name": "Snap Shot", "type": "active",
             "desc": "160% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 1.6, "single_target": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "evasive_maneuvers", "name": "Evasive Maneuvers", "type": "passive",
             "desc": "+10% dodge chance", "effect": {"dodge_pct": 0.10}},
        ],
        "epic": [
            {"id": "ambush_tactics", "name": "Ambush Tactics", "type": "active",
             "desc": "220% ATK, guaranteed crit", "cooldown": 5,
             "effect": {"dmg_pct": 2.2, "single_target": True, "guaranteed_crit": True, "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "ghost_in_the_woods", "name": "Ghost in the Woods", "type": "passive",
             "desc": "+18% dodge chance, +8% SPD",
             "effect": {"dodge_pct": 0.18, "agi_pct": 0.08}},
        ],
    },
    "Tactician": {
        "common": [
            {"id": "battlefield_read", "name": "Battlefield Read", "type": "passive",
             "desc": "+5% ATK to all frontline allies", "effect": {"team_atk_pct": 0.05}},
            {"id": "composed_mind", "name": "Composed Mind", "type": "passive",
             "desc": "-8% stress gain", "effect": {"stress_reduce": 0.08}},
        ],
        "uncommon": [
            {"id": "flank_signal", "name": "Flank Signal", "type": "active",
             "desc": "Permanently boost team ATK 8% for the rest of the fight", "cooldown": 6,
             "effect": {"team_buff_pct": 0.08, "buff_stat": "strength", "mana_cost": 30}},
        ],
        "rare": [
            {"id": "disabling_order", "name": "Disabling Order", "type": "active",
             "desc": "Stun all enemies for 1 round", "cooldown": 6,
             "effect": {"enemy_stun": 1, "mana_cost": 35}},
        ],
        "epic": [
            {"id": "coordinated_strike", "name": "Coordinated Strike", "type": "active",
             "desc": "Permanently boost team SPD 12% for the rest of the fight", "cooldown": 7,
             "effect": {"team_buff_pct": 0.12, "buff_stat": "agility", "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "grand_strategy", "name": "Grand Strategy", "type": "passive",
             "desc": "+15% ATK to all frontline allies", "effect": {"team_atk_pct": 0.15}},
        ],
    },
    "Merchant": {
        "common": [
            {"id": "haggle_swing", "name": "Coin Toss", "type": "active",
             "desc": "130% ATK to a single target", "cooldown": 2,
             "effect": {"dmg_pct": 1.3, "single_target": True, "mana_cost": 15}},
            {"id": "lucky_charm", "name": "Lucky Charm", "type": "passive",
             "desc": "+5% crit chance", "effect": {"crit_pct": 0.05}},
        ],
        "uncommon": [
            {"id": "gilded_gauntlet", "name": "Gilded Gauntlet", "type": "active",
             "desc": "170% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 1.7, "single_target": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "appraisers_eye", "name": "Appraiser's Eye", "type": "passive",
             "desc": "+8% crit chance", "effect": {"crit_pct": 0.08}},
        ],
        "epic": [
            {"id": "hard_bargain", "name": "Hard Bargain", "type": "active",
             "desc": "200% ATK, +60% damage if target below 30% Health", "cooldown": 5,
             "effect": {"dmg_pct": 2.0, "single_target": True, "execute_bonus_pct": 0.60, "execute_threshold": 0.30, "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "fortunes_favor", "name": "Fortune's Favor", "type": "passive",
             "desc": "+15% all stats", "effect": {"all_pct": 0.15}},
        ],
    },
    "Farmer": {
        "common": [
            {"id": "pitchfork_jab", "name": "Pitchfork Jab", "type": "active",
             "desc": "140% ATK to a single target", "cooldown": 2,
             "effect": {"dmg_pct": 1.4, "single_target": True, "mana_cost": 15}},
            {"id": "calloused_hands", "name": "Calloused Hands", "type": "passive",
             "desc": "+6% Health", "effect": {"hlt_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "scarecrow_stand", "name": "Scarecrow Stand", "type": "active",
             "desc": "Force all enemies to target you for 2 rounds", "cooldown": 4,
             "effect": {"taunt_duration": 2, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "harvest_swing", "name": "Harvest Swing", "type": "active",
             "desc": "Hit 2 enemies for 90% ATK each", "cooldown": 3,
             "effect": {"multi_target": 2, "dmg_pct": 0.90, "mana_cost": 25}},
        ],
        "epic": [
            {"id": "bountiful_resolve", "name": "Bountiful Resolve", "type": "passive",
             "desc": "+10% Health, +8% damage reduction",
             "effect": {"hlt_pct": 0.10, "dmg_reduction_pct": 0.08}},
        ],
        "legendary": [
            {"id": "harvest_moon", "name": "Harvest Moon", "type": "active",
             "desc": "Hit all enemies for 130% ATK", "cooldown": 7,
             "effect": {"aoe": True, "dmg_pct": 1.3, "mana_cost": 40}},
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # MORE BASE LINEAGES — the literal base name (Blacksmith, Alchemist,
    # Chef, Priest, Quartermaster) never fights, but every one of their
    # tier-30+ evolutions does (is_combat_class is True for all of them),
    # so the lineage still needs a real kit, just themed around the trade.
    # ═══════════════════════════════════════════════════════════════
    "Blacksmith": {
        "common": [
            {"id": "hammer_swing", "name": "Hammer Swing", "type": "active",
             "desc": "150% ATK to a single target", "cooldown": 2,
             "effect": {"dmg_pct": 1.5, "single_target": True, "mana_cost": 15}},
            {"id": "forge_calloused", "name": "Forge-Calloused", "type": "passive",
             "desc": "+8% damage reduction", "effect": {"dmg_reduction_pct": 0.08}},
        ],
        "uncommon": [
            {"id": "molten_edge", "name": "Molten Edge", "type": "active",
             "desc": "190% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 1.9, "single_target": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "tempered_plate", "name": "Tempered Plate", "type": "passive",
             "desc": "+10% physical resist", "effect": {"physical_resist_pct": 0.10}},
        ],
        "epic": [
            {"id": "sledgehammer_crush", "name": "Sledgehammer Crush", "type": "active",
             "desc": "260% ATK single target, ignore DEF", "cooldown": 5,
             "effect": {"dmg_pct": 2.6, "ignore_def": True, "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "masterwork", "name": "Masterwork", "type": "passive",
             "desc": "+15% ATK, +12% physical resist",
             "effect": {"str_pct": 0.15, "physical_resist_pct": 0.12}},
        ],
    },
    "Alchemist": {
        "common": [
            {"id": "acid_flask", "name": "Acid Flask", "type": "active",
             "desc": "140% ATK to a single target", "cooldown": 2,
             "effect": {"dmg_pct": 1.4, "single_target": True, "mana_cost": 15}},
            {"id": "tonic_resilience", "name": "Tonic Resilience", "type": "passive",
             "desc": "+8% Health", "effect": {"hlt_pct": 0.08}},
        ],
        "uncommon": [
            {"id": "caustic_brew", "name": "Caustic Brew", "type": "passive",
             "desc": "Attacks apply 3% max Health poison for 3 rounds",
             "effect": {"poison_pct": 0.03, "poison_duration": 3}},
        ],
        "rare": [
            {"id": "healing_draught", "name": "Healing Draught", "type": "active",
             "desc": "Heal the lowest-Health ally for 25% of their max Health", "cooldown": 4,
             "effect": {"heal_pct": 0.25, "mana_cost": 30}},
        ],
        "epic": [
            {"id": "volatile_mixture", "name": "Volatile Mixture", "type": "active",
             "desc": "Hit all enemies for 110% ATK", "cooldown": 6,
             "effect": {"aoe": True, "dmg_pct": 1.1, "mana_cost": 40}},
        ],
        "legendary": [
            {"id": "philosophers_elixir", "name": "Philosopher's Elixir", "type": "active",
             "desc": "Cleanse own afflictions and heal self 25%", "cooldown": 5,
             "effect": {"cleanse_self": True, "self_heal_pct": 0.25, "mana_cost": 35}},
        ],
    },
    "Chef": {
        "common": [
            {"id": "cleaver_chop", "name": "Cleaver Chop", "type": "active",
             "desc": "150% ATK to a single target", "cooldown": 2,
             "effect": {"dmg_pct": 1.5, "single_target": True, "mana_cost": 15}},
            {"id": "hearty_meal", "name": "Hearty Meal", "type": "passive",
             "desc": "+8% Health", "effect": {"hlt_pct": 0.08}},
        ],
        "uncommon": [
            {"id": "flambe", "name": "Flambé", "type": "active",
             "desc": "Hit 2 enemies for 90% ATK each", "cooldown": 3,
             "effect": {"multi_target": 2, "dmg_pct": 0.90, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "secret_recipe", "name": "Secret Recipe", "type": "active",
             "desc": "Heal the lowest-Health ally for 22% of their max Health", "cooldown": 4,
             "effect": {"heal_pct": 0.22, "mana_cost": 30}},
        ],
        "epic": [
            {"id": "knife_flurry", "name": "Knife Flurry", "type": "active",
             "desc": "Hit 3 enemies for 100% ATK each", "cooldown": 5,
             "effect": {"multi_target": 3, "dmg_pct": 1.0, "mana_cost": 35}},
        ],
        "legendary": [
            {"id": "michelin_mastery", "name": "Michelin Mastery", "type": "passive",
             "desc": "+15% all stats", "effect": {"all_pct": 0.15}},
        ],
    },
    "Priest": {
        "common": [
            {"id": "minor_blessing", "name": "Minor Blessing", "type": "active",
             "desc": "Heal the lowest-Health ally for 15% of their max Health", "cooldown": 3,
             "effect": {"heal_pct": 0.15, "mana_cost": 20}},
            {"id": "devout_calm", "name": "Devout Calm", "type": "passive",
             "desc": "-10% stress gain", "effect": {"stress_reduce": 0.10}},
        ],
        "uncommon": [
            {"id": "holy_smite", "name": "Holy Smite", "type": "active",
             "desc": "160% ATK to single target", "cooldown": 3,
             "effect": {"dmg_pct": 1.6, "single_target": True, "mana_cost": 25}},
        ],
        "rare": [
            {"id": "absolution", "name": "Absolution", "type": "active",
             "desc": "Cleanse own afflictions and heal self 20%", "cooldown": 4,
             "effect": {"cleanse_self": True, "self_heal_pct": 0.20, "mana_cost": 30}},
        ],
        "epic": [
            {"id": "divine_intervention", "name": "Divine Intervention", "type": "active",
             "desc": "Shield the team for 28% damage reduction for 2 rounds", "cooldown": 6,
             "effect": {"team_dmg_reduce": 0.28, "duration": 2, "mana_cost": 38}},
        ],
        "legendary": [
            {"id": "sacred_rebirth", "name": "Sacred Rebirth", "type": "active",
             "desc": "Revive a fallen ally at 45% Health (once per fight)", "cooldown": 99,
             "effect": {"revive_pct": 0.45, "min_star": 6, "mana_cost": 50}},
        ],
    },
    "Quartermaster": {
        "common": [
            {"id": "supply_strike", "name": "Supply Strike", "type": "active",
             "desc": "140% ATK to a single target", "cooldown": 2,
             "effect": {"dmg_pct": 1.4, "single_target": True, "mana_cost": 15}},
            {"id": "well_equipped", "name": "Well-Equipped", "type": "passive",
             "desc": "+6% damage reduction", "effect": {"dmg_reduction_pct": 0.06}},
        ],
        "uncommon": [
            {"id": "requisition", "name": "Requisition", "type": "active",
             "desc": "Permanently boost team ATK 8% for the rest of the fight", "cooldown": 6,
             "effect": {"team_buff_pct": 0.08, "buff_stat": "strength", "mana_cost": 30}},
        ],
        "rare": [
            {"id": "field_resupply", "name": "Field Resupply", "type": "active",
             "desc": "Heal the lowest-Health ally for 22% of their max Health", "cooldown": 4,
             "effect": {"heal_pct": 0.22, "mana_cost": 30}},
        ],
        "epic": [
            {"id": "stockpile_reserves", "name": "Stockpile Reserves", "type": "passive",
             "desc": "+12% Health, +8% damage reduction",
             "effect": {"hlt_pct": 0.12, "dmg_reduction_pct": 0.08}},
        ],
        "legendary": [
            {"id": "logistics_mastery", "name": "Logistics Mastery", "type": "passive",
             "desc": "+15% all stats", "effect": {"all_pct": 0.15}},
        ],
    },
    "Classless": {
        "common": [
            {"id": "adaptable", "name": "Adaptable", "type": "passive",
             "desc": "+5% all stats", "effect": {"all_pct": 0.05}},
            {"id": "improvised_strike", "name": "Improvised Strike", "type": "active",
             "desc": "140% ATK to a single target", "cooldown": 2,
             "effect": {"dmg_pct": 1.4, "single_target": True, "mana_cost": 15}},
        ],
        "uncommon": [
            {"id": "jack_of_all_trades", "name": "Jack of All Trades", "type": "passive",
             "desc": "+6% ATK, +6% dodge chance", "effect": {"str_pct": 0.06, "dodge_pct": 0.06}},
        ],
        "rare": [
            {"id": "self_taught", "name": "Self-Taught", "type": "active",
             "desc": "190% ATK to single target, heal self 10% of damage dealt", "cooldown": 4,
             "effect": {"dmg_pct": 1.9, "single_target": True, "lifesteal_pct": 0.10, "mana_cost": 30}},
        ],
        "epic": [
            {"id": "unbroken_will", "name": "Unbroken Will", "type": "passive",
             "desc": "Survive one killing blow with 1 Health (once per fight)",
             "effect": {"death_save": 1}},
        ],
        "legendary": [
            {"id": "true_potential", "name": "True Potential", "type": "passive",
             "desc": "+20% all stats", "effect": {"all_pct": 0.20}},
        ],
    },
}

# Lineage resolution — maps every evolved class name back to the BASE
# lineage name whose SKILL_POOL entry it should fall back to when it
# doesn't have its own exact-match entry above (e.g. tier-60 pinnacle
# forms like "Templar" or "Archmage", and any base class without a
# kit yet like Blacksmith/Alchemist/Chef/Priest/Quartermaster — those
# stay on GENERIC_SKILLS since they're not combat-capable anyway).
# Built once from class_service.CLASS_EVOLUTIONS so it can't drift out
# of sync with the actual evolution tree.
_LINEAGE_MAP = None

def _build_lineage_map() -> dict:
    from services.class_service import CLASS_EVOLUTIONS
    mapping = {}
    for base, tiers in CLASS_EVOLUTIONS.items():
        tier30 = tiers.get(30, [])
        for name in tier30:
            mapping.setdefault(name, base)
        tier60 = tiers.get(60, {})
        for branch_names in tier60.values():
            for name in branch_names:
                mapping.setdefault(name, base)
    return mapping

def _resolve_lineage(hero_class: str) -> str:
    global _LINEAGE_MAP
    if _LINEAGE_MAP is None:
        _LINEAGE_MAP = _build_lineage_map()
    return _LINEAGE_MAP.get(hero_class, hero_class)

# Generic skills for any class with no kit above (and no lineage fallback
# either) — mostly the non-combat support classes (Blacksmith, Alchemist,
# Chef, Priest, Quartermaster and their evolutions) which is harmless,
# since they never enter combat in the first place.
GENERIC_SKILLS = {
    "common": [
        {"id": "tough", "name": "Tough", "type": "passive",
         "desc": "+8% Health", "effect": {"hlt_pct": 0.08}},
        {"id": "determined", "name": "Determined", "type": "passive",
         "desc": "+5% all stats", "effect": {"all_pct": 0.05}},
        {"id": "calm_mind", "name": "Calm Mind", "type": "passive",
         "desc": "-10% stress gain", "effect": {"stress_reduce": 0.10}},
        {"id": "steady_hands", "name": "Steady Hands", "type": "passive",
         "desc": "+5% crit chance", "effect": {"crit_add": 0.05}},
        {"id": "light_footed", "name": "Light Footed", "type": "passive",
         "desc": "+5% dodge chance", "effect": {"dodge_add": 0.05}},
        # A common-tier active so even a 1-star's first roll has a real
        # shot at an active skill, not just the uncommon+ ones below.
        {"id": "quick_strike", "name": "Quick Strike", "type": "active",
         "desc": "130% ATK to a single target", "cooldown": 2, "mana_cost": 15,
         "effect": {"dmg_pct": 1.3, "single_target": True}},
    ],
    "uncommon": [
        {"id": "survivor", "name": "Survivor", "type": "passive",
         "desc": "+15% Health, -5% ATK", "effect": {"hlt_pct": 0.15, "str_pct": -0.05}},
        {"id": "field_medic", "name": "Field Medic", "type": "passive",
         "desc": "Restore 3% Health to self each round", "effect": {"regen_pct": 0.03}},
        {"id": "power_strike", "name": "Power Strike", "type": "active",
         "desc": "150% ATK to a single target", "cooldown": 3, "mana_cost": 25,
         "effect": {"dmg_pct": 1.5, "single_target": True}},
    ],
    "rare": [
        {"id": "iron_will", "name": "Iron Will", "type": "passive",
         "desc": "Immune to fear stun", "effect": {"fear_immune": True}},
        {"id": "hardy", "name": "Hardy", "type": "passive",
         "desc": "+10% damage reduction", "effect": {"dmg_reduction_pct": 0.10}},
        {"id": "focused_assault", "name": "Focused Assault", "type": "active",
         "desc": "180% ATK to a single target, guaranteed crit", "cooldown": 4, "mana_cost": 35,
         "effect": {"dmg_pct": 1.8, "single_target": True, "guaranteed_crit": True}},
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


def _eligible(skill: dict, hero_star: int) -> bool:
    """Some skills (e.g. revive) are deliberately gated to only the
    strongest heroes — too powerful a tool to hand a non-godlike figure.
    min_star lives on the effect dict; absent means no restriction."""
    return skill.get("effect", {}).get("min_star", 1) <= hero_star


def get_skill_for_class(hero_class: str, rarity: str = None, hero_star: int = 7) -> dict | None:
    """Get a random skill for a class at a given rarity. Resolution order:
    exact match in SKILL_POOL -> lineage base's SKILL_POOL entry -> GENERIC_SKILLS.
    hero_star filters out anything above the hero's reach (e.g. revive_pct
    skills require min_star 6) — defaults to 7 (unrestricted) for any
    caller that doesn't have a star on hand."""
    if rarity is None:
        rarity = roll_skill_rarity()

    pool = SKILL_POOL.get(hero_class)
    if pool is None:
        pool = SKILL_POOL.get(_resolve_lineage(hero_class))
    if pool is None:
        pool = GENERIC_SKILLS

    skills = [s for s in pool.get(rarity, []) if _eligible(s, hero_star)] if isinstance(pool, dict) else []

    # If no class-specific skill at this rarity, try generic
    if not skills:
        skills = [s for s in GENERIC_SKILLS.get(rarity, []) if _eligible(s, hero_star)]

    if not skills:
        return None

    skill = random.choice(skills).copy()
    skill["rarity"] = rarity
    skill["tier"] = "Beginner"
    skill["level"] = 1
    skill["xp"] = 0
    skill["max_xp"] = 100
    return skill


def _get_any_active_skill_for_class(hero_class: str, hero_star: int = 7) -> dict | None:
    """Scans every rarity tier (common -> legendary) for the first 'active'
    skill in this class's pool — used to guarantee 3★+ heroes get at least
    one active skill at birth. Several class pools only have an active
    skill starting at 'uncommon', and common-rarity rolls dominate at low
    star — without this, a caster could end up with passive-only skills,
    which combined with basic attacks now always scaling off Strength (see
    calc_damage's force_strength) would leave their Intelligence with
    nothing to actually do."""
    pool = SKILL_POOL.get(hero_class) or SKILL_POOL.get(_resolve_lineage(hero_class)) or GENERIC_SKILLS
    if not isinstance(pool, dict):
        return None
    for rarity in ["common", "uncommon", "rare", "epic", "legendary"]:
        for s in pool.get(rarity, []):
            if s.get("type") == "active" and _eligible(s, hero_star):
                skill = s.copy()
                skill["rarity"] = rarity
                skill["tier"] = "Beginner"
                skill["level"] = 1
                skill["xp"] = 0
                skill["max_xp"] = 100
                return skill
    return None


def assign_initial_skills(hero_class: str, birth_star: int) -> list[dict]:
    """Assign starting skills to a new hero. Higher star = better chance of rare skills."""
    skills = []

    # Everyone gets 1 skill at birth
    # Higher star heroes get a rarity bonus
    rarity_bonus = {1: 0, 2: 0, 3: 5, 4: 10, 5: 20, 6: 30, 7: 50}
    bonus = rarity_bonus.get(birth_star, 0)

    # Roll with bonus applied
    skill = get_skill_for_class(hero_class, hero_star=birth_star)
    if skill and bonus > 0:
        # Chance to upgrade rarity
        if random.randint(0, 100) < bonus:
            rarity_order = ["common", "uncommon", "rare", "epic", "legendary"]
            idx = rarity_order.index(skill["rarity"])
            if idx < len(rarity_order) - 1:
                upgraded = get_skill_for_class(hero_class, rarity_order[idx + 1], hero_star=birth_star)
                if upgraded:
                    skill = upgraded

    if skill:
        skills.append(skill)

    # 4★+ heroes get a second skill
    if birth_star >= 4:
        skill2 = get_skill_for_class(hero_class, hero_star=birth_star)
        if skill2 and skill2["id"] != skills[0]["id"]:
            skills.append(skill2)

    # 6★+ heroes get a third skill
    if birth_star >= 6 and len(skills) >= 2:
        skill3 = get_skill_for_class(hero_class, hero_star=birth_star)
        if skill3 and skill3["id"] not in [s["id"] for s in skills]:
            skills.append(skill3)

    # 3★+ are guaranteed at least one active skill — see
    # _get_any_active_skill_for_class for why this matters now that basic
    # attacks always scale off Strength regardless of class.
    if birth_star >= 3 and not any(s.get("type") == "active" for s in skills):
        guaranteed_active = _get_any_active_skill_for_class(hero_class, hero_star=birth_star)
        if guaranteed_active and guaranteed_active["id"] not in [s["id"] for s in skills]:
            skills.append(guaranteed_active)

    for s in skills:
        if "tier" not in s:
            s["tier"] = "Beginner"
            s["level"] = 1
            s["xp"] = 0
            s["max_xp"] = 100

    return skills


# ─── Weapon Art ──────────────────────────────────────────────────────
#
# A bonus active skill tied to the WEAPON TYPE itself, not the class or
# rarity roll — granted on top of a hero's normal skill list, for free,
# for as long as they have a matching-type weapon equipped (see
# class_service.get_weapon_affinity for the hard equip restriction and
# combat_service.resolve_hero_stats for where this gets granted). Every
# class sharing a weapon type shares its Art — a Knight and a Berserker
# both holding a Sword get the same Cross Slash; they're already
# distinct via their own class kit.
WEAPON_ART_SKILLS = {
    "Sword": {"id": "art_sword", "name": "Cross Slash", "type": "active",
              "desc": "190% ATK to a single target", "cooldown": 3,
              "effect": {"dmg_pct": 1.9, "single_target": True, "mana_cost": 25}},
    "Spear": {"id": "art_spear", "name": "Piercing Lunge", "type": "active",
              "desc": "170% ATK, ignore 20% DEF", "cooldown": 3,
              "effect": {"dmg_pct": 1.7, "single_target": True, "ignore_def": True, "mana_cost": 25}},
    "Staff": {"id": "art_staff", "name": "Arcane Discharge", "type": "active",
              "desc": "190% ATK to a single target", "cooldown": 3,
              "effect": {"dmg_pct": 1.9, "single_target": True, "mana_cost": 25}},
    "Bow": {"id": "art_bow", "name": "Eagle Eye Shot", "type": "active",
            "desc": "200% ATK, guaranteed crit", "cooldown": 4,
            "effect": {"dmg_pct": 2.0, "single_target": True, "guaranteed_crit": True, "mana_cost": 30}},
    "Dagger": {"id": "art_dagger", "name": "Twin Fang", "type": "active",
               "desc": "Hit 2 enemies for 90% ATK each, heal 15% of damage dealt", "cooldown": 3,
               "effect": {"multi_target": 2, "dmg_pct": 0.9, "lifesteal_pct": 0.15, "mana_cost": 25}},
}

def get_weapon_art_skill(weapon_type: str) -> dict | None:
    art = WEAPON_ART_SKILLS.get(weapon_type)
    if not art:
        return None
    skill = art.copy()
    skill["rarity"] = "art"
    skill["tier"] = "Beginner"
    skill["level"] = 1
    skill["xp"] = 0
    skill["max_xp"] = 100
    return skill


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

        if "str_pct" in eff:
            h["strength"] = int(h["strength"] * (1 + eff["str_pct"]))
        if "int_pct" in eff:
            h["intelligence"] = int(h["intelligence"] * (1 + eff["int_pct"]))
        if "agi_pct" in eff:
            h["agility"] = int(h["agility"] * (1 + eff["agi_pct"]))
        if "hlt_pct" in eff:
            h["max_health"] = int(h["max_health"] * (1 + eff["hlt_pct"]))
            h["health"] = int(h["health"] * (1 + eff["hlt_pct"]))
        if "all_pct" in eff:
            mult = 1 + eff["all_pct"]
            h["strength"] = int(h["strength"] * mult)
            h["intelligence"] = int(h["intelligence"] * mult)
            h["agility"] = int(h["agility"] * mult)
            h["max_health"] = int(h["max_health"] * mult)
            h["health"] = int(h["health"] * mult)
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
        if "dmg_reduction_pct" in eff:
            h["dmg_reduction_pct"] = h.get("dmg_reduction_pct", 0.0) + eff["dmg_reduction_pct"]
        if "physical_resist_pct" in eff:
            h["physical_resist_pct"] = h.get("physical_resist_pct", 0.0) + eff["physical_resist_pct"]
        if "magic_resist_pct" in eff:
            h["magic_resist_pct"] = h.get("magic_resist_pct", 0.0) + eff["magic_resist_pct"]

    return h

# ─── Active skill mana costs ───────────────────────────────────────
#
# mana_cost is an optional key on an active skill's effect dict — falls
# back to a flat default for any skill that doesn't specify one.
DEFAULT_SKILL_MANA_COST = 25

def get_skill_mana_cost(skill: dict) -> int:
    return skill.get("effect", {}).get("mana_cost", DEFAULT_SKILL_MANA_COST)

# Effect-key combos this version's combat dispatcher (combat_service.py
# _execute_active_skill) does NOT know how to resolve yet — Time Warp's
# extra-turn and Meteor's self-stun need a second action-queue concept, and
# Suppressing Fire's speed debuff needs a temp-stat-with-restore mechanism,
# none of which exist yet. Excluded from the castable pool rather than
# silently no-oping a turn away when picked.
UNHANDLED_ACTIVE_EFFECT_KEYS = {"team_double_turn", "self_stun", "enemy_spd_debuff"}

def is_skill_executable(skill: dict) -> bool:
    if skill.get("type") != "active":
        return False
    return not UNHANDLED_ACTIVE_EFFECT_KEYS.intersection(skill.get("effect", {}).keys())
