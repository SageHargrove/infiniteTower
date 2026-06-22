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

def pull_rarity() -> int:
    """Roll a birth star rarity using weighted RNG."""
    roll = random.uniform(0, TOTAL_WEIGHT)
    cumulative = 0
    for star, weight in RARITY_WEIGHTS.items():
        cumulative += weight
        if roll <= cumulative:
            return star
    return 1

def generate_base_stats(birth_star: int) -> dict:
    """
    Base stats scale with birth star, but not linearly.
    High birth star = strong start, less room for surprise growth.
    """
    base = {
        1: {"hp": 80,  "attack": 8,  "defense": 4,  "speed": 9},
        2: {"hp": 95,  "attack": 10, "defense": 5,  "speed": 10},
        3: {"hp": 115, "attack": 13, "defense": 7,  "speed": 11},
        4: {"hp": 140, "attack": 17, "defense": 9,  "speed": 12},
        5: {"hp": 175, "attack": 22, "defense": 12, "speed": 14},
        6: {"hp": 220, "attack": 30, "defense": 16, "speed": 16},
        7: {"hp": 300, "attack": 42, "defense": 22, "speed": 20},
    }
    stats = base[birth_star].copy()
    # Add some variance per hero (+/- 10%)
    for key in stats:
        variance = random.uniform(0.9, 1.1)
        stats[key] = max(1, int(stats[key] * variance))
    stats["max_hp"] = stats["hp"]
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
        return {f"apt_{apt}": random.randint(90, 100) for apt in ["combat", "tactical", "survival", "mental", "leadership"]}

    lo, hi = APTITUDE_RANGES.get(birth_star, (10, 55))
    return {f"apt_{apt}": random.randint(lo, hi) for apt in ["combat", "tactical", "survival", "mental", "leadership"]}

def get_pull_cost() -> int:
    return 100  # gold per pull, can expand to pity system later
