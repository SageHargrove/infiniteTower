"""
Combat Service — Deterministic simulation with class effects, level scaling,
skills, fear mechanics, legacy bonuses, and bond effects.
"""
import random
import json
from dataclasses import dataclass, field
from services.class_service import apply_class_combat_modifiers
from services.level_service import apply_level_to_stats, talent_score, get_hero_star, max_skill_slots

@dataclass
class CombatUnit:
    id: int
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    speed: int
    morale: int
    stress: int
    trauma: int = 0
    hero_class: str = "Classless"
    is_hero: bool = True
    alive: bool = True
    is_ranged: bool = False
    is_aoe: bool = False
    has_construct: bool = False
    construct_active: bool = False
    crit_chance: float = 0.05
    dodge_chance: float = 0.0
    kills: int = 0
    fear_immune: bool = False
    fear_stunned: bool = False
    death_save: int = 0
    armor_pen: float = 0.0
    skills: list = field(default_factory=list)
    portrait_path: str = ""
    abilities: list = field(default_factory=list)
    used_abilities: set = field(default_factory=set)
    talent: float = 0.5
    regen_pct: float = 0.0
    hero_star: int = 1

    def __post_init__(self):
        self.log_name = self.name if self.is_hero else f"[{self.name}]"
        if self.has_construct:
            self.construct_active = True

# name, hp_m, def_m, spd_m, archetype — shared with services/portrait_cache.py
# so the enemy portrait library is pre-generated for exactly these types.
ENEMY_TYPES = [
    ("Corpse Rat", 1.0, 1.0, 1.5, "swarm"),
    ("Grave Scarab", 1.0, 1.0, 1.6, "swarm"),
    ("Carrion Bat", 0.9, 0.8, 1.9, "swarm"),
    ("Plague Crawler", 1.0, 1.0, 1.3, "pack"),
    ("Abyssal Spider", 1.0, 1.0, 1.4, "pack"),
    ("Rotting Ghoul", 1.1, 0.9, 1.2, "pack"),
    ("Hollow Knight", 1.2, 1.1, 0.9, "normal"),
    ("Bone Warden", 1.0, 1.3, 0.8, "normal"),
    ("Flame Wraith", 0.9, 0.6, 1.4, "normal"),
    ("Shriek Shade", 0.7, 0.5, 1.6, "normal"),
    ("Iron Revenant", 1.3, 1.4, 0.7, "normal"),
    ("Venom Stalker", 0.9, 0.8, 1.5, "normal"),
    ("Stone Golem", 1.5, 1.8, 0.5, "elite"),
    ("Dread Brute", 1.8, 1.2, 0.7, "elite"),
    ("Abyssal Lurker", 1.3, 0.9, 1.8, "elite"),
    ("Frost Wight", 1.4, 1.1, 0.9, "elite"),
    ("Obsidian Behemoth", 2.0, 1.6, 0.4, "elite"),
]

def make_enemies(floor_number: int, count: int = None, difficulty_mult: float = 1.0) -> list[CombatUnit]:
    """
    Generate enemies for a floor. Difficulty is purely a function of floor
    number — not the player's team strength. A 7★ team and a 1★ team face
    the identical floor 10 enemies.

    difficulty_mult scales the TOTAL threat of the encounter (not just enemy
    count) — a "weak" target against an elite archetype still comes out
    weaker even though elites can't drop below a count of 1; the shortfall
    that rounding count to an integer can't absorb gets folded into a stat
    correction instead. This is what lets a choice like "fight defensively"
    mean something consistent regardless of which archetype gets rolled,
    rather than just meaning "fewer enemies" (5 weak swarmers can be an
    easier fight than 1 elite — raw count alone doesn't capture that).
    """
    scale = 1 + (floor_number * 0.12)

    etype = random.choice(ENEMY_TYPES)
    name, hp_m, def_m, spd_m, archetype = etype

    # Apply archetype modifiers first — count/difficulty math below needs
    # the post-archetype numbers, not the raw per-monster base stats.
    atk_m = 1.0
    if archetype == "swarm":
        atk_m = 0.5
        hp_m *= 0.5
        def_m *= 0.3
    elif archetype == "pack":
        atk_m = 0.4
        hp_m *= 0.4
        def_m *= 0.4
    elif archetype == "elite":
        atk_m = 1.5
        hp_m *= 1.5
        def_m *= 1.5

    if count is None:
        # Reference count for this archetype at "normal" (1.0) difficulty —
        # the midpoint of what the old fixed ranges used to roll.
        if archetype == "swarm":
            base_count = 4.5
        elif archetype == "pack":
            base_count = 3.5
        elif archetype == "elite":
            base_count = 1.0
        else:  # normal
            base_count = (1 + min(3, 1 + floor_number // 10)) / 2

        if difficulty_mult == 1.0:
            count = max(1, round(random.uniform(base_count - 0.5, base_count + 0.5)))
        else:
            unit_power = hp_m * (atk_m + def_m)
            target_total_power = base_count * unit_power * difficulty_mult
            count = max(1, min(8, round(target_total_power / unit_power))) if unit_power > 0 else max(1, round(base_count))
            actual_total = count * unit_power
            # Rounding count to an integer (especially count=1 for elites)
            # leaves a gap between actual and target total power — close it
            # with a stat correction so the encounter's real difficulty.
            # Power is HP * (ATK+DEF) — a product of two corrected terms —
            # so the correction must be split via sqrt across them, or it
            # would double-count and land at correction^2 instead.
            stat_correction = (target_total_power / actual_total) if actual_total > 0 else 1.0
            half_correction = stat_correction ** 0.5
            hp_m *= half_correction
            atk_m *= half_correction
            def_m *= half_correction

    import os
    enemy_portrait_path = f"static/portraits/enemies/{name.lower().replace(' ', '_')}.png"
    if not os.path.exists(enemy_portrait_path):
        enemy_portrait_path = ""

    abilities = ["cleave"] if archetype == "elite" else []

    enemies = []
    for i in range(count):
        enemies.append(CombatUnit(
            id=-(i+1),
            name=f"{name} {i+1}" if count > 1 else name,
            hp=max(1, int(80 * scale * hp_m)), max_hp=max(1, int(80 * scale * hp_m)),
            attack=max(1, int(8 * scale * atk_m)), defense=int(5 * scale * def_m),
            speed=int(10 * scale * spd_m),
            morale=100, stress=0, is_hero=False,
            portrait_path=enemy_portrait_path,
            abilities=list(abilities),
        ))
    return enemies


_UNSET = object()

def make_boss(floor_number: int, zone_theme: str = "", is_miniboss: bool = False, boss_data_override=_UNSET) -> list[CombatUnit]:
    """Create a boss or miniboss enemy."""
    scale = 1 + (floor_number * 0.12)

    # Boss naming is pure flavor — never let it block combat resolution.
    # boss_data_override lets the caller pre-fetch this concurrently with the
    # zone theme call instead of sequentially after it (see tower.py) — if the
    # caller already tried and got nothing (timeout), trust that and use the
    # local fallback pool below instead of attempting a second, redundant
    # sequential LLM call here. Only attempt our own call if the caller never
    # tried pre-fetching at all (boss_data_override wasn't passed).
    boss_data = None if boss_data_override is _UNSET else boss_data_override
    if boss_data_override is _UNSET and zone_theme:
        from services.llm_service import generate_boss_enemy, call_with_timeout
        boss_data = call_with_timeout(generate_boss_enemy, zone_theme, floor_number, is_miniboss, timeout=1.5)

    if boss_data:
        name = boss_data.get("name", "Unknown Boss")
        mod = {
            "name": boss_data.get("modifier", "Enraged"),
            "hp": boss_data.get("hp_multiplier", 1.2),
            "atk": boss_data.get("atk_multiplier", 1.2),
            "def": boss_data.get("def_multiplier", 1.0),
            "spd": boss_data.get("spd_multiplier", 1.0)
        }
    else:
        boss_names = [
            "The Hollow King", "Dread Sentinel", "Abyssal Warden",
            "The Shattered One", "Lord of Ash", "The Undying",
            "Nightmare Colossus", "The Tower's Hunger",
        ]
        name = boss_names[min(len(boss_names) - 1, floor_number // 10 - 1)]
        boss_modifiers = [
            {"name": "Enraged", "atk": 1.5, "def": 0.7, "spd": 1.0, "hp": 1.0},
            {"name": "Armored", "atk": 1.0, "def": 2.0, "spd": 0.8, "hp": 1.0},
            {"name": "Colossal", "atk": 1.0, "def": 1.0, "spd": 0.7, "hp": 1.8},
            {"name": "Frenzied", "atk": 1.2, "def": 1.0, "spd": 1.5, "hp": 1.0},
            {"name": "Vampiric", "atk": 1.1, "def": 1.1, "spd": 1.1, "hp": 1.1},
            {"name": "Cursed", "atk": 1.3, "def": 0.8, "spd": 1.2, "hp": 0.9},
        ]
        mod = random.choice(boss_modifiers)

    if is_miniboss and not boss_data:
        name = f"Lieutenant of {name}"
    
    # Power curves were originally tuned far too aggressively (a floor-10
    # boss hit for ~106 base attack — a near-instant kill against an early
    # team's 80-170 HP heroes). Scaled down so a boss is a meaningfully
    # tougher single-target fight, not a one/two-shot machine.
    if is_miniboss:
        power = 1.5 + (floor_number / 40)
    else:
        power = 2.5 + (floor_number / 30)

    boss_title = f"{mod['name']} {name}"

    # Signature abilities by tier — minibosses get a recurring party-wide
    # threat (cleave) plus a one-time enrage; full bosses get two big
    # one-time swings instead (an early crushing blow, a late-game heal).
    abilities = ["cleave", "enrage"] if is_miniboss else ["crushing_blow", "last_stand"]

    from services.portrait_cache import get_random_boss_portrait
    boss = CombatUnit(
        id=-99, name=boss_title,
        hp=int(220 * scale * power * mod['hp']), max_hp=int(220 * scale * power * mod['hp']),
        attack=int(16 * scale * (power * 0.28) * mod['atk']), defense=int(12 * scale * (power * 0.35) * mod['def']),
        speed=int(8 * scale * mod['spd']),
        morale=100, stress=0, is_hero=False,
        portrait_path=get_random_boss_portrait(is_miniboss=is_miniboss),
        abilities=abilities,
    )
    return [boss]


def _fear_check(unit: CombatUnit, log: list) -> bool:
    """
    Check if a hero is paralyzed by fear this round.
    Based on trauma + stress levels.
    Returns True if the hero is fear-stunned.
    """
    if unit.fear_immune or not unit.is_hero:
        return False

    trauma = unit.trauma
    stress = unit.stress

    # Fear chance: 0% below 40 trauma, scales up
    if trauma < 40:
        return False
    elif trauma < 60:
        chance = 0.08 + (stress * 0.001)
    elif trauma < 80:
        chance = 0.15 + (stress * 0.002)
    else:
        chance = 0.25 + (stress * 0.003)

    if random.random() < chance:
        unit.fear_stunned = True
        fear_lines = [
            f"  ✗ {unit.name} freezes — the trauma overwhelms them.",
            f"  ✗ {unit.name}'s hands tremble. They cannot move.",
            f"  ✗ {unit.name} screams and covers their eyes. Fear takes hold.",
            f"  ✗ {unit.name} is paralyzed by terror. The memories are too much.",
        ]
        log.append(random.choice(fear_lines))
        return True

    return False


def calc_damage(attacker: CombatUnit, defender: CombatUnit) -> tuple[int, bool]:
    effective_def = defender.defense * (1 - attacker.armor_pen)
    base = attacker.attack * (100 / (100 + max(0, effective_def)))

    if attacker.is_hero and attacker.morale < 40:
        morale_factor = 0.5 + (attacker.morale / 80)
        base *= morale_factor

    variance = random.uniform(0.85, 1.15)
    damage = max(1, int(base * variance))

    is_crit = random.random() < attacker.crit_chance
    if is_crit:
        damage = int(damage * 1.8)

    return damage, is_crit


# Enemy signature abilities — elite/miniboss/boss tiers get 1-2 of these
# instead of just a plain basic attack every turn. "cleave" can recur each
# turn (chance-gated); the rest are one-time triggers gated on the
# attacker's own HP, tracked via used_abilities so they only fire once.
def _try_use_ability(attacker: CombatUnit, alive_heroes: list, log: list, morale_changes: dict, stress_changes: dict) -> bool:
    """Returns True if an ability fired this turn (attacker's normal attack
    is skipped), False to fall through to a normal attack."""
    hp_pct = attacker.hp / attacker.max_hp if attacker.max_hp else 0

    if "cleave" in attacker.abilities and random.random() < 0.20:
        log.append(f"  ⚔ {attacker.log_name} cleaves at the whole party!")
        for target in alive_heroes:
            damage, is_crit = calc_damage(attacker, target)
            damage = int(damage * 0.5)
            target.hp -= damage
            crit_text = " CRIT!" if is_crit else ""
            log.append(f"    → {target.log_name} takes {damage}{crit_text} [{max(0,target.hp)}/{target.max_hp}]")
            if target.hp <= 0:
                target.alive = False
                log.append(f"    ✦ {target.log_name} has fallen.")
                for h in alive_heroes:
                    if h.alive and h is not target:
                        morale_changes[h.id] = morale_changes.get(h.id, 0) - random.randint(8, 18)
                        stress_changes[h.id] = stress_changes.get(h.id, 0) + random.randint(5, 12)
        return True

    if "enrage" in attacker.abilities and "enrage" not in attacker.used_abilities and hp_pct < 0.5:
        attacker.used_abilities.add("enrage")
        attacker.attack = int(attacker.attack * 1.4)
        log.append(f"  ⚡ {attacker.log_name} flies into a rage! Attack sharply rises!")
        return False  # still takes a normal attack this turn, just buffed first

    if "crushing_blow" in attacker.abilities and "crushing_blow" not in attacker.used_abilities and hp_pct < 0.7 and alive_heroes:
        attacker.used_abilities.add("crushing_blow")
        target = max(alive_heroes, key=lambda h: h.hp)
        damage, is_crit = calc_damage(attacker, target)
        damage = int(damage * 2.2)
        target.hp -= damage
        log.append(f"  ☠ {attacker.log_name} unleashes a CRUSHING BLOW on {target.log_name} for {damage} damage! [{max(0,target.hp)}/{target.max_hp}]")
        if target.hp <= 0:
            target.alive = False
            log.append(f"    ✦ {target.log_name} has fallen.")
        return True

    if "last_stand" in attacker.abilities and "last_stand" not in attacker.used_abilities and hp_pct < 0.2:
        attacker.used_abilities.add("last_stand")
        heal = int(attacker.max_hp * 0.25)
        attacker.hp = min(attacker.max_hp, attacker.hp + heal)
        log.append(f"  ✚ {attacker.log_name} makes a last stand, recovering {heal} HP! [{attacker.hp}/{attacker.max_hp}]")
        return True

    return False

def run_combat(heroes: list[dict], floor_number: int, is_boss: bool = False, is_miniboss: bool = False, zone_theme: str = "", boss_data_override=_UNSET, enemy_count_override: int = None, difficulty_mult: float = 1.0) -> dict:
    log = []
    turns = []
    morale_changes = {h["id"]: 0 for h in heroes}
    kill_counts = {h["id"]: 0 for h in heroes}
    stress_changes = {h["id"]: 0 for h in heroes}

    # Apply level scaling → class modifiers → synergy → equipment → legacy bonuses → skill passives
    processed = []
    
    # Calculate synergies on active team
    synergy_counts = {}
    for h in heroes:
        sg = h.get("synergy_group")
        if sg:
            synergy_counts[sg] = synergy_counts.get(sg, 0) + 1
    # Fetch relics
    try:
        from services.relic_service import get_all_relics, apply_relic_stats
        relics = get_all_relics()
    except Exception:
        relics = []

    # Fetch bonds
    try:
        from services.bonds_service import get_team_bonds_multiplier
        hero_ids = [h["id"] for h in heroes]
        bond_totals = get_team_bonds_multiplier(hero_ids)
    except Exception:
        bond_totals = {h["id"]: 0 for h in heroes}

    # Pre-pass for support class buffs (Tactician, Scout, etc)
    team_atk_mult = 1.0
    team_def_mult = 1.0
    team_spd_mult = 1.0
    for h in heroes:
        mods = apply_class_combat_modifiers(h)
        if "team_atk_mult" in mods: team_atk_mult *= mods["team_atk_mult"]
        if "team_def_mult" in mods: team_def_mult *= mods["team_def_mult"]
        if "team_spd_mult" in mods: team_spd_mult *= mods["team_spd_mult"]

    for h in heroes:
        scaled = apply_level_to_stats(h)
        modified = apply_class_combat_modifiers(scaled)
        
        # Apply team class buffs
        if team_atk_mult > 1.0: modified["attack"] = int(modified["attack"] * team_atk_mult)
        if team_def_mult > 1.0: modified["defense"] = int(modified["defense"] * team_def_mult)
        if team_spd_mult > 1.0: modified["speed"] = int(modified["speed"] * team_spd_mult)
        
        # Apply synergy buff
        sg = modified.get("synergy_group")
        if sg and synergy_counts.get(sg, 0) > 1:
            multiplier = 1.0 + (0.05 * synergy_counts[sg])
            modified["max_hp"] = int(modified["max_hp"] * multiplier)
            modified["hp"] = modified["max_hp"]
            modified["attack"] = int(modified["attack"] * multiplier)
            modified["defense"] = int(modified["defense"] * multiplier)
            modified["speed"] = int(modified["speed"] * multiplier)

        # Apply equipment bonuses
        try:
            from services.equipment_service import apply_equipment_stats
            modified = apply_equipment_stats(modified)
        except Exception:
            pass

        # Apply legacy bonuses
        try:
            from services.legacy_service import apply_legacy_bonuses
            modified = apply_legacy_bonuses(modified)
        except Exception:
            pass
            
        # Apply relic stats
        if relics:
            modified = apply_relic_stats(modified, relics)
            
        # Apply Base Floor LP stats
        try:
            from services.base_service import get_floor_lp
            from database import db
            with db() as conn:
                lp_data = get_floor_lp(conn, modified.get("base_floor", 1))
                lp_mult = 1.0 + (lp_data["stat_bonus_pct"] / 100.0)
                modified["max_hp"] = int(modified["max_hp"] * lp_mult)
                modified["hp"] = min(modified["max_hp"], modified["hp"])
                modified["attack"] = int(modified["attack"] * lp_mult)
                modified["defense"] = int(modified["defense"] * lp_mult)
                modified["speed"] = int(modified["speed"] * lp_mult)
        except Exception:
            pass

        # Apply bond stats
        bond_lvl = bond_totals.get(modified["id"], 0)
        if bond_lvl > 0:
            bond_mult = 1.0 + (0.01 * bond_lvl)
            modified["max_hp"] = int(modified["max_hp"] * bond_mult)
            modified["hp"] = min(modified["max_hp"], modified["hp"])
            modified["attack"] = int(modified["attack"] * bond_mult)
            modified["defense"] = int(modified["defense"] * bond_mult)
            modified["speed"] = int(modified["speed"] * bond_mult)

        # Apply passive skills and traits
        if "skills" in h and h["skills"]:
            from services.skills_service import apply_passive_skills
            hero_skills = json.loads(h.get("skills", "[]")) if isinstance(h.get("skills"), str) else h.get("skills", [])
            modified = apply_passive_skills(modified, hero_skills)
            
        if "traits" in h and h["traits"]:
            from services.skills_service import apply_passive_skills
            hero_traits = json.loads(h.get("traits", "[]")) if isinstance(h.get("traits"), str) else h.get("traits", [])
            # Traits use the exact same effect dict structure as passive skills!
            modified = apply_passive_skills(modified, hero_traits)

        # Apply equipped relics (Seals/Runes) — same passive effect shape as skills
        from services.relics_service import get_hero_relics
        from services.skills_service import apply_passive_skills
        hero_relics = get_hero_relics(h["id"])
        if hero_relics:
            modified = apply_passive_skills(modified, hero_relics)
        modified["regen_pct"] = modified.get("regen_pct", 0.0)

        # Remove raw string payload to avoid confusion later, but keep as python list for UI/Combat logic if needed
        if "skills" in modified:
            modified["_skills"] = hero_skills if 'hero_skills' in locals() else []
            del modified["skills"]
        if "traits" in modified:
            modified["_traits"] = hero_traits if 'hero_traits' in locals() else []
            del modified["traits"]
        processed.append(modified)

    combatants_heroes = []
    construct_id = -100
    for h in processed:
        hero_unit = CombatUnit(
            id=h["id"], name=h["name"],
            hp=h["hp"], max_hp=h["max_hp"],
            attack=h["attack"], defense=h["defense"],
            speed=h["speed"], morale=h["morale"], stress=h["stress"],
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
        )
        combatants_heroes.append(hero_unit)
        
        # Summon construct if the hero has the has_construct flag
        if h.get("has_construct"):
            c_hp = int(h["max_hp"] * 1.5)
            c_atk = int(h["attack"] * 0.8)
            c_def = int(h["defense"] * 1.5)
            c_spd = int(h["speed"] * 0.7)
            construct_unit = CombatUnit(
                id=construct_id, name=f"{h['name']}'s Construct",
                hp=c_hp, max_hp=c_hp, attack=c_atk, defense=c_def, speed=c_spd,
                morale=100, stress=0, hero_class="Construct", fear_immune=True
            )
            combatants_heroes.append(construct_unit)
            construct_id -= 1
            log.append(f"  {hero_unit.name} deploys a massive Construct to the frontline!")

    # Generate enemies — difficulty is purely floor-based, not adaptive to team strength.
    if is_boss or is_miniboss:
        enemies = make_boss(floor_number, zone_theme, is_miniboss, boss_data_override=boss_data_override)
        log.append(f"🔥💀🔥 {'MINIBOSS' if is_miniboss else 'BOSS'} FLOOR {floor_number} 🔥💀🔥")
        log.append(f"  {enemies[0].name} emerges from the darkness.")
    else:
        enemies = make_enemies(floor_number, count=enemy_count_override, difficulty_mult=difficulty_mult)

    initial_state = {
        "is_boss": is_boss,
        "is_miniboss": is_miniboss,
        "heroes": [
            {"id": h.id, "name": h.name, "hero_class": h.hero_class, "max_hp": h.max_hp, "hp": h.hp, "portrait_path": h.portrait_path}
            for h in combatants_heroes
        ],
        "enemies": [
            {"id": e.id, "name": e.name, "max_hp": e.max_hp, "hp": e.hp, "portrait_path": e.portrait_path}
            for e in enemies
        ]
    }

    log.append(f"Floor {floor_number}: {len(combatants_heroes)} heroes vs {len(enemies)} enemies.")

    # Log class composition
    class_summary = ", ".join([f"{h.name}({h.hero_class})" for h in combatants_heroes])
    log.append(f"  Party: {class_summary}")

    # Explicit 2-Front, 3-Back Formation
    frontline = combatants_heroes[:2]
    backline  = combatants_heroes[2:]

    all_units = combatants_heroes + enemies
    max_rounds = 30
    
    damage_dealt_stats = {h.id: 0 for h in combatants_heroes}

    for round_num in range(1, max_rounds + 1):
        all_units.sort(key=lambda u: u.speed + random.uniform(0, 2), reverse=True)

        alive_heroes  = [u for u in combatants_heroes if u.alive]
        alive_enemies = [u for u in enemies if u.alive]
        if not alive_heroes or not alive_enemies:
            break

        # ─── Fear checks at start of each round ───
        for hero in alive_heroes:
            hero.fear_stunned = False  # Reset from last round
            _fear_check(hero, log)

        # ─── Relic/skill regen ticks ───
        for unit in alive_heroes + alive_enemies:
            if unit.regen_pct > 0 and unit.hp < unit.max_hp:
                heal = int(unit.max_hp * unit.regen_pct)
                unit.hp = min(unit.max_hp, unit.hp + heal)
                log.append(f"  ✚ {unit.log_name} regenerates {heal} HP [{unit.hp}/{unit.max_hp}]")

        alive_frontline = [h for h in frontline if h.alive]

        for attacker in all_units:
            if not attacker.alive:
                continue

            # Fear-stunned heroes skip their turn
            if attacker.is_hero and attacker.fear_stunned:
                stress_changes[attacker.id] = stress_changes.get(attacker.id, 0) + 5
                continue

            if attacker.is_hero:
                targets = [u for u in alive_enemies if u.alive]
                if not targets:
                    break

                if attacker.is_aoe:
                    # Mage hits all enemies
                    log.append(f"  ✦ {attacker.name} ({attacker.hero_class}) casts — hits all enemies!")
                    for target in targets:
                        damage, is_crit = calc_damage(attacker, target)
                        damage_dealt_stats[attacker.id] += damage
                        target.hp -= damage
                        crit_text = " CRIT!" if is_crit else ""
                        log_msg = f"    → {target.log_name} takes {damage}{crit_text} [{max(0,target.hp)}/{target.max_hp}]"
                        log.append(log_msg)
                        turns.append({"round": round_num, "attacker_id": attacker.id, "target_id": target.id, "damage": damage, "is_crit": is_crit, "target_hp": max(0, target.hp), "log": log_msg})
                        if target.hp <= 0:
                            target.alive = False
                            attacker.kills += 1
                            kill_counts[attacker.id] = kill_counts.get(attacker.id, 0) + 1
                            log.append(f"    ✦ {target.log_name} falls.")
                            for h in combatants_heroes:
                                if h.alive:
                                    morale_changes[h.id] = morale_changes.get(h.id, 0) + random.randint(2, 5)
                else:
                    alive_frontline_enemies = [e for e in enemies[:2] if e.alive]
                    alive_backline_enemies = [e for e in enemies[2:] if e.alive]
                    
                    if attacker.hero_class == "Assassin" and alive_backline_enemies:
                        target = random.choice(alive_backline_enemies)
                    else:
                        # Front-to-Back targeting for heroes
                        if alive_frontline_enemies:
                            # Match index or random frontliner
                            idx = combatants_heroes.index(attacker) % len(alive_frontline_enemies)
                            target = alive_frontline_enemies[idx]
                        elif alive_backline_enemies:
                            target = random.choice(alive_backline_enemies)
                        else:
                            continue

                    # Dodge check
                    if random.random() < target.dodge_chance and not attacker.is_hero:
                        log.append(f"  {target.name} dodges!")
                        continue

                    damage, is_crit = calc_damage(attacker, target)
                    damage_dealt_stats[attacker.id] += damage

                    # Construct absorbs first hit for Magic Engineer
                    if target.is_hero and target.has_construct and target.construct_active:
                        target.construct_active = False
                        log.append(f"  {target.name}'s construct absorbs the hit!")
                        continue

                    target.hp -= damage
                    crit_text = " CRIT!" if is_crit else ""
                    log_msg = f"  {attacker.log_name} hits {target.log_name} for {damage}{crit_text} [{max(0,target.hp)}/{target.max_hp}]"
                    log.append(log_msg)
                    turns.append({"round": round_num, "attacker_id": attacker.id, "target_id": target.id, "damage": damage, "is_crit": is_crit, "target_hp": max(0, target.hp), "log": log_msg})

                    if target.hp <= 0:
                        target.alive = False
                        attacker.kills += 1
                        kill_counts[attacker.id] = kill_counts.get(attacker.id, 0) + 1
                        log.append(f"  ✦ {target.log_name} falls.")
                        morale_changes[attacker.id] = morale_changes.get(attacker.id, 0) + random.randint(2, 5)

            else:
                if attacker.abilities:
                    alive_heroes_now = [h for h in combatants_heroes if h.alive]
                    if alive_heroes_now and _try_use_ability(attacker, alive_heroes_now, log, morale_changes, stress_changes):
                        continue  # ability replaced the normal attack this turn

                alive_frontline = [h for h in frontline if h.alive]
                alive_backline = [h for h in backline if h.alive]

                if alive_frontline:
                    idx = enemies.index(attacker) % len(alive_frontline)
                    target = alive_frontline[idx]
                elif alive_backline:
                    target = random.choice(alive_backline)
                else:
                    continue

                # Dodge check for thief
                if random.random() < target.dodge_chance:
                    log.append(f"  {target.name} dodges {attacker.log_name}'s attack!")
                    continue

                # Construct check
                if target.has_construct and target.construct_active:
                    target.construct_active = False
                    log.append(f"  {target.name}'s construct absorbs the hit!")
                    continue

                damage, is_crit = calc_damage(attacker, target)
                target.hp -= damage
                crit_text = " CRIT!" if is_crit else ""
                log_msg = f"  {attacker.log_name} hits {target.log_name} for {damage}{crit_text} [{max(0,target.hp)}/{target.max_hp}]"
                log.append(log_msg)
                turns.append({"round": round_num, "attacker_id": attacker.id, "target_id": target.id, "damage": damage, "is_crit": is_crit, "target_hp": max(0, target.hp), "log": log_msg})

                if target.hp <= 0:
                    # Death save check
                    if target.death_save > 0:
                        target.death_save -= 1
                        target.hp = 1
                        log.append(f"  ✦ {target.log_name} refuses to fall! (Undying Will)")
                        continue

                    target.alive = False
                    log.append(f"  ✦ {target.log_name} has fallen.")
                    # Witness death — morale crash + trauma spike + fear stress
                    for h in combatants_heroes:
                        if h.alive:
                            morale_changes[h.id] = morale_changes.get(h.id, 0) - random.randint(8, 18)
                            stress_changes[h.id] = stress_changes.get(h.id, 0) + random.randint(5, 12)
                            log.append(f"    {h.name}'s morale wavers...")

        alive_heroes  = [u for u in combatants_heroes if u.alive]
        alive_enemies = [u for u in enemies if u.alive]
        if not alive_heroes or not alive_enemies:
            break

    alive_heroes  = [u for u in combatants_heroes if u.alive]
    dead_heroes   = [u for u in combatants_heroes if not u.alive]
    heroes_won    = len(alive_heroes) > 0 and len([u for u in enemies if u.alive]) == 0

    if heroes_won:
        log.append(f"✓ Victory. {len(alive_heroes)} hero(es) survived.")
        if is_boss:
            log.append(f"  ═══ BOSS DEFEATED ═══")
        for h in alive_heroes:
            morale_changes[h.id] = morale_changes.get(h.id, 0) - random.randint(3, 10)
    else:
        log.append(f"✗ Defeat. All heroes fell on floor {floor_number}.")

    skill_upgrades = {}
    skills_learned = {}
    if heroes_won:
        for h in alive_heroes:
            for s in h.skills:
                if s.get("level", 1) >= 10:
                    # Chance to upgrade — talented heroes learn faster
                    base_chance = 0.20 if is_boss else 0.05
                    chance = base_chance * (0.6 + h.talent * 0.8)
                    if random.random() < chance:
                        tiers = ["Beginner", "Intermediate", "Advanced", "Legendary"]
                        current_tier = s.get("tier", "Beginner")
                        if current_tier in tiers:
                            idx = tiers.index(current_tier)
                            if idx < len(tiers) - 1:
                                new_tier = tiers[idx + 1]
                                skill_upgrades.setdefault(h.id, []).append({
                                    "skill_id": s["id"],
                                    "skill_name": s["name"],
                                    "new_tier": new_tier
                                })
                                log.append(f"  ✦ {h.name}'s {s['name']} ascended to {new_tier} tier!")

            # Chance to learn an entirely new skill — capacity grows with
            # star rank, but talent grows it further on top, so a highly
            # talented hero can out-learn a less-talented hero of the same
            # rarity over a long career.
            cap = max_skill_slots(h.hero_star, h.talent)
            if len(h.skills) < cap:
                base_chance = 0.10 if is_boss else 0.02
                chance = base_chance * (0.5 + h.talent * 1.5)
                if random.random() < chance:
                    from services.skills_service import get_skill_for_class
                    known_ids = {s["id"] for s in h.skills}
                    new_skill = get_skill_for_class(h.hero_class)
                    if new_skill and new_skill["id"] not in known_ids:
                        new_skill["tier"] = "Beginner"
                        new_skill["level"] = 1
                        new_skill["xp"] = 0
                        new_skill["max_xp"] = 100
                        skills_learned.setdefault(h.id, []).append(new_skill)
                        log.append(f"  ✦ {h.name} has learned a new skill: {new_skill['name']}!")

    result = {
        "winner": "heroes" if heroes_won else "enemies",
        "is_boss": is_boss,
        "initial_state": initial_state,
        "surviving_heroes": [
            {
                "id": h.id,
                "hp": max(0, h.hp),
                "morale_delta": morale_changes.get(h.id, 0),
                "kills_gained": kill_counts.get(h.id, 0),
                "stress_delta": stress_changes.get(h.id, 0),
            }
            for h in alive_heroes
        ],
        "dead_heroes": [h.id for h in dead_heroes],
        "skill_upgrades": skill_upgrades,
        "skills_learned": skills_learned,
        "log": log,
        "turns": turns,
        "rounds": round_num,
        "combat_metrics": damage_dealt_stats
    }

    if heroes_won:
        try:
            from database import db
            with db() as conn:
                base_info = conn.execute("SELECT global_buffs FROM base WHERE id = 1").fetchone()
                buffs = __import__('json').loads(base_info["global_buffs"] or "{}") if base_info else {}
            from services.equipment_service import generate_equipment_drop
            drop_bonus = buffs.get("drop_boost", 0) * 0.05
            equip = generate_equipment_drop(floor_number, is_boss, drop_bonus)
            if equip:
                result["equipment_drop"] = equip

            from services.relics_service import roll_relic_drop
            relic = roll_relic_drop(is_boss, is_miniboss, floor_number)
            if relic:
                result["relic_drop"] = relic

            # Guaranteed Drops
            result["gold_gained"] = int(300 * (1 + (floor_number/10)))
            result["supplies_gained"] = random.randint(2, 5)
            
            mats = ["Slime Core", "Iron Ore", "Goblin Ear", "Monster Bone", "Mystic Dust"]
            drops = {}
            for _ in range(random.randint(2, 4)):
                mat = random.choice(mats)
                drops[mat] = drops.get(mat, 0) + 1
            result["materials_gained"] = drops

            if is_boss:
                result["gold_gained"] += int(1500 * (1 + (floor_number/10)))
                result["supplies_gained"] += 10
                for _ in range(5):
                    mat = random.choice(mats)
                    drops[mat] = drops.get(mat, 0) + 1
                result["materials_gained"] = drops
        except Exception as e:
            print(f"Error generating drop: {e}")

    return result