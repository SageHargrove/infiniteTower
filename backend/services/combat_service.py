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
    health: int
    max_health: int
    strength: int
    intelligence: int
    agility: int
    morale: int
    stress: int
    defense: int = 5  # legacy mirror of endurance, kept for any stale readers
    endurance: int = 5  # replaces defense as the real mitigation stat — also drove this unit's max_health upstream
    willpower: int = 6  # fear/panic resistance, see _panic_check
    luck: int = 5  # combat/exploration drop-rate bonus, applied at the team-average level, not per-unit
    power_stat: str = "strength"  # which stat drives this unit's attack damage
    dmg_reduction_pct: float = 0.0  # flat % mitigation from equipped gear, applied after Defense
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
    level: int = 1
    battle_tendency: str = "Stoic"
    is_team_leader: bool = False
    isolated_rounds: int = 0   # Reckless panic response — exposed, takes bonus damage, preferred enemy target
    bracing_rounds: int = 0    # Calculating panic response — forgoes their strength to brace defensively
    spawn_template: str = ""  # name of the weak add this unit's "summon_add" ability spawns, if any
    summons_used: int = 0     # caps "summon_add" so a miniboss/boss can't stall a fight forever
    used_consumable: bool = False  # caps the shared Potion/Scroll backpack to one sip per hero per fight

    def __post_init__(self):
        self.log_name = self.name if self.is_hero else f"[{self.name}]"
        if self.has_construct:
            self.construct_active = True

# name, hp_m, def_m, spd_m, archetype, tier — shared with services/portrait_cache.py
# so the enemy portrait library is pre-generated for exactly these types.
# "archetype" (swarm/pack/normal/elite) drives count/difficulty math in
# _build_enemy_group; "tier" is a separate floor-gate (see ENEMY_TIER_FLOORS
# below) so a floor-2 fight can't roll something named like an end-game
# threat — the original 17 monster types (all undead/horror-flavored) read
# fine as "advanced"/"legendary" content but were previously available from
# floor 1, which is why early fights felt over-tuned in theme even when the
# raw stats were scaled down to match.
ENEMY_TYPES = [
    # --- beginner (floor 1+) ---
    ("Giant Rat", 0.8, 0.8, 1.6, "swarm", "beginner"),
    ("Goblin", 0.8, 0.7, 1.1, "normal", "beginner"),
    ("Bandit", 0.9, 0.8, 1.2, "normal", "beginner"),
    ("Wolf", 0.9, 0.7, 1.5, "pack", "beginner"),
    ("Slime", 0.6, 0.5, 0.7, "swarm", "beginner"),
    # Elite variants of the floor 1-10 family (Slime/Goblin/Rat/Wolf) — same
    # species, better stats, one extra ability via ENEMY_ABILITY_OVERRIDES
    # below. See backend/services/enemy_families.py for the matching
    # miniboss/boss tier for this floor range.
    ("Acid Slime", 1.1, 0.9, 0.7, "elite", "beginner"),
    ("Goblin Warrior", 1.2, 1.1, 1.0, "elite", "beginner"),
    ("Goblin Shaman", 1.0, 0.8, 1.0, "elite", "beginner"),
    ("Giant Rat Alpha", 1.1, 0.8, 1.7, "elite", "beginner"),
    ("Wolf Alpha", 1.2, 0.9, 1.6, "elite", "beginner"),
    # --- intermediate (floor 15+) ---
    ("Dire Wolf", 1.1, 0.9, 1.6, "pack", "intermediate"),
    ("Orc", 1.1, 1.0, 0.9, "normal", "intermediate"),
    ("Harpy", 0.8, 0.6, 1.8, "pack", "intermediate"),
    ("Ogre", 1.6, 1.3, 0.6, "elite", "intermediate"),
    ("Troll", 1.7, 1.0, 0.6, "elite", "intermediate"),
    # --- advanced (floor 40+) ---
    ("Grave Scarab", 1.0, 1.0, 1.6, "swarm", "advanced"),
    ("Rotting Ghoul", 1.1, 0.9, 1.2, "pack", "advanced"),
    ("Bone Warden", 1.0, 1.3, 0.8, "normal", "advanced"),
    # --- legendary (floor 70+) ---
    ("Stone Golem", 1.5, 1.8, 0.5, "elite", "legendary"),
    ("Dread Brute", 1.8, 1.2, 0.7, "elite", "legendary"),
    ("Abyssal Lurker", 1.3, 0.9, 1.8, "elite", "legendary"),
    ("Frost Wight", 1.4, 1.1, 0.9, "elite", "legendary"),
    ("Obsidian Behemoth", 2.0, 1.6, 0.4, "elite", "legendary"),
    ("Shrouded Reaper", 1.3, 1.0, 1.3, "elite", "legendary"),
]

ENEMY_TIER_UNLOCK_FLOOR = {"beginner": 1, "intermediate": 15, "advanced": 40, "legendary": 70}

# Purely organizational — which "waveN" review subfolder each named enemy's
# portrait lives in under enemies/<tier>/waveN/ (see _enemy_portrait_path and
# portrait_cache.py's generation functions, both of which consult this so a
# deleted portrait regenerates back into the same wave folder instead of the
# flat tier root). Has no effect on which floors an enemy actually spawns on
# — that's still ENEMY_TIER_UNLOCK_FLOOR — this just keeps the art library
# reviewable in the same batches you're already going through it in.
ENEMY_WAVE = {
    "Slime": 1, "Goblin": 1, "Giant Rat": 1, "Wolf": 1,
    "Acid Slime": 1, "Goblin Warrior": 1, "Goblin Shaman": 1, "Giant Rat Alpha": 1, "Wolf Alpha": 1,
    "Bandit": 2, "Dire Wolf": 2, "Harpy": 2, "Orc": 2, "Ogre": 2, "Troll": 2,
    "Grave Scarab": 4, "Rotting Ghoul": 4, "Bone Warden": 4,
    "Stone Golem": 6, "Obsidian Behemoth": 6, "Dread Brute": 6,
    "Abyssal Lurker": 7, "Frost Wight": 7, "Shrouded Reaper": 7,
}

# Per-name ability overrides — lets a specific elite/miniboss/boss entry use
# a different signature ability (or combo) than the blanket "elite archetype
# always gets cleave" default in _build_enemy_group. This is the "reusable
# mechanic library" the enemy-roster plan asked for: summon_add, team_buff_aura
# and self_regen are all generic, family-agnostic mechanics any future named
# enemy can be wired into just by adding an entry here (or to a family's
# elites list in enemy_families.py) — no new per-monster code needed.
ENEMY_ABILITY_OVERRIDES = {
    "Acid Slime": ["self_regen"],
    "Goblin Warrior": ["cleave"],
    "Goblin Shaman": ["team_buff_aura"],
    "Giant Rat Alpha": ["summon_add"],
    "Wolf Alpha": ["enrage"],
}

# Which weak swarm-type a "summon_add" user calls in as reinforcements.
ENEMY_SPAWN_TEMPLATE = {
    "Giant Rat Alpha": "Giant Rat",
}

SELF_REGEN_PCT = 0.06  # per-round Health regen granted by the "self_regen" ability
REVIVE_ALLY_HP_PCT = 0.4  # Health a "revive_ally" user brings a fallen ally back at, once per battle

# Potions/Scrolls are a shared base-wide "backpack," not a per-hero item
# slot — a hero who drops below this much Health drinks the best available
# healing-capable one at their own discretion, once per hero per fight, so
# one bad floor doesn't drain the whole shared stock on a single hero.
CONSUMABLE_LOW_HP_THRESHOLD = 0.35

def _enemy_pool_for_floor(floor_number: int) -> list[tuple]:
    """Every tier unlocked at or below this floor stays available — a
    floor-80 fight can still roll a Goblin, it's just no longer ONLY
    Goblins. Mirrors services/materials_service.py's tiered drop gating."""
    return [e for e in ENEMY_TYPES if floor_number >= ENEMY_TIER_UNLOCK_FLOOR[e[5]]]

def _build_enemy_group(etype, floor_number: int, difficulty_mult: float, id_start: int, count_override: int = None, max_count_override: int = None) -> list[CombatUnit]:
    """Build one monster type's portion of an encounter. Pulled out of
    make_enemies so a mixed encounter (two archetypes sharing one fight) can
    call this twice with a split difficulty_mult budget instead of duplicating
    the count/stat math. id_start offsets negative CombatUnit ids so two
    groups in the same encounter never collide."""
    scale = 1 + (floor_number * 0.12)
    name, hp_m, def_m, spd_m, archetype, _tier = etype

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

    if archetype == "swarm":
        base_count = 8.0
    elif archetype == "pack":
        base_count = 3.5
    elif archetype == "elite":
        base_count = 1.0
    else:  # normal
        base_count = (1 + min(3, 1 + floor_number // 10)) / 2

    # Survival Floor swarms intentionally blow past the normal per-archetype
    # cap below (max_count_override) — "countless" only reads as countless
    # next to the regular swarm's 20-unit ceiling.
    max_count = max_count_override or {"swarm": 20, "pack": 10, "elite": 3}.get(archetype, 8)

    if count_override is not None:
        count = max(1, min(max_count, count_override))
    elif difficulty_mult == 1.0:
        count = max(1, min(max_count, round(random.uniform(base_count - 0.5, base_count + 0.5))))
    else:
        unit_power = hp_m * (atk_m + def_m)
        target_total_power = base_count * unit_power * difficulty_mult
        count = max(1, min(max_count, round(target_total_power / unit_power))) if unit_power > 0 else max(1, round(base_count))
        actual_total = count * unit_power
        # Rounding count to an integer (especially count=1 for elites)
        # leaves a gap between actual and target total power — close it
        # with a stat correction so the encounter's real difficulty.
        # Power is Health * (ATK+DEF) — a product of two corrected terms —
        # so the correction must be split via sqrt across them, or it
        # would double-count and land at correction^2 instead.
        stat_correction = (target_total_power / actual_total) if actual_total > 0 else 1.0
        half_correction = stat_correction ** 0.5
        hp_m *= half_correction
        atk_m *= half_correction
        def_m *= half_correction

    enemy_portrait_path = _enemy_portrait_path(name, "elite" if archetype == "elite" else "")

    abilities = ENEMY_ABILITY_OVERRIDES.get(name) or (["cleave"] if archetype == "elite" else [])
    spawn_template = ENEMY_SPAWN_TEMPLATE.get(name, "")
    regen_pct = SELF_REGEN_PCT if "self_regen" in abilities else 0.0
    # Enemy "level" is purely a flavor readout matching floor depth (elites
    # read a little tougher than their floor) — it doesn't feed back into
    # their actual stats, which are already fully determined by hp_m/atk_m/
    # def_m above. Duplicates in an encounter now share one name + level tag
    # ("Rotting Ghoul [Lv 12]") instead of being numbered 1/2/3.
    enemy_level = max(1, floor_number + (3 if archetype == "elite" else 0))

    enemies = []
    for i in range(count):
        enemies.append(CombatUnit(
            id=-(id_start + i + 1),
            name=name,
            level=enemy_level,
            health=max(1, int(80 * scale * hp_m)), max_health=max(1, int(80 * scale * hp_m)),
            strength=max(1, int(8 * scale * atk_m)), intelligence=0, defense=int(5 * scale * def_m),
            endurance=int(5 * scale * def_m),
            agility=int(10 * scale * spd_m),
            morale=100, stress=0, is_hero=False,
            portrait_path=enemy_portrait_path,
            abilities=list(abilities),
            spawn_template=spawn_template,
            regen_pct=regen_pct,
        ))
    return enemies


def _make_swarm_add(name: str, floor_number: int, unit_id: int) -> CombatUnit:
    """Builds a single weak swarm-tier add for a 'summon_add' ability —
    reuses the same swarm archetype math _build_enemy_group applies (0.5x
    atk/hp, 0.3x def) but as a standalone unit rather than a whole group, and
    based off floor depth rather than the summoner's own (much stronger)
    stats, so reinforcements read as "more chip damage," not a second boss."""
    scale = 1 + (floor_number * 0.12)
    portrait_path = _enemy_portrait_path(name)
    return CombatUnit(
        id=-unit_id, name=name, level=max(1, floor_number),
        health=max(1, int(80 * scale * 0.5)), max_health=max(1, int(80 * scale * 0.5)),
        strength=max(1, int(8 * scale * 0.5)), intelligence=0,
        defense=int(5 * scale * 0.3), endurance=int(5 * scale * 0.3),
        agility=int(10 * scale * 1.2),
        morale=100, stress=0, is_hero=False, portrait_path=portrait_path,
    )


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
    pool = _enemy_pool_for_floor(floor_number)
    etype = random.choice(pool)

    # Mixed encounters (two different monster types in one fight) are now
    # the default flavor for common floors — splits the same difficulty
    # budget across two archetypes instead of always rolling one. Skipped
    # when the caller passed an explicit count (survival-floor overrides
    # etc. want one clean group, not a fractional split of a fixed number).
    if count is None and random.random() < 0.45:
        other_types = [e for e in pool if e[0] != etype[0]]
        etype2 = random.choice(other_types)
        split = random.uniform(0.35, 0.65)
        group1 = _build_enemy_group(etype, floor_number, difficulty_mult * split, id_start=0)
        group2 = _build_enemy_group(etype2, floor_number, difficulty_mult * (1 - split), id_start=len(group1))
        return group1 + group2

    return _build_enemy_group(etype, floor_number, difficulty_mult, id_start=0, count_override=count)


# Survival Floor (Boss Swarm) — an alternative to the typical single strong
# miniboss on a %5 floor: instead of one tough unique, the floor throws an
# "overwhelming swarm" the team can't realistically kill in time. Distinct
# from make_enemies' regular swarm archetype (capped at 20, plain
# kill-them-all win condition) — this is specifically the "countless, just
# survive the clock" framing, so it spawns far more bodies than any normal
# combat floor would, plus 1-2 genuinely dangerous Elites mixed in so the
# fight isn't pure chip damage.
SURVIVAL_SWARM_COUNT_RANGE = (30, 50)
SURVIVAL_SWARM_ELITE_COUNT_RANGE = (1, 2)

def make_swarm_miniboss_encounter(floor_number: int) -> list[CombatUnit]:
    """Builds the enemy roster for a Survival Floor miniboss encounter."""
    pool = _enemy_pool_for_floor(floor_number)
    swarm_types = [e for e in pool if e[4] in ("swarm", "pack")] or pool
    elite_types = [e for e in pool if e[4] == "elite"]

    swarm_etype = random.choice(swarm_types)
    swarm_count = random.randint(*SURVIVAL_SWARM_COUNT_RANGE)
    enemies = _build_enemy_group(swarm_etype, floor_number, difficulty_mult=1.0, id_start=0,
                                  count_override=swarm_count, max_count_override=swarm_count)

    if elite_types:
        elite_count = random.randint(*SURVIVAL_SWARM_ELITE_COUNT_RANGE)
        elite_etype = random.choice(elite_types)
        elites = _build_enemy_group(elite_etype, floor_number, difficulty_mult=1.0, id_start=len(enemies),
                                     count_override=elite_count, max_count_override=elite_count)
        enemies += elites

    return enemies


# Survival Floor pacing — "illusion of neverending" means the swarm doesn't
# realistically die before the clock does. 10 rounds (vs. the normal 30-round
# safety cap) keeps a fight long enough to feel like an onslaught without
# dragging a single floor entry on forever. Confirmed scope: this is a random
# *alternative* on miniboss floors only (floor % 5 == 0, not % 10) — it does
# not replace every miniboss encounter, and never appears on regular combat
# or boss floors.
SURVIVAL_TURN_LIMIT = 10
SWARM_SURVIVAL_CHANCE = 0.35

_UNSET = object()

def _enemy_portrait_path(name: str, subfolder: str = "") -> str:
    """Looks up a dedicated portrait for a named enemy — checked under
    enemies/<subfolder>/<slug>.png first (the per-tier folders the enemy
    roster overhaul plan asked for: elite/miniboss/boss/raid_boss), then
    enemies/normal/<slug>.png (where every plain-tier enemy's art now
    lives), then the flat enemies/<slug>.png used by the pre-reorg roster
    for anything not yet moved, then "" (frontend already renders a
    placeholder for that, same as any as-yet-unportraited enemy like
    Goblin/Wolf today).

    Within each tier folder, files may also sit one level deeper in a
    "waveN" subfolder (purely organizational, for reviewing a floor-range
    family's art together — e.g. enemies/normal/wave1/slime.png) — checked
    after the tier folder's own root so moving a file into a wave folder
    for review never breaks the lookup."""
    import os, glob
    slug = name.lower().replace(' ', '_')
    for sf in filter(None, [subfolder, "normal"]):
        tiered = f"static/portraits/enemies/{sf}/{slug}.png"
        if os.path.exists(tiered):
            return tiered
        wave_matches = glob.glob(f"static/portraits/enemies/{sf}/wave*/{slug}.png")
        if wave_matches:
            return wave_matches[0].replace("\\", "/")
    flat = f"static/portraits/enemies/{slug}.png"
    return flat if os.path.exists(flat) else ""


def make_boss(floor_number: int, zone_theme: str = "", is_miniboss: bool = False, boss_data_override=_UNSET, family_override: dict = None) -> list[CombatUnit]:
    """Create a boss or miniboss enemy. family_override (see
    services/enemy_families.py) lets a defined floor-range family supply a
    deterministic named encounter (e.g. floor 5's "Goblin King") instead of
    the generic procedural LLM/fallback naming below — used for floor ranges
    that have a built-out family, skipped entirely otherwise."""
    scale = 1 + (floor_number * 0.12)

    if family_override:
        boss_title = family_override["name"]
        mod = family_override.get("stat_mod") or {"atk": 1.0, "def": 1.0, "spd": 1.0, "health": 1.0}
        abilities = family_override.get("abilities") or (["cleave", "enrage"] if is_miniboss else ["crushing_blow", "last_stand"])
        spawn_template = family_override.get("spawn_template", "")
        # A family can pin an exact existing portrait (e.g. a hand-picked
        # piece of preserved art) instead of relying on the name-based
        # lookup — these boss archetype files live under enemies/boss/ but
        # are named by archetype (boss_undead_monarch.png), not by the
        # family's display name ("The Undead Monarch"), so the slug-based
        # lookup wouldn't find them on its own.
        portrait_path = family_override.get("portrait_path") or _enemy_portrait_path(boss_title, "miniboss" if is_miniboss else "boss") or None
        power = (1.5 + (floor_number / 40)) if is_miniboss else (2.5 + (floor_number / 30))
        from services.portrait_cache import get_random_boss_portrait
        boss = CombatUnit(
            id=-99, name=boss_title,
            level=max(1, floor_number + (10 if not is_miniboss else 5)),
            health=int(220 * scale * power * mod['health']), max_health=int(220 * scale * power * mod['health']),
            strength=int(16 * scale * (power * 0.28) * mod['atk']), intelligence=0,
            defense=int(12 * scale * (power * 0.35) * mod['def']),
            endurance=int(12 * scale * (power * 0.35) * mod['def']),
            agility=int(8 * scale * mod['spd']),
            morale=100, stress=0, is_hero=False,
            portrait_path=portrait_path or get_random_boss_portrait(is_miniboss=is_miniboss),
            abilities=abilities,
            spawn_template=spawn_template,
        )
        return [boss]

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
            "health": boss_data.get("hp_multiplier", 1.2),
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
            {"name": "Enraged", "atk": 1.5, "def": 0.7, "spd": 1.0, "health": 1.0},
            {"name": "Armored", "atk": 1.0, "def": 2.0, "spd": 0.8, "health": 1.0},
            {"name": "Colossal", "atk": 1.0, "def": 1.0, "spd": 0.7, "health": 1.8},
            {"name": "Frenzied", "atk": 1.2, "def": 1.0, "spd": 1.5, "health": 1.0},
            {"name": "Vampiric", "atk": 1.1, "def": 1.1, "spd": 1.1, "health": 1.1},
            {"name": "Cursed", "atk": 1.3, "def": 0.8, "spd": 1.2, "health": 0.9},
        ]
        mod = random.choice(boss_modifiers)

    if is_miniboss and not boss_data:
        name = f"Lieutenant of {name}"
    
    # Power curves were originally tuned far too aggressively (a floor-10
    # boss hit for ~106 base strength — a near-instant kill against an early
    # team's 80-170 Health heroes). Scaled down so a boss is a meaningfully
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
        level=max(1, floor_number + (10 if not is_miniboss else 5)),
        health=int(220 * scale * power * mod['health']), max_health=int(220 * scale * power * mod['health']),
        strength=int(16 * scale * (power * 0.28) * mod['atk']), intelligence=0,
        defense=int(12 * scale * (power * 0.35) * mod['def']),
        endurance=int(12 * scale * (power * 0.35) * mod['def']),
        agility=int(8 * scale * mod['spd']),
        morale=100, stress=0, is_hero=False,
        portrait_path=get_random_boss_portrait(is_miniboss=is_miniboss),
        abilities=abilities,
    )
    return [boss]


def _fear_check(unit: CombatUnit, log: list, resist_mult: float = 1.0) -> bool:
    """
    Check if a hero is paralyzed by fear this round.
    Based on trauma + stress levels.
    Returns True if the hero is fear-stunned.

    resist_mult comes from a Stoic Leader's leadership bonus (see
    LEADERSHIP_BONUS) — 1.0 for everyone else, lower when a calm Leader is
    steadying the whole squad's nerves for the fight.
    """
    if unit.fear_immune or not unit.is_hero:
        return False

    trauma = unit.trauma
    stress = unit.stress

    # Fear chance: 0% below 40 trauma, scales up
    if trauma < 40:
        return False
    elif trauma < 60:
        chance = (0.08 + (stress * 0.001)) * resist_mult
    elif trauma < 80:
        chance = (0.15 + (stress * 0.002)) * resist_mult
    else:
        chance = (0.25 + (stress * 0.003)) * resist_mult

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


# battle_tendency -> the whole squad's passive combat modifier while this
# Leader is assigned, scaled by leader_star_mult where it's applied. Tuned
# so a single tendency never reads as strictly better than another — each
# is a different flavor of "this squad fights like its Leader."
LEADERSHIP_BONUS = {
    "Reckless":      {"atk_mult": 0.04},
    "Calculating":   {"def_mult": 0.04, "crit_bonus": 0.02},
    "Protective":    {"def_mult": 0.06},
    "Glory-Seeking": {"crit_bonus": 0.04},
    "Vengeful":      {"atk_mult": 0.03, "crit_bonus": 0.02},
    "Stoic":         {"fear_resist": 0.3},  # scales down the whole squad's fear/panic chance
}
LEADER_STEADY_CHANCE_BASE = 0.10  # per star, per-round chance to snap a squadmate out of fear/panic

TENDENCY_TARGET_OVERRIDE_CHANCE = 0.3

def _apply_tendency_target_override(default_target: CombatUnit, candidates: list[CombatUnit], squad_tendency: str | None) -> CombatUnit:
    """Light, probabilistic nudge driven by the team Leader's battle_tendency
    (squad_tendency) — never overrides class-locked targeting rules (e.g.
    Assassin's backline rule, handled entirely by the caller before this is
    invoked), and only fires some of the time so it reshuffles focus rather
    than replacing the existing front-to-back logic outright."""
    if not squad_tendency or len(candidates) < 2:
        return default_target
    if random.random() > TENDENCY_TARGET_OVERRIDE_CHANCE:
        return default_target

    if squad_tendency in ("Reckless", "Glory-Seeking"):
        return min(candidates, key=lambda u: u.health)
    elif squad_tendency == "Calculating":
        return max(candidates, key=lambda u: u.strength)
    return default_target


TENDENCY_FLAVOR_CHANCE = 0.25
TENDENCY_KILL_LINES = {
    "Reckless": "  ✦ {attacker} doesn't even wait to see {target} fall before moving on.",
    "Calculating": "  ✦ {attacker} finishes {target} with cold precision.",
    "Protective": "  ✦ {attacker} ends {target} without hesitation — no one else gets hurt today.",
    "Glory-Seeking": "  ✦ {attacker} makes a show of {target}'s fall.",
    "Vengeful": "  ✦ {attacker} drives the killing blow home like it's personal.",
    "Stoic": "  ✦ {target} falls.",
}

def _kill_log_line(attacker: CombatUnit, target: CombatUnit) -> str:
    """Occasionally flavors a kill with the attacker's OWN battle_tendency
    (individual flavor — distinct from the leader-driven squad targeting
    nudge above, which is about who gets targeted, not how it's narrated)."""
    if random.random() < TENDENCY_FLAVOR_CHANCE and attacker.battle_tendency in TENDENCY_KILL_LINES:
        return TENDENCY_KILL_LINES[attacker.battle_tendency].format(attacker=attacker.log_name, target=target.log_name)
    return f"  ✦ {target.log_name} falls."


# Star rank no longer makes a hero immune to panic outright — it just makes
# it less likely, alongside talent and battle_tendency. The chance is then
# scaled by the encounter's power_ratio (enemy power / hero power for this
# fight, from the same difficulty-budget numbers make_enemies already uses)
# so a curb-stomp panics people regardless of star, and a clean win rarely
# does even for a 1-star.
PANIC_BASE_CHANCE_BY_STAR = {1: 0.20, 2: 0.14, 3: 0.10, 4: 0.07, 5: 0.05, 6: 0.035, 7: 0.025}
# Reckless/Calculating are no more fear-prone than anyone else now, but the
# OTHER tendencies hold up better under pressure — Protective/Stoic/Vengeful
# shield, steel themselves, or get angry instead of scared; Glory-Seeking is
# partway between (vain confidence helps some, but not as much as the above).
TENDENCY_PANIC_RESIST = {
    "Protective": 0.5, "Stoic": 0.55, "Vengeful": 0.6, "Glory-Seeking": 0.8,
}

# Panic doesn't remove a hero from the fight, it makes them WORSE off in it —
# there's no escaping the floor, you clear it or you don't:
#   - Reckless/Glory-Seeking break formation and get isolated — exposed,
#     take bonus damage, become the enemy's preferred target.
#   - Everyone else falls back defensively instead, skipping their strength
#     to brace and try to survive the next hit.
ISOLATED_ROUNDS = 2
BRACING_ROUNDS = 1

def _panic_check(unit: CombatUnit, trigger: str, log: list, power_ratio: float = 1.0, resist_mult: float = 1.0) -> bool:
    """Any hero can panic now — star rank, talent, and battle_tendency reduce
    susceptibility rather than gating it outright. Distinct from the
    trauma-gated _fear_check above (which just skips a turn) — this is a
    rarer, harsher response triggered by specific events (witnessing a death,
    dropping critically low) rather than an ongoing trauma/stress level."""
    if not unit.is_hero or not unit.alive:
        return False
    if unit.isolated_rounds > 0 or unit.bracing_rounds > 0:
        return False  # already panicking this fight, don't restack

    base = PANIC_BASE_CHANCE_BY_STAR.get(unit.hero_star, 0.02)
    base *= (1.0 - unit.talent * 0.4)  # talented heroes keep their cool better
    tendency_resist = TENDENCY_PANIC_RESIST.get(unit.battle_tendency, 1.0)
    # Willpower stat resistance — capped at 50% reduction so it's a strong,
    # visible effect without making a high-Willpower hero flatly immune
    # (consistent with this fight's "no hard immune switch" design).
    willpower_resist = max(0.5, 1.0 - unit.willpower / 100)
    chance = base * willpower_resist * tendency_resist * resist_mult * max(0.4, min(2.2, power_ratio))
    if trigger == "hp_critical":
        chance *= 1.5
    if random.random() >= chance:
        return False

    if unit.battle_tendency in ("Reckless", "Glory-Seeking"):
        unit.isolated_rounds = ISOLATED_ROUNDS
        isolated_lines = [
            f"  {unit.name} panics and breaks formation — exposed and alone!",
            f"  {unit.name} loses their head and charges off-formation!",
            f"  {unit.name} scatters from the group, vulnerable.",
        ]
        log.append(random.choice(isolated_lines))
    else:
        unit.bracing_rounds = BRACING_ROUNDS
        bracing_lines = [
            f"  {unit.name} abandons the offensive, bracing defensively to survive.",
            f"  {unit.name} knows running alone is a death sentence — they dig in instead.",
            f"  {unit.name} falls back, covering themselves rather than attacking.",
        ]
        log.append(random.choice(bracing_lines))
    return True


def calc_damage(attacker: CombatUnit, defender: CombatUnit) -> tuple[int, bool]:
    effective_def = defender.endurance * (1 - attacker.armor_pen)
    if defender.bracing_rounds > 0:
        effective_def *= 1.6  # bracing defensively to survive — the whole point of not fleeing
    power = attacker.intelligence if attacker.power_stat == "intelligence" else attacker.strength
    base = power * (100 / (100 + max(0, effective_def)))

    if attacker.is_hero and attacker.morale < 40:
        morale_factor = 0.5 + (attacker.morale / 80)
        base *= morale_factor

    variance = random.uniform(0.85, 1.15)
    damage = max(1, int(base * variance))

    if defender.dmg_reduction_pct > 0:
        damage = max(1, int(damage * (1 - defender.dmg_reduction_pct)))

    if defender.isolated_rounds > 0:
        damage = int(damage * 1.3)  # exposed and unsupported, out of formation

    is_crit = random.random() < attacker.crit_chance
    if is_crit:
        damage = int(damage * 1.8)

    return damage, is_crit


# Enemy signature abilities — elite/miniboss/boss tiers get 1-2 of these
# instead of just a plain basic strength every turn. "cleave" can recur each
# turn (chance-gated); the rest are one-time triggers gated on the
# attacker's own Health, tracked via used_abilities so they only fire once.
MAX_SUMMONS_PER_BATTLE = 3
SUMMON_ADD_CHANCE = 0.18
TEAM_BUFF_AURA_ATK_MULT = 1.25

def _try_use_ability(attacker: CombatUnit, alive_heroes: list, log: list, morale_changes: dict, stress_changes: dict,
                      enemies: list = None, all_units: list = None, floor_number: int = 1) -> bool:
    """Returns True if an ability fired this turn (attacker's normal strength
    is skipped), False to fall through to a normal strength."""
    hlt_pct = attacker.health / attacker.max_health if attacker.max_health else 0

    # "summon_add" — a recurring, capped reinforcement call (Goblin King
    # summoning goblins, Giant Rat Alpha calling the swarm, etc). Needs
    # access to the live enemies/all_units lists so the new add actually
    # gets a turn this fight, not just a cosmetic log line.
    if ("summon_add" in attacker.abilities and enemies is not None and all_units is not None
            and attacker.summons_used < MAX_SUMMONS_PER_BATTLE and random.random() < SUMMON_ADD_CHANCE):
        spawn_name = attacker.spawn_template or "Goblin"
        spawn_count = random.randint(1, 2)
        new_id = -(2000 + attacker.summons_used * 10 + len([u for u in enemies if not u.is_hero]))
        new_adds = []
        for i in range(spawn_count):
            add = _make_swarm_add(spawn_name, floor_number, abs(new_id) + i)
            new_adds.append(add)
        enemies.extend(new_adds)
        all_units.extend(new_adds)
        attacker.summons_used += 1
        log.append(f"  📯 {attacker.log_name} calls for reinforcements! {len(new_adds)}x {spawn_name} joins the fight!")
        return True

    # "team_buff_aura" — a one-time rallying cry that empowers every other
    # enemy still standing (Goblin Shaman channeling power into the horde).
    if ("team_buff_aura" in attacker.abilities and "team_buff_aura" not in attacker.used_abilities
            and enemies and any(a.alive and a is not attacker for a in enemies)):
        attacker.used_abilities.add("team_buff_aura")
        buffed = 0
        for ally in enemies:
            if ally.alive and ally is not attacker:
                ally.strength = int(ally.strength * TEAM_BUFF_AURA_ATK_MULT)
                buffed += 1
        log.append(f"  🔥 {attacker.log_name} channels power into the horde! {buffed} ally(s) hit harder now.")
        return True

    # "revive_ally" — once per battle, brings one fallen ally back at partial
    # Health (Skeleton Champion "reviving the fallen"). Needs the live
    # enemies list to find a dead ally and actually bring them back into the
    # turn order, not just a cosmetic log line.
    if ("revive_ally" in attacker.abilities and "revive_ally" not in attacker.used_abilities
            and enemies is not None and any((not a.alive) and a is not attacker for a in enemies)):
        attacker.used_abilities.add("revive_ally")
        fallen = [a for a in enemies if not a.alive and a is not attacker]
        target = max(fallen, key=lambda a: a.max_health)
        target.alive = True
        target.health = int(target.max_health * REVIVE_ALLY_HP_PCT)
        log.append(f"  ✟ {attacker.log_name} channels dark energy — {target.log_name} rises again! [{target.health}/{target.max_health}]")
        return True

    if "cleave" in attacker.abilities and random.random() < 0.20:
        log.append(f"  ⚔ {attacker.log_name} cleaves at the whole party!")
        for target in alive_heroes:
            damage, is_crit = calc_damage(attacker, target)
            damage = int(damage * 0.5)
            target.health -= damage
            crit_text = " CRIT!" if is_crit else ""
            log.append(f"    → {target.log_name} takes {damage}{crit_text} [{max(0,target.health)}/{target.max_health}]")
            if target.health <= 0:
                target.alive = False
                log.append(f"    ✦ {target.log_name} has fallen.")
                for h in alive_heroes:
                    if h.alive and h is not target:
                        morale_changes[h.id] = morale_changes.get(h.id, 0) - random.randint(8, 18)
                        stress_changes[h.id] = stress_changes.get(h.id, 0) + random.randint(5, 12)
        return True

    if "enrage" in attacker.abilities and "enrage" not in attacker.used_abilities and hlt_pct < 0.5:
        attacker.used_abilities.add("enrage")
        attacker.strength = int(attacker.strength * 1.4)
        log.append(f"  ⚡ {attacker.log_name} flies into a rage! Strength sharply rises!")
        return False  # still takes a normal strength this turn, just buffed first

    if "crushing_blow" in attacker.abilities and "crushing_blow" not in attacker.used_abilities and hlt_pct < 0.7 and alive_heroes:
        attacker.used_abilities.add("crushing_blow")
        target = max(alive_heroes, key=lambda h: h.health)
        damage, is_crit = calc_damage(attacker, target)
        damage = int(damage * 2.2)
        target.health -= damage
        log.append(f"  ☠ {attacker.log_name} unleashes a CRUSHING BLOW on {target.log_name} for {damage} damage! [{max(0,target.health)}/{target.max_health}]")
        if target.health <= 0:
            target.alive = False
            log.append(f"    ✦ {target.log_name} has fallen.")
        return True

    if "last_stand" in attacker.abilities and "last_stand" not in attacker.used_abilities and hlt_pct < 0.2:
        attacker.used_abilities.add("last_stand")
        heal = int(attacker.max_health * 0.25)
        attacker.health = min(attacker.max_health, attacker.health + heal)
        log.append(f"  ✚ {attacker.log_name} makes a last stand, recovering {heal} Health! [{attacker.health}/{attacker.max_health}]")
        return True

    return False

def resolve_hero_stats(heroes: list[dict]) -> list[dict]:
    """Applies level scaling → class modifiers → synergy → equipment →
    legacy bonuses → relics → base-floor LP → bonds → passive skills/traits,
    in that order. This is the one full pipeline that turns raw DB hero rows
    into the fully-resolved stat dicts combat actually fights with. Also
    used standalone (not followed by a fight) to build the snapshot a player
    submits to the Arena server — see routers/arena.py's snapshot endpoint
    and run_combat's skip_stat_pipeline param, which lets the Arena server
    accept that snapshot back in without re-deriving it (it has no DB access
    to do so anyway)."""
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
    team_end_mult = 1.0
    team_spd_mult = 1.0
    for h in heroes:
        mods = apply_class_combat_modifiers(h)
        if "team_atk_mult" in mods: team_atk_mult *= mods["team_atk_mult"]
        if "team_end_mult" in mods: team_end_mult *= mods["team_end_mult"]
        if "team_spd_mult" in mods: team_spd_mult *= mods["team_spd_mult"]

    for h in heroes:
        scaled = apply_level_to_stats(h)
        modified = apply_class_combat_modifiers(scaled)

        # Apply team class buffs
        if team_atk_mult > 1.0: modified["strength"] = int(modified["strength"] * team_atk_mult)
        if team_end_mult > 1.0: modified["endurance"] = int(modified.get("endurance", modified.get("defense", 5)) * team_end_mult)
        if team_spd_mult > 1.0: modified["agility"] = int(modified["agility"] * team_spd_mult)

        # Apply Depression Penalty (-75% stats)
        if modified.get("condition") == "Depressed":
            modified["strength"] = max(1, int(modified["strength"] * 0.25))
            modified["agility"] = max(1, int(modified["agility"] * 0.25))
            modified["intelligence"] = max(1, int(modified["intelligence"] * 0.25))
            modified["defense"] = max(1, int(modified.get("defense", 5) * 0.25))
            modified["max_health"] = max(1, int(modified["max_health"] * 0.25))
            modified["health"] = min(modified["health"], modified["max_health"])

        # Apply synergy buff
        sg = modified.get("synergy_group")
        if sg and synergy_counts.get(sg, 0) > 1:
            multiplier = 1.0 + (0.05 * synergy_counts[sg])
            modified["max_health"] = int(modified["max_health"] * multiplier)
            modified["health"] = modified["max_health"]
            modified["strength"] = int(modified["strength"] * multiplier)
            modified["intelligence"] = int(modified["intelligence"] * multiplier)
            modified["defense"] = int(modified.get("defense", 5) * multiplier)
            modified["agility"] = int(modified["agility"] * multiplier)

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
                # 6 stats, not 7 -- Endurance already determines Health
                # (see health_from_endurance in gacha_service.py), so
                # buffing Health on top of Endurance here would double-count it.
                modified["strength"] = int(modified["strength"] * lp_mult)
                modified["intelligence"] = int(modified["intelligence"] * lp_mult)
                modified["agility"] = int(modified["agility"] * lp_mult)
                modified["endurance"] = int(modified["endurance"] * lp_mult)
                modified["willpower"] = int(modified["willpower"] * lp_mult)
                modified["luck"] = int(modified["luck"] * lp_mult)
        except Exception:
            pass

        # Apply bond stats
        bond_lvl = bond_totals.get(modified["id"], 0)
        if bond_lvl > 0:
            bond_mult = 1.0 + (0.01 * bond_lvl)
            modified["max_health"] = int(modified["max_health"] * bond_mult)
            modified["health"] = min(modified["max_health"], modified["health"])
            modified["strength"] = int(modified["strength"] * bond_mult)
            modified["intelligence"] = int(modified["intelligence"] * bond_mult)
            modified["agility"] = int(modified["agility"] * bond_mult)

        # Apply passive skills and traits
        hero_skills = []
        hero_traits = []
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
            modified["_skills"] = hero_skills
            del modified["skills"]
        if "traits" in modified:
            modified["_traits"] = hero_traits
            del modified["traits"]
        processed.append(modified)

    return processed


def run_combat(heroes: list[dict], floor_number: int, is_boss: bool = False, is_miniboss: bool = False, zone_theme: str = "", boss_data_override=_UNSET, enemy_count_override: int = None, difficulty_mult: float = 1.0, preset_enemies: list = None, outer_conn=None, skip_stat_pipeline: bool = False, family_override: dict = None, is_survival_swarm: bool = False, turn_limit: int = None, available_consumables: list = None) -> dict:
    log = []
    turns = []
    morale_changes = {h["id"]: 0 for h in heroes}
    kill_counts = {h["id"]: 0 for h in heroes}
    stress_changes = {h["id"]: 0 for h in heroes}

    # skip_stat_pipeline lets a caller hand in hero dicts that are *already*
    # fully resolved (level/class/equipment/relic/bond/base-floor bonuses all
    # baked in) instead of raw DB rows — used by the Arena server, which has
    # no access to either player's local save/equipment/relics to compute
    # this pipeline itself. The caller (the player's own local backend) runs
    # this exact pipeline normally for a Tower floor, then ships the
    # resulting dict over the wire instead of re-deriving it remotely.
    if skip_stat_pipeline:
        processed = heroes
        result = _resolve_combat_from_processed(processed, floor_number, is_boss, is_miniboss, zone_theme,
                                                 boss_data_override, enemy_count_override, difficulty_mult,
                                                 preset_enemies, outer_conn, log, turns,
                                                 morale_changes, kill_counts, stress_changes,
                                                 family_override, is_survival_swarm, turn_limit, available_consumables)
        result.pop("_avg_luck", None)
        return result

    processed = resolve_hero_stats(heroes)

    result = _resolve_combat_from_processed(processed, floor_number, is_boss, is_miniboss, zone_theme,
                                             boss_data_override, enemy_count_override, difficulty_mult,
                                             preset_enemies, outer_conn, log, turns,
                                             morale_changes, kill_counts, stress_changes,
                                             family_override, is_survival_swarm, turn_limit, available_consumables)
    _apply_combat_drops(result, floor_number, is_boss, is_miniboss, outer_conn)
    return result


def _resolve_combat_from_processed(processed, floor_number, is_boss, is_miniboss, zone_theme,
                                    boss_data_override, enemy_count_override, difficulty_mult,
                                    preset_enemies, outer_conn, log, turns,
                                    morale_changes, kill_counts, stress_changes,
                                    family_override=None, is_survival_swarm=False, turn_limit=None,
                                    available_consumables=None):
    """The CombatUnit-construction-and-turn-loop core of run_combat, split out
    of the stat-resolution pipeline above it so a caller that already has
    fully-resolved hero dicts (no local DB to re-derive equipment/relic/bond/
    base-floor bonuses from — see run_combat's skip_stat_pipeline) can run a
    fight directly without re-deriving anything. Returns the same result dict
    run_combat used to build inline; drop generation is applied by the caller
    afterward (_apply_combat_drops), not here, since Arena fights skip drops
    entirely."""
    combatants_heroes = []
    construct_id = -100
    for h in processed:
        hero_unit = CombatUnit(
            id=h["id"], name=h["name"],
            level=h.get("level", 1),
            health=h["health"], max_health=h["max_health"],
            strength=h["strength"], intelligence=h["intelligence"],
            agility=h["agility"], morale=h["morale"], stress=h["stress"],
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
        )
        combatants_heroes.append(hero_unit)
        
        # Summon construct if the hero has the has_construct flag
        if h.get("has_construct"):
            c_hp = int(h["max_health"] * 1.5)
            c_atk = int(h["strength"] * 0.8)
            c_def = int(h.get("defense", 5) * 1.5)
            c_spd = int(h["agility"] * 0.7)
            construct_unit = CombatUnit(
                id=construct_id, name=f"{h['name']}'s Construct",
                level=h.get("level", 1),
                health=c_hp, max_health=c_hp, strength=c_atk, intelligence=0, defense=c_def, endurance=c_def, agility=c_spd,
                morale=100, stress=0, hero_class="Construct", fear_immune=True
            )
            combatants_heroes.append(construct_unit)
            construct_id -= 1
            log.append(f"  {hero_unit.name} deploys a massive Construct to the frontline!")

    # Generate enemies — difficulty is purely floor-based, not adaptive to team strength.
    if is_survival_swarm:
        if preset_enemies:
            enemies = preset_enemies
        else:
            enemies = make_swarm_miniboss_encounter(floor_number)
        log.append(f"🌊💀🌊 SURVIVAL FLOOR {floor_number} 🌊💀🌊")
        log.append(f"  An overwhelming swarm pours in. Survive {turn_limit or SURVIVAL_TURN_LIMIT} rounds!")
    elif is_boss or is_miniboss:
        if preset_enemies:
            enemies = preset_enemies
        else:
            enemies = make_boss(floor_number, zone_theme, is_miniboss, boss_data_override=boss_data_override, family_override=family_override)
        log.append(f"🔥💀🔥 {'MINIBOSS' if is_miniboss else 'BOSS'} FLOOR {floor_number} 🔥💀🔥")
        log.append(f"  {enemies[0].name} emerges from the darkness.")
    else:
        if preset_enemies:
            enemies = preset_enemies
        else:
            enemies = make_enemies(floor_number, count=enemy_count_override, difficulty_mult=difficulty_mult)

    initial_state = {
        "is_boss": is_boss,
        "is_miniboss": is_miniboss,
        "is_survival_swarm": is_survival_swarm,
        "turn_limit": (turn_limit or SURVIVAL_TURN_LIMIT) if is_survival_swarm else None,
        "heroes": [
            {"id": h.id, "name": h.name, "hero_class": h.hero_class, "max_health": h.max_health, "health": h.health,
             "portrait_path": h.portrait_path, "hero_star": h.hero_star, "level": h.level,
             "power_stat": h.power_stat, "is_ranged": h.is_ranged}
            for h in combatants_heroes
        ],
        "enemies": [
            {"id": e.id, "name": e.name, "max_health": e.max_health, "health": e.health, "portrait_path": e.portrait_path, "level": e.level}
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
    max_rounds = (turn_limit or SURVIVAL_TURN_LIMIT) if is_survival_swarm else 30

    # Squad tactical doctrine: if the team has a manually-assigned Leader, their
    # battle_tendency nudges everyone's default targeting choice (a "the whole
    # squad fights the way the Leader fights" effect) — leaderless teams have
    # no doctrine and fall back to the unmodified default targeting entirely.
    squad_leader = next((h for h in combatants_heroes if h.is_team_leader), None)
    squad_tendency = squad_leader.battle_tendency if squad_leader else None

    # Leadership bonus: a manually-assigned Leader's battle_tendency grants
    # the whole squad one passive combat-wide modifier for the fight, scaled
    # by the Leader's own star rank — a 1-star Leader barely rallies anyone,
    # a 7-star one is a real force multiplier. Layered on top of the
    # targeting-doctrine nudge above and the fear-steadying check below.
    leader_star_mult = 1.0
    leader_steady_chance = 0.0
    fear_resist_mult = 1.0
    if squad_leader:
        leader_star_mult = 1 + (squad_leader.hero_star - 1) * 0.3
        bonus = LEADERSHIP_BONUS.get(squad_leader.battle_tendency, {})
        atk_mult = 1 + bonus.get("atk_mult", 0) * leader_star_mult
        def_mult = 1 + bonus.get("def_mult", 0) * leader_star_mult
        crit_bonus = bonus.get("crit_bonus", 0) * leader_star_mult
        if atk_mult != 1 or def_mult != 1 or crit_bonus:
            for h in combatants_heroes:
                if atk_mult != 1: h.strength = int(h.strength * atk_mult)
                if def_mult != 1: h.endurance = int(h.endurance * def_mult)
                if crit_bonus: h.crit_chance += crit_bonus
        if bonus.get("fear_resist"):
            fear_resist_mult = 1 - min(0.6, bonus["fear_resist"] * leader_star_mult)
        leader_steady_chance = LEADER_STEADY_CHANCE_BASE * leader_star_mult

    # Encounter power ratio (enemy power / hero power) — gates universal
    # panic susceptibility below; a lopsided fight panics people regardless
    # of star, a clean win rarely does even for a 1-star.
    hero_power = sum(h.strength + h.intelligence + h.endurance + h.max_health * 0.05 for h in combatants_heroes) or 1
    enemy_power = sum(e.strength + e.endurance + e.max_health * 0.05 for e in enemies) or 1
    power_ratio = enemy_power / hero_power

    damage_dealt_stats = {h.id: 0 for h in combatants_heroes}
    consumables_used = {}

    for round_num in range(1, max_rounds + 1):
        all_units.sort(key=lambda u: u.agility + random.uniform(0, 2), reverse=True)

        alive_heroes  = [u for u in combatants_heroes if u.alive]
        alive_enemies = [u for u in enemies if u.alive]
        if not alive_heroes or not alive_enemies:
            break

        # ─── Fear checks at start of each round ───
        for hero in alive_heroes:
            hero.fear_stunned = False  # Reset from last round
            _fear_check(hero, log, fear_resist_mult)
            if hero.isolated_rounds > 0:
                hero.isolated_rounds -= 1
            if hero.bracing_rounds > 0:
                hero.bracing_rounds -= 1

        # A steady Leader can pull a squadmate back together mid-fight —
        # personality-flavored, not guaranteed, and the Leader can't steady
        # themselves.
        if squad_leader and squad_leader.alive and not squad_leader.fear_stunned and leader_steady_chance > 0:
            for hero in alive_heroes:
                if hero is squad_leader:
                    continue
                if hero.fear_stunned and random.random() < leader_steady_chance:
                    hero.fear_stunned = False
                    log.append(f"  ◆ {squad_leader.log_name} steadies {hero.log_name} — the line holds.")
                elif (hero.isolated_rounds > 0 or hero.bracing_rounds > 0) and random.random() < leader_steady_chance:
                    hero.isolated_rounds = 0
                    hero.bracing_rounds = 0
                    log.append(f"  ◆ {squad_leader.log_name} snaps {hero.log_name} out of it — formation reforms.")

        # ─── Relic/skill regen ticks ───
        for unit in alive_heroes + alive_enemies:
            if unit.regen_pct > 0 and unit.health < unit.max_health:
                heal = int(unit.max_health * unit.regen_pct)
                unit.health = min(unit.max_health, unit.health + heal)
                log.append(f"  ✚ {unit.log_name} regenerates {heal} Health [{unit.health}/{unit.max_health}]")

        # ─── Shared-backpack Potion/Scroll auto-use ───
        if available_consumables:
            for hero in alive_heroes:
                if hero.used_consumable or hero.health >= hero.max_health * CONSUMABLE_LOW_HP_THRESHOLD:
                    continue
                usable = [c for c in available_consumables if c["quantity"] > 0]
                if not usable:
                    continue
                best = max(usable, key=lambda c: c["heal_pct"])
                heal = int(hero.max_health * best["heal_pct"])
                hero.health = min(hero.max_health, hero.health + heal)
                best["quantity"] -= 1
                hero.used_consumable = True
                consumables_used[best["item_name"]] = consumables_used.get(best["item_name"], 0) + 1
                log.append(f"  ✚ {hero.log_name} drinks a {best['item_name']}, healing {heal} Health [{hero.health}/{hero.max_health}]")

        alive_frontline = [h for h in frontline if h.alive]

        for attacker in all_units:
            if not attacker.alive:
                continue

            # Fear-stunned heroes skip their turn
            if attacker.is_hero and attacker.fear_stunned:
                stress_changes[attacker.id] = stress_changes.get(attacker.id, 0) + 5
                continue

            # Bracing heroes forgo their strength to hunker down defensively
            if attacker.is_hero and attacker.bracing_rounds > 0:
                log.append(f"  {attacker.name} stays braced, watching for an opening.")
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
                        target.health -= damage
                        crit_text = " CRIT!" if is_crit else ""
                        log_msg = f"    → {target.log_name} takes {damage}{crit_text} [{max(0,target.health)}/{target.max_health}]"
                        log.append(log_msg)
                        turns.append({"round": round_num, "attacker_id": attacker.id, "target_id": target.id, "damage": damage, "is_crit": is_crit, "target_hp": max(0, target.health), "log": log_msg})
                        if target.health <= 0:
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
                        # Squad tactical doctrine — only applies to this unlocked
                        # default-targeting branch, never to the Assassin rule above.
                        target = _apply_tendency_target_override(target, targets, squad_tendency)

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

                    target.health -= damage
                    crit_text = " CRIT!" if is_crit else ""
                    log_msg = f"  {attacker.log_name} hits {target.log_name} for {damage}{crit_text} [{max(0,target.health)}/{target.max_health}]"
                    log.append(log_msg)
                    turns.append({"round": round_num, "attacker_id": attacker.id, "target_id": target.id, "damage": damage, "is_crit": is_crit, "target_hp": max(0, target.health), "log": log_msg})

                    if target.health <= 0:
                        target.alive = False
                        attacker.kills += 1
                        kill_counts[attacker.id] = kill_counts.get(attacker.id, 0) + 1
                        log.append(_kill_log_line(attacker, target))
                        morale_changes[attacker.id] = morale_changes.get(attacker.id, 0) + random.randint(2, 5)

            else:
                if attacker.abilities:
                    alive_heroes_now = [h for h in combatants_heroes if h.alive]
                    if alive_heroes_now and _try_use_ability(attacker, alive_heroes_now, log, morale_changes, stress_changes,
                                                              enemies=enemies, all_units=all_units, floor_number=floor_number):
                        continue  # ability replaced the normal strength this turn

                alive_frontline = [h for h in frontline if h.alive]
                alive_backline = [h for h in backline if h.alive]

                if alive_frontline:
                    idx = enemies.index(attacker) % len(alive_frontline)
                    target = alive_frontline[idx]
                elif alive_backline:
                    target = random.choice(alive_backline)
                else:
                    continue

                # An isolated hero is exposed and out of formation — enemies
                # preferentially pick them off over the formation's intended target.
                isolated_targets = [h for h in (alive_frontline + alive_backline) if h.isolated_rounds > 0]
                if isolated_targets:
                    target = random.choice(isolated_targets)

                # Dodge check for thief
                if random.random() < target.dodge_chance:
                    log.append(f"  {target.name} dodges {attacker.log_name}'s strength!")
                    continue

                # Construct check
                if target.has_construct and target.construct_active:
                    target.construct_active = False
                    log.append(f"  {target.name}'s construct absorbs the hit!")
                    continue

                damage, is_crit = calc_damage(attacker, target)
                target.health -= damage
                crit_text = " CRIT!" if is_crit else ""
                log_msg = f"  {attacker.log_name} hits {target.log_name} for {damage}{crit_text} [{max(0,target.health)}/{target.max_health}]"
                log.append(log_msg)
                turns.append({"round": round_num, "attacker_id": attacker.id, "target_id": target.id, "damage": damage, "is_crit": is_crit, "target_hp": max(0, target.health), "log": log_msg})

                if target.health <= 0:
                    # Death save check
                    if target.death_save > 0:
                        target.death_save -= 1
                        target.health = 1
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
                            _panic_check(h, "witness_death", log, power_ratio, fear_resist_mult)
                elif target.health > 0 and (target.health / target.max_health) < 0.25:
                    _panic_check(target, "hp_critical", log, power_ratio, fear_resist_mult)

        alive_heroes  = [u for u in combatants_heroes if u.alive]
        alive_enemies = [u for u in enemies if u.alive]
        if not alive_heroes or not alive_enemies:
            break

    alive_heroes  = [u for u in combatants_heroes if u.alive]
    dead_heroes   = [u for u in combatants_heroes if not u.alive]
    # Survival Floor wins by outlasting the clock with anyone still standing
    # — wiping the swarm early still counts (just rare at these counts), but
    # killing every enemy is not required, unlike every other floor type.
    if is_survival_swarm:
        heroes_won = len(alive_heroes) > 0
    else:
        heroes_won = len(alive_heroes) > 0 and len([u for u in enemies if u.alive]) == 0

    if heroes_won:
        if is_survival_swarm:
            log.append(f"✓ Survived! {len(alive_heroes)} hero(es) held the line for {round_num} round(s).")
        else:
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
        "is_survival_swarm": is_survival_swarm,
        "rounds_survived": round_num if is_survival_swarm else None,
        "turn_limit": max_rounds if is_survival_swarm else None,
        "consumables_used": consumables_used,
        "initial_state": initial_state,
        "surviving_heroes": [
            {
                "id": h.id,
                "health": max(0, h.health),
                "morale_delta": morale_changes.get(h.id, 0),
                "kills_gained": kill_counts.get(h.id, 0),
                "stress_delta": stress_changes.get(h.id, 0),
            }
            for h in alive_heroes
        ],
        "dead_heroes": [h.id for h in dead_heroes],
        "surviving_enemies": alive_enemies,
        "skill_upgrades": skill_upgrades,
        "skills_learned": skills_learned,
        "log": log,
        "turns": turns,
        "rounds": round_num,
        "combat_metrics": damage_dealt_stats,
        # Internal bookkeeping for _apply_combat_drops below — not meant for
        # API consumers, but combatants_heroes only exists in this function's
        # scope, so the average has to be threaded through somehow.
        "_avg_luck": sum(h.luck for h in combatants_heroes) / max(1, len(combatants_heroes)),
    }
    return result


def _apply_combat_drops(result: dict, floor_number: int, is_boss: bool, is_miniboss: bool, outer_conn):
    """Tower-specific economy rewards (gold/materials/equipment/relic drops)
    on a winning fight — split out of run_combat so Arena fights (which use
    _resolve_combat_from_processed directly, skipping this entirely) don't
    grant Tower currency for a PvP match. Mutates result in place."""
    avg_luck = result.pop("_avg_luck", 5.0)
    if result["winner"] != "heroes":
        return
    try:
        # Reuse the caller's connection if it handed one in — opening a
        # second connection here while the caller's own `with db()`
        # transaction is still uncommitted causes "database is locked"
        # on SQLite, which this block's except then silently swallowed,
        # also skipping the gold/supplies/materials grant below it.
        if outer_conn is not None:
            base_info = outer_conn.execute("SELECT global_buffs FROM base WHERE id = 1").fetchone()
            buffs = __import__('json').loads(base_info["global_buffs"] or "{}") if base_info else {}
        else:
            from database import db
            with db() as _conn:
                base_info = _conn.execute("SELECT global_buffs FROM base WHERE id = 1").fetchone()
                buffs = __import__('json').loads(base_info["global_buffs"] or "{}") if base_info else {}
        from services.equipment_service import generate_equipment_drop
        # Luck is averaged across the deployed team, not taken from a
        # single hero — a team-comp consideration, not "stack one lucky
        # hero and ignore the rest."
        drop_bonus = buffs.get("drop_boost", 0) * 0.05 + avg_luck / 100
        equip = generate_equipment_drop(floor_number, is_boss, drop_bonus)
        if equip:
            result["equipment_drop"] = equip

        from services.relics_service import roll_relic_drop
        relic = roll_relic_drop(is_boss, is_miniboss, floor_number, conn=outer_conn)
        if relic:
            result["relic_drop"] = relic

        # Guaranteed Drops
        result["gold_gained"] = int(300 * (1 + (floor_number/10)))
        result["supplies_gained"] = random.randint(2, 5)

        from services.materials_service import roll_material_name, tiered_material_name
        drops = {}
        for _ in range(random.randint(2, 4)):
            mat = tiered_material_name(roll_material_name(floor_number), avg_luck=avg_luck)
            drops[mat] = drops.get(mat, 0) + 1
        result["materials_gained"] = drops

        if is_boss:
            result["gold_gained"] += int(1500 * (1 + (floor_number/10)))
            result["supplies_gained"] += 10
            for _ in range(5):
                mat = tiered_material_name(roll_material_name(floor_number), avg_luck=avg_luck)
                drops[mat] = drops.get(mat, 0) + 1
            result["materials_gained"] = drops
        elif is_miniboss:
            # Miniboss floors didn't have a bonus tier before — every
            # miniboss round (Survival Floor swarms included, since those
            # only ever happen on a miniboss floor) gets a smaller version
            # of the Boss bonus on top of the guaranteed drops above.
            result["gold_gained"] += int(600 * (1 + (floor_number/10)))
            result["supplies_gained"] += 4
            for _ in range(2):
                mat = tiered_material_name(roll_material_name(floor_number), avg_luck=avg_luck)
                drops[mat] = drops.get(mat, 0) + 1
            result["materials_gained"] = drops
    except Exception as e:
        print(f"Error generating drop: {e}")

def run_multi_combat(hero_teams: list[list[dict]], floor_number: int, is_boss: bool = False, is_miniboss: bool = False, zone_theme: str = "", boss_data_override=_UNSET, difficulty_mult: float = 1.0, conn=None, family_override: dict = None, is_survival_swarm: bool = False, turn_limit: int = None, available_consumables: list = None) -> dict:
    # Raid Boss (Every 20th floor is Raid Boss) — family_override was missing
    # here before, so a floor-20/40/60/80/100 family boss could never
    # actually appear; every raid floor fell through to the generic
    # LLM-flavored naming regardless of whether that range had a built-out
    # family. Floor 100 still gets its own random pick (Lich King/Nightwing
    # Devourer) via family_override exactly like any other boss floor now.
    if is_boss and floor_number % 20 == 0:
        combined_heroes = []
        for team in hero_teams:
            combined_heroes.extend(team)
        return run_combat(combined_heroes, floor_number, is_boss=True, is_miniboss=False, zone_theme=zone_theme, boss_data_override=boss_data_override, difficulty_mult=difficulty_mult * len(hero_teams), outer_conn=conn, available_consumables=available_consumables, family_override=family_override)

    # Shared Encounter relay — one enemy roster scaled for the combined
    # threat of every deployed team (same scaling the boss-merge branch above
    # already uses), so teams relay into the SAME fight instead of each
    # rolling an independent one. Team 2 picks up whatever Team 1 left alive
    # (same enemy HP/state carried forward). This team-by-team order is just
    # how the backend computes the HP handoff — the frontend renders every
    # team's own arena (see team_results) at the same time, so on screen it
    # reads as simultaneous parallel battles, not one-then-the-other.
    #
    # NOTE: this used to always call make_enemies() here regardless of
    # is_boss/is_miniboss — meaning every boss/miniboss floor that wasn't
    # also a %20 Raid Boss (so: every floor 5/15/25/... and every floor
    # 10/30/50/70/90) silently fought a regular mob encounter instead of an
    # actual named boss/miniboss, since preset_enemies short-circuits
    # make_boss() inside run_combat. Fixed below.
    if is_survival_swarm:
        shared_enemies = make_swarm_miniboss_encounter(floor_number)
    elif is_boss or is_miniboss:
        shared_enemies = make_boss(floor_number, zone_theme, is_miniboss, boss_data_override=boss_data_override, family_override=family_override)
    else:
        shared_enemies = make_enemies(floor_number, difficulty_mult=difficulty_mult * len(hero_teams))

    logs = []
    final_result = {
        "winner": "enemies",
        "is_boss": is_boss,
        "surviving_heroes": [],
        "dead_heroes": [],
        "skill_upgrades": {},
        "skills_learned": {},
        "log": logs,
        "combat_metrics": {},
        "gold_gained": 0,
        "supplies_gained": 0,
        "materials_gained": {},
        "consumables_used": {},
        # One entry per deployed team (None if that team was empty or had
        # nothing left to fight) — the frontend renders one CombatArena per
        # entry, each with its own initial_state/turns/log for that team's leg
        # of the shared fight.
        "team_results": [],
    }

    current_enemies = shared_enemies
    for i, team in enumerate(hero_teams):
        logs.append(f"\n=== TEAM {i+1} ENGAGES ===")
        if not team:
            logs.append(f"Team {i+1} is empty.")
            final_result["team_results"].append(None)
            continue
        if not current_enemies:
            logs.append(f"Team {i+1} arrives to find the encounter already cleared.")
            final_result["team_results"].append(None)
            continue

        # is_boss used to be hardcoded False here regardless of the real
        # flag — harmless for the %20 Raid Boss case (handled in its own
        # branch above before reaching this loop), but for every other boss
        # floor (10, 30, 50, 70, 90) it meant _apply_combat_drops below never
        # applied the Boss reward bonus, and the frontend never got
        # initial_state.is_boss=True to size the enemy sprite as a boss.
        # Potions/Scrolls are a shared base-wide backpack, not per-team — the
        # same list object is passed (and mutated in place) into every team's
        # fight in this loop, so a multi-team floor can't double-dip the same
        # finite stock once one team's fight already spent it.
        res = run_combat(team, floor_number, is_boss=is_boss, is_miniboss=is_miniboss, zone_theme=zone_theme, difficulty_mult=difficulty_mult, preset_enemies=current_enemies, outer_conn=conn, is_survival_swarm=is_survival_swarm, turn_limit=turn_limit, available_consumables=available_consumables)
        logs.extend(res.get("log", []))
        final_result["team_results"].append(res)

        for hid, upg in res.get("skill_upgrades", {}).items():
            final_result["skill_upgrades"].setdefault(hid, []).extend(upg)
        for hid, lrn in res.get("skills_learned", {}).items():
            final_result["skills_learned"].setdefault(hid, []).extend(lrn)
        for hid, dmg in res.get("combat_metrics", {}).items():
            final_result["combat_metrics"][hid] = final_result["combat_metrics"].get(hid, 0) + dmg

        final_result["surviving_heroes"].extend(res.get("surviving_heroes", []))
        final_result["dead_heroes"].extend(res.get("dead_heroes", []))
        final_result["gold_gained"] += res.get("gold_gained", 0)
        final_result["supplies_gained"] += res.get("supplies_gained", 0)
        for k, v in res.get("materials_gained", {}).items():
            final_result["materials_gained"][k] = final_result["materials_gained"].get(k, 0) + v
        for k, v in res.get("consumables_used", {}).items():
            final_result["consumables_used"][k] = final_result["consumables_used"].get(k, 0) + v
        if "equipment_drop" in res and "equipment_drop" not in final_result:
            final_result["equipment_drop"] = res["equipment_drop"]
        if "relic_drop" in res and "relic_drop" not in final_result:
            final_result["relic_drop"] = res["relic_drop"]

        current_enemies = res.get("surviving_enemies", [])

    if is_survival_swarm:
        # Survival Floors are single-team only (they only ever fire on a
        # %5 miniboss floor, which never requires 2+ teams) — winning means
        # outlasting the clock, not clearing the roster, so the "did the
        # enemy count hit zero" inference below doesn't apply here.
        only = final_result["team_results"][0] if final_result["team_results"] else None
        final_result["winner"] = only["winner"] if only else "enemies"
    else:
        # The shared encounter counts as cleared once the relay runs the
        # enemy roster down to nothing — win/loss is for the encounter as a
        # whole, not any single team's leg of it.
        final_result["winner"] = "heroes" if not current_enemies else "enemies"

    # Single-team floors are a relay of length one — also forward that one
    # team's initial_state/turns/rounds at the top level so the existing
    # single-arena frontend path keeps working unchanged.
    if len(hero_teams) == 1 and final_result["team_results"] and final_result["team_results"][0]:
        only = final_result["team_results"][0]
        final_result["initial_state"] = only.get("initial_state")
        final_result["turns"] = only.get("turns")
        final_result["rounds"] = only.get("rounds")
        final_result["is_survival_swarm"] = only.get("is_survival_swarm", False)
        final_result["rounds_survived"] = only.get("rounds_survived")
        final_result["turn_limit"] = only.get("turn_limit")

    return final_result
