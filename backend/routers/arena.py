"""
Local-backend side of Arena support. This endpoint runs the exact same
hero stat-resolution pipeline (level/class/equipment/relics/bonds/base-floor
LP/passives) that a normal Tower floor fight uses, then hands the result
back to the client as a JSON snapshot — the client then ships that snapshot
to the separately-hosted arena_server via POST /arena/submit_team there.
This local backend never talks to the arena_server directly; it has no
knowledge of it at all, just like before Arena existed.
"""
from fastapi import APIRouter, HTTPException
from database import db
from services.combat_service import resolve_hero_stats

router = APIRouter()


@router.get("/team/{team_id}/snapshot")
def get_team_snapshot(team_id: int):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM heroes WHERE is_on_team = ? AND is_alive = 1 ORDER BY team_position ASC, id ASC",
            (team_id,),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=400, detail="That team has no living heroes assigned")
    heroes = [dict(r) for r in rows]
    processed = resolve_hero_stats(heroes)
    return {"team": processed}
