from datetime import datetime


def process_infirmary(conn):
    """Assigned Medics/Priests passively heal trauma and HP for the whole
    living roster over time. Own tick clock, same pattern as the other
    facility services."""
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

    infirmary = conn.execute("SELECT id FROM facilities WHERE type = 'Infirmary' AND base_id = 1").fetchone()
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

    trauma_per_tick = 0
    hp_pct_per_tick = 0.0
    for a in assignments:
        if a["hero_class"] in ("Medic", "Priest"):
            trauma_per_tick += 2
            hp_pct_per_tick += 0.03
        else:
            trauma_per_tick += 1
            hp_pct_per_tick += 0.01

    ticks = minutes_passed // 5
    if ticks > 0:
        heroes = conn.execute("SELECT id, hp, max_hp, trauma FROM heroes WHERE is_alive = 1").fetchall()
        for h in heroes:
            new_trauma = max(0, h["trauma"] - trauma_per_tick * ticks)
            new_hp = min(h["max_hp"], h["hp"] + int(h["max_hp"] * hp_pct_per_tick * ticks))
            conn.execute("UPDATE heroes SET trauma = ?, hp = ? WHERE id = ?", (new_trauma, new_hp, h["id"]))

    conn.execute("UPDATE base SET last_infirmary_tick = CURRENT_TIMESTAMP WHERE id = 1")
