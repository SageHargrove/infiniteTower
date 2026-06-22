import json
from datetime import datetime, timezone
from database import db

def process_research_points(conn):
    base = conn.execute("SELECT last_training_tick FROM base WHERE id = 1").fetchone()
    if not base: return
    
    last_tick_str = dict(base).get("last_training_tick")
    if not last_tick_str: return
    
    # We will just piggyback off the training tick, assuming training_service updates it.
    # Wait, if training_service updates last_training_tick to CURRENT_TIMESTAMP, 
    # we can't calculate minutes_passed here!
    # Let's add last_research_tick instead.
    pass

SCROLL_CATALOG = [
    {"name": "Scroll of Restoration", "desc": "Clears 15 stress and 10 trauma from a hero.", "effect": {"stress_delta": -15, "trauma_delta": -10}, "min_level": 1},
    {"name": "Scroll of Insight", "desc": "Grants 60 bonus XP to one of a hero's skills.", "effect": {"skill_xp": 60}, "min_level": 1},
    {"name": "Scroll of Vigor", "desc": "Fully heals a hero.", "effect": {"heal_pct": 1.0}, "min_level": 5},
    {"name": "Scroll of Mastery", "desc": "Grants 150 bonus XP to one of a hero's skills.", "effect": {"skill_xp": 150}, "min_level": 10},
    {"name": "Scroll of the Archmage", "desc": "Fully heals a hero and grants 300 bonus skill XP.", "effect": {"heal_pct": 1.0, "skill_xp": 300}, "min_level": 20},
]

def process_mage_research(conn):
    # Mage Tower used to share last_research_tick with the Market/Farm passive
    # generator (time_service.process_passive_generation) — that function
    # resets the column to NOW right before this one reads it, so research_points
    # never had more than a few seconds of "minutes_passed" to work with. Mage
    # Tower needs its own clock.
    try:
        conn.execute("ALTER TABLE base ADD COLUMN last_mage_tick TIMESTAMP")
    except Exception:
        pass

    base = conn.execute("SELECT last_mage_tick FROM base WHERE id = 1").fetchone()
    if not base:
        return

    last_tick_str = dict(base).get("last_mage_tick")
    if not last_tick_str:
        conn.execute("UPDATE base SET last_mage_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    try:
        last_tick = datetime.strptime(last_tick_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        conn.execute("UPDATE base SET last_mage_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    now = datetime.utcnow()
    diff = now - last_tick
    minutes_passed = int(diff.total_seconds() / 60)

    if minutes_passed > 0:
        mt = conn.execute("SELECT id, level FROM facilities WHERE type = 'Mage Tower' AND base_id = 1").fetchone()
        if not mt:
            return

        available_scrolls = [s for s in SCROLL_CATALOG if s["min_level"] <= mt["level"]]

        assignments = conn.execute("""
            SELECT fa.hero_id, h.hero_class, h.level, h.apt_mental
            FROM facility_assignments fa
            JOIN heroes h ON fa.hero_id = h.id
            WHERE fa.facility_id = ? AND h.is_alive = 1
        """, (mt["id"],)).fetchall()

        from services.level_service import talent_score
        rp_gain = 0
        scroll_chance_total = 0.0
        for a in assignments:
            # Base generation based on class
            if a["hero_class"] == "Magic Engineer":
                rp_gain += 6 * minutes_passed
            elif a["hero_class"] == "Mage":
                rp_gain += 5 * minutes_passed
            elif a["hero_class"] == "Spellsword":
                rp_gain += 4 * minutes_passed
            else:
                rp_gain += 1 * minutes_passed

            # Mental aptitude scales generation instead of the old retired
            # genius/prodigy birth-roll traits.
            mental_apt = (a["apt_mental"] or 50) / 100
            rp_gain += int(mental_apt * 5 * minutes_passed)
            scroll_chance_total += 0.01 + mental_apt * 0.02

        if rp_gain > 0:
            conn.execute("UPDATE base SET research_points = COALESCE(research_points, 0) + ? WHERE id = 1", (rp_gain,))

        # Scrolls: a small per-tick-minute chance per assigned mage to produce
        # one, scaled by mental aptitude. Capped so it can't spiral with idle time.
        import random
        scroll_rolls = min(minutes_passed, 30)
        for _ in range(scroll_rolls):
            if assignments and random.random() < (scroll_chance_total / max(1, len(assignments))):
                scroll = random.choice(available_scrolls)
                existing = conn.execute(
                    "SELECT id, quantity FROM inventory WHERE item_name = ? AND item_type = 'scroll'", (scroll["name"],)
                ).fetchone()
                if existing:
                    conn.execute("UPDATE inventory SET quantity = quantity + 1 WHERE id = ?", (existing["id"],))
                else:
                    conn.execute(
                        "INSERT INTO inventory (item_name, item_type, quantity, description) VALUES (?, 'scroll', 1, ?)",
                        (scroll["name"], scroll["desc"])
                    )

        conn.execute("UPDATE base SET last_mage_tick = CURRENT_TIMESTAMP WHERE id = 1")
