import random

# Base material types — combat/explore drops roll one of these plus a tier
# letter (matching equipment's grade vocabulary) rather than a flat
# untiered count. Steel/Copper/Leather are new variety alongside the
# original five.
CRAFTING_MATERIALS = [
    "Slime Core", "Iron Ore", "Goblin Ear", "Monster Bone", "Mystic Dust",
    "Steel", "Copper", "Leather",
]

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
