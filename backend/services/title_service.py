def check_and_assign_titles(conn, hero_id: int) -> list:
    """Check a hero's metrics and assign titles if earned. Returns list of new titles."""
    row = conn.execute("SELECT name, title, lifetime_kills, sole_survivor_boss_clears, leader_clears, unique_floor_clears FROM heroes WHERE id = ?", (hero_id,)).fetchone()
    if not row: return []

    hero = dict(row)
    new_titles = []
    
    current_title = hero.get("title")
    
    earned = None
    # Priority order: The higher ones override lower ones if they meet multiple in one go
    if hero["lifetime_kills"] >= 1000: earned = "The Executioner"
    elif hero["sole_survivor_boss_clears"] >= 1: earned = "The Survivor"
    elif hero["leader_clears"] >= 50: earned = "The Commander"
    elif hero["unique_floor_clears"] >= 10: earned = "The Vanguard"

    # Only assign if they don't have a title, or if we want to overwrite it. For now, 
    # we just overwrite to the latest earned title if it's different.
    if earned and current_title != earned:
        conn.execute("UPDATE heroes SET title = ? WHERE id = ?", (earned, hero_id))
        new_titles.append(f"👑 {hero['name']} earned the title: {earned}!")

    return new_titles
