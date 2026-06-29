# Difficulty is a profile-level, creation-time-only setting (database.py's
# set_profile only writes it on first creation) — these are the three
# presets it can pick from. Read-only after creation by design: no setter
# is exposed to players, only the migration default ('normal') and the
# one-time write path in set_profile.
DIFFICULTY_PRESETS = {
    "easy":   {"enemy_stat_mult": 0.75, "gold_mult": 1.25, "rare_drop_mult": 0.70},
    "normal": {"enemy_stat_mult": 1.00, "gold_mult": 1.00, "rare_drop_mult": 1.00},
    "hard":   {"enemy_stat_mult": 1.35, "gold_mult": 1.00, "rare_drop_mult": 1.40},
}


def get_difficulty(conn) -> str:
    row = conn.execute("SELECT difficulty FROM base WHERE id = 1").fetchone()
    difficulty = row["difficulty"] if row else None
    return difficulty if difficulty in DIFFICULTY_PRESETS else "normal"


def get_difficulty_mults(conn) -> dict:
    return DIFFICULTY_PRESETS[get_difficulty(conn)]
