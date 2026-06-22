import sqlite3
import json
import os
from contextlib import contextmanager

SAVES_DIR = "saves"
os.makedirs(SAVES_DIR, exist_ok=True)

_ACTIVE_PROFILE_FILE = os.path.join(SAVES_DIR, ".active_profile")

def _load_active_profile():
    if os.path.exists(_ACTIVE_PROFILE_FILE):
        try:
            name = open(_ACTIVE_PROFILE_FILE, "r", encoding="utf-8").read().strip()
            if name:
                return name
        except Exception:
            pass
    return "main"

# Persisted to disk so a backend restart/reload (e.g. during dev) doesn't
# silently snap back to "main" while the frontend still thinks another
# profile is active.
ACTIVE_PROFILE = _load_active_profile()

if os.path.exists("game.db") and not os.path.exists(os.path.join(SAVES_DIR, "main.db")):
    os.rename("game.db", os.path.join(SAVES_DIR, "main.db"))

def get_db_path():
    return os.path.join(SAVES_DIR, f"{ACTIVE_PROFILE}.db")

def set_profile(profile_name):
    global ACTIVE_PROFILE
    ACTIVE_PROFILE = profile_name
    try:
        with open(_ACTIVE_PROFILE_FILE, "w", encoding="utf-8") as f:
            f.write(profile_name)
    except Exception:
        pass
    init_db()

def clear_active_profile():
    global ACTIVE_PROFILE
    ACTIVE_PROFILE = None
    try:
        if os.path.exists(_ACTIVE_PROFILE_FILE):
            os.remove(_ACTIVE_PROFILE_FILE)
    except Exception:
        pass

def get_profiles():
    if not os.path.exists(SAVES_DIR):
        return ["main"]
    profiles = []
    for f in os.listdir(SAVES_DIR):
        if f.endswith(".db"):
            profiles.append(f.replace(".db", ""))
    if not profiles:
        return ["main"]
    return profiles

def get_conn():
    conn = sqlite3.connect(get_db_path())
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
            hidden_class TEXT,
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
            team_position INTEGER DEFAULT 0,
            ego_type TEXT,
            ego_patience INTEGER DEFAULT 100,

            -- Progression
            kills INTEGER DEFAULT 0,
            floors_survived INTEGER DEFAULT 0,
            missions_completed INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_star INTEGER,
            synthesized INTEGER DEFAULT 0,
            skills TEXT DEFAULT '[]',
            synergy_group TEXT,
            gender TEXT,
            fatigue INTEGER DEFAULT 0,
            base_floor INTEGER DEFAULT 0,
            traits TEXT DEFAULT '[]',
            xp INTEGER DEFAULT 0,
            runes TEXT DEFAULT '[]',
            seals TEXT DEFAULT '[]'
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
            gold INTEGER DEFAULT 1000,
            gems INTEGER DEFAULT 500,
            supplies INTEGER DEFAULT 50,
            materials TEXT DEFAULT '{}',
            highest_floor INTEGER DEFAULT 0,
            max_roster_size INTEGER DEFAULT 10,
            unlocked_features TEXT DEFAULT '[]',
            research_points INTEGER DEFAULT 0,
            global_buffs TEXT DEFAULT '{}',
            pity_counter INTEGER DEFAULT 0,
            spark_points INTEGER DEFAULT 0,
            last_training_tick TIMESTAMP,
            last_fatigue_tick TIMESTAMP
        , last_research_tick TIMESTAMP, last_mage_tick TIMESTAMP, last_alchemist_tick TIMESTAMP, last_restaurant_tick TIMESTAMP);

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
        , gender TEXT, class_name TEXT);

CREATE TABLE IF NOT EXISTS facilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            base_id INTEGER DEFAULT 1,
            type TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            slots_unlocked INTEGER DEFAULT 1
        );

CREATE TABLE IF NOT EXISTS facility_assignments (
            facility_id INTEGER REFERENCES facilities(id),
            hero_id INTEGER REFERENCES heroes(id),
            role TEXT,
            target_hero_id INTEGER,
            target_skill_id TEXT,
            UNIQUE(hero_id)
        );

CREATE TABLE IF NOT EXISTS hero_chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT DEFAULT 'The Square',
            message TEXT NOT NULL,
            participants TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            rarity TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            base_atk INTEGER DEFAULT 0,
            base_def INTEGER DEFAULT 0,
            base_hp INTEGER DEFAULT 0,
            base_spd INTEGER DEFAULT 0,
            atk_pct REAL DEFAULT 0.0,
            def_pct REAL DEFAULT 0.0,
            hp_pct REAL DEFAULT 0.0,
            spd_pct REAL DEFAULT 0.0,
            crit_chance REAL DEFAULT 0.0,
            dodge_chance REAL DEFAULT 0.0,
            armor_pen REAL DEFAULT 0.0,
            is_equipped_to INTEGER REFERENCES heroes(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE IF NOT EXISTS hero_relics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relic_type TEXT NOT NULL,
            name TEXT NOT NULL,
            rarity TEXT NOT NULL,
            desc TEXT,
            effect TEXT NOT NULL,
            min_star INTEGER DEFAULT 1,
            is_equipped_to INTEGER REFERENCES heroes(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE IF NOT EXISTS legacies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hero_id INTEGER,
            hero_name TEXT,
            hero_star INTEGER,
            title TEXT,
            flavor_text TEXT,
            bonus_json TEXT,
            score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            description TEXT
        );

CREATE TABLE IF NOT EXISTS hero_bonds (
    hero_a_id INTEGER,
    hero_b_id INTEGER,
    bond_level REAL DEFAULT 0,
    floors_together INTEGER DEFAULT 0,
    PRIMARY KEY (hero_a_id, hero_b_id)
);

INSERT OR IGNORE INTO base (id) VALUES (1);






        """)

        try:
            conn.execute("ALTER TABLE base ADD COLUMN supplies INTEGER DEFAULT 500")
            print("[DB] Migrated: added column 'supplies' to base")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE base ADD COLUMN gems INTEGER DEFAULT 500")
            print("[DB] Migrated: added column 'gems' to base")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE portrait_cache ADD COLUMN gender TEXT")
            print("[DB] Migrated: added column 'gender' to portrait_cache")
        except sqlite3.OperationalError:
            pass
            
        try:
            conn.execute("ALTER TABLE portrait_cache ADD COLUMN class_name TEXT")
            print("[DB] Migrated: added column 'class_name' to portrait_cache")
        except sqlite3.OperationalError:
            pass
            
        try:
            conn.execute("ALTER TABLE heroes ADD COLUMN xp INTEGER DEFAULT 0")
            print("[DB] Migrated: added column 'xp' to heroes")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE base ADD COLUMN max_roster_size INTEGER DEFAULT 10")
            print("[DB] Migrated: added column 'max_roster_size' to base")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE base ADD COLUMN materials TEXT DEFAULT '{}'")
            print("[DB] Migrated: added column 'materials' to base")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE base ADD COLUMN last_rest_time REAL DEFAULT 0")
            print("[DB] Migrated: added column 'last_rest_time' to base")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE legacies ADD COLUMN is_sacrifice INTEGER DEFAULT 0")
            print("[DB] Migrated: added column 'is_sacrifice' to legacies")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE legacies ADD COLUMN portrait_path TEXT")
            print("[DB] Migrated: added column 'portrait_path' to legacies")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE equipment ADD COLUMN atk_pct REAL DEFAULT 0.0")
            conn.execute("ALTER TABLE equipment ADD COLUMN def_pct REAL DEFAULT 0.0")
            conn.execute("ALTER TABLE equipment ADD COLUMN hp_pct REAL DEFAULT 0.0")
            conn.execute("ALTER TABLE equipment ADD COLUMN spd_pct REAL DEFAULT 0.0")
            print("[DB] Migrated: added pct columns to equipment")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("UPDATE facilities SET type = 'The Lobby' WHERE type = 'The Square'")
            conn.commit()
        except Exception as e:
            print(f"[DB] Migration error for The Lobby: {e}")

        # Floor type is rolled once per floor number and cached here so
        # re-entering the same floor (rerun) always gives the same floor type.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS floor_cache (
                floor_number INTEGER PRIMARY KEY,
                floor_type TEXT NOT NULL
            )
        """)

        # Migrate existing DB — add columns if they don't exist
        existing = [r[1] for r in conn.execute("PRAGMA table_info(heroes)").fetchall()]
        migrations = [
            ("hero_class",  "ALTER TABLE heroes ADD COLUMN hero_class TEXT DEFAULT 'Classless'"),
            ("can_pilot",   "ALTER TABLE heroes ADD COLUMN can_pilot INTEGER DEFAULT 0"),
            ("level",       "ALTER TABLE heroes ADD COLUMN level INTEGER DEFAULT 1"),
            ("ego_patience", "ALTER TABLE heroes ADD COLUMN ego_patience INTEGER DEFAULT 100"),
        ]
        for col, sql in migrations:
            if col not in existing:
                conn.execute(sql)
                print(f"[DB] Migrated: added column '{col}'")

    print("Database initialized.")