import sys
with open('routers/heroes.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

old_func = """class SynthesizeRequest(BaseModel):
    target_id: int
    sacrifice_id: int

@router.post("/synthesize")
def synthesize_hero(data: SynthesizeRequest):"""

new_func = """class SynthesizeRequest(BaseModel):
    target_id: int
    sacrifice_ids: list[int]

@router.post("/synthesize")
def synthesize_hero(data: SynthesizeRequest):"""

content = content.replace(old_func, new_func)

# Now we need to replace the body of the function.
# It's easier to just replace the whole function using regex or string splitting.
parts = content.split('@router.post("/synthesize")\ndef synthesize_hero(data: SynthesizeRequest):')
prefix = parts[0]
rest = parts[1]

# Find the next endpoint which is @router.get("/{hero_id}") or similar? No, let's just find the end of the function.
# Wait, @router.post("/{hero_id}/level_up") is the next endpoint.
parts2 = rest.split('@router.post("/{hero_id}/level_up")')
body = parts2[0]
suffix = '@router.post("/{hero_id}/level_up")' + parts2[1]

new_body = '''
    """
    Sacrifice heroes to empower another. Causes trauma to roster.
    The sacrifice is permanent. All living heroes witness the act.
    """
    from services.morale_service import get_morale_state
    from services.level_service import recalculate_hero_level

    if data.target_id in data.sacrifice_ids:
        raise HTTPException(status_code=400, detail="Cannot sacrifice a hero to themselves.")
    if not data.sacrifice_ids:
        raise HTTPException(status_code=400, detail="Must provide at least one sacrifice.")

    with db() as conn:
        target = conn.execute("SELECT * FROM heroes WHERE id = ? AND is_alive = 1", (data.target_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Target hero not found or dead.")
        target_dict = dict(target)

        placeholders = ",".join("?" * len(data.sacrifice_ids))
        sacrifices = conn.execute(f"SELECT * FROM heroes WHERE id IN ({placeholders}) AND is_alive = 1", data.sacrifice_ids).fetchall()
        if len(sacrifices) != len(data.sacrifice_ids):
            raise HTTPException(status_code=404, detail="One or more sacrifice heroes not found or already dead.")

        total_base_xp = 0
        total_trauma = 0
        total_stress = 0
        total_morale_loss = 0
        inherited_skills_traits = []
        msg_suffix = ""
        any_resonant = False

        import json

        for sacrifice in sacrifices:
            sacrifice_dict = dict(sacrifice)
            transfer_pct = 0.10 + (sacrifice_dict["birth_star"] * 0.015)
            xp_gain = (200 + sacrifice_dict.get("level", 1) * 80) * transfer_pct
            
            is_resonant = (target_dict["hero_class"] == sacrifice_dict["hero_class"] and target_dict["hero_class"] != "Classless")
            if is_resonant:
                xp_gain *= 2
                any_resonant = True

            total_base_xp += xp_gain
            total_trauma += 5 + sacrifice_dict["birth_star"]
            total_stress += 10 + sacrifice_dict["birth_star"] * 2
            total_morale_loss += -(8 + sacrifice_dict["birth_star"] * 2)

            import random
            b_skills = json.loads(sacrifice_dict.get("skills") or "[]")
            b_traits = json.loads(sacrifice_dict.get("traits") or "[]")
            if random.random() < 0.5 and (b_skills or b_traits):
                inherited_skills_traits.append(random.choice(b_skills + b_traits))

            # Mark sacrifice as dead/synthesized
            conn.execute("""
                UPDATE heroes SET is_alive = 0, is_on_team = 0, synthesized = 1
                WHERE id = ?
            """, (sacrifice_dict["id"],))

        if any_resonant:
            conn.execute("UPDATE heroes SET ego_type = 'Resonant' WHERE id = ?", (data.target_id,))
            msg_suffix += " EGO RESONANCE TRIGGERED!"

        # Scale down the cumulative effect slightly for bulk
        # e.g. 4 heroes -> 4^0.8 / 4 = 0.75x of the additive sum
        num_sacs = len(data.sacrifice_ids)
        scale = (num_sacs ** 0.8) / num_sacs if num_sacs > 0 else 1.0
        
        final_xp = int(total_base_xp * scale)
        final_trauma = int(total_trauma * scale)
        final_stress = int(total_stress * scale)
        final_morale_loss = int(total_morale_loss * scale)

        a_skills = json.loads(target_dict.get("skills") or "[]")
        a_traits = json.loads(target_dict.get("traits") or "[]")
        a_names = set(x["name"] for x in a_skills + a_traits)
        
        for inherited in inherited_skills_traits:
            if inherited["name"] not in a_names:
                if "level" in inherited: # Likely a skill
                    a_skills.append(inherited)
                else:
                    a_traits.append(inherited)
                a_names.add(inherited["name"])
                msg_suffix += f" Inherited {inherited['name']}!"

        conn.execute("UPDATE heroes SET skills = ?, traits = ? WHERE id = ?", (json.dumps(a_skills), json.dumps(a_traits), data.target_id))

        # Apply XP gain, then recalculate level
        conn.execute("UPDATE heroes SET xp = COALESCE(xp, 0) + ? WHERE id = ?", (final_xp, data.target_id))
        target_after_xp = dict(conn.execute("SELECT * FROM heroes WHERE id = ?", (data.target_id,)).fetchone())
        new_level = recalculate_hero_level(target_after_xp)
        leveled_up = new_level != target_after_xp.get("level", 1)
        if leveled_up:
            conn.execute("UPDATE heroes SET level = ? WHERE id = ?", (new_level, data.target_id))
            msg_suffix += f" {target_dict['name']} reached level {new_level}!"

        # Trauma to all living heroes
        living_heroes = conn.execute(
            "SELECT * FROM heroes WHERE is_alive = 1 AND id != ?", (data.target_id,)
        ).fetchall()
        for hero in living_heroes:
            h = dict(hero)
            new_trauma = min(100, h["trauma"] + final_trauma)
            new_stress = min(100, h["stress"] + final_stress)
            trauma_ceiling = 100 - int(new_trauma * 0.4)
            new_morale = max(0, min(trauma_ceiling, h["morale"] + final_morale_loss))
            conn.execute(
                "UPDATE heroes SET trauma = ?, stress = ?, morale = ?, morale_state = ? WHERE id = ?",
                (new_trauma, new_stress, new_morale, get_morale_state(new_morale), h["id"])
            )

        # Target also gets some guilt
        new_trauma = min(100, target_dict["trauma"] + int(5 * scale))
        new_stress = min(100, target_dict["stress"] + int(5 * scale))
        trauma_ceiling = 100 - int(new_trauma * 0.4)
        new_morale = max(0, min(trauma_ceiling, target_dict["morale"] - int(5 * scale)))
        conn.execute(
            "UPDATE heroes SET trauma = ?, stress = ?, morale = ?, morale_state = ? WHERE id = ?",
            (new_trauma, new_stress, new_morale, get_morale_state(new_morale), data.target_id)
        )

        return {"message": f"Synthesized {num_sacs} hero(es) into {target_dict['name']}." + msg_suffix, "xp_gain": final_xp}

'''

final_content = prefix + '@router.post("/synthesize")\ndef synthesize_hero(data: SynthesizeRequest):' + new_body + suffix

with open('routers/heroes.py', 'w', encoding='utf-8') as f:
    f.write(final_content)
