"""Achievement catalog + progress/claim logic.

Achievements are entirely computed from existing live DB state (or the new
total_summons/total_battles_won/arena_wins/arena_losses counters on `base`)
rather than fired by event hooks — every achievement's `metric_fn` just
re-reads the relevant stat each time the list is requested, so there's no
risk of an achievement silently never firing because some call site forgot
to bump a counter. The one exception is total_summons/total_battles_won
themselves, which DO need a counter (no existing column tracks them), and
arena_wins/arena_losses, which stay at 0 until the separate arena_server
reports results back to the local profile (not wired yet — see README).

Rewards are mostly gems; a handful of the hardest ones grant a Summon
Ticket (see services/gacha service's _create_one_hero / routers/gacha.py's
/use-ticket) or a piece of equipment.
"""

CATEGORIES = ["Tower", "Summoning", "Roster", "Combat", "Economy", "Equipment", "Arena"]


def _scalar(conn, sql, params=()) -> int:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return 0
    val = row[0]
    return int(val) if val is not None else 0


ACHIEVEMENTS = [
    # ─── Tower Progress ───
    {"id": "floor_1", "name": "First Steps", "desc": "Reach Floor 1.", "category": "Tower",
     "metric_fn": lambda c: _scalar(c, "SELECT highest_floor FROM base WHERE id=1"), "target": 1,
     "reward": {"gems": 50}},
    {"id": "floor_5", "name": "Climbing", "desc": "Reach Floor 5.", "category": "Tower",
     "metric_fn": lambda c: _scalar(c, "SELECT highest_floor FROM base WHERE id=1"), "target": 5,
     "reward": {"gems": 100}},
    {"id": "floor_10", "name": "Getting Serious", "desc": "Reach Floor 10.", "category": "Tower",
     "metric_fn": lambda c: _scalar(c, "SELECT highest_floor FROM base WHERE id=1"), "target": 10,
     "reward": {"gems": 200}},
    {"id": "floor_25", "name": "Quarter Tower", "desc": "Reach Floor 25.", "category": "Tower",
     "metric_fn": lambda c: _scalar(c, "SELECT highest_floor FROM base WHERE id=1"), "target": 25,
     "reward": {"gems": 400}},
    {"id": "floor_50", "name": "Halfway Up", "desc": "Reach Floor 50 and survive the Raid Boss.", "category": "Tower",
     "metric_fn": lambda c: _scalar(c, "SELECT highest_floor FROM base WHERE id=1"), "target": 50,
     "reward": {"gems": 750, "summon_ticket": "5-Star Summon Ticket"}},
    {"id": "floor_75", "name": "Thin Air", "desc": "Reach Floor 75.", "category": "Tower",
     "metric_fn": lambda c: _scalar(c, "SELECT highest_floor FROM base WHERE id=1"), "target": 75,
     "reward": {"gems": 1000}},
    {"id": "floor_100", "name": "Top of the Spire", "desc": "Reach Floor 100 and survive the final Raid Boss.", "category": "Tower",
     "metric_fn": lambda c: _scalar(c, "SELECT highest_floor FROM base WHERE id=1"), "target": 100,
     "reward": {"gems": 2000, "summon_ticket": "7-Star Summon Ticket"}},

    # ─── Summoning ───
    {"id": "summon_1", "name": "First Summon", "desc": "Summon your first hero.", "category": "Summoning",
     "metric_fn": lambda c: _scalar(c, "SELECT total_summons FROM base WHERE id=1"), "target": 1,
     "reward": {"gems": 50}},
    {"id": "summon_10", "name": "Getting Started", "desc": "Summon 10 heroes total.", "category": "Summoning",
     "metric_fn": lambda c: _scalar(c, "SELECT total_summons FROM base WHERE id=1"), "target": 10,
     "reward": {"gems": 100}},
    {"id": "summon_50", "name": "Dedicated Summoner", "desc": "Summon 50 heroes total.", "category": "Summoning",
     "metric_fn": lambda c: _scalar(c, "SELECT total_summons FROM base WHERE id=1"), "target": 50,
     "reward": {"gems": 300}},
    {"id": "summon_150", "name": "Veteran Summoner", "desc": "Summon 150 heroes total.", "category": "Summoning",
     "metric_fn": lambda c: _scalar(c, "SELECT total_summons FROM base WHERE id=1"), "target": 150,
     "reward": {"gems": 600}},
    {"id": "summon_300", "name": "Whale's Path", "desc": "Summon 300 heroes total.", "category": "Summoning",
     "metric_fn": lambda c: _scalar(c, "SELECT total_summons FROM base WHERE id=1"), "target": 300,
     "reward": {"gems": 1000}},
    {"id": "pull_5star", "name": "Lucky Star", "desc": "Pull a 5★ hero.", "category": "Summoning",
     "metric_fn": lambda c: _scalar(c, "SELECT COUNT(*) FROM heroes WHERE birth_star >= 5"), "target": 1,
     "reward": {"gems": 150}},
    {"id": "pull_6star", "name": "Brilliant Star", "desc": "Pull a 6★ hero.", "category": "Summoning",
     "metric_fn": lambda c: _scalar(c, "SELECT COUNT(*) FROM heroes WHERE birth_star >= 6"), "target": 1,
     "reward": {"gems": 400}},
    {"id": "pull_7star", "name": "Mythic Pull", "desc": "Pull a 7★ hero.", "category": "Summoning",
     "metric_fn": lambda c: _scalar(c, "SELECT COUNT(*) FROM heroes WHERE birth_star >= 7"), "target": 1,
     "reward": {"gems": 1000, "summon_ticket": "4-Star Summon Ticket"}},
    {"id": "pull_7star_5", "name": "Star Collector", "desc": "Own 5 seven-star heroes at once.", "category": "Summoning",
     "metric_fn": lambda c: _scalar(c, "SELECT COUNT(*) FROM heroes WHERE birth_star >= 7 AND is_alive = 1"), "target": 5,
     "reward": {"gems": 1500, "summon_ticket": "6-Star Summon Ticket"}},

    # ─── Roster ───
    {"id": "roster_10", "name": "Growing Family", "desc": "Have 10 living heroes in your roster.", "category": "Roster",
     "metric_fn": lambda c: _scalar(c, "SELECT COUNT(*) FROM heroes WHERE is_alive = 1"), "target": 10,
     "reward": {"gems": 150}},
    {"id": "roster_full", "name": "Full House", "desc": "Fill your roster to its current maximum size.", "category": "Roster",
     "metric_fn": lambda c: 1 if _scalar(c, "SELECT COUNT(*) FROM heroes WHERE is_alive = 1") >= max(1, _scalar(c, "SELECT max_roster_size FROM base WHERE id=1")) else 0,
     "target": 1, "reward": {"gems": 300}},
    {"id": "hero_level_20", "name": "Veteran", "desc": "Get a hero to Level 20.", "category": "Roster",
     "metric_fn": lambda c: _scalar(c, "SELECT COUNT(*) FROM heroes WHERE level >= 20"), "target": 1,
     "reward": {"gems": 200}},
    {"id": "hero_ascended", "name": "Ascended", "desc": "Ascend a hero at least once.", "category": "Roster",
     "metric_fn": lambda c: _scalar(c, "SELECT COUNT(*) FROM heroes WHERE ascension_star >= 1"), "target": 1,
     "reward": {"gems": 500}},

    # ─── Combat ───
    {"id": "battle_1", "name": "First Blood", "desc": "Win your first battle.", "category": "Combat",
     "metric_fn": lambda c: _scalar(c, "SELECT total_battles_won FROM base WHERE id=1"), "target": 1,
     "reward": {"gems": 50}},
    {"id": "battle_50", "name": "Battle-Hardened", "desc": "Win 50 battles.", "category": "Combat",
     "metric_fn": lambda c: _scalar(c, "SELECT total_battles_won FROM base WHERE id=1"), "target": 50,
     "reward": {"gems": 300}},
    {"id": "battle_200", "name": "War Veteran", "desc": "Win 200 battles.", "category": "Combat",
     "metric_fn": lambda c: _scalar(c, "SELECT total_battles_won FROM base WHERE id=1"), "target": 200,
     "reward": {"gems": 750}},
    {"id": "battle_500", "name": "Unstoppable", "desc": "Win 500 battles.", "category": "Combat",
     "metric_fn": lambda c: _scalar(c, "SELECT total_battles_won FROM base WHERE id=1"), "target": 500,
     "reward": {"gems": 1500, "summon_ticket": "5-Star Summon Ticket"}},

    # ─── Economy ───
    {"id": "gold_1000", "name": "Pocket Change", "desc": "Hold 1,000 gold at once.", "category": "Economy",
     "metric_fn": lambda c: _scalar(c, "SELECT gold FROM base WHERE id=1"), "target": 1000,
     "reward": {"gems": 50}},
    {"id": "gold_10000", "name": "Wealthy", "desc": "Hold 10,000 gold at once.", "category": "Economy",
     "metric_fn": lambda c: _scalar(c, "SELECT gold FROM base WHERE id=1"), "target": 10000,
     "reward": {"gems": 200}},
    {"id": "gold_50000", "name": "Tycoon", "desc": "Hold 50,000 gold at once.", "category": "Economy",
     "metric_fn": lambda c: _scalar(c, "SELECT gold FROM base WHERE id=1"), "target": 50000,
     "reward": {"gems": 500}},
    {"id": "gems_1000", "name": "Gem Hoarder", "desc": "Hold 1,000 gems at once.", "category": "Economy",
     "metric_fn": lambda c: _scalar(c, "SELECT gems FROM base WHERE id=1"), "target": 1000,
     "reward": {"gems": 300}},

    # ─── Equipment ───
    {"id": "equip_10", "name": "Geared Up", "desc": "Own 10 pieces of equipment.", "category": "Equipment",
     "metric_fn": lambda c: _scalar(c, "SELECT COUNT(*) FROM equipment"), "target": 10,
     "reward": {"gems": 150}},
    {"id": "equip_z", "name": "Master Collector", "desc": "Own a Z-rarity item.", "category": "Equipment",
     "metric_fn": lambda c: _scalar(c, "SELECT COUNT(*) FROM equipment WHERE rarity = 'Z'"), "target": 1,
     "reward": {"gems": 1000}},
    {"id": "equip_set", "name": "Matching Set", "desc": "Equip a full 3-piece gear set on one hero.", "category": "Equipment",
     "metric_fn": lambda c: _scalar(c, """
        SELECT COUNT(*) FROM (
            SELECT is_equipped_to, set_family, COUNT(*) as cnt
            FROM equipment
            WHERE is_equipped_to IS NOT NULL AND set_family IS NOT NULL
            GROUP BY is_equipped_to, set_family
            HAVING cnt >= 3
        )
     """), "target": 1, "reward": {"gems": 400}},

    # ─── Arena (PvP — stays at 0/locked until the arena_server reports
    # results back to this profile; see README Known Gaps) ───
    {"id": "arena_win_1", "name": "Arena Debut", "desc": "Win your first Arena match.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_wins FROM base WHERE id=1"), "target": 1,
     "reward": {"gems": 200}},
    {"id": "arena_win_10", "name": "Gladiator", "desc": "Win 10 Arena matches.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_wins FROM base WHERE id=1"), "target": 10,
     "reward": {"gems": 750}},
    {"id": "arena_win_25", "name": "Champion", "desc": "Win 25 Arena matches.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_wins FROM base WHERE id=1"), "target": 25,
     "reward": {"gems": 1500, "summon_ticket": "6-Star Summon Ticket"}},

    # ELO-rating milestones. Arena starts everyone at 1000; the K-factor
    # (arena_server/elo.py) tapers hard from 1800 toward the 2500 soft cap,
    # so each tier costs noticeably more wins than the last and the top one
    # or two are realistically out of reach for the vast majority of the
    # playerbase rather than a hard, ever wall.
    {"id": "arena_elo_1100", "name": "Up and Coming", "desc": "Reach 1,100 Arena ELO.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_elo FROM base WHERE id=1"), "target": 1100,
     "reward": {"gems": 150}},
    {"id": "arena_elo_1200", "name": "Proven Contender", "desc": "Reach 1,200 Arena ELO.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_elo FROM base WHERE id=1"), "target": 1200,
     "reward": {"gems": 250}},
    {"id": "arena_elo_1400", "name": "Seasoned Duelist", "desc": "Reach 1,400 Arena ELO.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_elo FROM base WHERE id=1"), "target": 1400,
     "reward": {"gems": 400}},
    {"id": "arena_elo_1600", "name": "Veteran Combatant", "desc": "Reach 1,600 Arena ELO.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_elo FROM base WHERE id=1"), "target": 1600,
     "reward": {"gems": 600}},
    {"id": "arena_elo_1800", "name": "Elite Gladiator", "desc": "Reach 1,800 Arena ELO — the point where every further gain starts getting hard.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_elo FROM base WHERE id=1"), "target": 1800,
     "reward": {"gems": 900, "summon_ticket": "5-Star Summon Ticket"}},
    {"id": "arena_elo_2000", "name": "Tower Vanguard", "desc": "Reach 2,000 Arena ELO.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_elo FROM base WHERE id=1"), "target": 2000,
     "reward": {"gems": 1300}},
    {"id": "arena_elo_2200", "name": "Spire's Apex", "desc": "Reach 2,200 Arena ELO.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_elo FROM base WHERE id=1"), "target": 2200,
     "reward": {"gems": 1800, "summon_ticket": "6-Star Summon Ticket"}},
    {"id": "arena_elo_2500", "name": "Legend of the Arena", "desc": "Reach 2,500 Arena ELO — the theoretical ceiling. Vanishingly few will ever see this.", "category": "Arena",
     "metric_fn": lambda c: _scalar(c, "SELECT arena_elo FROM base WHERE id=1"), "target": 2500,
     "reward": {"gems": 3000, "summon_ticket": "7-Star Summon Ticket"}},
]

_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}


def get_achievements_with_progress(conn) -> list[dict]:
    claimed_ids = {r["id"] for r in conn.execute("SELECT id FROM achievements_claimed").fetchall()}
    out = []
    for a in ACHIEVEMENTS:
        progress = a["metric_fn"](conn)
        out.append({
            "id": a["id"], "name": a["name"], "desc": a["desc"], "category": a["category"],
            "progress": min(progress, a["target"]), "target": a["target"],
            "complete": progress >= a["target"],
            "claimed": a["id"] in claimed_ids,
            "reward": a["reward"],
        })
    return out


def claim_achievement(conn, achievement_id: str) -> dict:
    a = _BY_ID.get(achievement_id)
    if not a:
        return {"error": "Unknown achievement."}
    already = conn.execute("SELECT 1 FROM achievements_claimed WHERE id = ?", (achievement_id,)).fetchone()
    if already:
        return {"error": "Already claimed."}
    progress = a["metric_fn"](conn)
    if progress < a["target"]:
        return {"error": "Not yet complete."}

    reward = a["reward"]
    if reward.get("gems"):
        conn.execute("UPDATE base SET gems = gems + ? WHERE id = 1", (reward["gems"],))
    if reward.get("gold"):
        conn.execute("UPDATE base SET gold = gold + ? WHERE id = 1", (reward["gold"],))
    if reward.get("summon_ticket"):
        ticket_name = reward["summon_ticket"]
        existing = conn.execute(
            "SELECT id, quantity FROM inventory WHERE item_name = ? AND item_type = 'summon_ticket'",
            (ticket_name,)
        ).fetchone()
        if existing:
            conn.execute("UPDATE inventory SET quantity = quantity + 1 WHERE id = ?", (existing["id"],))
        else:
            conn.execute(
                "INSERT INTO inventory (item_name, item_type, quantity, description) VALUES (?, 'summon_ticket', 1, ?)",
                (ticket_name, f"Use to summon a guaranteed {ticket_name.split('-')[0]}+ hero.")
            )

    conn.execute("INSERT INTO achievements_claimed (id) VALUES (?)", (achievement_id,))
    return {"ok": True, "reward": reward}
