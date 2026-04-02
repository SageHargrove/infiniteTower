"""
Combat Service — Deterministic simulation with class effects and level scaling.
"""
import random
from dataclasses import dataclass, field
from services.class_service import apply_class_combat_modifiers
from services.level_service import apply_level_to_stats

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

    def __post_init__(self):
        self.log_name = self.name if self.is_hero else f"[{self.name}]"
        if self.has_construct:
            self.construct_active = True

def make_enemies(floor_number: int, count: int = None) -> list[CombatUnit]:
    scale = 1 + (floor_number * 0.08)
    if count is None:
        count = random.randint(1, min(4, 1 + floor_number // 5))

    enemy_types = [
        ("Hollow Knight", 1.2, 1.1, 0.9),
        ("Plague Crawler", 0.8, 0.7, 1.3),
        ("Stone Golem",    1.5, 1.8, 0.5),
        ("Shriek Shade",   0.7, 0.5, 1.6),
        ("Bone Warden",    1.0, 1.3, 0.8),
    ]

    enemies = []
    for i in range(count):
        etype = random.choice(enemy_types)
        name, hp_m, def_m, spd_m = etype
        enemies.append(CombatUnit(
            id=-(i+1), name=name,
            hp=int(80 * scale * hp_m), max_hp=int(80 * scale * hp_m),
            attack=int(8 * scale), defense=int(5 * scale * def_m),
            speed=int(10 * scale * spd_m),
            morale=100, stress=0, is_hero=False,
        ))
    return enemies

def calc_damage(attacker: CombatUnit, defender: CombatUnit) -> tuple[int, bool]:
    base = attacker.attack * (100 / (100 + defender.defense))

    if attacker.is_hero and attacker.morale < 40:
        morale_factor = 0.5 + (attacker.morale / 80)
        base *= morale_factor

    variance = random.uniform(0.85, 1.15)
    damage = max(1, int(base * variance))

    is_crit = random.random() < attacker.crit_chance
    if is_crit:
        damage = int(damage * 1.8)

    return damage, is_crit

def run_combat(heroes: list[dict], floor_number: int, is_boss: bool = False) -> dict:
    log = []
    morale_changes = {h["id"]: 0 for h in heroes}
    kill_counts = {h["id"]: 0 for h in heroes}

    # Apply level scaling then class modifiers
    processed = []
    for h in heroes:
        scaled = apply_level_to_stats(h)
        modified = apply_class_combat_modifiers(scaled)
        processed.append(modified)

    combatants_heroes = [
        CombatUnit(
            id=h["id"], name=h["name"],
            hp=h["hp"], max_hp=h["max_hp"],
            attack=h["attack"], defense=h["defense"],
            speed=h["speed"], morale=h["morale"], stress=h["stress"],
            hero_class=h.get("hero_class", "Classless"),
            is_ranged=h.get("is_ranged", False),
            is_aoe=h.get("is_aoe", False),
            has_construct=h.get("has_construct", False),
            crit_chance=h.get("crit_chance", 0.05),
            dodge_chance=h.get("dodge_chance", 0.0),
        )
        for h in processed
    ]

    enemy_count = 1 if is_boss else None
    enemies = make_enemies(floor_number, count=enemy_count)
    if is_boss:
        for e in enemies:
            e.hp = int(e.hp * 2.5)
            e.max_hp = e.hp
            e.attack = int(e.attack * 2)
            e.name = f"BOSS: {e.name}"
            e.log_name = f"[{e.name}]"

    log.append(f"Floor {floor_number}: {len(combatants_heroes)} heroes vs {len(enemies)} enemies.")

    # Log class composition
    class_summary = ", ".join([f"{h.name}({h.hero_class})" for h in combatants_heroes])
    log.append(f"  Party: {class_summary}")

    # Check for ranged heroes — they attack from backline
    frontline = [h for h in combatants_heroes if not h.is_ranged]
    backline  = [h for h in combatants_heroes if h.is_ranged]
    if backline:
        log.append(f"  Archers in backline: {', '.join(h.name for h in backline)}")

    all_units = combatants_heroes + enemies
    max_rounds = 30

    for round_num in range(1, max_rounds + 1):
        all_units.sort(key=lambda u: u.speed + random.uniform(0, 2), reverse=True)

        alive_heroes  = [u for u in combatants_heroes if u.alive]
        alive_enemies = [u for u in enemies if u.alive]
        if not alive_heroes or not alive_enemies:
            break

        alive_frontline = [h for h in frontline if h.alive]

        for attacker in all_units:
            if not attacker.alive:
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
                        target.hp -= damage
                        crit_text = " CRIT!" if is_crit else ""
                        log.append(f"    → {target.log_name} takes {damage}{crit_text} [{max(0,target.hp)}/{target.max_hp}]")
                        if target.hp <= 0:
                            target.alive = False
                            attacker.kills += 1
                            kill_counts[attacker.id] = kill_counts.get(attacker.id, 0) + 1
                            log.append(f"    ✦ {target.log_name} falls.")
                            for h in combatants_heroes:
                                if h.alive:
                                    morale_changes[h.id] = morale_changes.get(h.id, 0) + random.randint(2, 5)
                else:
                    target = min(targets, key=lambda u: u.hp)

                    # Dodge check
                    if random.random() < attacker.dodge_chance and not attacker.is_hero:
                        log.append(f"  {attacker.name} dodges!")
                        continue

                    damage, is_crit = calc_damage(attacker, target)

                    # Construct absorbs first hit for Magic Engineer
                    if target.is_hero and target.has_construct and target.construct_active:
                        target.construct_active = False
                        log.append(f"  {target.name}'s construct absorbs the hit!")
                        continue

                    target.hp -= damage
                    crit_text = " CRIT!" if is_crit else ""
                    log.append(f"  {attacker.log_name} hits {target.log_name} for {damage}{crit_text} [{max(0,target.hp)}/{target.max_hp}]")

                    if target.hp <= 0:
                        target.alive = False
                        attacker.kills += 1
                        kill_counts[attacker.id] = kill_counts.get(attacker.id, 0) + 1
                        log.append(f"  ✦ {target.log_name} falls.")
                        morale_changes[attacker.id] = morale_changes.get(attacker.id, 0) + random.randint(2, 5)

            else:
                # Enemy targeting — ranged heroes protected while frontline alive
                alive_frontline = [h for h in frontline if h.alive]
                if alive_frontline:
                    valid_targets = alive_frontline
                else:
                    valid_targets = [h for h in combatants_heroes if h.alive]

                if not valid_targets:
                    break

                target = min(valid_targets, key=lambda u: u.hp)

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
                log.append(f"  {attacker.log_name} hits {target.log_name} for {damage}{crit_text} [{max(0,target.hp)}/{target.max_hp}]")

                if target.hp <= 0:
                    target.alive = False
                    log.append(f"  ✦ {target.log_name} has fallen.")
                    for h in combatants_heroes:
                        if h.alive:
                            morale_changes[h.id] = morale_changes.get(h.id, 0) - random.randint(8, 18)
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
        for h in alive_heroes:
            morale_changes[h.id] = morale_changes.get(h.id, 0) - random.randint(3, 10)
    else:
        log.append(f"✗ Defeat. All heroes fell on floor {floor_number}.")

    return {
        "winner": "heroes" if heroes_won else "enemies",
        "surviving_heroes": [
            {
                "id": h.id,
                "hp": max(0, h.hp),
                "morale_delta": morale_changes.get(h.id, 0),
                "kills_gained": kill_counts.get(h.id, 0),
            }
            for h in alive_heroes
        ],
        "dead_heroes": [h.id for h in dead_heroes],
        "log": log,
        "rounds": round_num,
    }