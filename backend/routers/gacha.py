from fastapi import APIRouter, HTTPException
from database import db
from services.gacha_service import pull_rarity, generate_base_stats, generate_aptitudes, get_pull_cost
from services.llm_service import generate_hero_profile
from services.portrait_cache import pop_cached_portrait, rename_portrait_for_hero, queue_custom_portrait
from services.class_service import assign_class, can_pilot
from services.level_service import recalculate_hero_level
from services.skills_service import assign_initial_skills
from pydantic import BaseModel
import json
import threading

router = APIRouter()

MALE_FALLBACK_NAMES = [
    "Valerius", "Kaelen", "Tavian", "Rykard", "Jerrick", "Darius", "Fenris", "Corvus", "Sylas", "Bram",
    "Thorne", "Lysander", "Rowan", "Orion", "Soren", "Caelum", "Silas", "Evander", "Theron", "Aelar",
    "Zephyr", "Kael", "Ignis", "Sol", "Alistair", "Lucius", "Gideon", "Caius", "Marcus", "Eldric", "Finn",
    "Ronan", "Declan", "Aldous", "Vane", "Kaelan", "Orik", "Varian", "Zane", "Jax", "Lars", "Rex"
]
FEMALE_FALLBACK_NAMES = [
    "Elara", "Seris", "Isolde", "Nia", "Lorien", "Vanya", "Myra", "Gael", "Aria", "Cassia", "Kira", "Eira",
    "Vesper", "Juno", "Nyssa", "Lirael", "Rhea", "Lyra", "Nyx", "Nova", "Aura", "Seraphina", "Lumina",
    "Thalia", "Vespera", "Celeste", "Iris", "Maeve", "Senna", "Talia", "Ayla", "Mira", "Lina", "Cia"
]
FALLBACK_SURNAMES = [
    "Blackwood", "Vane", "Ash", "Storm", "Frost", "Gale", "Silver", "Iron", "Crow", "Hawk",
    "Dusk", "Dawn", "Wraith", "Grim", "Vale", "Thorn", "Shadow", "Drake", "Wolf", "Moon",
    "Blood", "Blade", "Stone", "Fire", "Star", "Sun", "Night", "Day", "Sky", "Sea", "River",
    "Winter", "Summer", "Autumn", "Spring", "Gold", "Steel", "Copper", "Brass", "Glass"
]
FALLBACK_TITLES = [
    "the Forsaken", "the Lost", "the Wanderer", "the Quiet", "the Exile", "the Broken",
    "the Swift", "the Resolute", "the Shadow", "the Undying", "the Vengeful", "the Silent",
    "the Bloodied", "the Merciful", "the Iron-Willed", "the Fearless", "the Accursed", "the Blessed",
    "the Cursed", "the Damned", "the Doomed", "the Fated", "the Destined", "the Chosen"
]
FALLBACK_BACKSTORIES = [
    "They have forgotten their past, or perhaps they simply refuse to speak of it. Only the tower remains for them.",
    "A former soldier from a ruined kingdom. They seek redemption in the endless floors.",
    "Born in the slums, they fought tooth and nail to survive. Now, they fight for gold.",
    "An exile from a noble house, stripped of their name and lands. They have nothing left to lose.",
    "A wandering mercenary who goes wherever the coin flows. The tower is just another job.",
    "They claim to be a hero from a forgotten age, awakened to climb the tower.",
    "A rogue mage who dabbled in forbidden arts. They seek ancient knowledge hidden in the spire.",
    "A sole survivor of a mercenary band wiped out on the lower floors. They climb to avenge their comrades.",
    "They woke up in the tower with no memory of how they got here. They climb to find answers.",
    "A zealot of a forgotten god, believing the top of the tower holds salvation."
]


def build_instant_profile(birth_star: int, gender_hint: str = None, synergy_theme_desc: str = None):
    """
    Build a placeholder hero identity with zero network calls, so a pull
    never blocks on the LLM. The real profile enriches this in the
    background once Gemini responds.
    """
    import random
    from services.portrait_cache import build_varied_prompt

    gender = gender_hint if gender_hint in ("male", "female") else random.choice(["male", "female"])
    name = random.choice(MALE_FALLBACK_NAMES if gender == "male" else FEMALE_FALLBACK_NAMES) + " " + random.choice(FALLBACK_SURNAMES)
    portrait_prompt = build_varied_prompt(birth_star, gender)[0]
    if synergy_theme_desc:
        portrait_prompt += f", {synergy_theme_desc}"

    class _Profile:
        pass
    profile = _Profile()
    profile.name = name
    profile.title = random.choice(FALLBACK_TITLES)
    profile.backstory = random.choice(FALLBACK_BACKSTORIES)
    profile.personality = "Watchful and silent."
    profile.gender = gender
    profile.portrait_prompt = portrait_prompt
    profile.ego_type = None
    return profile


# A bulk pull spawns one background thread per hero, all calling the LLM at
# nearly the same instant. generate_hero_profile()'s anti-repeat check only
# queries names already committed to the DB — it can't see sibling threads'
# picks while they're still in flight, so under concurrent load Gemini can
# (and did — "Jian Li" on nearly every hero in one pull) converge on the
# same name across the whole batch. This in-process registry of "names
# claimed by a still-running batch" closes that gap; the DB recheck below
# is the final guarantee in case the registry still missed a collision.
_names_in_flight = set()
_names_in_flight_lock = threading.Lock()

def finalize_hero_async(hero_id: int, birth_star: int, aptitudes: dict, extra_prompt: str,
                         needs_custom_portrait: bool, fallback_gender: str, fallback_portrait_prompt: str):
    """
    Call the LLM in the background and enrich the hero's name/lore once it
    responds. Runs after the pull has already returned to the player.
    """
    def _run():
        claimed_name = None
        try:
            for attempt in range(2):
                extra = extra_prompt
                with _names_in_flight_lock:
                    in_flight = [n for n in _names_in_flight]
                if in_flight:
                    extra = (extra or "") + (
                        f"\nAnother hero in this same batch was just given one of these names — "
                        f"do NOT reuse them or close variants: {', '.join(in_flight)}."
                    )
                profile = generate_hero_profile(birth_star, aptitudes, extra)

                with db() as conn:
                    exists = conn.execute("SELECT 1 FROM heroes WHERE name = ? AND id != ?", (profile.name, hero_id)).fetchone()
                
                with _names_in_flight_lock:
                    collides_in_flight = profile.name in _names_in_flight
                    if not exists and not collides_in_flight:
                        _names_in_flight.add(profile.name)
                        claimed_name = profile.name

                if claimed_name:
                    break
                # Collision — try once more with the offending name explicitly banned.
                extra_prompt = (extra_prompt or "") + f"\nThe name \"{profile.name}\" is already taken — pick something else entirely."

            if claimed_name is None:
                # Both attempts collided — guarantee uniqueness with a suffix
                # rather than silently leaving a duplicate name in the roster.
                base_name = profile.name
                suffix = 2
                with db() as conn:
                    while conn.execute("SELECT 1 FROM heroes WHERE name = ? AND id != ?", (profile.name, hero_id)).fetchone():
                        profile.name = f"{base_name} {suffix}"
                        suffix += 1
                claimed_name = profile.name

            with db() as conn:
                conn.execute("""
                    UPDATE heroes SET name=?, title=?, backstory=?, personality=?, gender=?, ego_type=?
                    WHERE id=?
                """, (
                    profile.name, profile.title, profile.backstory, profile.personality,
                    getattr(profile, "gender", "unknown"), getattr(profile, "ego_type", None), hero_id
                ))
            if needs_custom_portrait:
                queue_custom_portrait(hero_id, profile.portrait_prompt, profile.name, getattr(profile, "gender", "unknown"))
        except Exception as e:
            print(f"[Gacha] Background LLM profile failed for hero {hero_id}: {e}")
            if needs_custom_portrait:
                queue_custom_portrait(hero_id, fallback_portrait_prompt, f"hero_{hero_id}", fallback_gender)
        finally:
            if claimed_name:
                with _names_in_flight_lock:
                    _names_in_flight.discard(claimed_name)

    threading.Thread(target=_run, daemon=True).start()

class PullRequest(BaseModel):
    count: int = 1

@router.post("/pull")
def pull_heroes(req: PullRequest):
    if req.count < 1 or req.count > 10:
        raise HTTPException(status_code=400, detail="Pull 1-10 heroes at a time")

    cost = 900 if req.count == 10 else 100 * req.count

    with db() as conn:
        base_row = conn.execute("SELECT gems, max_roster_size FROM base WHERE id = 1").fetchone()
        if not base_row or base_row["gems"] < cost:
            raise HTTPException(status_code=400, detail=f"Not enough gems. Need {cost} Gems.")
        roster_count = conn.execute("SELECT COUNT(*) AS c FROM heroes WHERE is_alive = 1").fetchone()["c"]
        max_roster = base_row["max_roster_size"] or 10
        if roster_count + req.count > max_roster:
            room_left = max(0, max_roster - roster_count)
            raise HTTPException(status_code=400, detail=f"Roster is full ({roster_count}/{max_roster}). Only room for {room_left} more — upgrade your base or release/lose heroes first.")
        conn.execute("UPDATE base SET gems = gems - ? WHERE id = 1", (cost,))

    import random
    synergy_group_name = None
    synergy_indices = set()
    synergy_leader_idx = -1
    synergy_theme_desc = ""

    if req.count == 10 and random.random() < 0.25:
        themes = [
            ("The Crimson Vanguard", "wearing identical crimson cloaks and silver armor"),
            ("The Obsidian Order", "clad in heavy dark armor with violet glowing runes"),
            ("The Silent Brotherhood", "wearing dark leather rogue gear with hidden blades"),
            ("The Azure Circle", "wearing elegant blue mage robes with glowing staffs"),
            ("The Ironclads", "massive heavy plate armor and tower shields"),
            ("The Exiled Royalty", "tattered, ruined royal finery and broken crowns"),
            ("The Bloodmoon Sect", "crimson cultist robes with bone masks"),
        ]
        chosen = random.choice(themes)
        synergy_group_name = chosen[0]
        synergy_theme_desc = chosen[1]
        
        num_synergy = random.randint(3, 5)
        synergy_indices = set(random.sample(range(10), num_synergy))
        
        if random.random() < 0.20:
            synergy_leader_idx = random.choice(list(synergy_indices))

    results = []
    rolled_rarities = [pull_rarity() for _ in range(req.count)]
    
    if synergy_group_name:
        follower_rarities = [rolled_rarities[i] for i in synergy_indices if i != synergy_leader_idx]
        max_follower_rarity = max(follower_rarities) if follower_rarities else 1
        rolled_rarities[synergy_leader_idx] = max(rolled_rarities[synergy_leader_idx], max_follower_rarity + 1)
        rolled_rarities[synergy_leader_idx] = min(7, rolled_rarities[synergy_leader_idx])

    for idx in range(req.count):
        birth_star = rolled_rarities[idx]
        is_synergy = idx in synergy_indices
        is_leader = idx == synergy_leader_idx
        current_synergy = synergy_group_name if is_synergy else None

        # ─── Pity system ───
        with db() as conn:
            base_row = conn.execute("SELECT pity_counter, spark_points FROM base WHERE id = 1").fetchone()
            pity = (base_row["pity_counter"] if base_row else 0) or 0
            sparks = (base_row["spark_points"] if base_row else 0) or 0

            pity += 1
            sparks += 1

            # Pity: guaranteed 4★+ after 50 pulls
            if pity >= 50 and birth_star < 4:
                birth_star = 4
                pity = 0  # Reset pity

            # Reset pity on natural 4★+
            if birth_star >= 4:
                pity = 0

            conn.execute("UPDATE base SET pity_counter = ?, spark_points = ? WHERE id = 1",
                         (pity, sparks))

        stats = generate_base_stats(birth_star)
        aptitudes = generate_aptitudes(birth_star)
        
        cached_data = pop_cached_portrait(birth_star)
        old_path, p_gender, p_class = cached_data if cached_data else (None, None, None)
        
        hero_class, hidden_class = assign_class(birth_star)
        if p_class:
            hero_class = p_class
            
        # Assign starting skills and traits
        from services.skills_service import assign_initial_skills
        from services.traits_service import generate_traits
        skills = assign_initial_skills(hero_class, birth_star)
        skills_json = json.dumps(skills)
        traits = generate_traits(birth_star)
        traits_json = json.dumps(traits)

        # Basic stat scaling logic
        # 1-star: 1x, 2-star: 1.5x, 3-star: 2x, 4-star: 3x, 5-star: 4.5x, 6-star: 7x, 7-star: 10x
        multipliers = {1: 1.0, 2: 1.5, 3: 2.0, 4: 3.0, 5: 4.5, 6: 7.0, 7: 10.0}
        mult = multipliers.get(birth_star, 1.0)
        pilot = 1 if can_pilot(hero_class) else 0

        # Force leader to have higher aptitudes to ensure they are visibly stronger
        if is_leader:
            for k in aptitudes:
                aptitudes[k] = min(100, aptitudes[k] + random.randint(10, 20))
            stats["max_hp"] += 25
            stats["hp"] = stats["max_hp"]
            stats["attack"] += 5
            stats["defense"] += 3

        # Build extra LLM prompt context, but don't call the LLM yet — the
        # pull must return instantly, so text generation happens in the
        # background after the hero is already inserted with a placeholder.
        extra_prompt = ""
        if is_synergy:
            extra_prompt = f" Make them a member of {current_synergy}. In the visual prompt, describe them {synergy_theme_desc}."
        if is_leader:
            extra_prompt += " They are the powerful LEADER of this group."
        if p_class:
            extra_prompt += f" This hero's class is {p_class}."
        if p_gender and p_gender != "unknown":
            extra_prompt += f" This hero is {p_gender}."

        profile = build_instant_profile(birth_star, p_gender, synergy_theme_desc if is_synergy else None)

        # Claim cached portrait instantly, or use default placeholder
        if old_path:
            portrait_path = old_path
        else:
            # No cached portrait available — use a default and queue generation
            portrait_path = f"static/portraits/defaults/default_{hero_class.lower().replace(' ', '_')}.png"

        with db() as conn:
            cursor = conn.execute("""
                INSERT INTO heroes (
                    name, title, backstory, personality, portrait_path, gender,
                    birth_star, hero_class, hidden_class, can_pilot, level, skills, traits,
                    hp, max_hp, attack, defense, speed,
                    apt_combat, apt_tactical, apt_survival, apt_mental, apt_leadership,
                    synergy_group, ego_type
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                profile.name, profile.title, profile.backstory,
                profile.personality, portrait_path, getattr(profile, "gender", "unknown"),
                birth_star, hero_class, hidden_class, pilot, 1, skills_json, traits_json,
                stats["hp"], stats["max_hp"], stats["attack"], stats["defense"], stats["speed"],
                aptitudes["apt_combat"], aptitudes["apt_tactical"], aptitudes["apt_survival"],
                aptitudes["apt_mental"], aptitudes["apt_leadership"],
                current_synergy, getattr(profile, "ego_type", None)
            ))
            hero_id = cursor.lastrowid
            
            # Convert cached image to a permanent custom image instantly
            if portrait_path and "cached_" in portrait_path:
                import os, time
                import database
                custom_dir = f"static/portraits/{database.ACTIVE_PROFILE}"
                os.makedirs(custom_dir, exist_ok=True)
                safe_name = profile.name.replace(" ", "_").lower()
                new_path = f"{custom_dir}/custom_hero_{hero_id}_{safe_name}_{int(time.time())}.png"
                try:
                    os.rename(portrait_path, new_path)
                    conn.execute("UPDATE heroes SET portrait_path = ? WHERE id = ?", (new_path, hero_id))
                    conn.execute("DELETE FROM portrait_cache WHERE path = ?", (portrait_path,))
                    portrait_path = new_path
                except Exception as e:
                    print(f"Failed to rename cached portrait: {e}")

            hero = conn.execute("SELECT * FROM heroes WHERE id = ?", (hero_id,)).fetchone()
            results.append(dict(hero))

        # Enrich name/lore via the LLM in the background, and queue a custom
        # portrait too if we never had a cached one to claim.
        finalize_hero_async(
            hero_id, birth_star, aptitudes, extra_prompt,
            needs_custom_portrait="default_" in portrait_path,
            fallback_gender=profile.gender,
            fallback_portrait_prompt=profile.portrait_prompt,
        )

    with db() as conn:
        base_row = conn.execute("SELECT gems FROM base WHERE id = 1").fetchone()
        new_gems = base_row["gems"] if base_row else 0

    return {"pulled": results, "cost": cost, "gems": new_gems}

@router.get("/odds")
def get_odds():
    from services.gacha_service import RARITY_WEIGHTS, TOTAL_WEIGHT
    return {
        str(star): {
            "weight": w,
            "percent": round(w / TOTAL_WEIGHT * 100, 4)
        }
        for star, w in RARITY_WEIGHTS.items()
    }

@router.get("/cache-status")
def cache_status():
    from services.portrait_cache import get_cache_counts
    counts = get_cache_counts()
    return {"available": counts, "total": sum(counts.values())}

@router.get("/class-info")
def class_info():
    from services.class_service import CLASS_ICONS, CLASS_DESCRIPTIONS
    return {"icons": CLASS_ICONS, "descriptions": CLASS_DESCRIPTIONS}


@router.get("/pity-info")
def pity_info():
    """Get current pity counter and spark points."""
    with db() as conn:
        base = conn.execute("SELECT pity_counter, spark_points FROM base WHERE id = 1").fetchone()
        pity = (base["pity_counter"] if base else 0) or 0
        sparks = (base["spark_points"] if base else 0) or 0
    return {
        "pity_counter": pity,
        "pity_threshold": 50,
        "pulls_until_pity": max(0, 50 - pity),
        "spark_points": sparks,
        "spark_threshold": 100,
        "sparks_until_redeem": max(0, 100 - sparks),
    }


@router.post("/spark-redeem")
def spark_redeem():
    """Spend 100 spark points for a guaranteed random 5★ hero."""
    with db() as conn:
        base = conn.execute("SELECT spark_points, gold, max_roster_size FROM base WHERE id = 1").fetchone()
        sparks = (base["spark_points"] if base else 0) or 0
        if sparks < 100:
            raise HTTPException(status_code=400, detail=f"Need 100 spark points. Have {sparks}.")

        roster_count = conn.execute("SELECT COUNT(*) AS c FROM heroes WHERE is_alive = 1").fetchone()["c"]
        max_roster = base["max_roster_size"] or 10
        if roster_count + 1 > max_roster:
            raise HTTPException(status_code=400, detail=f"Roster is full ({roster_count}/{max_roster}). Upgrade your base before redeeming sparks.")

        # Deduct sparks
        conn.execute("UPDATE base SET spark_points = spark_points - 100 WHERE id = 1")

    # Pull a guaranteed 5★ using the normal pull mechanism but overriding rarity
    from services.gacha_service import generate_base_stats, generate_aptitudes
    from services.portrait_cache import pop_cached_portrait, rename_portrait_for_hero, queue_custom_portrait
    from services.class_service import assign_class, can_pilot

    birth_star = 5  # guaranteed 5★
    stats = generate_base_stats(birth_star)
    aptitudes = generate_aptitudes(birth_star)
    
    cached_data = pop_cached_portrait(birth_star)
    old_path, p_gender, p_class = cached_data if cached_data else (None, None, None)
    
    hero_class, hidden_class = assign_class(birth_star)
    if p_class:
        hero_class = p_class
        
    pilot = 1 if can_pilot(hero_class) else 0
    skills = assign_initial_skills(hero_class, birth_star)
    skills_json = json.dumps(skills)
    
    from services.traits_service import generate_traits
    traits = generate_traits(birth_star)
    traits_json = json.dumps(traits)

    extra_prompt = ""
    if p_class:
        extra_prompt += f" This hero's class is {p_class}."
    if p_gender and p_gender != "unknown":
        extra_prompt += f" This hero is {p_gender}."
    profile = build_instant_profile(birth_star, p_gender)

    if old_path:
        portrait_path = old_path
    else:
        portrait_path = f"static/portraits/default_{hero_class.lower().replace(' ', '_')}.png"

    with db() as conn:
        cursor = conn.execute("""
            INSERT INTO heroes (
                name, title, backstory, personality, portrait_path, gender,
                birth_star, hero_class, hidden_class, can_pilot, level, skills, traits,
                hp, max_hp, attack, defense, speed,
                apt_combat, apt_tactical, apt_survival, apt_mental, apt_leadership
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            profile.name, profile.title, profile.backstory,
            profile.personality, portrait_path, getattr(profile, "gender", "unknown"),
            birth_star, hero_class, hidden_class, pilot, 1, skills_json, traits_json,
            stats["hp"], stats["max_hp"], stats["attack"],
            stats["defense"], stats["speed"],
            aptitudes["apt_combat"], aptitudes["apt_tactical"],
            aptitudes["apt_survival"], aptitudes["apt_mental"],
            aptitudes["apt_leadership"],
        ))
        hero_id = cursor.lastrowid
        
        # Convert cached image to a permanent custom image instantly
        if portrait_path and "cached_" in portrait_path:
            import os, time
            import database
            custom_dir = f"static/portraits/{database.ACTIVE_PROFILE}"
            os.makedirs(custom_dir, exist_ok=True)
            safe_name = profile.name.replace(" ", "_").lower()
            new_path = f"{custom_dir}/custom_spark_{hero_id}_{safe_name}_{int(time.time())}.png"
            try:
                os.rename(portrait_path, new_path)
                conn.execute("UPDATE heroes SET portrait_path = ? WHERE id = ?", (new_path, hero_id))
                conn.execute("DELETE FROM portrait_cache WHERE path = ?", (portrait_path,))
                portrait_path = new_path
            except Exception as e:
                print(f"Failed to rename cached portrait: {e}")
                
        hero = conn.execute("SELECT * FROM heroes WHERE id = ?", (hero_id,)).fetchone()

    finalize_hero_async(
        hero_id, birth_star, aptitudes, extra_prompt,
        needs_custom_portrait="default_" in portrait_path,
        fallback_gender=profile.gender,
        fallback_portrait_prompt=profile.portrait_prompt,
    )

    return {"hero": dict(hero), "spark_cost": 100}