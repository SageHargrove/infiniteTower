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
        conn.execute(
            "UPDATE arena_players SET wins = wins + 1 WHERE username = ?", (winner_username,)
        )
        conn.execute(
            "UPDATE arena_players SET losses = losses + 1 WHERE username = ?", (loser_username,)
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
    }


@app.get("/arena/leaderboard")
def leaderboard(limit: int = 20):
    with db() as conn:
        rows = conn.execute(
            "SELECT username, wins, losses FROM arena_players "
            "ORDER BY wins DESC, losses ASC LIMIT ?",
            (limit,),
        ).fetchall()
    return {
        "leaderboard": [
            {"username": r["username"], "wins": r["wins"], "losses": r["losses"]}
            for r in rows
        ]
    }


@app.get("/arena/health")
def health():
    return {"status": "ok"}
