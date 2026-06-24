"""
Resolves an Arena fight between two already-fully-resolved hero team
snapshots. Imports the real combat simulation from the main game's backend
(services/combat_service.py) instead of duplicating combat math — this
server only ever sees pre-computed hero stat dicts; it has no access to
either player's local save, equipment, relics, or bonds, so it can't (and
shouldn't try to) recompute anything. The player's own local backend
already ran that full pipeline once for a normal Tower floor; submitting a
team here just ships the same resulting dict over the wire.
"""
import os
import sys

# backend/ is a sibling directory, not an installed package — add it to the
# path so `from services.combat_service import ...` resolves the same way
# it does inside the main backend process.
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from services.combat_service import run_combat, CombatUnit, talent_score, get_hero_star  # noqa: E402


def _hero_dict_to_unit(h: dict) -> CombatUnit:
    """Mirrors the hero-side CombatUnit construction in
    combat_service.py's _resolve_combat_from_processed — same field
    mapping, but is_hero=False since this unit plays the "opponent" side
    via run_combat's preset_enemies hook."""
    return CombatUnit(
        id=h["id"], name=h["name"],
        level=h.get("level", 1),
        health=h["health"], max_health=h["max_health"],
        strength=h["strength"], intelligence=h["intelligence"],
        agility=h["agility"], morale=h.get("morale", 100), stress=h.get("stress", 0),
        defense=h.get("defense", 5), endurance=h.get("endurance", h.get("defense", 5)),
        willpower=h.get("willpower", 6), luck=h.get("luck", 5),
        power_stat=h.get("power_stat", "strength"),
        dmg_reduction_pct=h.get("dmg_reduction_pct", 0.0),
        trauma=h.get("trauma", 0),
        hero_class=h.get("hero_class", "Classless"),
        is_ranged=h.get("is_ranged", False),
        is_aoe=h.get("is_aoe", False),
        has_construct=h.get("has_construct", False),
        crit_chance=h.get("crit_chance", 0.05),
        dodge_chance=h.get("dodge_chance", 0.0),
        fear_immune=h.get("fear_immune", False),
        death_save=h.get("death_save", 0),
        armor_pen=h.get("armor_pen", 0.0),
        skills=h.get("_skills", []),
        portrait_path=h.get("portrait_path", ""),
        talent=talent_score(h),
        regen_pct=h.get("regen_pct", 0.0),
        hero_star=get_hero_star(h),
        battle_tendency=h.get("battle_tendency") or "Stoic",
        is_team_leader=bool(h.get("is_team_leader")),
        is_hero=False,
    )


def resolve_arena_fight(team_a: list[dict], team_b: list[dict]) -> dict:
    """team_a plays as "heroes", team_b as the preset "enemy" side. Returns
    the same result shape run_combat always returns (winner/log/turns/etc.),
    minus any Tower-specific economy fields — skip_stat_pipeline=True means
    _apply_combat_drops never runs, so no gold/materials/equipment_drop
    appears in the result."""
    opponent_units = [_hero_dict_to_unit(h) for h in team_b]
    return run_combat(team_a, floor_number=1, preset_enemies=opponent_units, skip_stat_pipeline=True)
