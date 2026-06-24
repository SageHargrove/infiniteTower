import random

# Base material types — combat/explore drops roll one of these plus a tier
# letter (matching equipment's grade vocabulary) rather than a flat
# untiered count. Materials are also split into four progression tiers so a
# "Dragon Scale" can't show up on floor 2 no matter what quality letter it
# rolls — each tier unlocks at a floor threshold and stays a minority pick
# even once unlocked, layered on top of (not replacing) the D-S quality roll.
CRAFTING_MATERIALS = [
    "Slime Core", "Iron Ore", "Goblin Ear", "Monster Bone", "Mystic Dust",
    "Steel", "Copper", "Leather",
]

INTERMEDIATE_CRAFTING_MATERIALS = [
    "Wolf Pelt", "Ogre Hide", "Hardened Bone", "Refined Iron", "Spirit Dust",
]
INTERMEDIATE_MATERIAL_UNLOCK_FLOOR = 15
INTERMEDIATE_MATERIAL_DROP_CHANCE = 0.25

ADVANCED_CRAFTING_MATERIALS = [
    "Wyvern Scale", "Enchanted Steel", "Demon Ichor", "Runed Crystal",
]
ADVANCED_MATERIAL_UNLOCK_FLOOR = 40
ADVANCED_MATERIAL_DROP_CHANCE = 0.20

# Legendary materials are named like end-game gear components — these are
# the rarest tier, gated the furthest out and still a minority once unlocked.
LEGENDARY_CRAFTING_MATERIALS = [
    "Mithril", "Adamantine", "Dragon Scale", "Phoenix Feather", "Void Crystal",
]
LEGENDARY_MATERIAL_UNLOCK_FLOOR = 70
LEGENDARY_MATERIAL_DROP_CHANCE = 0.15

def roll_material_name(floor_number: int = 1) -> str:
    """Picks which base material drops. Rolls from the highest unlocked tier
    down, so a roster floor deep enough to see legendary materials can still
    get any lower tier too — only the common pool is unconditionally
    available, everything else is floor-gated AND a minority chance."""
    if floor_number >= LEGENDARY_MATERIAL_UNLOCK_FLOOR and random.random() < LEGENDARY_MATERIAL_DROP_CHANCE:
        return random.choice(LEGENDARY_CRAFTING_MATERIALS)
    if floor_number >= ADVANCED_MATERIAL_UNLOCK_FLOOR and random.random() < ADVANCED_MATERIAL_DROP_CHANCE:
        return random.choice(ADVANCED_CRAFTING_MATERIALS)
    if floor_number >= INTERMEDIATE_MATERIAL_UNLOCK_FLOOR and random.random() < INTERMEDIATE_MATERIAL_DROP_CHANCE:
        return random.choice(INTERMEDIATE_CRAFTING_MATERIALS)
    return random.choice(CRAFTING_MATERIALS)

MATERIAL_TIERS = ["D", "C", "B", "A", "S"]
MATERIAL_TIER_WEIGHTS = [0.45, 0.30, 0.16, 0.07, 0.02]

def roll_material_tier(avg_luck: float = 5.0) -> str:
    """Each tier is an independent weighted pick — there's no single
    multiplier point to scale by Luck without restructuring the weights
    themselves. Light-touch compromise instead: a roll that lands on the
    lowest tier ("D") gets a Luck-scaled chance to bump up one tier, rather
    than rewriting the weighting system."""
    tier = random.choices(MATERIAL_TIERS, weights=MATERIAL_TIER_WEIGHTS, k=1)[0]
    if tier == "D" and random.random() < min(0.5, avg_luck / 50):
        tier = MATERIAL_TIERS[1]
    return tier

def tiered_material_name(base_name: str, tier: str = None, avg_luck: float = 5.0) -> str:
    return f"{base_name} ({tier or roll_material_tier(avg_luck)})"

def base_material_name(tiered_name: str) -> str:
    """Strip the "(tier)" suffix, if present, back to the plain base name —
    recipes/costs are written against base names and don't care which tier
    satisfies them."""
    if tiered_name.endswith(")") and "(" in tiered_name:
        return tiered_name.rsplit(" (", 1)[0]
    return tiered_name

def get_material_total(materials: dict, base_name: str) -> int:
    """Sum every tier of base_name the player holds — recipes/ascension costs
    are written against the base name only, agnostic to which tier(s)
    actually cover the cost."""
    return sum(qty for name, qty in materials.items() if base_material_name(name) == base_name)

def consume_material(materials: dict, base_name: str, qty: int) -> dict:
    """Deduct qty of base_name from materials, spending the lowest tiers
    first so better material stays banked for when it's actually needed.
    Mutates and returns the same dict. Raises ValueError if insufficient."""
    if get_material_total(materials, base_name) < qty:
        raise ValueError(f"Not enough {base_name}.")
    remaining = qty
    matching_keys = [k for k in materials if base_material_name(k) == base_name]
    tier_order = {t: i for i, t in enumerate(MATERIAL_TIERS)}
    def tier_of(key):
        bn = base_material_name(key)
        suffix = key[len(bn):].strip(" ()")
        return tier_order.get(suffix, 0)
    matching_keys.sort(key=tier_of)
    for key in matching_keys:
        if remaining <= 0:
            break
        take = min(materials[key], remaining)
        materials[key] -= take
        remaining -= take
        if materials[key] <= 0:
            del materials[key]
    return materials
