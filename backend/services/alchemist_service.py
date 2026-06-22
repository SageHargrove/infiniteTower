from datetime import datetime

POTION_CATALOG = [
    {"name": "Minor Healing Draught", "desc": "Heals a hero for 30% of max HP.", "effect": {"heal_pct": 0.3}, "min_level": 1},
    {"name": "Calming Tonic", "desc": "Clears 25 stress from a hero.", "effect": {"stress_delta": -25}, "min_level": 1},
    {"name": "Vitality Elixir", "desc": "Heals 60% max HP and clears 10 stress.", "effect": {"heal_pct": 0.6, "stress_delta": -10}, "min_level": 5},
    {"name": "Greater Healing Draught", "desc": "Heals a hero for 90% of max HP.", "effect": {"heal_pct": 0.9}, "min_level": 10},
    {"name": "Panacea", "desc": "Fully heals a hero and clears 50 stress and 20 trauma.", "effect": {"heal_pct": 1.0, "stress_delta": -50, "trauma_delta": -20}, "min_level": 20},
]


def process_alchemist_lab(conn):
    """Assigned Alchemists/Priests passively brew potions into the inventory
    over time, scaled by mental aptitude. Mirrors Mage Tower's research tick
    but on its own clock — same shared-column starvation bug must be avoided."""
    try:
        conn.execute("ALTER TABLE base ADD COLUMN last_alchemist_tick TIMESTAMP")
    except Exception:
        pass

    base = conn.execute("SELECT last_alchemist_tick FROM base WHERE id = 1").fetchone()
    if not base:
        return

    last_tick_str = dict(base).get("last_alchemist_tick")
    if not last_tick_str:
        conn.execute("UPDATE base SET last_alchemist_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    try:
        last_tick = datetime.strptime(last_tick_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        conn.execute("UPDATE base SET last_alchemist_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    now = datetime.utcnow()
    minutes_passed = int((now - last_tick).total_seconds() / 60)
    if minutes_passed <= 0:
        return

    lab = conn.execute("SELECT id, level FROM facilities WHERE type = 'Alchemist Lab' AND base_id = 1").fetchone()
    if not lab:
        return

    available_potions = [p for p in POTION_CATALOG if p["min_level"] <= lab["level"]]

    assignments = conn.execute("""
        SELECT fa.hero_id, h.hero_class, h.apt_mental
        FROM facility_assignments fa
        JOIN heroes h ON fa.hero_id = h.id
        WHERE fa.facility_id = ? AND h.is_alive = 1
    """, (lab["id"],)).fetchall()

    if not assignments:
        conn.execute("UPDATE base SET last_alchemist_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    import random
    brew_chance_total = 0.0
    for a in assignments:
        class_bonus = 0.04 if a["hero_class"] in ("Alchemist", "Grand Alchemist", "Mage") else 0.015
        mental_apt = (a["apt_mental"] or 50) / 100
        brew_chance_total += class_bonus + mental_apt * 0.02

    brew_rolls = min(minutes_passed, 30)
    for _ in range(brew_rolls):
        if random.random() < (brew_chance_total / max(1, len(assignments))):
            potion = random.choice(available_potions)
            existing = conn.execute(
                "SELECT id FROM inventory WHERE item_name = ? AND item_type = 'potion'", (potion["name"],)
            ).fetchone()
            if existing:
                conn.execute("UPDATE inventory SET quantity = quantity + 1 WHERE id = ?", (existing["id"],))
            else:
                conn.execute(
                    "INSERT INTO inventory (item_name, item_type, quantity, description) VALUES (?, 'potion', 1, ?)",
                    (potion["name"], potion["desc"])
                )

    conn.execute("UPDATE base SET last_alchemist_tick = CURRENT_TIMESTAMP WHERE id = 1")
