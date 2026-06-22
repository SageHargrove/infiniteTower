from datetime import datetime


def process_restaurant(conn):
    """Assigned Chefs passively raise morale for the whole living roster
    (not just the deployed team) — distinct from manual Rest & Recovery,
    which is a one-time action. Own tick clock, same pattern as the other
    facility services."""
    try:
        conn.execute("ALTER TABLE base ADD COLUMN last_restaurant_tick TIMESTAMP")
    except Exception:
        pass

    base = conn.execute("SELECT last_restaurant_tick FROM base WHERE id = 1").fetchone()
    if not base:
        return

    last_tick_str = dict(base).get("last_restaurant_tick")
    if not last_tick_str:
        conn.execute("UPDATE base SET last_restaurant_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    try:
        last_tick = datetime.strptime(last_tick_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        conn.execute("UPDATE base SET last_restaurant_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    now = datetime.utcnow()
    minutes_passed = int((now - last_tick).total_seconds() / 60)
    if minutes_passed <= 0:
        return

    restaurant = conn.execute("SELECT id FROM facilities WHERE type = 'Restaurant' AND base_id = 1").fetchone()
    if not restaurant:
        return

    assignments = conn.execute("""
        SELECT fa.hero_id, h.hero_class
        FROM facility_assignments fa
        JOIN heroes h ON fa.hero_id = h.id
        WHERE fa.facility_id = ? AND h.is_alive = 1
    """, (restaurant["id"],)).fetchall()

    if not assignments:
        conn.execute("UPDATE base SET last_restaurant_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    morale_per_tick = 0
    for a in assignments:
        morale_per_tick += 3 if a["hero_class"] == "Chef" else 1

    ticks = minutes_passed // 5
    if ticks > 0:
        from services.morale_service import get_morale_state
        gain = morale_per_tick * ticks
        heroes = conn.execute("SELECT id, morale FROM heroes WHERE is_alive = 1").fetchall()
        for h in heroes:
            new_morale = min(100, h["morale"] + gain)
            conn.execute("UPDATE heroes SET morale = ?, morale_state = ? WHERE id = ?",
                         (new_morale, get_morale_state(new_morale), h["id"]))

    conn.execute("UPDATE base SET last_restaurant_tick = CURRENT_TIMESTAMP WHERE id = 1")
