"""
Arena server — a small, separate FastAPI app from the main game backend.
Hosts PvP challenges between players using client-submitted, already-fully-
resolved hero stat snapshots. Never touches any player's local save file;
this process owns nothing but arena.db (player accounts/tokens + match
history). See arena_server/database.py and combat.py for why.
"""
import os
import secrets
import time
import json

import bcrypt
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, init_db
from combat import resolve_arena_fight
from elo import update_elo

TOKEN_LIFETIME_SECONDS = 7 * 24 * 60 * 60  # 7 days

app = FastAPI(title="Tower of Eternity — Arena Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class SubmitTeamRequest(BaseModel):
    team: list[dict]


class ChallengeRequest(BaseModel):
    opponent: str


class UpdateFloorRequest(BaseModel):
    highest_floor: int


def _require_player(authorization: str | None) -> str:
    """Validates the Bearer token from the Authorization header, returns
    the owning username. Raises 401 on anything wrong."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    with db() as conn:
        row = conn.execute(
            "SELECT username, token_expiry FROM arena_players WHERE token = ?", (token,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    if row["token_expiry"] is None or row["token_expiry"] < time.time():
        raise HTTPException(status_code=401, detail="Token expired, please log in again")
    return row["username"]


@app.post("/arena/register")
def register(req: RegisterRequest):
    username = req.username.strip()
    if not username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    password_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    with db() as conn:
        existing = conn.execute(
            "SELECT username FROM arena_players WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Username already taken")
        conn.execute(
            "INSERT INTO arena_players (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
    return {"status": "registered", "username": username}


@app.post("/arena/login")
def login(req: LoginRequest):
    with db() as conn:
        row = conn.execute(
            "SELECT username, password_hash FROM arena_players WHERE username = ?",
            (req.username.strip(),),
        ).fetchone()
        if not row or not bcrypt.checkpw(req.password.encode(), row["password_hash"].encode()):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        token = secrets.token_hex(32)
        expiry = time.time() + TOKEN_LIFETIME_SECONDS
        conn.execute(
            "UPDATE arena_players SET token = ?, token_expiry = ? WHERE username = ?",
            (token, expiry, row["username"]),
        )
    return {"token": token, "username": row["username"]}


@app.post("/arena/submit_team")
def submit_team(req: SubmitTeamRequest, authorization: str | None = Header(default=None)):
    """Stores the caller's current best team snapshot — the team an
    opponent's challenge will be resolved against. The client computes this
    snapshot exactly as it already does for a normal Tower floor; the
    server does no stat recomputation (see the known-risk note in combat.py
    / the arena plan: a modified client could inflate stats — accepted
    for a friends-scale v1)."""
    if not req.team:
        raise HTTPException(status_code=400, detail="Team cannot be empty")
    username = _require_player(authorization)
    with db() as conn:
        conn.execute(
            "UPDATE arena_players SET team_json = ? WHERE username = ?",
            (json.dumps(req.team), username),
        )
    return {"status": "team submitted", "team_size": len(req.team)}


@app.post("/arena/challenge")
def challenge(req: ChallengeRequest, authorization: str | None = Header(default=None)):
    username = _require_player(authorization)
    opponent = req.opponent.strip()
    if opponent == username:
        raise HTTPException(status_code=400, detail="You can't challenge yourself")

    with db() as conn:
        me = conn.execute(
            "SELECT team_json FROM arena_players WHERE username = ?", (username,)
        ).fetchone()
        them = conn.execute(
            "SELECT team_json FROM arena_players WHERE username = ?", (opponent,)
        ).fetchone()
    if not them:
        raise HTTPException(status_code=404, detail=f"No such player: {opponent}")
    if not me or not me["team_json"]:
        raise HTTPException(status_code=400, detail="Submit your team before challenging (POST /arena/submit_team)")
    if not them["team_json"]:
        raise HTTPException(status_code=400, detail=f"{opponent} hasn't submitted a team yet")

    team_a = json.loads(me["team_json"])
    team_b = json.loads(them["team_json"])
    result = resolve_arena_fight(team_a, team_b)

    winner_username = username if result["winner"] == "heroes" else opponent
    loser_username = opponent if winner_username == username else username

    with db() as conn:
        elo_row_w = conn.execute("SELECT elo FROM arena_players WHERE username = ?", (winner_username,)).fetchone()
        elo_row_l = conn.execute("SELECT elo FROM arena_players WHERE username = ?", (loser_username,)).fetchone()
        new_winner_elo, new_loser_elo = update_elo(elo_row_w["elo"] or 1000, elo_row_l["elo"] or 1000)

        conn.execute(
            "UPDATE arena_players SET wins = wins + 1, elo = ? WHERE username = ?", (new_winner_elo, winner_username)
        )
        conn.execute(
            "UPDATE arena_players SET losses = losses + 1, elo = ? WHERE username = ?", (new_loser_elo, loser_username)
        )
        conn.execute(
            "INSERT INTO arena_matches (player1, player2, winner, log_json, timestamp) VALUES (?, ?, ?, ?, ?)",
            (username, opponent, winner_username, json.dumps(result.get("log", [])), time.time()),
        )

    return {
        "winner": winner_username,
        "loser": loser_username,
        "log": result.get("log", []),
        "turns": result.get("turns", []),
        "elo_change": {winner_username: new_winner_elo, loser_username: new_loser_elo},
    }


@app.post("/arena/matchmake")
def matchmake(authorization: str | None = Header(default=None)):
    username = _require_player(authorization)
    with db() as conn:
        me = conn.execute("SELECT wins, losses, elo, team_json FROM arena_players WHERE username = ?", (username,)).fetchone()
        if not me or not me["team_json"]:
            raise HTTPException(status_code=400, detail="Submit your team before matchmaking")

        my_elo = me["elo"] or 1000

        # Find opponent with the closest ELO rating — a true skill-based pairing
        # now that ELO exists, rather than the old raw net-wins proxy.
        opponent_row = conn.execute(
            """SELECT username, team_json, ABS(COALESCE(elo, 1000) - ?) as diff
               FROM arena_players
               WHERE username != ? AND team_json IS NOT NULL
               ORDER BY diff ASC
               LIMIT 1""",
            (my_elo, username)
        ).fetchone()

    if not opponent_row:
        raise HTTPException(status_code=404, detail="No suitable opponents found. Wait for others to join!")

    # We found an opponent. Proceed to run a challenge exactly like /arena/challenge
    opponent = opponent_row["username"]
    team_a = json.loads(me["team_json"])
    team_b = json.loads(opponent_row["team_json"])
    result = resolve_arena_fight(team_a, team_b)

    winner_username = username if result["winner"] == "heroes" else opponent
    loser_username = opponent if winner_username == username else username

    with db() as conn:
        elo_row_w = conn.execute("SELECT elo FROM arena_players WHERE username = ?", (winner_username,)).fetchone()
        elo_row_l = conn.execute("SELECT elo FROM arena_players WHERE username = ?", (loser_username,)).fetchone()
        new_winner_elo, new_loser_elo = update_elo(elo_row_w["elo"] or 1000, elo_row_l["elo"] or 1000)

        conn.execute("UPDATE arena_players SET wins = wins + 1, elo = ? WHERE username = ?", (new_winner_elo, winner_username))
        conn.execute("UPDATE arena_players SET losses = losses + 1, elo = ? WHERE username = ?", (new_loser_elo, loser_username))
        conn.execute(
            "INSERT INTO arena_matches (player1, player2, winner, log_json, timestamp) VALUES (?, ?, ?, ?, ?)",
            (username, opponent, winner_username, json.dumps(result.get("log", [])), time.time()),
        )

    return {
        "opponent": opponent,
        "winner": winner_username,
        "loser": loser_username,
        "log": result.get("log", []),
        "turns": result.get("turns", []),
        "elo_change": {winner_username: new_winner_elo, loser_username: new_loser_elo},
    }


@app.post("/arena/update_floor")
def update_floor(req: UpdateFloorRequest, authorization: str | None = Header(default=None)):
    username = _require_player(authorization)
    with db() as conn:
        # Only update if it's strictly greater (so we don't accidentally revert)
        conn.execute(
            "UPDATE arena_players SET highest_floor = ? WHERE username = ? AND highest_floor < ?",
            (req.highest_floor, username, req.highest_floor)
        )
    return {"status": "floor updated", "highest_floor": req.highest_floor}


@app.get("/arena/leaderboard")
def leaderboard(limit: int = 20):
    with db() as conn:
        pvp_rows = conn.execute(
            "SELECT username, wins, losses, elo FROM arena_players "
            "ORDER BY COALESCE(elo, 1000) DESC LIMIT ?",
            (limit,),
        ).fetchall()
        pve_rows = conn.execute(
            "SELECT username, highest_floor FROM arena_players "
            "ORDER BY highest_floor DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return {
        "leaderboard": [
            {"username": r["username"], "wins": r["wins"], "losses": r["losses"], "elo": r["elo"] or 1000}
            for r in pvp_rows
        ],
        "pve_leaderboard": [
            {"username": r["username"], "highest_floor": r["highest_floor"]}
            for r in pve_rows
        ]
    }


@app.get("/arena/health")
def health():
    return {"status": "ok"}


# ─── Seasons & Rewards ────────────────────────────────────────────

class ResetSeasonRequest(BaseModel):
    admin_key: str

@app.post("/arena/admin/reset_season")
def reset_season(req: ResetSeasonRequest):
    # In a real app this would be a cron job or secure admin endpoint.
    if req.admin_key != "secret_admin_key_123":
        raise HTTPException(status_code=403, detail="Forbidden")
        
    now = time.time()
    with db() as conn:
        # Rank by wins for PvP rewards
        pvp_rows = conn.execute("SELECT username, wins, losses FROM arena_players ORDER BY wins DESC, losses ASC LIMIT 100").fetchall()
        for i, row in enumerate(pvp_rows):
            rank = i + 1
            gems = 0
            if rank == 1:
                gems = 1500
            elif rank <= 3:
                gems = 1000
            elif rank <= 10:
                gems = 500
            elif rank <= 50:
                gems = 200
            else:
                gems = 50
                
            conn.execute(
                "INSERT INTO arena_season_rewards (username, season_end_date, reward_type, amount) VALUES (?, ?, ?, ?)",
                (row["username"], now, "gems", gems)
            )
            
        # Reset PvP scores
        conn.execute("UPDATE arena_players SET wins = 0, losses = 0")
        
    return {"status": "season_reset", "awarded_pvp_ranks": len(pvp_rows)}

@app.get("/arena/my_rewards")
def my_rewards(authorization: str | None = Header(default=None)):
    username = _require_player(authorization)
    with db() as conn:
        rows = conn.execute(
            "SELECT id, reward_type, amount, season_end_date FROM arena_season_rewards WHERE username = ? AND claimed = 0",
            (username,)
        ).fetchall()
        
    return {"rewards": [dict(r) for r in rows]}

class ClaimRewardRequest(BaseModel):
    reward_id: int

@app.post("/arena/claim_reward")
def claim_reward(req: ClaimRewardRequest, authorization: str | None = Header(default=None)):
    username = _require_player(authorization)
    with db() as conn:
        row = conn.execute(
            "SELECT id, reward_type, amount FROM arena_season_rewards WHERE id = ? AND username = ? AND claimed = 0",
            (req.reward_id, username)
        ).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Reward not found or already claimed.")
            
        conn.execute("UPDATE arena_season_rewards SET claimed = 1 WHERE id = ?", (req.reward_id,))
        
    return {"status": "claimed", "reward_type": row["reward_type"], "amount": row["amount"]}


# ─── Training Market ──────────────────────────────────────────────

class ListTeacherRequest(BaseModel):
    hero_name: str
    hero_class: str
    hero_stats: dict
    hero_skills: list
    gem_cost: int

@app.post("/arena/market/list")
def list_teacher(req: ListTeacherRequest, authorization: str | None = Header(default=None)):
    username = _require_player(authorization)
    if req.gem_cost < 0:
        raise HTTPException(status_code=400, detail="Gem cost cannot be negative.")
        
    with db() as conn:
        # Check how many they have listed to prevent spam
        count = conn.execute("SELECT COUNT(*) as c FROM training_market WHERE username = ?", (username,)).fetchone()["c"]
        if count >= 3:
            raise HTTPException(status_code=400, detail="You can only list up to 3 teachers at a time.")
            
        conn.execute(
            """INSERT INTO training_market 
               (username, hero_name, hero_class, hero_stats_json, hero_skills_json, gem_cost, listed_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (username, req.hero_name, req.hero_class, json.dumps(req.hero_stats), json.dumps(req.hero_skills), req.gem_cost, time.time())
        )
    return {"status": "listed"}

@app.get("/arena/market")
def get_training_market(authorization: str | None = Header(default=None)):
    _require_player(authorization)
    with db() as conn:
        rows = conn.execute("SELECT * FROM training_market ORDER BY listed_at DESC LIMIT 50").fetchall()
        
    return {"listings": [
        {
            "id": r["id"],
            "username": r["username"],
            "hero_name": r["hero_name"],
            "hero_class": r["hero_class"],
            "hero_stats": json.loads(r["hero_stats_json"]),
            "hero_skills": json.loads(r["hero_skills_json"]),
            "gem_cost": r["gem_cost"]
        } for r in rows
    ]}

class HireTeacherRequest(BaseModel):
    listing_id: int

@app.post("/arena/market/hire")
def hire_teacher(req: HireTeacherRequest, authorization: str | None = Header(default=None)):
    username = _require_player(authorization)
    with db() as conn:
        listing = conn.execute("SELECT * FROM training_market WHERE id = ?", (req.listing_id,)).fetchone()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found.")
            
        if listing["username"] == username:
            raise HTTPException(status_code=400, detail="You cannot hire your own teacher.")
            
        # Payout the lister! We use the season rewards table as a generic inbox for now.
        if listing["gem_cost"] > 0:
            conn.execute(
                "INSERT INTO arena_season_rewards (username, season_end_date, reward_type, amount) VALUES (?, ?, ?, ?)",
                (listing["username"], time.time(), "gems", listing["gem_cost"])
            )
            
    return {
        "status": "hired", 
        "teacher": {
            "hero_name": listing["hero_name"],
            "hero_class": listing["hero_class"],
            "hero_stats": json.loads(listing["hero_stats_json"]),
            "hero_skills": json.loads(listing["hero_skills_json"]),
            "gem_cost": listing["gem_cost"]
        }
    }
