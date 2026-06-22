import json
from datetime import datetime, timezone
from database import db

def assign_training(facility_id: int, hero_id: int, role: str, target_skill_id: str = None, target_hero_id: int = None):
    """
    Roles:
    - solo: Train a skill alone.
    - spar: Spar with another hero to train a skill faster. (target_hero_id required)
    - mentor: Teach a skill to a student. (target_hero_id = student)
    - student: Learn a skill from a teacher. (target_hero_id = teacher)
    """
    with db() as conn:
        # Clear existing assignment
        conn.execute("DELETE FROM facility_assignments WHERE hero_id = ?", (hero_id,))
        
        if role in ["spar", "mentor", "student"]:
            if not target_hero_id:
                raise ValueError("Target hero required for this role.")
            
        conn.execute("""
            INSERT INTO facility_assignments (facility_id, hero_id, role, target_skill_id, target_hero_id)
            VALUES (?, ?, ?, ?, ?)
        """, (facility_id, hero_id, role, target_skill_id, target_hero_id))
        
    return {"ok": True}

def process_training_xp(conn):
    base = conn.execute("SELECT last_training_tick FROM base WHERE id = 1").fetchone()
    if not base:
        return
        
    last_tick_str = dict(base).get("last_training_tick")
    if not last_tick_str:
        try:
            conn.execute("ALTER TABLE base ADD COLUMN last_training_tick TIMESTAMP")
        except:
            pass
        conn.execute("UPDATE base SET last_training_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return

    try:
        last_tick = datetime.strptime(last_tick_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        conn.execute("UPDATE base SET last_training_tick = CURRENT_TIMESTAMP WHERE id = 1")
        return
        
    now = datetime.utcnow()
    diff = now - last_tick
    minutes_passed = int(diff.total_seconds() / 60)
    
    # Tick every 1 minute
    if minutes_passed > 0:
        # Get all heroes in Training Grounds
        tg = conn.execute("SELECT id FROM facilities WHERE type = 'Training Grounds' AND base_id = 1").fetchone()
        if not tg:
            return
            
        assignments = conn.execute("SELECT * FROM facility_assignments WHERE facility_id = ?", (tg["id"],)).fetchall()
        
        from services.level_service import talent_score
        # Load heroes and skills
        heroes = {}
        hero_rows = conn.execute("SELECT * FROM heroes").fetchall()
        for r in hero_rows:
            rd = dict(r)
            heroes[r["id"]] = {
                "skills": json.loads(rd.get("skills") or "[]"),
                "talent": talent_score(rd),
            }
            
        for a in assignments:
            hid = a["hero_id"]
            if hid not in heroes: continue
            
            hero = heroes[hid]
            role = a["role"]
            skill_id = a["target_skill_id"]
            if not skill_id: continue
            
            # Find skill
            skill_idx = None
            for i, s in enumerate(hero["skills"]):
                if s["id"] == skill_id:
                    skill_idx = i
                    break
                    
            if skill_idx is None: continue
            skill = hero["skills"][skill_idx]
            
            if skill.get("level", 1) >= 10:
                continue # Cannot level past 10 passively, needs breakthrough
                
            # Base XP gain per minute
            xp_gain = 1 * minutes_passed
            
            # Global Buffs
            try:
                base_info = conn.execute("SELECT global_buffs FROM base WHERE id = 1").fetchone()
                buffs = json.loads(base_info["global_buffs"] or "{}")
                xp_gain *= (1 + buffs.get("xp_boost", 0) * 0.10)
            except:
                pass
            
            # Talent (aptitude growth rate) scales how fast training sticks,
            # same multiplier shape as combat skill-tier ascension.
            xp_gain *= (0.7 + hero["talent"] * 0.8)
                
            if role == "spar":
                # Check if target is also sparring with us
                target_a = next((ta for ta in assignments if ta["hero_id"] == a["target_hero_id"] and ta["role"] == "spar" and ta["target_hero_id"] == hid), None)
                if target_a:
                    xp_gain *= 1.5 # 50% bonus for valid sparring
            
            elif role == "student":
                # Check if teacher is mentoring us
                teacher_a = next((ta for ta in assignments if ta["hero_id"] == a["target_hero_id"] and ta["role"] == "mentor" and ta["target_hero_id"] == hid), None)
                if teacher_a:
                    xp_gain *= 2.0 # 100% bonus for being taught
            
            skill["xp"] = skill.get("xp", 0) + int(xp_gain)
            
            # Level up logic
            max_xp = skill.get("max_xp", 100)
            if skill["xp"] >= max_xp:
                skill["xp"] = 0
                skill["level"] = skill.get("level", 1) + 1
                skill["max_xp"] = int(max_xp * 1.5)
                
            hero["skills"][skill_idx] = skill
            
            conn.execute("UPDATE heroes SET skills = ? WHERE id = ?", (json.dumps(hero["skills"]), hid))
            
        conn.execute("UPDATE base SET last_training_tick = CURRENT_TIMESTAMP WHERE id = 1")
