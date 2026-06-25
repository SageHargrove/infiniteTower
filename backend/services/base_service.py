def get_base_upgrade_level(conn, upgrade_id: str) -> int:
    """Shared lookup for the base-wide upgrade tree (Barracks/Infirmary/Forge/
    Watchtower/Archive/Chapel — see DEFAULT_UPGRADES in routers/base.py).
    Returns 0 if the upgrade hasn't been purchased yet (or doesn't exist),
    same as a hero who's never leveled up."""
    row = conn.execute("SELECT level FROM base_upgrades WHERE id = ?", (upgrade_id,)).fetchone()
    return row["level"] if row else 0


def get_floor_lp(conn, base_floor: int) -> dict:
    """Calculates the LP (Luxury Points) per hero on a given base floor, and the stat bonus pct."""
    all_heroes = conn.execute("SELECT base_floor FROM heroes WHERE is_alive = 1").fetchall()
    count = 0
    for h in all_heroes:
        if h["base_floor"] == base_floor:
            count += 1
            
    total_lp = base_floor * 100
    
    import math
    c = max(1, count)
    lp_per_hero = int(total_lp * (1.0 / math.sqrt(c)))
    stat_bonus_pct = lp_per_hero // 10
    
    return {
        "lp_per_hero": lp_per_hero,
        "stat_bonus_pct": stat_bonus_pct
    }
