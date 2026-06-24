from fastapi import APIRouter, HTTPException
from database import db
from services.combat_service import run_combat
from services.morale_service import between_floor_recovery, witness_death_trauma, get_morale_state, apply_morale_delta, apply_stress, apply_trauma
from services.llm_service import generate_combat_narration, generate_event_narrative, generate_event_resolution_narrative
from services.event_service import select_event, resolve_event_choice
from services.floor_templates import (
    get_floor_type, get_cached_floor_type, FLOOR_FLAVOR_INTRO,
    generate_explore_floor, get_explore_choice, resolve_explore_loot,
    generate_rest_floor, resolve_rest_floor,
)
import json
import random
from pydantic import BaseModel

router = APIRouter()

class EnterFloorRequest(BaseModel):
    team_ids: list[int] = []
    team_id: int = 1
    floor_number: int

# Combat narration used to block floor-entry for up to 1.5s waiting on an LLM
# call that has nowhere to render on the frontend anyway. Now fired in the
# background; the response carries an id the frontend can poll once, a
# moment later, to upgrade the placeholder text if the real one is ready.
_narrative_futures = {}
_narrative_id_counter = 0

def _register_narrative_future(future):
    global _narrative_id_counter
    _narrative_id_counter += 1
    nid = _narrative_id_counter
    _narrative_futures[nid] = future
    if len(_narrative_futures) > 50:
        for old_id in sorted(_narrative_futures)[:-50]:
            del _narrative_futures[old_id]
    return nid

@router.get("/narrative/{narrative_id}")
def get_narrative(narrative_id: int):
    future = _narrative_futures.get(narrative_id)
    if future is None:
        return {"ready": False}
    if not future.done():
        return {"ready": False}
    try:
        return {"ready": True, "narrative": future.result()}
    except Exception:
        return {"ready": True, "narrative": "A fierce battle took place."}


def _resolve_real_combat(conn, hero_teams, floor_number, is_boss, is_miniboss, zone_theme,
                          boss_data_override, base_row, pending_legacies,
                          enemy_count_override=None, flavor_intro=None, difficulty_mult=1.0):
    """Run a real fight and apply every resulting effect."""
    from services.llm_service import generate_combat_narration, submit_flavor_text
    from services.combat_service import run_multi_combat

    try:
        combat_result = run_multi_combat(
            hero_teams, floor_number, is_boss=is_boss, is_miniboss=is_miniboss,
            zone_theme=zone_theme, boss_data_override=boss_data_override,
            difficulty_mult=difficulty_mult, conn=conn,
        )
    except Exception as e:
        print(f"Combat error: {e}")
        raise HTTPException(status_code=500, detail=f"Combat simulation failed: {str(e)}")

    if flavor_intro:
        combat_result["log"] = [flavor_intro] + combat_result.get("log", [])

    result = {"combat": combat_result}

    if combat_result["winner"] == "heroes":
        result["message"] = f"Floor {floor_number} Cleared!"
    else:
        result["message"] = f"Team defeated on Floor {floor_number}."
        result["run_over"] = True

    flat_hero_names = [h["name"] for team in hero_teams for h in team]
    narrative_future = submit_flavor_text(generate_combat_narration, combat_result.get("log", []), flat_hero_names)
    narrative = "A fierce battle took place."
    result["narrative_id"] = _register_narrative_future(narrative_future)

    # One narration future per team's leg of the fight — multi-team floors
    # (21+) keep each team's turns in team_results, not the top-level
    # "turns" (that's only forwarded for the single-team case below).
    from services.llm_service import generate_turn_narrations
    team_results = combat_result.get("team_results") or [combat_result]
    turn_narrative_ids = []
    for tr in team_results:
        tr_turn_lines = [t["log"] for t in (tr or {}).get("turns", [])]
        fut = submit_flavor_text(generate_turn_narrations, tr_turn_lines, flat_hero_names)
        turn_narrative_ids.append(_register_narrative_future(fut))
    result["turn_narrative_ids"] = turn_narrative_ids
    if turn_narrative_ids:
        result["turn_narrative_id"] = turn_narrative_ids[0]

    import datetime
    from services.bonds_service import get_bond
    
    dead_ids = []
    for dead_hero_row in combat_result["dead_heroes"]:
        dead_id = dead_hero_row if isinstance(dead_hero_row, int) else dead_hero_row["id"]
        dead_ids.append(dead_id)
        
        # Determine if they meet the legacy threshold (unique_floors_cleared >= 10)
        hr = conn.execute("SELECT * FROM heroes WHERE id = ?", (dead_id,)).fetchone()
        if hr:
            hr_dict = dict(hr)
            # Automatic Legacy Check
            if hr_dict.get("unique_floors_cleared", 0) >= 10:
                clears = hr_dict["unique_floors_cleared"]
                # Calculate legacy buffs based on clears
                # 10 clears = base 5% atk/hp, +1% per clear above 10
                buff_pct = min(25, 5 + (clears - 10))
                buffs = json.dumps({"primary_bonus": {"stat": "str_pct", "label": "ATK", "value": buff_pct * 0.01, "desc": f"+{buff_pct}% ATK to all"}})
                conn.execute(
                    "INSERT INTO legacies (hero_id, hero_name, hero_star, title, flavor_text, bonus_json, score, is_sacrifice) VALUES (?, ?, ?, ?, ?, ?, 1000, 1)",
                    (hr_dict["id"], hr_dict["name"], hr_dict.get("birth_star", 1), f"Memory of {hr_dict['name']}", f"Fell on Floor {floor_number} after {clears} unique clears.", buffs)
                )
            pending_legacies.append((hr_dict, False))
            
        conn.execute("UPDATE heroes SET is_alive = 0, is_on_team = 0 WHERE id = ?", (dead_id,))

    # Survival logic: Survivor's Guilt & Bonds
    if dead_ids:
        # Was this a near-wipe? If >= 3 heroes died in this battle...
        is_near_wipe = len(dead_ids) >= 3
        
        for surviving in combat_result["surviving_heroes"]:
            surv_id = surviving["id"]
            surv_hr = conn.execute("SELECT * FROM heroes WHERE id = ?", (surv_id,)).fetchone()
            if not surv_hr: continue
            
            # Check bonds with the dead heroes
            high_bonds_count = 0
            for did in dead_ids:
                bond_val = get_bond(conn, surv_id, did)
                if bond_val > 30:
                    high_bonds_count += 1
            
            # Apply Depression if they lost someone they had a strong bond with
            if high_bonds_count > 0:
                # Set depressed for 24 hours
                until = (datetime.datetime.utcnow() + datetime.timedelta(hours=24)).isoformat()
                conn.execute("UPDATE heroes SET condition = 'Depressed', condition_until = ? WHERE id = ?", (until, surv_id))
                combat_result.setdefault("log", []).append(f"  🌧️ {surv_hr['name']} is overcome with despair after losing bonded comrades.")
                
            # Apply Retirement (Survivor's Guilt) if near-wipe of bonded allies
            if is_near_wipe and high_bonds_count >= 2:
                # Check constitution (apt_mental)
                if surv_hr["apt_mental"] < 70:
                    conn.execute("UPDATE heroes SET near_wipes_survived = near_wipes_survived + 1 WHERE id = ?", (surv_id,))
                    nw_surv = surv_hr["near_wipes_survived"] + 1
                    if nw_surv >= 2:
                        # Retire
                        conn.execute("UPDATE heroes SET condition = 'Retired', is_on_team = 0 WHERE id = ?", (surv_id,))
                        combat_result.setdefault("log", []).append(f"  💀 {surv_hr['name']}'s mind breaks from surviving another massacre. They retire from active duty.")
                        
            # Apply standard trauma
            trauma_data = witness_death_trauma(is_close_ally=high_bonds_count > 0)
            conn.execute("""
                UPDATE heroes SET
                    trauma = MIN(100, trauma + ?),
                    stress = MIN(100, stress + ?)
                WHERE id = ?
            """, (len(dead_ids) * trauma_data["trauma_delta"],
                  len(dead_ids) * trauma_data["stress_delta"], surv_id))

    for s in combat_result["surviving_heroes"]:
        hid = s["id"]
        hero_row = conn.execute("SELECT morale, trauma, skills FROM heroes WHERE id = ?", (hid,)).fetchone()
        if hero_row:
            hero_dict = dict(hero_row)
            new_morale = apply_morale_delta(hero_dict["morale"], hero_dict["trauma"], s["morale_delta"])

            skills_json = hero_dict["skills"]
            skills = json.loads(skills_json) if skills_json else []
            if hid in combat_result.get("skill_upgrades", {}):
                upgrades = combat_result["skill_upgrades"][hid]
                for upg in upgrades:
                    for sk in skills:
                        if sk["id"] == upg["skill_id"]:
                            sk["tier"] = upg["new_tier"]
                            sk["level"] = 1
                            sk["xp"] = 0
                            sk["max_xp"] = 100

            if hid in combat_result.get("skills_learned", {}):
                skills.extend(combat_result["skills_learned"][hid])

            skills_json = json.dumps(skills)

            conn.execute("""
                UPDATE heroes SET health = MIN(max_health, ?), morale = ?, morale_state = ?, skills = ? WHERE id = ?
            """, (s["health"], new_morale, get_morale_state(new_morale), skills_json, s["id"]))

    result["gold_gained"] = combat_result.get("gold_gained", 0)
    result["supplies_gained"] = combat_result.get("supplies_gained", 0)
    result["materials_gained"] = combat_result.get("materials_gained", {})

    if floor_number <= base_row["highest_floor"]:
        result["gold_gained"] = int(result["gold_gained"] * 0.05)
        result["supplies_gained"] = int(result["supplies_gained"] * 0.05)

    if result["gold_gained"] > 0 or result["supplies_gained"] > 0 or result["materials_gained"]:
        conn.execute(
            "UPDATE base SET gold = gold + ?, supplies = supplies + ? WHERE id = 1",
            (result["gold_gained"], result["supplies_gained"])
        )
        if result["materials_gained"]:
            base_row_current = conn.execute("SELECT materials FROM base WHERE id = 1").fetchone()
            current_mats = json.loads(base_row_current["materials"]) if base_row_current["materials"] else {}
            for m, qty in result["materials_gained"].items():
                current_mats[m] = current_mats.get(m, 0) + qty
            conn.execute("UPDATE base SET materials = ? WHERE id = 1", (json.dumps(current_mats),))

    if combat_result.get("equipment_drop"):
        from services.equipment_service import save_equipment
        equip = combat_result["equipment_drop"]
        equip["id"] = save_equipment(equip, conn=conn)
        result["equipment_drop"] = equip

    if combat_result.get("relic_drop"):
        result["relic_drop"] = combat_result["relic_drop"]

    result["narrative"] = narrative
    return result

@router.get("/floor/preview/{floor_number}")
def preview_floor(floor_number: int):
    """Peek at a floor's type/flavor without spending supplies or resolving
    anything. Floor type is cached on first peek (or first enter, whichever
    comes first) so it never changes on a later visit or rerun."""
    with db() as conn:
        floor_type = get_cached_floor_type(conn, floor_number)
    return {
        "floor_type": floor_type,
        "blurb": FLOOR_FLAVOR_INTRO.get(floor_type, ""),
    }

@router.post("/floor/enter")
def enter_floor(req: EnterFloorRequest):
    """Resolve a single floor for a specific team without any 'Run' constraints."""
    pending_legacies = []
    with db() as conn:
        # Check base and supplies
        base_row = conn.execute("SELECT highest_floor, supplies FROM base WHERE id = 1").fetchone()
        if not base_row:
            raise HTTPException(status_code=500, detail="Base not found")
            
        if req.floor_number > base_row["highest_floor"] + 1:
            raise HTTPException(status_code=400, detail="Cannot skip floors.")

        supply_cost = 2
        if base_row["supplies"] < supply_cost:
            raise HTTPException(status_code=400, detail=f"Not enough supplies to enter the tower. Need {supply_cost}.")

        # Get heroes
        teams_to_deploy = req.team_ids if req.team_ids else [req.team_id]
        
        # Verify required teams
        required_teams = (req.floor_number - 1) // 20 + 1
        if req.floor_number == 1 and not req.team_ids: required_teams = 1
        if len(teams_to_deploy) < required_teams:
            raise HTTPException(status_code=400, detail=f"Floor {req.floor_number} requires {required_teams} team(s) to be deployed.")
            
        hero_teams = []
        ego_rebellions = []
        for tid in teams_to_deploy[:required_teams]:
            from services.ego_service import process_ego_patience
            ego_rebellions.extend(process_ego_patience(conn, tid))
            team_heroes = [dict(r) for r in conn.execute("SELECT * FROM heroes WHERE is_on_team = ? AND is_alive = 1 ORDER BY team_position ASC, id ASC", (tid,)).fetchall()]
            if not team_heroes:
                raise HTTPException(status_code=400, detail=f"No heroes assigned to Team {tid}.")
            hero_teams.append(team_heroes)

        for team in hero_teams:
            for hero in team:
                if hero["fatigue"] >= 10:
                    raise HTTPException(status_code=400, detail=f"{hero['name']} is exhausted (Fatigue 10) and must rest before entering the tower.")

        # Auto-apply Bandages (if any in inventory) to the most-injured
        # deployed heroes before the fight — combat resolves as one
        # deterministic simulation rather than a turn-by-turn player loop,
        # so "using" a Bandage means patching up before you go in, not a
        # mid-fight action.
        from services.infirmary_service import BANDAGE_HEAL_PCT
        mats_row = conn.execute("SELECT materials FROM base WHERE id = 1").fetchone()
        materials = json.loads(mats_row["materials"]) if mats_row["materials"] else {}
        bandages = materials.get("Bandage", 0)
        if bandages > 0:
            flat_heroes = [hero for team in hero_teams for hero in team]
            injured = sorted([hero for hero in flat_heroes if hero["health"] < hero["max_health"]], key=lambda hero: hero["health"] / hero["max_health"])
            used = 0
            for hero in injured:
                if used >= bandages:
                    break
                heal = int(hero["max_health"] * BANDAGE_HEAL_PCT)
                hero["health"] = min(hero["max_health"], hero["health"] + heal)
                conn.execute("UPDATE heroes SET health = ? WHERE id = ?", (hero["health"], hero["id"]))
                used += 1
            if used > 0:
                materials["Bandage"] = bandages - used
                conn.execute("UPDATE base SET materials = ? WHERE id = 1", (json.dumps(materials),))

        conn.execute("UPDATE base SET supplies = supplies - ? WHERE id = 1", (supply_cost,))

        # Flavor text (zone theme, boss naming, narration) must never stack into
        # a multi-second wait before combat starts — none of it affects combat
        # math. Each call is bounded to a short timeout; on timeout we fall
        # back to local text rather than wait.
        from services.llm_service import generate_zone_theme, generate_boss_enemy, call_with_timeout, submit_flavor_text, await_flavor_text
        floor_type = get_cached_floor_type(conn, req.floor_number)
        hero_list = [h for team in hero_teams for h in team] # flattened for event logs and logic
        is_boss = floor_type == "boss"
        is_miniboss = floor_type == "miniboss"

        # Zone theme and boss naming are independent enough to run concurrently
        # instead of sequentially — boss naming uses a generic placeholder theme
        # rather than waiting on the real zone theme text first.
        zone_theme_future = submit_flavor_text(generate_zone_theme, req.floor_number)
        boss_future = None
        if is_boss or is_miniboss:
            placeholder_theme = f"a dark, dangerous zone around floor {req.floor_number} of a tower"
            boss_future = submit_flavor_text(generate_boss_enemy, placeholder_theme, req.floor_number, is_miniboss)

        zone_theme = await_flavor_text(zone_theme_future, timeout=1.5, fallback="")
        zone_theme_display = zone_theme or "The Dark Unknown: Shadows obscure the path ahead."
        boss_data_override = await_flavor_text(boss_future, timeout=1.5, fallback=None) if boss_future else None

        result = {}
        narrative = None

        # Resolve Floor Logic — survival/defend/escort are real fights with
        # a different frame and a bigger/different enemy wave, not abstract
        # stat checks. They share the exact same resolution path as plain
        # combat (death/legacy/trauma/rewards/equipment) below.
        if floor_type in ("combat", "miniboss", "boss", "survival", "defend", "escort"):
            enemy_count_override = None
            flavor_intro = FLOOR_FLAVOR_INTRO.get(floor_type)
            if floor_type == "survival":
                enemy_count_override = random.randint(6, 8)
            elif floor_type == "escort":
                npc = random.choice(["a wounded traveler", "a lost child", "a captured merchant", "a dying scholar"])
                flavor_intro = f"You find {npc} who needs safe passage. Enemies close in on the path."

            result = _resolve_real_combat(
                conn, hero_teams, req.floor_number, is_boss, is_miniboss, zone_theme,
                boss_data_override, base_row, pending_legacies,
                enemy_count_override=enemy_count_override, flavor_intro=flavor_intro,
            )
            result["floor_type"] = floor_type

        elif floor_type == "event":
            event_data = select_event(req.floor_number, zone_theme_display)
            narrative = call_with_timeout(
                generate_event_narrative, zone_theme_display, req.floor_number, [h["name"] for h in hero_list],
                timeout=1.5, fallback=event_data["description"]
            )
            result = {
                "floor_type": "event",
                "event": event_data,
                "event_narrative": narrative,
                "awaiting_choice": True,
                "theme": zone_theme_display
            }

        elif floor_type == "explore":
            # Explore is a real player choice (thorough/quick/leave), not an
            # auto-resolve — mirrors the event awaiting_choice flow. The actual
            # discovery/trap roll happens fresh in /floor/explore/resolve once
            # the player picks; nothing here is random-sensitive to persist.
            template = generate_explore_floor(req.floor_number)
            result = {
                "floor_type": "explore",
                "explore": {
                    "theme": template["theme"],
                    "choices": [
                        {"id": c["id"], "label": c["label"], "hint": c["hint"]}
                        for c in template["choices"]
                    ],
                },
                "awaiting_choice": True,
            }

        elif floor_type == "rest":
            template = generate_rest_floor(req.floor_number)
            resolution = resolve_rest_floor(template, hero_list)
            for hr in resolution["hero_results"]:
                hero_data = next((h for h in hero_list if h["id"] == hr["id"]), None)
                if hero_data:
                    new_morale = max(0, min(100, hero_data["morale"] + hr.get("morale_delta", 0)))
                    new_stress = max(0, hero_data["stress"] + hr.get("stress_gained", 0))
                    conn.execute("UPDATE heroes SET health = MIN(max_health, ?), morale = ?, stress = ?, morale_state = ? WHERE id = ?",
                                 (hr["health"], new_morale, new_stress, get_morale_state(new_morale), hr["id"]))
            result = {
                "floor_type": "rest",
                "resolution": resolution,
                "narrative": resolution["summary"],
                "log": resolution["log"],
            }

        # Add fatigue to deployed heroes
        conn.execute(
            """
            UPDATE heroes 
            SET fatigue = MIN(10, fatigue + 1) 
            WHERE is_on_team = ? AND is_alive = 1
            """,
            (req.team_id,)
        )

        from services.level_service import recalculate_hero_level, level_up_summary
        surviving_ids = []
        
        survivors = []
        if result.get("combat") and "surviving_heroes" in result["combat"]:
            survivors = result["combat"]["surviving_heroes"]
        elif not result.get("run_over") and not result.get("awaiting_choice"):
            survivors = hero_list

        for s in survivors:
            hid = s["id"]
            surviving_ids.append(hid)
            kills_gained = s.get("kills_gained", 0)
            stress_delta = s.get("stress_delta", 0)
            conn.execute("""
                UPDATE heroes SET
                    floors_survived = floors_survived + 1,
                    kills = kills + ?,
                    stress = MIN(100, MAX(0, stress + ?))
                WHERE id = ?
            """, (kills_gained, stress_delta, hid))

            # Recalculate level
            hero_row = conn.execute("SELECT * FROM heroes WHERE id = ?", (hid,)).fetchone()
            if hero_row:
                hero_dict = dict(hero_row)
                old_level = hero_dict.get("level", 1)
                new_level = recalculate_hero_level(hero_dict)
                if new_level != old_level:
                    conn.execute("UPDATE heroes SET level = ? WHERE id = ?", (new_level, hid))
                    level_msgs = level_up_summary(old_level, new_level, hero_dict["name"])
                    result.setdefault("level_ups", []).extend(level_msgs)

        if len(surviving_ids) >= 2:
            for i in range(len(surviving_ids)):
                for j in range(i + 1, len(surviving_ids)):
                    a, b = min(surviving_ids[i], surviving_ids[j]), max(surviving_ids[i], surviving_ids[j])
                    conn.execute("""
                        INSERT INTO hero_bonds (hero_a_id, hero_b_id, bond_level, floors_together)
                        VALUES (?, ?, 1, 1)
                        ON CONFLICT(hero_a_id, hero_b_id) DO UPDATE SET
                            floors_together = floors_together + 1,
                            bond_level = floors_together / 5
                    """, (a, b))

        # IMPORTANT: Between floor recovery applied immediately since we return to base instantly!
        # HP fully heals on lobby return too — the tower trip is over, not a
        # siege, and this is what makes the Infirmary's old passive HP regen
        # and the Rest action's old HP heal both redundant (removed elsewhere).
        for hid in surviving_ids:
            hero_row = conn.execute("SELECT * FROM heroes WHERE id = ?", (hid,)).fetchone()
            if hero_row:
                recovery = between_floor_recovery(dict(hero_row))
                conn.execute("""
                    UPDATE heroes SET health = max_health, morale = ?, stress = ?, trauma = ?, morale_state = ? WHERE id = ?
                """, (recovery["morale"], recovery["stress"], recovery["trauma"], recovery["morale_state"], hid))

        if not result.get("run_over") and not result.get("awaiting_choice") and req.floor_number > base_row["highest_floor"]:
            gems_reward = 500 if req.floor_number % 5 == 0 else 100
            conn.execute("UPDATE base SET highest_floor = ?, gems = gems + ? WHERE id = 1", (req.floor_number, gems_reward))
            result["gems_gained"] = gems_reward
            if survivors:
                ids_str = ",".join(str(s["id"]) for s in survivors)
                conn.execute(f"UPDATE heroes SET unique_floors_cleared = unique_floors_cleared + 1 WHERE id IN ({ids_str})")

    for hero_dict, is_sacrifice in pending_legacies:
        try:
            from services.portrait_cache import handle_fallen_portrait
            new_path = handle_fallen_portrait(hero_dict["id"], hero_dict.get("portrait_path"), is_sacrifice)
            hero_dict["portrait_path"] = new_path
        except Exception as e:
            print(f"Portrait cleanup error: {e}")
        try:
            from services.legacy_service import create_legacy
            create_legacy(hero_dict, is_sacrifice=is_sacrifice)
        except Exception as e:
            print(f"Legacy creation error: {e}")

    result["floor"] = req.floor_number
    if ego_rebellions:
        result["ego_rebellions"] = ego_rebellions
    return result

class ResolveEventRequest(BaseModel):
    floor_number: int
    team_id: int
    template_id: str
    choice_id: str
    theme: str = "An event occurred."

@router.post("/floor/event/resolve")
def resolve_event_floor(data: ResolveEventRequest):
    """Resolve a player's event floor choice."""
    pending_legacies = []
    with db() as conn:
        heroes = conn.execute(
            "SELECT * FROM heroes WHERE is_on_team = ? AND is_alive = 1", (data.team_id,)
        ).fetchall()
        hero_list = [dict(h) for h in heroes]
        hero_names = [h["name"] for h in hero_list]

        resolution = resolve_event_choice(data.template_id, data.choice_id, hero_list)
        if "error" in resolution:
            raise HTTPException(status_code=400, detail=resolution["error"])

        effects = resolution["effects"]

        if "gold" in effects and effects["gold"] != 0:
            conn.execute("UPDATE base SET gold = gold + ? WHERE id = 1", (effects["gold"],))

        if "item" in effects:
            try:
                from services.equipment_service import save_equipment
                equip = {
                    "name": effects["item"],
                    "type": "Accessory",
                    "rarity": "A",
                    "level": 1,
                    "base_hlt": 150, "base_str": 15, "base_int": 10, "base_agi": 5,
                }
                save_equipment(equip, conn=conn)
            except Exception as e:
                print(f"Failed to grant event item: {e}")

        sacrificed_name = None
        if effects.get("sacrifice_hero") and hero_list:
            import random
            sacrificed = random.choice(hero_list)
            sacrificed_name = sacrificed["name"]
            conn.execute("UPDATE heroes SET is_alive = 0, is_on_team = 0 WHERE id = ?", (sacrificed["id"],))
            hero_list = [h for h in hero_list if h["id"] != sacrificed["id"]]
            pending_legacies.append((sacrificed, True))

        for hero in hero_list:
            hid = hero["id"]
            updates = []
            params = []

            if "hlt_pct" in effects and effects["hlt_pct"] != 0:
                hp_change = int(hero["max_health"] * effects["hlt_pct"])
                new_hp = max(1, min(hero["max_health"], hero["health"] + hp_change))
                updates.append("health = ?")
                params.append(new_hp)

            if "morale" in effects and effects["morale"] != 0:
                new_morale = max(0, min(100, hero["morale"] + effects["morale"]))
                updates.append("morale = ?")
                params.append(new_morale)

            if "stress" in effects and effects["stress"] != 0:
                new_stress = max(0, min(100, hero["stress"] + effects["stress"]))
                updates.append("stress = ?")
                params.append(new_stress)

            if "trauma" in effects and effects["trauma"] != 0:
                new_trauma = max(0, min(100, hero["trauma"] + effects["trauma"]))
                updates.append("trauma = ?")
                params.append(new_trauma)

            if updates:
                params.append(hid)
                conn.execute(f"UPDATE heroes SET {', '.join(updates)} WHERE id = ?", params)

        try:
            narrative = generate_event_resolution_narrative(
                data.theme, resolution["choice_label"], effects, hero_names
            )
        except Exception:
            narrative = f"The party chose: {resolution['choice_label']}."

        # Floor progress (floors_survived/level) only lands once the choice
        # is actually resolved — not on mere entry (see /floor/enter).
        from services.level_service import recalculate_hero_level
        for hero in hero_list:
            conn.execute("UPDATE heroes SET floors_survived = floors_survived + 1 WHERE id = ?", (hero["id"],))
            hero_row = conn.execute("SELECT * FROM heroes WHERE id = ?", (hero["id"],)).fetchone()
            if hero_row:
                new_level = recalculate_hero_level(dict(hero_row))
                if new_level != hero_row["level"]:
                    conn.execute("UPDATE heroes SET level = ? WHERE id = ?", (new_level, hero["id"]))

        base_row = conn.execute("SELECT highest_floor FROM base WHERE id = 1").fetchone()
        if data.floor_number > base_row["highest_floor"]:
            gems_reward = 500 if data.floor_number % 5 == 0 else 100
            conn.execute("UPDATE base SET highest_floor = ?, gems = gems + ? WHERE id = 1", (data.floor_number, gems_reward))
            effects["gems"] = gems_reward

    for hero_dict, is_sacrifice in pending_legacies:
        try:
            from services.portrait_cache import handle_fallen_portrait
            new_path = handle_fallen_portrait(hero_dict["id"], hero_dict.get("portrait_path"), is_sacrifice)
            hero_dict["portrait_path"] = new_path
        except Exception as e:
            print(f"Portrait cleanup error: {e}")
        try:
            from services.legacy_service import create_legacy
            create_legacy(hero_dict, is_sacrifice=is_sacrifice)
        except Exception as e:
            print(f"Legacy creation error: {e}")

    return {
        "ok": True,
        "choice_label": resolution["choice_label"],
        "effects": effects,
        "narrative": narrative,
    }

class ResolveExploreRequest(BaseModel):
    floor_number: int
    team_id: int
    choice_id: str

@router.post("/floor/explore/resolve")
def resolve_explore_floor_choice(data: ResolveExploreRequest):
    """Resolve a player's explore floor choice. Every choice still leads to
    a real fight — the choice sets the encounter's overall difficulty
    (difficulty_mult, not just enemy count — a handful of weak swarmers
    and a single elite can land at the same real threat level) and the
    post-win loot odds. It doesn't skip combat."""
    pending_legacies = []
    with db() as conn:
        base_row = conn.execute("SELECT highest_floor FROM base WHERE id = 1").fetchone()

        heroes = conn.execute(
            "SELECT * FROM heroes WHERE is_on_team = ? AND is_alive = 1", (data.team_id,)
        ).fetchall()
        hero_list = [dict(h) for h in heroes]
        if not hero_list:
            raise HTTPException(status_code=400, detail=f"No heroes assigned to Team {data.team_id}.")

        template = generate_explore_floor(data.floor_number)
        choice = get_explore_choice(template, data.choice_id)

        result = _resolve_real_combat(
            conn, hero_list, data.floor_number, is_boss=False, is_miniboss=False, zone_theme="",
            boss_data_override=None, base_row=base_row, pending_legacies=pending_legacies,
            difficulty_mult=choice["difficulty_mult"], flavor_intro=template["theme"],
        )
        result["floor_type"] = "explore"

        # Loot is a bonus on top of the fight — only rolls if the fight was won.
        if not result.get("run_over"):
            loot_result = resolve_explore_loot(template, choice)
            result["explore_loot"] = loot_result
            loot = loot_result.get("loot", {})
            if loot.get("type") == "gold":
                conn.execute("UPDATE base SET gold = gold + ? WHERE id = 1", (loot.get("amount", 0),))
                result["gold_gained"] = result.get("gold_gained", 0) + loot.get("amount", 0)
            elif loot.get("type") in ("materials", "rare_materials"):
                mats_row = conn.execute("SELECT materials FROM base WHERE id = 1").fetchone()
                current_mats = json.loads(mats_row["materials"]) if mats_row["materials"] else {}
                mat_name = loot.get("name") or loot.get("type", "materials")
                current_mats[mat_name] = current_mats.get(mat_name, 0) + loot.get("amount", 1)
                conn.execute("UPDATE base SET materials = ? WHERE id = 1", (json.dumps(current_mats),))
                result.setdefault("materials_gained", {})
                result["materials_gained"][mat_name] = result["materials_gained"].get(mat_name, 0) + loot.get("amount", 1)

        if not result.get("run_over") and data.floor_number > base_row["highest_floor"]:
            gems_reward = 500 if data.floor_number % 5 == 0 else 100
            conn.execute("UPDATE base SET highest_floor = ?, gems = gems + ? WHERE id = 1", (data.floor_number, gems_reward))
            result["gems_gained"] = gems_reward

    for hero_dict, is_sacrifice in pending_legacies:
        try:
            from services.portrait_cache import handle_fallen_portrait
            new_path = handle_fallen_portrait(hero_dict["id"], hero_dict.get("portrait_path"), is_sacrifice)
            hero_dict["portrait_path"] = new_path
        except Exception as e:
            print(f"Portrait cleanup error: {e}")
        try:
            from services.legacy_service import create_legacy
            create_legacy(hero_dict, is_sacrifice=is_sacrifice)
        except Exception as e:
            print(f"Legacy creation error: {e}")

    result["floor"] = data.floor_number
    return result
