"""
Arena server's own SQLite store — completely separate from any player's
local save file. Nothing here ever touches backend/saves/*.db; a player's
real heroes/profile are never read or written by this service. Arena
fights are resolved against snapshots the client submits, not live saves.
"""
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "arena.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS arena_players (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            token TEXT,
            token_expiry REAL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            team_json TEXT,
            highest_floor INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS arena_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player1 TEXT NOT NULL,
            player2 TEXT NOT NULL,
            winner TEXT,
            log_json TEXT,
            timestamp REAL NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS arena_season_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            season_end_date REAL NOT NULL,
            reward_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            claimed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS training_market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            hero_name TEXT NOT NULL,
            hero_class TEXT NOT NULL,
            hero_stats_json TEXT NOT NULL,
            hero_skills_json TEXT NOT NULL,
            gem_cost INTEGER NOT NULL,
            listed_at REAL NOT NULL
        );
    """)

    # Attempt to add highest_floor column if it doesn't exist (for existing DBs)
    try:
        conn.execute("ALTER TABLE arena_players ADD COLUMN highest_floor INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists

    try:
        conn.execute("ALTER TABLE arena_players ADD COLUMN elo INTEGER DEFAULT 1000")
    except sqlite3.OperationalError:
        pass # Column already exists
    conn.commit()
    conn.close()
    print("[Arena] Database initialized.")
