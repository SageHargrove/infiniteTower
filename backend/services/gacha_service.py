import random
import math

# Pull weights — strict percentages (out of 10000 total)
RARITY_WEIGHTS = {
    1: 6000, # 60.00%
    2: 2000, # 20.00%
    3: 1200, # 12.00%
    4: 600,  # 6.00%
    5: 175,  # 1.75%
    6: 20,   # 0.20%
    7: 5,    # 0.05%
}

TOTAL_WEIGHT = sum(RARITY_WEIGHTS.values())

def pull_rarity(min_star: int = 1, max_star: int = 7) -> int:
    """Roll a birth star rarity using weighted RNG, optionally restricted to
    a [min_star, max_star] window (gold pulls are capped at 1-4★, gem pulls
    at 2-7★ — see /gacha/pull). Re-normalizes against just that subset of
    RARITY_WEIGHTS rather than clamping the unrestricted roll, so the
    relative odds between the allowed stars stay proportional to their
    original weights instead of getting distorted by clamping."""
    allowed = {s: w for s, w in RARITY_WEIGHTS.items() if min_star <= s <= max_star}
    total = sum(allowed.values())
    roll = random.uniform(0, total)
    cumulative = 0
    for star, weight in allowed.items():
        cumulative += weight
        if roll <= cumulative:
            return star
    return min_star

# Health is no longer its own rolled stat — Endurance (the old Defense slot)
# now drives it directly, so a hero's effective tankiness is one number, not
# two independently-rolled ones. See HP_FLOOR/HP_PER_ENDURANCE below.
HP_FLOOR = 20
HP_PER_ENDURANCE = 12

def health_from_endurance(endurance: int) -> int:
    return HP_FLOOR + int(endurance) * HP_PER_ENDURANCE

def generate_base_stats(birth_star: int) -> dict:
    """
    Base stats scale with birth star, but not linearly.
    High birth star = strong start, less room for surprise growth.
    """
    base = {
        1: {"strength": 8,  "intelligence": 4,  "endurance": 5,  "agility": 9,  "willpower": 6,  "luck": 5},
        2: {"strength": 10, "intelligence": 5,  "endurance": 6,  "agility": 10, "willpower": 7,  "luck": 6},
        3: {"strength": 13, "intelligence": 7,  "endurance": 8,  "agility": 11, "willpower": 9,  "luck": 7},
        4: {"strength": 17, "intelligence": 9,  "endurance": 10, "agility": 12, "willpower": 12, "luck": 8},
        5: {"strength": 22, "intelligence": 12, "endurance": 14, "agility": 14, "willpower": 16, "luck": 9},
        6: {"strength": 30, "intelligence": 16, "endurance": 18, "agility": 16, "willpower": 21, "luck": 10},
        7: {"strength": 42, "intelligence": 22, "endurance": 26, "agility": 20, "willpower": 28, "luck": 12},
    }
    stats = base[birth_star].copy()
    # Add some variance per hero (+/- 10%)
    for key in stats:
        variance = random.uniform(0.9, 1.1)
        stats[key] = max(1, int(stats[key] * variance))
    # defense is the legacy column name still read by a few old call sites —
    # kept in sync with endurance rather than removed, see database.py migration notes.
    stats["defense"] = stats["endurance"]
    stats["max_health"] = health_from_endurance(stats["endurance"])
    stats["health"] = stats["max_health"]
    return stats

# Generation gives every hero a class-neutral STR/INT split — a Mage would
# otherwise roll with more raw muscle than magic, which makes no sense once
# class is known. Lean shifts points between STR and INT (positive = more
# physical, negative = more magical) without changing their combined total,
# so a class's overall power budget at a given star stays the same — it's
# reshuffled, not boosted.
CLASS_STAT_LEAN = {
    "Warrior": 0.40, "Spearman": 0.35, "Thief": 0.30, "Archer": 0.30,
    "Mage": -0.45, "Spellsword": -0.05, "Acolyte": -0.35, "Priest": -0.40,
    "Tactician": -0.20, "Scout": 0.15, "Blacksmith": 0.20, "Medic": -0.25,
    "Quartermaster": -0.10, "Farmer": 0.10, "Merchant": -0.10,
    "Alchemist": -0.30, "Magic Engineer": -0.30,
}

def apply_class_stat_bias(stats: dict, hero_class: str) -> dict:
    lean = CLASS_STAT_LEAN.get(hero_class, 0.0)
    if lean == 0.0:
        return stats
    total = stats["strength"] + stats["intelligence"]
    shift = int(total * abs(lean) * 0.5)
    if lean > 0:
        stats["strength"] += shift
        stats["intelligence"] = max(1, stats["intelligence"] - shift)
    else:
        stats["intelligence"] += shift
        stats["strength"] = max(1, stats["strength"] - shift)
    return stats

APTITUDE_RANGES = {
    1: (10, 55), 2: (15, 60), 3: (25, 65), 4: (35, 70),
    5: (55, 80), 6: (70, 90), 7: (85, 100),
}

# A 1-5★ pull has a tiny, genuinely rare chance to be a hidden prodigy —
# talent on par with a natural 7★, just born into a lower rarity. This
# drives growth potential (see level_service.talent_score), NOT current
# stats — you have to find it, then choose to invest in raising them.
# 6-7★ are already near the talent ceiling, so there's no jackpot to roll
# into; pulling a 7★ means you can assume top-tier talent already.
APTITUDE_JACKPOT_CHANCE = {1: 0.005, 2: 0.005, 3: 0.01, 4: 0.015, 5: 0.03}

def generate_aptitudes(birth_star: int) -> dict:
    """
    Hidden aptitudes drive how steeply a hero's stats grow per level —
    not their current power. Higher birth_star reliably rolls high
    aptitude; lower birth_star usually rolls modest aptitude, with a rare
    jackpot chance at true prodigy-tier talent.
    """
    if random.random() < APTITUDE_JACKPOT_CHANCE.get(birth_star, 0):
        return {f"apt_{apt}": random.randint(90, 100) for apt in ["combat", "tactical", "survival", "mental", "leadership", "diligence"]}

    lo, hi = APTITUDE_RANGES.get(birth_star, (10, 55))
    return {f"apt_{apt}": random.randint(lo, hi) for apt in ["combat", "tactical", "survival", "mental", "leadership", "diligence"]}

def get_pull_cost() -> int:
    return 100  # gold per pull, can expand to pity system later

EQUIPMENT_PULL_COST = {"gold": 500, "gem": 150}
# Gold pulls: D-B tier (cheap, common gear). Gem pulls: C-S tier (pricier,
# meaningfully better floor). SS/SSS/Z are never available from any gacha
# pull either way — crafting and rare boss/high-floor drops only.
EQUIPMENT_PULL_ODDS = {
    "gold": [("D-", "D", "D+", 0.55), ("C-", "C", "C+", 0.35), ("B-", "B", "B+", 0.10)],
    "gem":  [("C-", "C", "C+", 0.45), ("B-", "B", "B+", 0.40), ("A-", "A", "A+", 0.12), ("S-", "S", "S+", 0.03)],
}

def pull_equipment_gacha(conn, currency: str = "gold") -> dict:
    from services.equipment_service import _roll_equipment_stats, RARITY_MULTS, EQUIPMENT_ADJECTIVES
    import random

    currency = currency if currency in EQUIPMENT_PULL_COST else "gold"
    cost = EQUIPMENT_PULL_COST[currency]
    col = "gems" if currency == "gem" else "gold"
    base = conn.execute(f"SELECT {col} FROM base WHERE id = 1").fetchone()
    if base[col] < cost:
        raise ValueError(f"Not enough {col}.")
    conn.execute(f"UPDATE base SET {col} = {col} - ? WHERE id = 1", (cost,))

    roll = random.random()
    cumulative = 0.0
    tiers = EQUIPMENT_PULL_ODDS[currency]
    rarity = tiers[-1][1]  # fallback to the top tier's middle sub-grade
    for *grades, weight in tiers:
        cumulative += weight
        if roll <= cumulative:
            rarity = random.choice(grades)
            break

    eq_type = random.choice(["Weapon", "Armor", "Accessory"])
    mult = RARITY_MULTS[rarity]
    stats = _roll_equipment_stats(eq_type, mult)
    name = f"{EQUIPMENT_ADJECTIVES.get(rarity, rarity)} {eq_type}"

    return {
        "name": name, "type": eq_type, "rarity": rarity, "level": 1,
        **stats,
    }
