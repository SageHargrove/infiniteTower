import sqlite3
import json
import os
import random
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
    if not ACTIVE_PROFILE:
        # Don't default to "main.db" because it causes zombie profiles to respawn
        # when background polling hits the API after deleting the last profile.
        raise ValueError("No active profile set")
    return os.path.join(SAVES_DIR, f"{ACTIVE_PROFILE}.db")

def set_profile(profile_name):
    global ACTIVE_PROFILE
    ACTIVE_PROFILE = profile_name
    os.makedirs(SAVES_DIR, exist_ok=True)
    with open(_ACTIVE_PROFILE_FILE, "w") as f:
        f.write(profile_name)
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
        return []
    profiles = []
    for f in os.listdir(SAVES_DIR):
        if f.endswith(".db") and f != "None.db":
            profiles.append(f.replace(".db", ""))
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
            health INTEGER DEFAULT 100,
            max_health INTEGER DEFAULT 100,
            strength INTEGER DEFAULT 10,
            intelligence INTEGER DEFAULT 5,
            defense INTEGER DEFAULT 5,
            agility INTEGER DEFAULT 10,
            -- defense is legacy/inert — endurance replaces it (mitigation +
            -- drives max_health) and is backfilled from defense on migration.
            -- See the ALTER TABLE block below for willpower/luck backfill too.
            endurance INTEGER DEFAULT 5,
            willpower INTEGER DEFAULT 6,
            luck INTEGER DEFAULT 5,

            -- Hidden aptitudes (0-100 each)
            apt_combat INTEGER DEFAULT 50,
            apt_tactical INTEGER DEFAULT 50,
            apt_survival INTEGER DEFAULT 50,
            apt_mental INTEGER DEFAULT 50,
            apt_leadership INTEGER DEFAULT 50,
            apt_diligence INTEGER DEFAULT 50,
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
            
            -- Titles Tracking
            lifetime_kills INTEGER DEFAULT 0,
            sole_survivor_boss_clears INTEGER DEFAULT 0,
            leader_clears INTEGER DEFAULT 0,
            unique_floor_clears INTEGER DEFAULT 0,
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
            equip_spark_points INTEGER DEFAULT 0,
            last_training_tick TIMESTAMP,
            last_fatigue_tick TIMESTAMP
        , last_research_tick TIMESTAMP, last_mage_tick TIMESTAMP, last_alchemist_tick TIMESTAMP, last_restaurant_tick TIMESTAMP, master_name TEXT, tutorial_complete INTEGER DEFAULT 0);

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

        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            materials_json TEXT NOT NULL, -- e.g. {"Iron": 3, "Slime": 1}
            gold_cost INTEGER DEFAULT 0,
            base_stat_mult REAL DEFAULT 1.0, -- multiplier for stats based on crafter power
            is_discovered INTEGER DEFAULT 1
        );

CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            rarity TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            base_str INTEGER DEFAULT 0,
            base_int INTEGER DEFAULT 0,
            base_hlt INTEGER DEFAULT 0,
            base_agi INTEGER DEFAULT 0,
            base_def INTEGER DEFAULT 0,
            base_end INTEGER DEFAULT 0,
            base_wil INTEGER DEFAULT 0,
            base_luck INTEGER DEFAULT 0,
            str_pct REAL DEFAULT 0.0,
            int_pct REAL DEFAULT 0.0,
            hlt_pct REAL DEFAULT 0.0,
            agi_pct REAL DEFAULT 0.0,
            crit_chance REAL DEFAULT 0.0,
            dodge_chance REAL DEFAULT 0.0,
            armor_pen REAL DEFAULT 0.0,
            dmg_reduction_pct REAL DEFAULT 0.0,
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

CREATE TABLE IF NOT EXISTS base_upgrades (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            level INTEGER DEFAULT 0,
            max_level INTEGER DEFAULT 5,
            unlocked INTEGER DEFAULT 0
        );

CREATE TABLE IF NOT EXISTS hero_bonds (
    hero_a_id INTEGER,
    hero_b_id INTEGER,
    bond_level REAL DEFAULT 0,
    floors_together INTEGER DEFAULT 0,
    PRIMARY KEY (hero_a_id, hero_b_id)
);

INSERT OR IGNORE INTO base (id) VALUES (1);
INSERT INTO facilities (base_id, type, slots_unlocked) 
SELECT 1, 'Training Center', 1 
WHERE NOT EXISTS (SELECT 1 FROM facilities WHERE type = 'Training Center');

INSERT INTO recipes (name, type, description, materials_json, gold_cost, base_stat_mult, is_discovered)
SELECT 'Basic Sword', 'weapon', 'A sturdy basic sword.', '{"Iron Ore": 3, "Monster Bone": 1}', 100, 1.0, 1
WHERE NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Basic Sword');

INSERT INTO recipes (name, type, description, materials_json, gold_cost, base_stat_mult, is_discovered)
SELECT 'Basic Armor', 'armor', 'Standard protective gear.', '{"Slime Core": 2, "Iron Ore": 2}', 100, 1.0, 1
WHERE NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Basic Armor');

INSERT INTO recipes (name, type, description, materials_json, gold_cost, base_stat_mult, is_discovered)
SELECT 'Basic Ring', 'accessory', 'A simple ring with minor enchantments.', '{"Mystic Dust": 3, "Goblin Ear": 1}', 100, 1.0, 1
WHERE NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Basic Ring');

-- Blueprint-discoverable recipes — hidden until found via the 15% post-combat
-- blueprint roll (see routers/tower.py). Mix of mid-tier (common materials,
-- found on any floor) and high-tier (gated behind the rare material pool,
-- which itself only drops floor 30+) so later discoveries feel like a real step up.
INSERT INTO recipes (name, type, description, materials_json, gold_cost, base_stat_mult, is_discovered)
SELECT 'Steel Broadsword', 'weapon', 'A broadsword forged from refined steel.', '{"Steel": 4, "Iron Ore": 2}', 300, 1.6, 0
WHERE NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Steel Broadsword');

INSERT INTO recipes (name, type, description, materials_json, gold_cost, base_stat_mult, is_discovered)
SELECT 'Leather Vest', 'armor', 'Light, flexible protection favoring mobility over raw defense.', '{"Leather": 4, "Copper": 1}', 250, 1.4, 0
WHERE NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Leather Vest');

INSERT INTO recipes (name, type, description, materials_json, gold_cost, base_stat_mult, is_discovered)
SELECT 'Hunters Charm', 'accessory', 'A trinket said to favor the wearer''s fortune in the field.', '{"Goblin Ear": 3, "Mystic Dust": 2}', 280, 1.5, 0
WHERE NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Hunters Charm');

INSERT INTO recipes (name, type, description, materials_json, gold_cost, base_stat_mult, is_discovered)
SELECT 'Mithril Chainmail', 'armor', 'Chainmail woven from mithril thread — light as cloth, hard as steel.', '{"Mithril": 3, "Steel": 3}', 900, 2.4, 0
WHERE NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Mithril Chainmail');

INSERT INTO recipes (name, type, description, materials_json, gold_cost, base_stat_mult, is_discovered)
SELECT 'Adamantine Greatblade', 'weapon', 'A blade of near-indestructible adamantine.', '{"Adamantine": 3, "Steel": 2}', 950, 2.5, 0
WHERE NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Adamantine Greatblade');

INSERT INTO recipes (name, type, description, materials_json, gold_cost, base_stat_mult, is_discovered)
SELECT 'Void Ring', 'accessory', 'A ring carved from a shard of crystallized void.', '{"Void Crystal": 2, "Mystic Dust": 3}', 1000, 2.6, 0
WHERE NOT EXISTS (SELECT 1 FROM recipes WHERE name = 'Void Ring');







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
            
        for col in ["lifetime_kills", "sole_survivor_boss_clears", "leader_clears", "unique_floor_clears"]:
            try:
                conn.execute(f"ALTER TABLE heroes ADD COLUMN {col} INTEGER DEFAULT 0")
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
            conn.execute("ALTER TABLE base ADD COLUMN fairy_gender TEXT")
            print("[DB] Migrated: added column 'fairy_gender' to base")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE base ADD COLUMN equip_spark_points INTEGER DEFAULT 0")
            print("[DB] Migrated: added column 'equip_spark_points' to base")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE base ADD COLUMN master_name TEXT")
            print("[DB] Migrated: added column 'master_name' to base")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE base ADD COLUMN tutorial_complete INTEGER DEFAULT 0")
            # Backfill: an existing save with real progress already lived
            # through everything the tutorial would teach — don't make it
            # pop up retroactively on profiles that aren't brand new.
            conn.execute(
                "UPDATE base SET tutorial_complete = 1 WHERE highest_floor > 0 "
                "OR EXISTS (SELECT 1 FROM heroes)"
            )
            print("[DB] Migrated: added column 'tutorial_complete' to base")
        except sqlite3.OperationalError:
            pass

        # Stat rework: Endurance replaces Defense (same mitigation role, but
        # also drives max_health going forward) and Willpower/Luck are new.
        # Old defense/base_def columns are left in place, inert, rather than
        # risking a SQLite column rename/drop on live save files.
        try:
            conn.execute("ALTER TABLE heroes ADD COLUMN endurance INTEGER DEFAULT 5")
            conn.execute("UPDATE heroes SET endurance = defense")
            print("[DB] Migrated: added column 'endurance' to heroes (backfilled from defense)")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE heroes ADD COLUMN willpower INTEGER DEFAULT 6")
            conn.execute("ALTER TABLE heroes ADD COLUMN luck INTEGER DEFAULT 5")
            # Existing heroes have no prior willpower/luck to copy — roll them
            # fresh, scaled to birth_star same as new hero generation, so
            # already-pulled heroes aren't punished relative to future pulls.
            wil_by_star = {1: 6, 2: 7, 3: 9, 4: 12, 5: 16, 6: 21, 7: 28}
            luck_by_star = {1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 10, 7: 12}
            rows = conn.execute("SELECT id, birth_star FROM heroes").fetchall()
            for r in rows:
                star = r["birth_star"] or 1
                wil = max(1, int(wil_by_star.get(star, 6) * random.uniform(0.9, 1.1)))
                luck = max(1, int(luck_by_star.get(star, 5) * random.uniform(0.9, 1.1)))
                conn.execute("UPDATE heroes SET willpower = ?, luck = ? WHERE id = ?", (wil, luck, r["id"]))
            print(f"[DB] Migrated: added columns 'willpower'/'luck' to heroes, backfilled {len(rows)} hero(es)")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE equipment ADD COLUMN base_end INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE equipment ADD COLUMN base_wil INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE equipment ADD COLUMN base_luck INTEGER DEFAULT 0")
            conn.execute("UPDATE equipment SET base_end = base_def")
            print("[DB] Migrated: added columns 'base_end'/'base_wil'/'base_luck' to equipment (base_end backfilled from base_def)")
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
            conn.execute("ALTER TABLE equipment ADD COLUMN str_pct REAL DEFAULT 0.0")
            conn.execute("ALTER TABLE equipment ADD COLUMN int_pct REAL DEFAULT 0.0")
            conn.execute("ALTER TABLE equipment ADD COLUMN hlt_pct REAL DEFAULT 0.0")
            conn.execute("ALTER TABLE equipment ADD COLUMN agi_pct REAL DEFAULT 0.0")
            print("[DB] Migrated: added pct columns to equipment")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE equipment ADD COLUMN base_def INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE equipment ADD COLUMN dmg_reduction_pct REAL DEFAULT 0.0")
            print("[DB] Migrated: added base_def/dmg_reduction_pct columns to equipment")
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
            ("is_team_leader", "ALTER TABLE heroes ADD COLUMN is_team_leader INTEGER DEFAULT 0"),
            ("battle_tendency", "ALTER TABLE heroes ADD COLUMN battle_tendency TEXT"),
            ("condition", "ALTER TABLE heroes ADD COLUMN condition TEXT DEFAULT 'Normal'"),
            ("condition_until", "ALTER TABLE heroes ADD COLUMN condition_until TEXT"),
            ("near_wipes_survived", "ALTER TABLE heroes ADD COLUMN near_wipes_survived INTEGER DEFAULT 0"),
            ("unique_floors_cleared", "ALTER TABLE heroes ADD COLUMN unique_floors_cleared INTEGER DEFAULT 0"),
            ("defense", "ALTER TABLE heroes ADD COLUMN defense INTEGER DEFAULT 5"),
        ]
        for col, sql in migrations:
            if col not in existing:
                conn.execute(sql)
                print(f"[DB] Migrated: added column '{col}'")

    print("Database initialized.")