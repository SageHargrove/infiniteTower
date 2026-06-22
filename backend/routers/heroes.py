from fastapi import APIRouter, HTTPException
from database import db
from pydantic import BaseModel
from services.level_service import get_revealed_aptitudes, recalculate_hero_level

router = APIRouter()

def row_to_hero(row, equipment_rows=[], is_ego_satisfied=None) -> dict:
    from services.class_service import get_class_evolution_options
    from services.equipment_service import apply_equipment_stats
    h = dict(row)
    h["equipment"] = [dict(e) for e in equipment_rows if e["is_equipped_to"] == h["id"]]
    h["evolution_options"] = get_class_evolution_options(h["hero_class"], h.get("level", 1))
    h = apply_equipment_stats(h, h["equipment"])
    if is_ego_satisfied is not None:
        h["is_ego_satisfied"] = is_ego_satisfied
    return h

@router.get("/")
def list_heroes(alive_only: bool = False):
    with db() as conn:
        query = "SELECT * FROM heroes"
        if alive_only:
            query += " WHERE is_alive = 1"
        query += " ORDER BY birth_star DESC, created_at DESC"
        rows = conn.execute(query).fetchall()
        
        # Fetch equipment for all listed heroes
        hero_ids = [r["id"] for r in rows]
        if hero_ids:
            placeholders = ",".join("?" * len(hero_ids))
            equipment_rows = conn.execute(f"SELECT * FROM equipment WHERE is_equipped_to IN ({placeholders})", hero_ids).fetchall()
        else:
            equipment_rows = []
            
        # Calculate ego satisfaction for heroes on teams
        from services.ego_service import check_ego_satisfaction
        teams = {}
        alive_rows = [dict(r) for r in rows if r["is_alive"]]
        for r in alive_rows:
            if r["is_on_team"]:
                teams.setdefault(r["is_on_team"], []).append(r)
        
        satisfaction_map = {}
        for r in alive_rows:
            if r["ego_type"] and r["is_on_team"]:
                team_members = teams[r["is_on_team"]]
                satisfaction_map[r["id"]] = check_ego_satisfaction(r, team_members, alive_rows)
            
    return [row_to_hero(r, equipment_rows, satisfaction_map.get(r["id"])) for r in rows]

@router.get("/{hero_id}")
def get_hero(hero_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM heroes WHERE id = ?", (hero_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Hero not found")
        equipment_rows = conn.execute("SELECT * FROM equipment WHERE is_equipped_to = ?", (hero_id,)).fetchall()
    return row_to_hero(row, equipment_rows)

@router.post("/{hero_id}/regenerate-profile")
def regenerate_profile(hero_id: int):
    """Force an update or regeneration of a hero's portrait, and completely rewrite name/lore if it was a fallback."""
    with db() as conn:
        row = conn.execute("SELECT * FROM heroes WHERE id = ?", (hero_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Hero not found")
        
        hero = dict(row)
        
        fallback_names = [
            "Valerius", "Kaelen", "Elara", "Tavian", "Seris", "Rykard", "Isolde", "Jerrick", "Nia", "Lorien", "Darius",
            "Fenris", "Vanya", "Corvus", "Sylas", "Myra", "Bram", "Gael", "Aria", "Thorne", "Lysander", "Rowan",
            "Cassia", "Kira", "Orion", "Soren", "Eira", "Vesper", "Caelum", "Juno", "Silas", "Evander", "Nyssa",
            "Theron", "Lirael", "Aelar", "Zephyr", "Rhea", "Kael", "Lyra", "Ignis", "Nyx", "Sol", "Nova", "Aura"
        ]
        
        is_fallback = hero["name"] in fallback_names or hero["name"].startswith("Unknown")
        prompt = f"dark fantasy anime warrior portrait, {hero['birth_star']} star rarity"
        
        # If it was a fallback, completely regenerate the LLM profile
        if is_fallback:
            from services.llm_service import generate_hero_profile
            aptitudes = {
                "apt_combat": hero["apt_combat"],
                "apt_tactical": hero["apt_tactical"],
                "apt_survival": hero["apt_survival"],
                "apt_mental": hero["apt_mental"],
                "apt_leadership": hero["apt_leadership"]
            }
            try:
                profile = generate_hero_profile(hero["birth_star"], aptitudes)
                conn.execute("""
                    UPDATE heroes 
                    SET name = ?, title = ?, backstory = ?, personality = ?, gender = ?
                    WHERE id = ?
                """, (profile.name, profile.title, profile.backstory, profile.personality, getattr(profile, "gender", "unknown"), hero_id))
                prompt = profile.portrait_prompt
                hero["gender"] = getattr(profile, "gender", "unknown")
            except Exception as e:
                print(f"Regen failed: {e}")
        
        from services.portrait_cache import queue_custom_portrait
        queue_custom_portrait(hero_id, prompt, hero["name"] if not is_fallback else "Regenerated", hero.get("gender", "unknown"))
        return {"ok": True, "message": "Profile regenerating! Portrait and lore will update shortly."}

@router.delete("/{hero_id}")
def dismiss_hero(hero_id: int):
    """Dismiss (remove) a hero from roster. Not the same as death."""
    with db() as conn:
        hero = conn.execute("SELECT portrait_path FROM heroes WHERE id = ?", (hero_id,)).fetchone()
        # Remove from any tower run teams first (foreign key constraint)
        conn.execute("DELETE FROM run_heroes WHERE hero_id = ?", (hero_id,))
        # Remove from active team
        conn.execute("UPDATE heroes SET is_on_team = 0 WHERE id = ?", (hero_id,))
        # Delete the hero
        conn.execute("DELETE FROM heroes WHERE id = ?", (hero_id,))
        
    if hero and hero["portrait_path"]:
        try:
            import os
            path = hero["portrait_path"]
            if "default_" not in path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    return {"ok": True}

class BulkDismissRequest(BaseModel):
    hero_ids: list[int]

@router.post("/dismiss-bulk")
def dismiss_heroes_bulk(req: BulkDismissRequest):
    """Dismiss multiple heroes at once."""
    deleted_count = 0
    with db() as conn:
        for hero_id in req.hero_ids:
            hero = conn.execute("SELECT portrait_path FROM heroes WHERE id = ?", (hero_id,)).fetchone()
            if not hero:
                continue
            
            conn.execute("DELETE FROM run_heroes WHERE hero_id = ?", (hero_id,))
            conn.execute("UPDATE heroes SET is_on_team = 0 WHERE id = ?", (hero_id,))
            conn.execute("DELETE FROM heroes WHERE id = ?", (hero_id,))
            
            if hero["portrait_path"]:
                try:
                    import os
                    path = hero["portrait_path"]
                    if "default_" not in path and os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
            deleted_count += 1
            
    return {"ok": True, "deleted_count": deleted_count}

class TeamUpdate(BaseModel):
    team_id: int = 1
    hero_ids: list[int]

@router.post("/team/set")
def set_team(data: TeamUpdate):
    if len(data.hero_ids) > 5:
        raise HTTPException(status_code=400, detail="Max 5 heroes per team")
    if data.team_id < 1 or data.team_id > 10:
        raise HTTPException(status_code=400, detail="Team ID must be between 1 and 10")
        
    with db() as conn:
        # Clear this specific team
        conn.execute("UPDATE heroes SET is_on_team = 0, team_position = 0 WHERE is_on_team = ?", (data.team_id,))
        # Set new team
        for idx, hid in enumerate(data.hero_ids):
            # Also ensures hero is removed from any other team they were on
            conn.execute("UPDATE heroes SET is_on_team = ?, team_position = ? WHERE id = ? AND is_alive = 1", (data.team_id, idx, hid))
    return {"ok": True, "team_id": data.team_id, "team": data.hero_ids}

class ReorderTeamReq(BaseModel):
    team_id: int
    hero_ids: list[int]

@router.post("/team/reorder")
def reorder_team(data: ReorderTeamReq):
    with db() as conn:
        for idx, hid in enumerate(data.hero_ids):
            conn.execute("UPDATE heroes SET team_position = ? WHERE id = ? AND is_on_team = ?", (idx, hid, data.team_id))
    return {"ok": True}

class EgoAutoReq(BaseModel):
    team_id: int
    ego_hero_id: int

@router.post("/team/ego_auto")
def ego_auto_team(data: EgoAutoReq):
    from services.ego_service import auto_assign_ego_team
    try:
        new_team = auto_assign_ego_team(data.ego_hero_id, data.team_id)
        return {"ok": True, "team": new_team}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/team/{team_id}")
def get_team_by_id(team_id: int):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM heroes WHERE is_on_team = ? AND is_alive = 1 ORDER BY team_position ASC, id ASC", (team_id,)
        ).fetchall()
    return [row_to_hero(r) for r in rows]

@router.get("/team/current")
def get_team():
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM heroes WHERE is_on_team = 1 AND is_alive = 1 ORDER BY team_position ASC, id ASC"
        ).fetchall()
    return [row_to_hero(r) for r in rows]

@router.get("/teams/all")
def get_all_teams():
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM heroes WHERE is_on_team > 0 AND is_alive = 1 ORDER BY is_on_team ASC, team_position ASC, id ASC"
        ).fetchall()
        
    teams = {i: [] for i in range(1, 11)}
    for r in rows:
        if r["is_on_team"] in teams:
            teams[r["is_on_team"]].append(row_to_hero(r))
    return teams


# ─── Aptitude reveal endpoint ───────────────────────────────────────

@router.get("/{hero_id}/aptitudes")
def get_hero_aptitudes(hero_id: int):
    """Return revealed aptitudes for a hero based on their level."""
    with db() as conn:
        row = conn.execute("SELECT * FROM heroes WHERE id = ?", (hero_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Hero not found")
    hero = dict(row)
    revealed = get_revealed_aptitudes(hero)
    return {"hero_id": hero_id, "level": hero.get("level", 1), "aptitudes": revealed}


# ─── Synthesis endpoint ─────────────────────────────────────────────

class SynthesizeRequest(BaseModel):
    target_id: int
    sacrifice_id: int

@router.post("/synthesize")
def synthesize_hero(data: SynthesizeRequest):
    """
    Sacrifice one hero to empower another. Causes trauma to roster.
    The sacrifice is permanent. All living heroes witness the act.
    """
    from services.morale_service import get_morale_state

    if data.target_id == data.sacrifice_id:
        raise HTTPException(status_code=400, detail="Cannot sacrifice a hero to themselves.")

    with db() as conn:
        target = conn.execute("SELECT * FROM heroes WHERE id = ? AND is_alive = 1", (data.target_id,)).fetchone()
        sacrifice = conn.execute("SELECT * FROM heroes WHERE id = ? AND is_alive = 1", (data.sacrifice_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Target hero not found or dead.")
        if not sacrifice:
            raise HTTPException(status_code=404, detail="Sacrifice hero not found or dead.")

        target_dict = dict(target)
        sacrifice_dict = dict(sacrifice)

        # Calculate stat gains: 10-20% of sacrifice's stats based on rarity
        transfer_pct = 0.10 + (sacrifice_dict["birth_star"] * 0.015)
        hp_gain = int(sacrifice_dict["max_hp"] * transfer_pct)
        atk_gain = max(1, int(sacrifice_dict["attack"] * transfer_pct))
        def_gain = max(1, int(sacrifice_dict["defense"] * transfer_pct))
        spd_gain = max(1, int(sacrifice_dict["speed"] * transfer_pct))

        is_resonant = (target_dict["hero_class"] == sacrifice_dict["hero_class"] and target_dict["hero_class"] != "Classless")
        msg_suffix = ""
        if is_resonant:
            hp_gain *= 2
            atk_gain *= 2
            def_gain *= 2
            spd_gain *= 2
            conn.execute("UPDATE heroes SET ego_type = 'Resonant' WHERE id = ?", (data.target_id,))
            msg_suffix += " EGO RESONANCE TRIGGERED!"
            
        import random
        b_skills = json.loads(sacrifice_dict.get("skills") or "[]")
        b_traits = json.loads(sacrifice_dict.get("traits") or "[]")
        if random.random() < 0.5 and (b_skills or b_traits):
            inherited = random.choice(b_skills + b_traits)
            a_skills = json.loads(target_dict.get("skills") or "[]")
            a_traits = json.loads(target_dict.get("traits") or "[]")
            a_names = [x["name"] for x in a_skills + a_traits]
            if inherited["name"] not in a_names:
                if inherited in b_skills:
                    a_skills.append(inherited)
                    conn.execute("UPDATE heroes SET skills = ? WHERE id = ?", (json.dumps(a_skills), data.target_id))
                else:
                    a_traits.append(inherited)
                    conn.execute("UPDATE heroes SET traits = ? WHERE id = ?", (json.dumps(a_traits), data.target_id))
                msg_suffix += f" Inherited {inherited['name']}!"

        # Apply gains to target
        conn.execute("""
            UPDATE heroes SET
                max_hp = max_hp + ?, hp = hp + ?,
                attack = attack + ?, defense = defense + ?, speed = speed + ?
            WHERE id = ?
        """, (hp_gain, hp_gain, atk_gain, def_gain, spd_gain, data.target_id))

        # Mark sacrifice as dead/synthesized
        conn.execute("""
            UPDATE heroes SET is_alive = 0, is_on_team = 0, synthesized = 1
            WHERE id = ?
        """, (data.sacrifice_id,))

        # Trauma to all living heroes (they witnessed a sacrifice)
        trauma_gain = 5 + sacrifice_dict["birth_star"]
        stress_gain = 10 + sacrifice_dict["birth_star"] * 2
        morale_loss = -(8 + sacrifice_dict["birth_star"] * 2)

        living_heroes = conn.execute(
            "SELECT * FROM heroes WHERE is_alive = 1 AND id != ?", (data.target_id,)
        ).fetchall()
        for hero in living_heroes:
            h = dict(hero)
            
            # Observer confidence factor: if they are stronger than the sacrifice, they feel safer.
            # If they are weaker, they realize nobody is safe and take more damage.
            star_diff = h["birth_star"] - sacrifice_dict["birth_star"]
            level_diff = h.get("level", 1) - sacrifice_dict.get("level", 1)
            observer_mult = 1.0 - (star_diff * 0.15) - (level_diff * 0.01)
            observer_mult = max(0.2, min(2.0, observer_mult))
            
            actual_trauma = int(trauma_gain * observer_mult)
            actual_stress = int(stress_gain * observer_mult)
            actual_morale = int(morale_loss * observer_mult)

            new_trauma = min(100, h["trauma"] + actual_trauma)
            new_stress = min(100, h["stress"] + actual_stress)
            trauma_ceiling = 100 - int(new_trauma * 0.4)
            new_morale = max(0, min(trauma_ceiling, h["morale"] + actual_morale))
            new_state = get_morale_state(new_morale)
            conn.execute("""
                UPDATE heroes SET trauma = ?, stress = ?, morale = ?, morale_state = ?
                WHERE id = ?
            """, (new_trauma, new_stress, new_morale, new_state, hero["id"]))

        # Target also gets some guilt, scaling similarly
        t = target_dict
        t_star_diff = t["birth_star"] - sacrifice_dict["birth_star"]
        t_level_diff = t.get("level", 1) - sacrifice_dict.get("level", 1)
        t_mult = max(0.2, min(2.0, 1.0 - (t_star_diff * 0.15) - (t_level_diff * 0.01)))

        t_trauma_gain = int(max(2, trauma_gain // 2) * t_mult)
        t_stress_gain = int(max(3, stress_gain // 2) * t_mult)
        t_morale_loss = int((morale_loss // 2) * t_mult)

        t_trauma = min(100, t["trauma"] + t_trauma_gain)
        t_stress = min(100, t["stress"] + t_stress_gain)
        t_ceiling = 100 - int(t_trauma * 0.4)
        t_morale = max(0, min(t_ceiling, t["morale"] + t_morale_loss))
        conn.execute("""
            UPDATE heroes SET trauma = ?, stress = ?, morale = ?, morale_state = ?
            WHERE id = ?
        """, (t_trauma, t_stress, t_morale, get_morale_state(t_morale), data.target_id))

        updated = conn.execute("SELECT * FROM heroes WHERE id = ?", (data.target_id,)).fetchone()

    return {
        "ok": True,
        "target": dict(updated),
        "sacrifice_name": sacrifice_dict["name"],
        "sacrifice_star": sacrifice_dict["birth_star"],
        "gains": {"hp": hp_gain, "attack": atk_gain, "defense": def_gain, "speed": spd_gain},
        "roster_trauma": trauma_gain,
        "roster_stress": stress_gain,
        "message": f"{sacrifice_dict['name']} was consumed. {target_dict['name']} grows stronger.{msg_suffix}",
    }


# ─── Ascension endpoint ─────────────────────────────────────────────

ASCENSION_GOLD_COST = {
    0: 500,
    1: 1000,
    2: 2000,
    3: 4000,
    4: 8000,
    5: 15000,
    6: 30000,
}

ASCENSION_LEVEL_REQ = {
    0: 10,
    1: 20,
    2: 30,
    3: 40,
    4: 50,
    5: 60,
    6: 75,
}

@router.post("/{hero_id}/ascend")
def ascend_hero(hero_id: int):
    """
    Ascend a hero to break their level cap.
    Requires hero to be at current level cap and gold cost.
    """
    with db() as conn:
        hero = conn.execute("SELECT * FROM heroes WHERE id = ? AND is_alive = 1", (hero_id,)).fetchone()
        if not hero:
            raise HTTPException(status_code=404, detail="Hero not found or dead.")
        hero = dict(hero)

        current_asc = hero.get("ascension_star", 0) or 0
        if current_asc >= 7:
            raise HTTPException(status_code=400, detail="Hero is already at max ascension.")

        # Check level requirement
        level_req = ASCENSION_LEVEL_REQ.get(current_asc, 100)
        hero_level = hero.get("level", 1)
        if hero_level < level_req:
            raise HTTPException(
                status_code=400,
                detail=f"Hero must be level {level_req} to ascend. Currently level {hero_level}."
            )

        # Check gold
        gold_cost = ASCENSION_GOLD_COST.get(current_asc, 50000)
        base = conn.execute("SELECT gold FROM base WHERE id = 1").fetchone()
        if base["gold"] < gold_cost:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough gold. Need {gold_cost}, have {base['gold']}."
            )

        # Deduct gold and ascend
        conn.execute("UPDATE base SET gold = gold - ? WHERE id = 1", (gold_cost,))
        new_asc = current_asc + 1
        conn.execute(
            "UPDATE heroes SET ascension_star = ? WHERE id = ?",
            (new_asc, hero_id)
        )

        # Recalculate level with new cap
        updated_hero = conn.execute("SELECT * FROM heroes WHERE id = ?", (hero_id,)).fetchone()
        new_level = recalculate_hero_level(dict(updated_hero))
        conn.execute("UPDATE heroes SET level = ? WHERE id = ?", (new_level, hero_id))

        from services.portrait_cache import queue_custom_portrait
        prompt = f"dark fantasy anime {hero['hero_class']} portrait, {hero['current_star']} star rarity, {new_asc} star ascension"
        queue_custom_portrait(hero_id, prompt, hero["name"], hero.get("gender", "unknown"))

    return {
        "ok": True,
        "hero_id": hero_id,
        "new_ascension": new_asc,
        "gold_spent": gold_cost,
        "new_level": new_level,
        "message": f"{hero['name']} ascended to {new_asc}★ ascension!"
    }

# ─── Promotion endpoint (star rank upgrade) ────────────────────────

PROMOTION_GOLD_COST = {
    1: 300,    # 1★ → 2★
    2: 800,    # 2★ → 3★
    3: 2000,   # 3★ → 4★
    4: 5000,   # 4★ → 5★
    5: 12000,  # 5★ → 6★
    6: 30000,  # 6★ → 7★ (transcendence cost, requires special item too)
}

@router.post("/{hero_id}/promote")
def promote_hero(hero_id: int):
    """
    Promote a hero to the next star rank.
    Requires hero to be at max level for their current star.
    """
    from services.level_service import level_cap, get_hero_star, STAR_LEVEL_CAPS

    with db() as conn:
        hero = conn.execute("SELECT * FROM heroes WHERE id = ? AND is_alive = 1", (hero_id,)).fetchone()
        if not hero:
            raise HTTPException(status_code=404, detail="Hero not found or dead.")
        hero = dict(hero)

        current_star = get_hero_star(hero)
        if current_star >= 7:
            raise HTTPException(status_code=400, detail="Hero is already at max star rank.")

        # Must be at max level for current star
        max_lvl = level_cap(current_star, hero.get("ascension_star", 0))
        hero_level = hero.get("level", 1)
        if hero_level < max_lvl:
            raise HTTPException(
                status_code=400,
                detail=f"Hero must be level {max_lvl} to promote. Currently level {hero_level}."
            )

        # Check gold
        gold_cost = PROMOTION_GOLD_COST.get(current_star, 50000)
        base = conn.execute("SELECT gold FROM base WHERE id = 1").fetchone()
        if base["gold"] < gold_cost:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough gold. Need {gold_cost}, have {base['gold']}."
            )

        # Deduct gold and promote
        conn.execute("UPDATE base SET gold = gold - ? WHERE id = 1", (gold_cost,))
        new_star = current_star + 1
        
        # Check for hidden class unlock (1/2★ to 3★ promotion)
        unlocked_class = None
        if new_star >= 3 and hero.get("hidden_class"):
            unlocked_class = hero["hidden_class"]
            conn.execute(
                "UPDATE heroes SET current_star = ?, hero_class = ?, hidden_class = NULL WHERE id = ?",
                (new_star, unlocked_class, hero_id)
            )
        else:
            conn.execute(
                "UPDATE heroes SET current_star = ? WHERE id = ?",
                (new_star, hero_id)
            )

        # Stat boost on promotion (+10% all stats)
        conn.execute("""
            UPDATE heroes SET
                max_hp = max_hp + max_hp / 10,
                hp = hp + hp / 10,
                attack = attack + attack / 10,
                defense = defense + defense / 10,
                speed = speed + speed / 10
            WHERE id = ?
        """, (hero_id,))
        
        current_class = unlocked_class if unlocked_class else hero["hero_class"]
        if new_star in [3, 5, 7]:
            from services.portrait_cache import queue_upgrade_portrait
            queue_upgrade_portrait(hero_id, new_star)

    msg = f"{hero['name']} promoted from {current_star}★ to {new_star}★!"
    if unlocked_class:
        msg += f" Hidden potential awakened: Class is now {unlocked_class}!"
        
    return {
        "ok": True,
        "hero_id": hero_id,
        "new_star": new_star,
        "old_star": current_star,
        "gold_spent": gold_cost,
        "unlocked_class": unlocked_class,
        "message": msg
    }


# ─── Legacy & Bond endpoints ───────────────────────────────────────

@router.get("/legacies")
def list_legacies():
    """List all fallen hero legacies and their bonuses."""
    from services.legacy_service import get_all_legacies, get_active_legacy_bonuses
    return {
        "legacies": get_all_legacies(),
        "active_bonuses": get_active_legacy_bonuses(),
    }


@router.get("/bonds")
def list_bonds():
    """List all hero bonds."""
    with db() as conn:
        rows = conn.execute("""
            SELECT hb.*, h1.name as hero_a_name, h2.name as hero_b_name
            FROM hero_bonds hb
            JOIN heroes h1 ON h1.id = hb.hero_a_id
            JOIN heroes h2 ON h2.id = hb.hero_b_id
            WHERE hb.bond_level > 0
            ORDER BY hb.bond_level DESC
        """).fetchall()
    return [dict(r) for r in rows]
class EvolveRequest(BaseModel):
    target_class: str

@router.post("/{hero_id}/evolve")
def evolve_hero(hero_id: int, req: EvolveRequest):
    from services.class_service import get_class_evolution_options
    with db() as conn:
        row = conn.execute("SELECT * FROM heroes WHERE id = ? AND is_alive = 1", (hero_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Hero not found")
        hero = dict(row)
        options = get_class_evolution_options(hero["hero_class"], hero.get("level", 1))
        if req.target_class not in options:
            raise HTTPException(status_code=400, detail=f"Cannot evolve {hero['hero_class']} to {req.target_class}. Valid options: {options}")
        
        conn.execute("UPDATE heroes SET hero_class = ? WHERE id = ?", (req.target_class, hero_id))
    return {"ok": True, "new_class": req.target_class}

class EquipRequest(BaseModel):
    equipment_id: int

@router.post("/{hero_id}/equip")
def equip_item(hero_id: int, req: EquipRequest):
    with db() as conn:
        # Check hero
        hero = conn.execute("SELECT id FROM heroes WHERE id = ? AND is_alive = 1", (hero_id,)).fetchone()
        if not hero:
            raise HTTPException(status_code=404, detail="Hero not found or dead")
        
        # Check equip
        equip = conn.execute("SELECT * FROM equipment WHERE id = ?", (req.equipment_id,)).fetchone()
        if not equip:
            raise HTTPException(status_code=404, detail="Equipment not found")
        
        # If equipment is already equipped by someone else, remove it
        if equip["equipped_to"]:
            conn.execute("UPDATE equipment SET equipped_to = NULL WHERE id = ?", (equip["id"],))
            
        # Unequip whatever is currently in that slot for this hero
        conn.execute("UPDATE equipment SET equipped_to = NULL WHERE equipped_to = ? AND slot = ?", (hero_id, equip["slot"]))
        
        # Equip new item
        conn.execute("UPDATE equipment SET equipped_to = ? WHERE id = ?", (hero_id, equip["id"]))
        
    return {"ok": True}

@router.post("/{hero_id}/unequip")
def unequip_item(hero_id: int, req: EquipRequest):
    with db() as conn:
        conn.execute("UPDATE equipment SET equipped_to = NULL WHERE id = ? AND equipped_to = ?", (req.equipment_id, hero_id))
    return {"ok": True}

@router.get("/classes/evolutions")
def get_all_class_evolutions():
    from services.class_service import CLASS_EVOLUTIONS
    return CLASS_EVOLUTIONS
