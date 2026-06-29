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


from pydantic import BaseModel
import json

class ApplyTrainingRequest(BaseModel):
    student_id: int
    gem_cost: int
    teacher_stats: dict
    teacher_skills: list

@router.post("/apply_training")
def apply_training(req: ApplyTrainingRequest):
    """
    Called by the frontend after hiring a teacher from the Arena Server market.
    Deducts the gems locally, and grants stat/skill XP to the student based on
    the teacher's strength.
    """
    with db() as conn:
        base = conn.execute("SELECT gems FROM base WHERE id = 1").fetchone()
        if base["gems"] < req.gem_cost:
            raise HTTPException(status_code=400, detail=f"Not enough gems. Need {req.gem_cost}.")
            
        student = conn.execute("SELECT * FROM heroes WHERE id = ? AND is_alive = 1", (req.student_id,)).fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student hero not found.")
            
        student = dict(student)
        
        # Deduct gems
        conn.execute("UPDATE base SET gems = gems - ? WHERE id = 1", (req.gem_cost,))
        
        # Calculate stat growth based on teacher's raw stats vs student's raw stats
        # A simple model: if the teacher's stat is higher, the student has a chance to gain 1 point.
        # Plus flat XP.
        stat_gains = {"health": 0, "attack": 0, "defense": 0, "speed": 0}
        
        if req.teacher_stats.get("max_health", 0) > student["max_health"]:
            stat_gains["health"] += 2
        if req.teacher_stats.get("attack", 0) > student["attack"]:
            stat_gains["attack"] += 1
        if req.teacher_stats.get("defense", 0) > student["defense"]:
            stat_gains["defense"] += 1
        if req.teacher_stats.get("speed", 0) > student["speed"]:
            stat_gains["speed"] += 1
            
        # Skill XP
        skills = json.loads(student["skills"]) if student["skills"] else []
        teacher_skill_ids = [s["id"] for s in req.teacher_skills]
        
        skill_log = []
        for s in skills:
            if s["id"] in teacher_skill_ids:
                # The teacher also has this skill, big bonus!
                s["xp"] = s.get("xp", 0) + 100
                skill_log.append(f"{s['name']} XP +100")
                if s["xp"] >= s.get("max_xp", 100):
                    s["level"] = s.get("level", 1) + 1
                    s["xp"] -= s.get("max_xp", 100)
                    s["max_xp"] = int(s.get("max_xp", 100) * 1.5)
                    skill_log.append(f"{s['name']} leveled up to {s['level']}!")
                    
        # General hero XP
        xp_gain = 500
        
        conn.execute(
            """UPDATE heroes 
               SET xp = xp + ?, max_health = max_health + ?, health = health + ?, attack = attack + ?, defense = defense + ?, speed = speed + ?, skills = ?
               WHERE id = ?""",
            (
                xp_gain, 
                stat_gains["health"], stat_gains["health"],
                stat_gains["attack"],
                stat_gains["defense"],
                stat_gains["speed"],
                json.dumps(skills),
                req.student_id
            )
        )
        
    return {
        "ok": True,
        "xp": xp_gain,
        "stats": stat_gains,
        "skills": skill_log
    }
