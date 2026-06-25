"""
Morale System
=============
Morale (0-100): Current emotional state. Drops from death, combat, events.
Stress  (0-100): Accumulated tension. High stress degrades morale faster.
Trauma  (0-100): Deep damage. Reduces morale ceiling and recovery rate.

States:
  steady  (morale 70-100): Normal performance
  shaken  (morale 40-69):  -10% effectiveness, occasional hesitation
  fearful (morale 20-39):  -25% effectiveness, may flee or freeze
  broken  (morale 0-19):   -50% effectiveness, unreliable, may collapse

Recovery:
  Base recovery between floors: +10 morale
  Modified by trauma: high trauma = slow recovery
  Rest at base: larger recovery
"""

MORALE_STATES = [
    (70, "steady"),
    (40, "shaken"),
    (20, "fearful"),
    (0,  "broken"),
]

def get_morale_state(morale: int) -> str:
    for threshold, state in MORALE_STATES:
        if morale >= threshold:
            return state
    return "broken"

def apply_morale_delta(current_morale: int, trauma: int, delta: int) -> int:
    """Apply a morale change, capped by trauma ceiling."""
    trauma_ceiling = 100 - int(trauma * 0.4)  # high trauma limits max morale
    new_morale = current_morale + delta
    new_morale = max(0, min(trauma_ceiling, new_morale))
    return new_morale

def apply_stress(current_stress: int, amount: int) -> int:
    return max(0, min(100, current_stress + amount))

def apply_trauma(current_trauma: int, amount: int) -> int:
    return max(0, min(100, current_trauma + amount))

def between_floor_recovery(hero: dict) -> dict:
    """Called after each floor. Returns updated morale/stress values."""
    morale = hero["morale"]
    stress = hero["stress"]
    trauma = hero["trauma"]

    # Stress slowly reduces morale passively
    passive_drain = max(0, (stress - 40) // 10)  # only above stress threshold
    morale -= passive_drain

    # Base recovery
    recovery = 10 - int(trauma * 0.08)  # trauma slows recovery
    recovery = max(2, recovery)
    morale += recovery

    # Stress naturally decays slightly
    stress = max(0, stress - 3)

    # Clamp
    trauma_ceiling = 100 - int(trauma * 0.4)
    morale = max(0, min(trauma_ceiling, morale))

    return {
        "morale": morale,
        "stress": stress,
        "trauma": trauma,
        "morale_state": get_morale_state(morale),
    }

def witness_death_trauma(is_close_ally: bool = False, chapel_level: int = 0) -> dict:
    """Trauma from watching someone die. chapel_level is the Chapel
    base-upgrade's level (DEFAULT_UPGRADES in routers/base.py, "Reduce
    trauma buildup") — -12% trauma gained per level, stress is unaffected
    since the upgrade is specifically about trauma."""
    trauma_gain = (8 if is_close_ally else 4) * max(0.0, 1.0 - 0.12 * chapel_level)
    stress_gain = 15 if is_close_ally else 8
    return {"trauma_delta": round(trauma_gain), "stress_delta": stress_gain}

def rest_at_base_recovery(hero: dict, rest_quality: str = "normal", upgrade_level: int = 0) -> dict:
    """Returning to base gives more significant recovery.

    Psych-only — Rest no longer touches HP (lobby return already fully
    heals HP after every floor, see tower.py). Magnitude is intentionally
    modest: this represents just resting, not therapy, and the action is
    spammable on a short cooldown.

    upgrade_level is the Infirmary base-upgrade's level (DEFAULT_UPGRADES in
    routers/base.py, "Improve rest recovery rates") — +15% recovery per level."""
    quality_map = {"poor": 0.5, "normal": 1.0, "good": 1.5}
    factor = quality_map.get(rest_quality, 1.0) * (1.0 + 0.15 * upgrade_level)

    morale_gain = int(12 * factor)
    stress_loss = int(10 * factor)
    trauma_loss = int(2 * factor)  # trauma heals very slowly

    morale = min(100 - int(hero["trauma"] * 0.4), hero["morale"] + morale_gain)
    stress = max(0, hero["stress"] - stress_loss)
    trauma = max(0, hero["trauma"] - trauma_loss)

    return {
        "morale": morale,
        "stress": stress,
        "trauma": trauma,
        "morale_state": get_morale_state(morale),
    }
