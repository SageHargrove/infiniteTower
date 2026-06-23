import json
from database import db
from services.materials_service import CRAFTING_MATERIALS, tiered_material_name

# The Market doubles as a buy-stuff panel on top of its existing passive
# gold generation (see time_service.process_passive_generation) — a simple
# first-pass catalog focused on convenience items that aren't already
# covered by the gacha pulls (which stay the only source of equipment and
# heroes), so this doesn't compete with or devalue those.
SHOP_CATALOG = {
    "supplies_small": {"name": "Supplies Pack", "currency": "gold", "cost": 150, "grants": {"supplies": 10}},
    "supplies_large": {"name": "Supplies Crate", "currency": "gold", "cost": 1200, "grants": {"supplies": 100}},
    "bandages": {"name": "Bandage Bundle", "currency": "gold", "cost": 200, "grants": {"material": "Bandage", "amount": 5}},
    "materials_small": {"name": "Raw Material Crate", "currency": "gold", "cost": 300, "grants": {"material_random_d": 5}},
}

def get_shop_catalog() -> dict:
    return SHOP_CATALOG

def purchase_item(conn, item_id: str) -> dict:
    item = SHOP_CATALOG.get(item_id)
    if not item:
        raise ValueError("Unknown shop item.")

    col = "gold" if item["currency"] == "gold" else "gems"
    base = conn.execute(f"SELECT {col}, materials FROM base WHERE id = 1").fetchone()
    if base[col] < item["cost"]:
        raise ValueError(f"Not enough {col}.")
    conn.execute(f"UPDATE base SET {col} = {col} - ? WHERE id = 1", (item["cost"],))

    grants = item["grants"]
    result = {"item": item["name"]}

    if "supplies" in grants:
        conn.execute("UPDATE base SET supplies = supplies + ? WHERE id = 1", (grants["supplies"],))
        result["supplies"] = grants["supplies"]

    if "material" in grants or "material_random_d" in grants:
        materials = json.loads(base["materials"]) if base["materials"] else {}
        if "material" in grants:
            mat_name = grants["material"]
            materials[mat_name] = materials.get(mat_name, 0) + grants["amount"]
            result["material"] = mat_name
            result["amount"] = grants["amount"]
        else:
            import random
            amount = grants["material_random_d"]
            mat_name = tiered_material_name(random.choice(CRAFTING_MATERIALS), "D")
            materials[mat_name] = materials.get(mat_name, 0) + amount
            result["material"] = mat_name
            result["amount"] = amount
        conn.execute("UPDATE base SET materials = ? WHERE id = 1", (json.dumps(materials),))

    return result
