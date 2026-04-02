from fastapi import APIRouter, HTTPException
from database import db
from services.combat_service import run_combat
from services.morale_service import between_floor_recovery, witness_death_trauma, get_morale_state, apply_morale_delta, apply_stress, apply_trauma
from services.llm_service import generate_combat_narration
import json
import random

router = APIRouter()

FLOOR_TYPES = {
    # (floor % 10) -> type
    0:  "boss",       # every 10
    5:  "miniboss",   # every 5
}

def get_floor_type(floor_number: int) -> str:
    mod = floor_number % 10
    if mod == 0:
        return "boss"
    elif mod == 5:
        return "miniboss"
    else:
        # Random weighted floor type
        return random.choices(
            ["combat", "combat", "combat", "event", "resource"],
            weights=[50, 50, 50, 25, 15]
        )[0]

@router.post("/run/start")
def start_run():
    """Start a new tower run with the current team."""
    with db() as conn:
        # Check for active run
        active = conn.execute(
            "SELECT id FROM runs WHERE status = 'active'"
        ).fetchone()
        if active:
            raise HTTPException(status_code=400, detail="A run is already active. Complete or abandon it first.")

        # Get team
        team = conn.execute(
            "SELECT * FROM heroes WHERE is_on_team = 1 AND is_alive = 1"
        ).fetchall()
        if not team:
            raise HTTPException(status_code=400, detail="No heroes on team. Set a team first.")
        if len(team) < 1:
            raise HTTPException(status_code=400, detail="Need at least 1 hero.")

        # Create run
        cursor = conn.execute("INSERT INTO runs (status, current_floor) VALUES ('active', 0)")
        run_id = cursor.lastrowid

        for hero in team:
            conn.execute(
                "INSERT INTO run_heroes (run_id, hero_id) VALUES (?,?)",
                (run_id, hero["id"])
            )

        conn.execute(
            "INSERT INTO event_log (run_id, floor_number, event_type, description) VALUES (?,?,?,?)",
            (run_id, 0, "run_start", f"A team of {len(team)} entered the tower.")
        )

    return {"run_id": run_id, "team_size": len(team)}

@router.get("/run/active")
def get_active_run():
    with db() as conn:
        run = conn.execute(
            "SELECT * FROM runs WHERE status = 'active'"
        ).fetchone()
        if not run:
            return {"run": None}

        run_dict = dict(run)
        heroes = conn.execute("""
            SELECT h.* FROM heroes h
            JOIN run_heroes rh ON h.id = rh.hero_id
            WHERE rh.run_id = ? AND h.is_alive = 1
        """, (run_dict["id"],)).fetchall()
        run_dict["heroes"] = [dict(h) for h in heroes]
    return {"run": run_dict}

@router.post("/run/floor/advance")
def advance_floor():
    """Resolve the next floor of the active run."""
    with db() as conn:
        run = conn.execute(
            "SELECT * FROM runs WHERE status = 'active'"
        ).fetchone()
        if not run:
            raise HTTPException(status_code=404, detail="No active run.")

        run_id = run["id"]
        next_floor = run["current_floor"] + 1
        floor_type = get_floor_type(next_floor)

        heroes = conn.execute("""
            SELECT h.* FROM heroes h
            JOIN run_heroes rh ON h.id = rh.hero_id
            WHERE rh.run_id = ? AND h.is_alive = 1
        """, (run_id,)).fetchall()

        if not heroes:
            # All heroes dead — end run
            conn.execute(
                "UPDATE runs SET status = 'failed', current_floor = ?, ended_at = CURRENT_TIMESTAMP WHERE id = ?",
                (next_floor - 1, run_id)
            )
            return {"result": "run_failed", "floor": next_floor - 1}

        hero_list = [dict(h) for h in heroes]

        result = {}
        narrative = None

        if floor_type in ("combat", "miniboss", "boss"):
            is_boss = floor_type == "boss"
            combat_result = run_combat(hero_list, next_floor, is_boss=is_boss)

            # Apply permadeath
            for dead_id in combat_result["dead_heroes"]:
                conn.execute(
                    "UPDATE heroes SET is_alive = 0, is_on_team = 0 WHERE id = ?",
                    (dead_id,)
                )
                # Trauma for surviving allies who witness death
                for surviving in combat_result["surviving_heroes"]:
                    trauma_data = witness_death_trauma(is_close_ally=True)
                    conn.execute("""
                        UPDATE heroes SET
                            trauma = MIN(100, trauma + ?),
                            stress = MIN(100, stress + ?)
                        WHERE id = ?
                    """, (trauma_data["trauma_delta"], trauma_data["stress_delta"], surviving["id"]))
                conn.execute(
                    "INSERT INTO event_log (run_id, floor_number, event_type, description) VALUES (?,?,?,?)",
                    (run_id, next_floor, "hero_death", f"Hero #{dead_id} has permanently fallen.")
                )

            # Apply HP and morale changes to survivors
            for s in combat_result["surviving_heroes"]:
                hero_row = conn.execute("SELECT * FROM heroes WHERE id = ?", (s["id"],)).fetchone()
                if hero_row:
                    hero_dict = dict(hero_row)
                    new_morale = apply_morale_delta(hero_dict["morale"], hero_dict["trauma"], s["morale_delta"])
                    conn.execute("""
                        UPDATE heroes SET hp = ?, morale = ?, morale_state = ? WHERE id = ?
                    """, (s["hp"], new_morale, get_morale_state(new_morale), s["id"]))

            # Apply between-floor recovery to all survivors
            surviving_ids = [s["id"] for s in combat_result["surviving_heroes"]]
            for hid in surviving_ids:
                hero_row = conn.execute("SELECT * FROM heroes WHERE id = ?", (hid,)).fetchone()
                if hero_row:
                    recovery = between_floor_recovery(dict(hero_row))
                    conn.execute("""
                        UPDATE heroes SET morale = ?, stress = ?, trauma = ?, morale_state = ? WHERE id = ?
                    """, (recovery["morale"], recovery["stress"], recovery["trauma"], recovery["morale_state"], hid))

            # LLM narration (cheap model, optional — won't block on failure)
            try:
                hero_names = [h["name"] for h in hero_list]
                narrative = generate_combat_narration(combat_result["log"], hero_names)
            except Exception as e:
                print(f"Narration failed: {e}")
                narrative = " ".join(combat_result["log"][-3:])

            result = {
                "floor_type": floor_type,
                "combat": combat_result,
                "narrative": narrative,
            }

        elif floor_type == "event":
            result = {
                "floor_type": "event",
                "message": "An event awaits. (Event system coming soon.)",
            }

        elif floor_type == "resource":
            gold_found = random.randint(20, 60) + next_floor * 2
            conn.execute("UPDATE base SET gold = gold + ? WHERE id = 1", (gold_found,))
            result = {
                "floor_type": "resource",
                "gold_found": gold_found,
                "message": f"The team found {gold_found} gold among the ruins.",
            }

        # Save floor record
        conn.execute("""
            INSERT INTO floors (run_id, floor_number, floor_type, status, outcome, narrative)
            VALUES (?,?,?,?,?,?)
        """, (run_id, next_floor, floor_type, "completed",
              json.dumps(result.get("combat", {}).get("log", [])), narrative))

        # Update run floor
        conn.execute(
            "UPDATE runs SET current_floor = ?, highest_floor = MAX(highest_floor, ?) WHERE id = ?",
            (next_floor, next_floor, run_id)
        )

        # Update hero stats, kills, floors_survived, and level after combat
        from services.level_service import recalculate_hero_level, level_up_summary
        for s in result.get("combat", {}).get("surviving_heroes", []):
            hid = s["id"]
            kills_gained = s.get("kills_gained", 0)
            conn.execute("""
                UPDATE heroes SET
                    floors_survived = floors_survived + 1,
                    kills = kills + ?
                WHERE id = ?
            """, (kills_gained, hid))

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
                    conn.execute("""
                        INSERT INTO event_log (run_id, floor_number, event_type, description)
                        VALUES (?,?,?,?)
                    """, (run_id, next_floor, "level_up",
                          f"{hero_dict['name']} reached level {new_level}.")  )

        # Auto-return to base every 10 floors
        if next_floor % 10 == 0 and result.get("combat", {}).get("winner") != "enemies":
            conn.execute(
                "UPDATE runs SET status = 'completed', ended_at = CURRENT_TIMESTAMP WHERE id = ?",
                (run_id,)
            )
            result["checkpoint"] = True
            result["message"] = f"Floor {next_floor} cleared. Return to base."

        # Check total failure
        remaining = conn.execute("""
            SELECT COUNT(*) as cnt FROM heroes h
            JOIN run_heroes rh ON h.id = rh.hero_id
            WHERE rh.run_id = ? AND h.is_alive = 1
        """, (run_id,)).fetchone()

        if remaining["cnt"] == 0:
            conn.execute(
                "UPDATE runs SET status = 'failed', ended_at = CURRENT_TIMESTAMP WHERE id = ?",
                (run_id,)
            )
            result["run_over"] = True

    result["floor"] = next_floor
    return result

@router.post("/run/abandon")
def abandon_run():
    with db() as conn:
        conn.execute(
            "UPDATE runs SET status = 'abandoned', ended_at = CURRENT_TIMESTAMP WHERE status = 'active'"
        )
    return {"ok": True}