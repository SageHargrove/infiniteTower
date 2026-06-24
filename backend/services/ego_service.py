from database import db
import random

EGO_PATIENCE_DECAY = 15
EGO_PATIENCE_REGEN = 10
EGO_SATISFACTION_OVERLAP = 0.6  # fraction of the ideal picks that must be present
EGO_CONFLICT_DECAY_MULT = 1.5  # extra patience-decay multiplier for ego heroes who clash with the team Leader
EGO_CONFLICT_OVERLAP_THRESHOLD = 0.5

# A hero this much weaker (by _power_score) than the team's strongest member
# defers to them entirely — their own ego never asserts itself while a
# clearly superior teammate is around, the way a weaker fighter falls in
# line with whoever's obviously stronger in practice. Independent of the
# manually-assigned Leader tag — raw power earns this regardless of who's
# flagged as Leader.
EGO_DOMINANCE_MARGIN = 1.25

BATTLE_TENDENCIES = ["Reckless", "Calculating", "Protective", "Glory-Seeking", "Stoic", "Vengeful"]


FRONTLINE_CLASSES = {'Warrior', 'Spearman', 'Thief', 'Spellsword', 'Scout', 'Blacksmith', 'Farmer', 'Rogue', 'Paladin'}

def get_archetype(hero_class: str) -> str:
    if not hero_class or hero_class == 'Classless': return 'Wildcard'
    for fc in FRONTLINE_CLASSES:
        if fc in hero_class: return 'Frontline'
    return 'Backline'

def _ideal_team(ego_hero_id: int, ego_type: str, alive_heroes: list[dict]) -> list[int]:
    """Pure sort — given the candidate pool, return the ego hero's preferred
    5-hero team (themselves + their top 4 picks)."""
    candidates = [h for h in alive_heroes if h["id"] != ego_hero_id]
    ego_hero = next((h for h in alive_heroes if h["id"] == ego_hero_id), {})

    if ego_type == "Aggressive":
        candidates.sort(key=lambda h: (h["strength"] + h["agility"]), reverse=True)
    elif ego_type == "Cautious":
        candidates.sort(key=lambda h: (h["intelligence"] + h["max_health"] + (100 if h["hero_class"] in ["Cleric", "Paladin"] else 0)), reverse=True)
    elif ego_type == "Tactical":
        candidates.sort(key=lambda h: (h["level"], h["strength"] + h["intelligence"]), reverse=True)
        ego_arch = get_archetype(ego_hero.get("hero_class", ""))
        front_needed = 2 - (1 if ego_arch in ('Frontline', 'Wildcard') else 0)
        back_needed = 3 - (1 if ego_arch == 'Backline' else 0)
        
        team_picks = []
        for h in candidates:
            arch = get_archetype(h.get("hero_class", ""))
            if arch == 'Frontline' and front_needed > 0:
                team_picks.append(h["id"])
                front_needed -= 1
            elif arch == 'Backline' and back_needed > 0:
                team_picks.append(h["id"])
                back_needed -= 1
            elif arch == 'Wildcard':
                team_picks.append(h["id"])
                if front_needed > 0: front_needed -= 1
                else: back_needed -= 1
            if len(team_picks) == 4:
                break
        
        if len(team_picks) < 4:
            for h in candidates:
                if h["id"] not in team_picks:
                    team_picks.append(h["id"])
                    if len(team_picks) == 4: break
        return [ego_hero_id] + team_picks
    elif ego_type == "Leader":
        candidates.sort(key=lambda h: (h["level"], -h["apt_leadership"]))
    else:
        candidates.sort(key=lambda h: h["level"], reverse=True)

    return [ego_hero_id] + [h["id"] for h in candidates[:4]]


def _power_score(h: dict) -> float:
    """Rough current combat-power read, used only to decide ego dominance —
    not the same as talent_score (which is growth rate, not current power)."""
    return h.get("level", 1) * 20 + h.get("strength", 0) + h.get("intelligence", 0) + h.get("agility", 0) + h.get("endurance", 0)


def is_ego_dominated(ego_hero: dict, team_members: list[dict]) -> bool:
    """True if some other hero on the team is clearly the strongest — that
    alone is enough for ego_hero to defer, regardless of whether the lineup
    matches their own preferences."""
    others = [h for h in team_members if h["id"] != ego_hero["id"]]
    if not others:
        return False
    my_power = _power_score(ego_hero)
    best_other = max(_power_score(h) for h in others)
    return best_other >= my_power * EGO_DOMINANCE_MARGIN


def get_team_leader(team_members: list[dict]) -> dict | None:
    """Leader is a manual player assignment (heroes.is_team_leader), not computed.
    Any hero can be Leader; mechanical effects elsewhere only apply if they also
    have an ego_type — callers should check that explicitly."""
    return next((h for h in team_members if h.get("is_team_leader")), None)


def get_ego_conflicts(leader: dict | None, team_members: list[dict], alive_heroes: list[dict]) -> list[dict]:
    """Non-Leader ego heroes whose ideal team barely overlaps with the Leader's
    ideal team are 'in conflict' — they chafe under a vision that isn't theirs.
    Returns [] if there's no Leader or the Leader has no ego_type (a flavor-only
    Leader has no mechanical pull yet)."""
    if not leader or not leader.get("ego_type"):
        return []

    leader_ideal = set(_ideal_team(leader["id"], leader["ego_type"], alive_heroes))
    conflicts = []
    for h in team_members:
        if h["id"] == leader["id"] or not h.get("ego_type"):
            continue
        if is_ego_dominated(h, team_members):
            continue
        their_ideal = set(_ideal_team(h["id"], h["ego_type"], alive_heroes))
        overlap = len(leader_ideal & their_ideal) / max(1, len(leader_ideal))
        if overlap < EGO_CONFLICT_OVERLAP_THRESHOLD:
            conflicts.append({
                "hero_id": h["id"],
                "hero_name": h["name"],
                "leader_id": leader["id"],
                "leader_name": leader["name"],
                "overlap": round(overlap, 2),
            })
    return conflicts


def auto_assign_ego_team(ego_hero_id: int, team_id: int) -> list[int]:
    """
    Given an Ego Hero's ID, clear the current team and pick an optimal team
    based on their specific Ego Type.
    """
    with db() as conn:
        ego_hero = conn.execute("SELECT * FROM heroes WHERE id = ?", (ego_hero_id,)).fetchone()
        if not ego_hero:
            raise ValueError("Ego hero not found.")

        ego_type = ego_hero["ego_type"]
        if not ego_type:
            raise ValueError("Hero does not have an Ego.")

        alive_heroes = [dict(r) for r in conn.execute("SELECT * FROM heroes WHERE is_alive = 1").fetchall()]

    team = _ideal_team(ego_hero_id, ego_type, alive_heroes)

    # Save the new team
    with db() as conn:
        conn.execute("UPDATE heroes SET is_on_team = 0 WHERE is_on_team = ?", (team_id,))
        for idx, hid in enumerate(team):
            conn.execute("UPDATE heroes SET is_on_team = ?, team_position = ? WHERE id = ?", (team_id, idx, hid))
        conn.execute("UPDATE heroes SET ego_patience = 100 WHERE id = ?", (ego_hero_id,))

    return team


def get_ego_recommendation(ego_hero_id: int) -> dict:
    """Preview what team an ego hero would build, without applying it —
    lets the player see the recommendation before deciding whether to
    follow it or risk a rebellion."""
    with db() as conn:
        ego_hero = conn.execute("SELECT * FROM heroes WHERE id = ?", (ego_hero_id,)).fetchone()
        if not ego_hero or not ego_hero["ego_type"]:
            raise ValueError("Hero does not have an Ego.")
        alive_heroes = [dict(r) for r in conn.execute("SELECT * FROM heroes WHERE is_alive = 1").fetchall()]
        ideal = _ideal_team(ego_hero_id, ego_hero["ego_type"], alive_heroes)
        names = {h["id"]: h["name"] for h in alive_heroes}

    return {
        "ego_type": ego_hero["ego_type"],
        "ego_patience": ego_hero["ego_patience"],
        "recommended_team": [{"id": hid, "name": names.get(hid, "Unknown")} for hid in ideal],
    }


def check_ego_satisfaction(ego_hero: dict, team_members: list[dict], alive_heroes: list[dict]) -> bool:
    if is_ego_dominated(ego_hero, team_members):
        return True

    ego_type = ego_hero.get("ego_type")

    if ego_type == "Tactical":
        if len(team_members) < 5:
            return False
        fronts = backs = wilds = 0
        for h in team_members:
            arch = get_archetype(h.get("hero_class", ""))
            if arch == "Frontline": fronts += 1
            elif arch == "Backline": backs += 1
            else: wilds += 1
        needed_fronts = max(0, 2 - fronts)
        needed_backs = max(0, 3 - backs)
        return wilds >= (needed_fronts + needed_backs)
        
    elif ego_type == "Resonant":
        classes = [h.get("hero_class") for h in team_members if h.get("hero_class") != "Classless"]
        if not classes: return False
        return all(c == classes[0] for c in classes) and len(team_members) == 5

    current_ids = {h["id"] for h in team_members}
    ideal = _ideal_team(ego_hero["id"], ego_type, alive_heroes)
    overlap = len(set(ideal) & current_ids) / max(1, len(ideal))
    return overlap >= EGO_SATISFACTION_OVERLAP

def process_ego_patience(conn, team_id: int) -> list[dict]:
    """Called when a team enters a floor. Any ego-type hero on the team has
    their patience nudged toward (satisfied) or away from (ignored) zero
    based on whether the current lineup matches their preference. At zero,
    they take matters into their own hands and rebuild the team themselves.
    Returns a list of rebellion events (for the floor result/log)."""
    team_members = [dict(r) for r in conn.execute(
        "SELECT * FROM heroes WHERE is_on_team = ? AND is_alive = 1", (team_id,)
    ).fetchall()]
    ego_members = [h for h in team_members if h.get("ego_type")]
    if not ego_members:
        return []

    alive_heroes = [dict(r) for r in conn.execute("SELECT * FROM heroes WHERE is_alive = 1").fetchall()]

    leader = get_team_leader(team_members)
    conflicts = get_ego_conflicts(leader, team_members, alive_heroes)
    conflicted_ids = {c["hero_id"] for c in conflicts}

    rebellions = []
    for ego_hero in ego_members:
        satisfied = check_ego_satisfaction(ego_hero, team_members, alive_heroes)

        if satisfied:
            new_patience = min(100, ego_hero["ego_patience"] + EGO_PATIENCE_REGEN)
            conn.execute("UPDATE heroes SET ego_patience = ? WHERE id = ?", (new_patience, ego_hero["id"]))
        else:
            decay = EGO_PATIENCE_DECAY
            if ego_hero["id"] in conflicted_ids:
                decay = round(decay * EGO_CONFLICT_DECAY_MULT)
            new_patience = ego_hero["ego_patience"] - decay
            if new_patience <= 0:
                new_team = auto_assign_ego_team(ego_hero["id"], team_id)
                names = {h["id"]: h["name"] for h in alive_heroes}
                rebellions.append({
                    "hero_id": ego_hero["id"],
                    "hero_name": ego_hero["name"],
                    "ego_type": ego_hero["ego_type"],
                    "new_team": [names.get(hid, "Unknown") for hid in new_team],
                    "message": f"{ego_hero['name']}'s patience ran out — they reorganized Team {team_id} to their liking.",
                })
                # auto_assign_ego_team already reset this hero's patience to 100,
                # and may have changed who's even on the team — refresh the pool
                # so a later ego hero in this loop sees the new lineup.
                team_members = [dict(r) for r in conn.execute(
                    "SELECT * FROM heroes WHERE is_on_team = ? AND is_alive = 1", (team_id,)
                ).fetchall()]
                current_ids = {h["id"] for h in team_members}
            else:
                conn.execute("UPDATE heroes SET ego_patience = ? WHERE id = ?", (new_patience, ego_hero["id"]))

    return rebellions
