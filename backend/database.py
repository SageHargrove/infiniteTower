import sqlite3
import json
from contextlib import contextmanager

DB_PATH = "game.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS heroes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            title TEXT,
            backstory TEXT,
            personality TEXT,
            portrait_path TEXT,

            -- Rarity
            birth_star INTEGER DEFAULT 1,
            ascension_star INTEGER DEFAULT 0,

            -- Class
            hero_class TEXT DEFAULT 'Classless',
            can_pilot INTEGER DEFAULT 0,

            -- Level
            level INTEGER DEFAULT 1,

            -- Base stats
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            attack INTEGER DEFAULT 10,
            defense INTEGER DEFAULT 5,
            speed INTEGER DEFAULT 10,

            -- Hidden aptitudes (0-100 each)
            apt_combat INTEGER DEFAULT 50,
            apt_tactical INTEGER DEFAULT 50,
            apt_survival INTEGER DEFAULT 50,
            apt_mental INTEGER DEFAULT 50,
            apt_leadership INTEGER DEFAULT 50,
            aptitudes_revealed INTEGER DEFAULT 0,

            -- Morale
            morale INTEGER DEFAULT 100,
            stress INTEGER DEFAULT 0,
            trauma INTEGER DEFAULT 0,
            morale_state TEXT DEFAULT 'steady',

            -- Status
            is_alive INTEGER DEFAULT 1,
            is_on_team INTEGER DEFAULT 0,
            floor_joined INTEGER DEFAULT 0,

            -- Progression
            kills INTEGER DEFAULT 0,
            floors_survived INTEGER DEFAULT 0,
            missions_completed INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT DEFAULT 'active',
            current_floor INTEGER DEFAULT 0,
            highest_floor INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS run_heroes (
            run_id INTEGER REFERENCES runs(id),
            hero_id INTEGER REFERENCES heroes(id),
            PRIMARY KEY (run_id, hero_id)
        );

        CREATE TABLE IF NOT EXISTS floors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES runs(id),
            floor_number INTEGER NOT NULL,
            floor_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            outcome TEXT,
            narrative TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS base (
            id INTEGER PRIMARY KEY DEFAULT 1,
            name TEXT DEFAULT 'The Hollow Spire',
            level INTEGER DEFAULT 1,
            gold INTEGER DEFAULT 10000,
            materials TEXT DEFAULT '{}',
            unlocked_features TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            floor_number INTEGER,
            event_type TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS portrait_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            birth_star INTEGER NOT NULL,
            path TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        INSERT OR IGNORE INTO base (id) VALUES (1);
        """)

        # Migrate existing DB — add columns if they don't exist
        existing = [r[1] for r in conn.execute("PRAGMA table_info(heroes)").fetchall()]
        migrations = [
            ("hero_class",  "ALTER TABLE heroes ADD COLUMN hero_class TEXT DEFAULT 'Classless'"),
            ("can_pilot",   "ALTER TABLE heroes ADD COLUMN can_pilot INTEGER DEFAULT 0"),
            ("level",       "ALTER TABLE heroes ADD COLUMN level INTEGER DEFAULT 1"),
        ]
        for col, sql in migrations:
            if col not in existing:
                conn.execute(sql)
                print(f"[DB] Migrated: added column '{col}'")

    print("Database initialized.")