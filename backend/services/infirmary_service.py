from datetime import datetime


def process_infirmary(conn):
    """Assigned Medics/Priests passively heal trauma for the whole living
    roster over time. Own tick clock, same pattern as the other facility
    services.

    No longer touches HP — lobby return already fully heals HP after every
    floor (see tower.py), so a passive HP trickle here had no purpose left.
    Infirmary is now purely the trauma/psych-recovery facility, plus
    Bandage crafting for assigned Medics/Priests (see craft_bandages)."""
    try:
        conn.execute("ALTER TABLE base ADD COLUMN last_infirmary_tick TIMESTAMP")
    except Exception:
        pass

    base = conn.execute("SELECT last_infirmary_tick FROM base WHERE id = 1").fetchone()
    if not base:
        return

    last_tick_str = dict(base).get("last_infirmary_tick")
    if not last_tick_str:
        conn.execute("UPDATE base SET last_infirmary_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    try:
        last_tick = datetime.strptime(last_tick_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        conn.execute("UPDATE base SET last_infirmary_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    now = datetime.utcnow()
    minutes_passed = int((now - last_tick).total_seconds() / 60)
    if minutes_passed <= 0:
        return

    infirmary = conn.execute("SELECT id, level FROM facilities WHERE type = 'Infirmary' AND base_id = 1").fetchone()
    if not infirmary:
        return

    assignments = conn.execute("""
        SELECT fa.hero_id, h.hero_class
        FROM facility_assignments fa
        JOIN heroes h ON fa.hero_id = h.id
        WHERE fa.facility_id = ? AND h.is_alive = 1
    """, (infirmary["id"],)).fetchall()

    if not assignments:
        conn.execute("UPDATE base SET last_infirmary_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    # Facility level used to do nothing here — leveling it only bought more
    # assignment slots, never made existing Medics/Priests heal any faster.
    level_mult = 1 + 0.10 * (infirmary["level"] - 1)
    trauma_per_tick = 0
    for a in assignments:
        if a["hero_class"] in ("Medic", "Priest"):
            trauma_per_tick += 2 * level_mult
        else:
            trauma_per_tick += 1 * level_mult

    ticks = minutes_passed // 5
    if ticks > 0:
        heroes = conn.execute("SELECT id, trauma FROM heroes WHERE is_alive = 1").fetchall()
        for h in heroes:
            new_trauma = max(0, h["trauma"] - int(trauma_per_tick * ticks))
            conn.execute("UPDATE heroes SET trauma = ? WHERE id = ?", (new_trauma, h["id"]))

    conn.execute("UPDATE base SET last_infirmary_tick = CURRENT_TIMESTAMP WHERE id = 1")


BANDAGE_CRAFT_COST = {"supplies": 15}
BANDAGE_HEAL_PCT = 0.30  # consumable in-combat heal, see services/combat_service.py usage


def craft_bandages(conn, crafter_id: int, quantity: int = 1) -> dict:
    """Medics/Priests assigned to the Infirmary can craft Bandages — a
    consumable usable in combat for in-fight healing (see BANDAGE_HEAL_PCT),
    giving the facility a productive role now that its old passive HP
    regen is gone. Crafting speed scales with the crafter's apt_tactical,
    same convention as equipment_service.craft_equipment."""
    crafter = conn.execute("SELECT id, hero_class, apt_tactical FROM heroes WHERE id = ? AND is_alive = 1", (crafter_id,)).fetchone()
    if not crafter:
        raise ValueError("Crafter not found or not alive.")

    infirmary = conn.execute("SELECT id FROM facilities WHERE type = 'Infirmary' AND base_id = 1").fetchone()
    if not infirmary:
        raise ValueError("No Infirmary built.")
    assigned = conn.execute("SELECT 1 FROM facility_assignments WHERE facility_id = ? AND hero_id = ?", (infirmary["id"], crafter_id)).fetchone()
    if not assigned:
        raise ValueError("Crafter must be assigned to the Infirmary.")

    total_cost = BANDAGE_CRAFT_COST["supplies"] * quantity
    base_row = conn.execute("SELECT supplies, materials FROM base WHERE id = 1").fetchone()
    if base_row["supplies"] < total_cost:
        raise ValueError(f"Not enough supplies. Need {total_cost}.")

    import json
    materials = json.loads(base_row["materials"]) if base_row["materials"] else {}
    materials["Bandage"] = materials.get("Bandage", 0) + quantity
    conn.execute("UPDATE base SET supplies = supplies - ?, materials = ? WHERE id = 1", (total_cost, json.dumps(materials)))

    return {"crafted": quantity, "material": "Bandage", "total": materials["Bandage"]}
